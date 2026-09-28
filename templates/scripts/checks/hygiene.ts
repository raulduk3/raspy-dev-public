/**
 * Commit and source hygiene check (`check:hygiene`).
 *
 * Reads the non-merge commits and the added lines between a base reference and `HEAD` and
 * rejects:
 * - `subject-format`: a commit subject that is not `type(scope): summary` with a known type, an
 *   optional lower-case scope, an optional `!`, and a summary of 1 to 72 characters;
 * - `forbidden-token`: a commit subject or body line, or a line added under `src/`, `tests/`,
 *   `scripts/` or `docs/`, that carries a process word, a tool or model name, a session or run
 *   identifier (commit messages only) or a person's name from `PEOPLE`. Trailer lines are exempt
 *   because they legitimately name a co-author. Files whose vocabulary legitimately contains a
 *   token are listed in `EXEMPTIONS`, each with its reason; changing that list is a pull request;
 * - `trailer-attribution`: a `Co-authored-by` trailer whose name or address names a tool or model
 *   (`ATTRIBUTION`), or a commit body line that says it was generated with something. Every
 *   commit is the author's own.
 *
 * Merge commits are exempt: their messages are generated from branch names. The base reference
 * comes from `--base REF`, then `HYGIENE_BASE_REF`, then the merge base with `origin/develop`,
 * then `HEAD~1`; with no parent commit there is nothing to check. Findings name the commit, or
 * the file and line. Deterministic; git only; no network. Exit 0 when clean, 1 when findings
 * exist, 2 on usage or git errors.
 */
import path from "node:path";

export type HygieneFindingCode = "subject-format" | "forbidden-token" | "trailer-attribution";

export interface HygieneFinding {
  readonly code: HygieneFindingCode;
  /** `<sha7>` for a commit finding, `<file>:<line>` for a diff finding. */
  readonly where: string;
  readonly message: string;
}

export interface HygieneOptions {
  readonly cwd: string;
  readonly baseRef?: string | undefined;
}

export interface HygieneResult {
  readonly findings: readonly HygieneFinding[];
  readonly rangeChecked: string | null;
  readonly commitsChecked: number;
  readonly linesChecked: number;
  readonly notes: readonly string[];
}

export const SUBJECT_PATTERN =
  /^(feat|fix|docs|test|refactor|perf|chore|ci)(\([a-z0-9-]+\))?!?: .{1,72}$/;

/** The directories whose added lines are scanned. Everything else is out of scope. */
export const SCANNED_PREFIXES: readonly string[] = ["src/", "tests/", "scripts/", "docs/"];

interface ForbiddenToken {
  readonly name: string;
  readonly pattern: RegExp;
  /** Identifiers are scanned in commit messages only: source fixtures legitimately carry them. */
  readonly commitsOnly?: boolean;
}

/** Names of people that never appear in commits or source. Fill in per repository; configuration, not code. */
export const PEOPLE: readonly string[] = [];

export const FORBIDDEN_TOKENS: readonly ForbiddenToken[] = [
  { name: "chunk-", pattern: /chunk-/i },
  { name: "overseer", pattern: /overseer/i },
  { name: "worker lane", pattern: /worker lane/i },
  { name: "repair r<n>", pattern: /\brepair r\d/i },
  // `subagent_resolve` and the other node identifiers do not match: `_` is a word character.
  { name: "subagent", pattern: /\bsubagents?\b/i },
  { name: "orchestrat", pattern: /orchestrat/i },
  { name: "copilot finding", pattern: /copilot findings?/i },
  { name: "claude", pattern: /claude/i },
  { name: "codex", pattern: /codex/i },
  { name: "gpt-", pattern: /gpt-/i },
  { name: "opus", pattern: /\bopus\b/i },
  { name: "sonnet", pattern: /sonnet/i },
  { name: "fable", pattern: /\bfable\b/i },
  { name: "gemini", pattern: /gemini/i },
  { name: "session id", pattern: /\bagent:[a-z]+:/i, commitsOnly: true },
  {
    name: "run id",
    pattern: /\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b/i,
    commitsOnly: true,
  },
  ...PEOPLE.map((person) => ({ name: person, pattern: new RegExp(`\\b${person}\\b`, "i") })),
];

interface Exemption {
  /** A path prefix; a directory prefix ends with `/`. */
  readonly path: string;
  /** Token names the path may carry, or `"all"`. */
  readonly tokens: readonly string[] | "all";
}

/**
 * Files whose vocabulary legitimately contains a token. One entry, one reason. An entry is not a
 * license for the other tokens: `overseer` in the model catalog is still a finding.
 */
export const EXEMPTIONS: readonly Exemption[] = [
  // The list itself.
  { path: "scripts/checks/hygiene.ts", tokens: "all" },
  // The counterexamples that prove the list is enforced.
  { path: "tests/checks/hygiene.test.ts", tokens: "all" },
];

const TRAILER_LINE =
  /^(co-authored-by|signed-off-by|reviewed-by|acked-by|tested-by|closes|fixes|refs?):/i;
const CO_AUTHOR_TRAILER = /^co-authored-by:\s*(.*)$/i;
/** A co-author name or address that names a tool or model. */
export const ATTRIBUTION = /anthropic|openai|claude|codex|copilot|noreply@/i;
const GENERATED_WITH = /\bgenerated with/i;

function exempt(file: string, token: string): boolean {
  return EXEMPTIONS.some(
    (entry) =>
      (entry.path.endsWith("/") ? file.startsWith(entry.path) : file === entry.path) &&
      (entry.tokens === "all" || entry.tokens.includes(token)),
  );
}

function tokensIn(line: string, scope: "commit" | "source"): string[] {
  return FORBIDDEN_TOKENS.filter(
    (token) => (scope === "commit" || token.commitsOnly !== true) && token.pattern.test(line),
  ).map((token) => token.name);
}

function git(
  cwd: string,
  args: readonly string[],
): { code: number; stdout: string; stderr: string } {
  const proc = Bun.spawnSync(["git", ...args], { cwd, stdout: "pipe", stderr: "pipe" });
  return {
    code: proc.exitCode,
    stdout: new TextDecoder().decode(proc.stdout),
    stderr: new TextDecoder().decode(proc.stderr),
  };
}

function resolvable(cwd: string, ref: string): boolean {
  return git(cwd, ["rev-parse", "--verify", "--quiet", `${ref}^{commit}`]).code === 0;
}

function resolveBase(options: HygieneOptions, notes: string[]): string | null {
  const candidate = options.baseRef?.trim();
  if (candidate !== undefined && candidate !== "" && !/^0+$/.test(candidate)) {
    if (resolvable(options.cwd, candidate)) return candidate;
    notes.push(`base ${candidate} is not resolvable; falling back`);
  }
  if (resolvable(options.cwd, "origin/develop")) {
    const mergeBase = git(options.cwd, ["merge-base", "origin/develop", "HEAD"]);
    if (mergeBase.code === 0 && mergeBase.stdout.trim() !== "") {
      notes.push("base is the merge base with origin/develop");
      return mergeBase.stdout.trim();
    }
  }
  if (resolvable(options.cwd, "HEAD~1")) {
    notes.push("base is HEAD~1");
    return "HEAD~1";
  }
  notes.push("no parent commit; nothing to check");
  return null;
}

/** The commits of a message: subject, then body lines. */
export function checkCommitMessage(sha: string, message: string): HygieneFinding[] {
  const findings: HygieneFinding[] = [];
  const where = sha.slice(0, 7);
  const [subject = "", ...body] = message.replace(/\s+$/, "").split("\n");
  if (!SUBJECT_PATTERN.test(subject)) {
    findings.push({
      code: "subject-format",
      where,
      message: `subject "${subject}" is not \`type(scope): summary\` with a known type and a summary of 1 to 72 characters`,
    });
  }
  const lines = [subject, ...body];
  for (const [index, line] of lines.entries()) {
    const trailerMatch = CO_AUTHOR_TRAILER.exec(line);
    if (trailerMatch !== null) {
      const coAuthor = (trailerMatch[1] ?? "").trim();
      if (ATTRIBUTION.test(coAuthor)) {
        findings.push({
          code: "trailer-attribution",
          where,
          message: `Co-authored-by "${coAuthor}" names a tool or model; the commit is the author's own`,
        });
      }
      continue;
    }
    if (GENERATED_WITH.test(line)) {
      findings.push({
        code: "trailer-attribution",
        where,
        message: `${index === 0 ? "subject" : `body line ${index}`} says it was generated with a tool; the commit is the author's own`,
      });
      continue;
    }
    if (TRAILER_LINE.test(line)) continue;
    for (const token of tokensIn(line, "commit")) {
      findings.push({
        code: "forbidden-token",
        where,
        message: `${index === 0 ? "subject" : `body line ${index}`} carries "${token}"`,
      });
    }
  }
  return findings;
}

/** Every added line of a unified diff under the scanned prefixes, with its file and line. */
export function checkAddedLines(diff: string): { findings: HygieneFinding[]; lines: number } {
  const findings: HygieneFinding[] = [];
  let file: string | null = null;
  let line = 0;
  let scanned = 0;
  for (const raw of diff.split("\n")) {
    if (raw.startsWith("+++ ")) {
      const target = raw.slice(4).trim();
      file = target.startsWith("b/") ? target.slice(2) : null;
      continue;
    }
    if (raw.startsWith("--- ")) continue;
    const hunk = /^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@/.exec(raw);
    if (hunk !== null) {
      line = Number(hunk[1] ?? "0");
      continue;
    }
    if (file === null) continue;
    if (raw.startsWith("+")) {
      const inScope = SCANNED_PREFIXES.some((prefix) => file?.startsWith(prefix) === true);
      if (inScope) {
        scanned += 1;
        for (const token of tokensIn(raw.slice(1), "source")) {
          if (exempt(file, token)) continue;
          findings.push({
            code: "forbidden-token",
            where: `${file}:${line}`,
            message: `added line carries "${token}"`,
          });
        }
      }
      line += 1;
    } else if (!raw.startsWith("-") && !raw.startsWith("\\")) {
      line += 1;
    }
  }
  return { findings, lines: scanned };
}

export function checkHygiene(options: HygieneOptions): HygieneResult {
  const notes: string[] = [];
  const findings: HygieneFinding[] = [];
  const base = resolveBase(options, notes);
  if (base === null) {
    return { findings, rangeChecked: null, commitsChecked: 0, linesChecked: 0, notes };
  }
  const rangeChecked = `${base}..HEAD`;
  const list = git(options.cwd, ["rev-list", "--no-merges", rangeChecked]);
  if (list.code !== 0) {
    throw new Error(`git rev-list ${rangeChecked} failed: ${list.stderr.trim()}`);
  }
  const shas = list.stdout.split("\n").filter((sha) => sha !== "");
  for (const sha of shas) {
    const show = git(options.cwd, ["show", "-s", "--format=%B", sha]);
    if (show.code !== 0) throw new Error(`git show ${sha} failed: ${show.stderr.trim()}`);
    findings.push(...checkCommitMessage(sha, show.stdout));
  }
  const diff = git(options.cwd, [
    "diff",
    "--no-color",
    "--no-ext-diff",
    "--unified=0",
    `${base}...HEAD`,
    "--",
    ...SCANNED_PREFIXES,
  ]);
  if (diff.code !== 0) throw new Error(`git diff ${base}...HEAD failed: ${diff.stderr.trim()}`);
  const added = checkAddedLines(diff.stdout);
  findings.push(...added.findings);
  return {
    findings,
    rangeChecked,
    commitsChecked: shas.length,
    linesChecked: added.lines,
    notes,
  };
}

function main(argv: readonly string[]): number {
  let baseRef: string | undefined = process.env.HYGIENE_BASE_REF;
  let cwd = path.resolve(import.meta.dir, "../..");
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    const value = argv[i + 1];
    if (arg === "--base" && value !== undefined) {
      baseRef = value;
      i += 1;
    } else if (arg === "--cwd" && value !== undefined) {
      cwd = path.resolve(value);
      i += 1;
    } else {
      console.error(`hygiene: unknown or incomplete argument ${arg ?? ""}`);
      return 2;
    }
  }
  let result: HygieneResult;
  try {
    result = checkHygiene({ cwd, baseRef });
  } catch (error) {
    console.error(`hygiene: ${error instanceof Error ? error.message : String(error)}`);
    return 2;
  }
  for (const note of result.notes) console.log(`hygiene: ${note}`);
  console.log(
    `hygiene: checked ${result.commitsChecked} commit(s) and ${result.linesChecked} added line(s) in ${result.rangeChecked ?? "<no range>"}`,
  );
  for (const f of result.findings) console.log(`  ${f.where}  [${f.code}]  ${f.message}`);
  console.log(
    result.findings.length === 0
      ? "hygiene: OK"
      : `hygiene: FAILED with ${result.findings.length} finding(s)`,
  );
  return result.findings.length === 0 ? 0 : 1;
}

if (import.meta.main) {
  process.exitCode = main(process.argv.slice(2));
}
