/**
 * Derived product version (`bun run scripts/version.ts [--json] [--cwd DIR]`).
 *
 * The git graph is the only source of the version string; nobody types it. The nearest reachable
 * release or candidate tag (`vX.Y.Z` or `vX.Y.Z-rc.N`, annotated, matched by exact shape so an
 * unrelated tag such as an audit baseline is never selected) and the distance to `HEAD` give:
 *
 * | State                                  | Version                                 |
 * | -------------------------------------- | --------------------------------------- |
 * | On a release tag                       | `X.Y.Z`                                 |
 * | On a candidate tag                     | `X.Y.Z-rc.N`                            |
 * | `develop`, N commits past the last tag | `<next patch>-develop.N+<sha8>`         |
 * | Another branch, N commits past the tag | `<next patch>-<branch-slug>.N+<sha8>`   |
 * | Dirty working tree                     | `.dirty` appended to the build metadata |
 *
 * `<next patch>` is the tag's `X.Y.Z` with the patch incremented, so every prerelease built after a
 * tag sorts above that tag and below the next release. Distance counts through ancestry, so a
 * branch cut from a branch sorts above its base. The script fails with exit 1 when git is
 * unavailable, the directory is not a repository or no tag of the right shape is reachable; it
 * never guesses. Consumers: the build, the image build (tag and label), the runtime's health and
 * startup surfaces, the CLI (`--version`) and the release step. Exit 0 with the string (or JSON) on stdout, 1 when no version can be derived, 2 on
 * usage errors.
 */
import path from "node:path";

export interface DerivedVersion {
  readonly version: string;
  /** The tag the version derives from, for example `v1.0.0` or `v1.1.0-rc.2`. */
  readonly tag: string;
  /** Commits between the tag and `HEAD`, counted through ancestry. */
  readonly distance: number;
  /** The full commit SHA of `HEAD`. */
  readonly sha: string;
  /** The branch name, or `detached`. */
  readonly branch: string;
  readonly dirty: boolean;
}

export const VERSION_TAG_PATTERN = /^v(\d+)\.(\d+)\.(\d+)(?:-rc\.(\d+))?$/;

/** The glob `git describe --match` needs; the regular expression above is the real filter. */
const TAG_GLOB = "v[0-9]*.[0-9]*.[0-9]*";

export class VersionUnavailableError extends Error {
  override readonly name = "VersionUnavailableError";
}

function git(cwd: string, args: readonly string[]): string {
  let proc: ReturnType<typeof Bun.spawnSync>;
  try {
    proc = Bun.spawnSync(["git", ...args], { cwd, stdout: "pipe", stderr: "pipe" });
  } catch (error) {
    throw new VersionUnavailableError(
      `git is unavailable: ${error instanceof Error ? error.message : String(error)}`,
    );
  }
  if (proc.exitCode !== 0) {
    throw new VersionUnavailableError(
      `git ${args.join(" ")} failed: ${new TextDecoder().decode(proc.stderr).trim()}`,
    );
  }
  return new TextDecoder().decode(proc.stdout).trim();
}

/** Lower-case, non-alphanumerics folded to one hyphen, trimmed: a SemVer prerelease identifier. */
export function branchSlug(branch: string): string {
  const slug = branch
    .toLowerCase()
    .replace(/[^0-9a-z]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return slug === "" ? "detached" : slug;
}

function branchOf(cwd: string, env: Readonly<Record<string, string | undefined>>): string {
  const name = git(cwd, ["rev-parse", "--abbrev-ref", "HEAD"]);
  if (name !== "HEAD") return name;
  // A detached checkout on a hosted runner still knows the ref it was made from.
  const fromEnvironment = env.GITHUB_REF_NAME;
  return fromEnvironment !== undefined && fromEnvironment !== "" ? fromEnvironment : "detached";
}

export interface DeriveOptions {
  readonly cwd: string;
  readonly env?: Readonly<Record<string, string | undefined>>;
}

export function deriveVersion(options: DeriveOptions): DerivedVersion {
  const { cwd } = options;
  const env = options.env ?? process.env;
  // Resolving HEAD first separates "not a repository" from "no tag": the former is a git error,
  // the latter is the loud refusal below.
  const sha = git(cwd, ["rev-parse", "HEAD"]);
  let described: string;
  try {
    described = git(cwd, ["describe", "--tags", "--long", "--match", TAG_GLOB, "HEAD"]);
  } catch (error) {
    described = `error: ${error instanceof Error ? error.message : String(error)}`;
  }
  // `<tag>-<distance>-g<sha>`; the tag itself may contain hyphens (`v1.1.0-rc.2`).
  const match = /^(.*)-(\d+)-g([0-9a-f]+)$/.exec(described);
  const tag = match?.[1] ?? "";
  const shape = VERSION_TAG_PATTERN.exec(tag);
  if (match === null || shape === null) {
    throw new VersionUnavailableError(
      `no reachable tag of the form vX.Y.Z or vX.Y.Z-rc.N from HEAD (git describe: ${described})`,
    );
  }
  const distance = Number(match[2]);
  const dirty = git(cwd, ["status", "--porcelain", "--untracked-files=no"]) !== "";
  const branch = branchOf(cwd, env);
  const [, major, minor, patch] = shape;
  const sha8 = sha.slice(0, 8);
  let version: string;
  if (distance === 0) {
    version = tag.slice(1) + (dirty ? `+${sha8}.dirty` : "");
  } else {
    const nextPatch = `${major ?? "0"}.${minor ?? "0"}.${String(Number(patch ?? "0") + 1)}`;
    version = `${nextPatch}-${branchSlug(branch)}.${String(distance)}+${sha8}${dirty ? ".dirty" : ""}`;
  }
  return { version, tag, distance, sha, branch, dirty };
}

function main(argv: readonly string[]): number {
  let cwd = path.resolve(import.meta.dir, "..");
  let json = false;
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    const value = argv[i + 1];
    if (arg === "--json") {
      json = true;
    } else if (arg === "--cwd" && value !== undefined) {
      cwd = path.resolve(value);
      i += 1;
    } else {
      console.error(`version: unknown or incomplete argument ${arg ?? ""}`);
      return 2;
    }
  }
  let derived: DerivedVersion;
  try {
    derived = deriveVersion({ cwd });
  } catch (error) {
    console.error(`version: ${error instanceof Error ? error.message : String(error)}`);
    return 1;
  }
  console.log(json ? JSON.stringify(derived) : derived.version);
  return 0;
}

if (import.meta.main) {
  process.exitCode = main(process.argv.slice(2));
}
