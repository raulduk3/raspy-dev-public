/** The journal tool: every role reads the owner's plain-text journal; none writes in it.
 *
 * Owner's decision (dev-server decisions.txt, 2026-10-05): all three roles may read ~/journal
 * through this tool; what a role would add goes to the owner's inbox for him to take or drop.
 * Assistant's own dense daily log lives in his memory. The layout read here is dev-server's:
 *   <journal>/log/YYYY/MM/DD.txt      the day's note
 *   <journal>/tasks/open/**           one task per file, its first line is the task
 * Nothing here writes under the journal root, by construction rather than by instruction.
 */
import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";

const ROLE = { assistant: "Assistant", engineer: "Engineer", ops: "Ops" };
const READS = ["tasks", "day", "entries"];
// What each role may add. Every addition is a small file in the inbox, never the journal.
const ALLOWED = {
  assistant: [...READS, "work", "task", "journal-line", "log-append", "log-path"],
  engineer: [...READS, "work"],
  ops: [...READS, "work"],
};
const MAX_READ = 64 * 1024;
const DATE = /^\d{4}-\d{2}-\d{2}$/;

const today = () => new Date().toLocaleDateString("sv-SE");
const stamp = () => {
  const d = new Date();
  return `${d.toLocaleDateString("sv-SE")}-${String(d.getHours()).padStart(2, "0")}${String(d.getMinutes()).padStart(2, "0")}`;
};

function inside(root, file) {
  const real = fs.realpathSync(file);
  const base = fs.realpathSync(root);
  if (real !== base && !real.startsWith(base + path.sep)) throw new Error("path leaves the journal");
  return real;
}

function readBounded(file) {
  const fd = fs.openSync(file, "r");
  try {
    const buffer = Buffer.alloc(MAX_READ);
    const n = fs.readSync(fd, buffer, 0, MAX_READ, 0);
    return buffer.subarray(0, n).toString("utf8") + (fs.fstatSync(fd).size > n ? "\n[cut at 64 KB]" : "");
  } finally { fs.closeSync(fd); }
}

function openTasks(root, limit) {
  const open = path.join(root, "tasks", "open");
  const found = [];
  const walk = dir => {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true }).sort((a, b) => a.name.localeCompare(b.name))) {
      if (entry.name.startsWith(".") || entry.isSymbolicLink()) continue;
      const file = path.join(dir, entry.name);
      if (entry.isDirectory()) walk(file);
      else if (entry.isFile()) found.push(file);
    }
  };
  if (fs.existsSync(open)) walk(open);
  // `task` writes the task on the first line, then "key: value" lines (due, scheduled, priority, tags).
  return found.slice(0, limit).map(file => {
    const [first, ...rest] = readBounded(inside(root, file)).split("\n");
    const item = { task: first.trim(), file: path.relative(root, file) };
    for (const line of rest) {
      const m = /^(due|scheduled|priority|tags):\s*(\S.*)$/.exec(line.trim());
      if (m && !(m[1] in item)) item[m[1]] = m[2].trim().slice(0, 200);
    }
    return item;
  });
}

function dayNote(root, date) {
  const [y, m, d] = date.split("-");
  const file = path.join(root, "log", y, m, `${d}.txt`);
  if (!fs.existsSync(file)) return `No note for ${date}.`;
  return readBounded(inside(root, file));
}

// Work entries are inbox files named <date>-<time>-<role>-work-<id>.txt; Assistant reconciles from them.
function workEntries(inbox, date) {
  if (!fs.existsSync(inbox)) return [];
  return fs.readdirSync(inbox)
    .filter(name => name.startsWith(date) && /-work-[0-9a-f]{6}\.txt$/.test(name))
    .sort()
    .map(name => {
      const fields = Object.fromEntries(readBounded(path.join(inbox, name)).split("\n")
        .map(line => line.match(/^(\w+): (.*)$/)).filter(Boolean).map(m => [m[1], m[2]]));
      return { file: name, ...fields, billable: Boolean(fields.project) };
    });
}

function leave(inbox, role, kind, lines) {
  if (!fs.existsSync(inbox)) throw new Error("the owner's inbox is not reachable from here.");
  const name = `${stamp()}-${role.toLowerCase()}-${kind}-${crypto.randomBytes(3).toString("hex")}.txt`;
  // wx: never replaces anything already in the inbox.
  fs.writeFileSync(path.join(inbox, name), lines.filter(l => l !== undefined).join("\n") + "\n", { flag: "wx", mode: 0o640 });
  return `left in the owner's inbox: ${name}`;
}

export function journalExtension({ root, agent, inbox, memory }) {
  if (!root || !path.isAbsolute(root)) throw new Error("Journal requires an absolute root.");
  if (!inbox || !path.isAbsolute(inbox)) throw new Error("Journal requires an absolute inbox.");
  const role = ROLE[agent];
  const allowed = ALLOWED[agent];
  if (!role || !allowed) throw new Error("Journal requires a known agent role.");
  const personal = agent === "assistant";
  if (personal && (!memory || !path.isAbsolute(memory))) throw new Error("Assistant's log needs his memory folder.");
  const days = personal ? path.join(memory, "days") : null;
  return (pi) => pi.registerTool({
    name: "journal",
    label: "Journal",
    description:
      `the owner's journal, read-only, and his inbox for anything you would add. You never write in his journal.\n` +
      `- tasks: his open tasks.\n- day: his note for a day (date YYYY-MM-DD, default today).\n` +
      `- entries: the work entries the roles left for a day, each with its role, project and minutes. An entry with no project cannot be billed.\n` +
      `- work: record one piece of work you did; it goes to the owner's inbox. Always give a project when the work belongs to one, and minutes when you know them.\n` +
      (personal
        ? `- task: propose a task for the owner (it goes to his inbox).\n- journal-line: propose one summary line for his journal (to his inbox), never in his voice.\n- log-append / log-path: your own dense daily log, in your memory.\n`
        : `Tasks, journal lines and the personal daily log are Assistant's, not yours. Durable reference belongs in your memory.\n`),
    parameters: { type: "object", required: ["action"], properties: {
      action: { type: "string", enum: allowed },
      summary: { type: "string", description: "work: what you did, one sentence" },
      project: { type: "string", description: "work: the project this belongs to, so it can be billed" },
      minutes: { type: "integer", minimum: 1, maximum: 1440, description: "work: time spent" },
      date: { type: "string", description: "day, entries: YYYY-MM-DD; defaults to today" },
      text: { type: "string", description: "task: the task description" },
      due: { type: "string" },
      title: { type: "string", description: "log-append: section title" },
      body: { type: "string", description: "log-append: section body, or journal-line: the line" },
    } },
    async execute(_id, params) {
      const action = params.action;
      if (!allowed.includes(action)) throw new Error(`${action} is not available to ${role}.`);
      const date = params.date ?? today();
      if (!DATE.test(date)) throw new Error("date must be YYYY-MM-DD");
      const one = s => String(s ?? "").replace(/\s+/g, " ").trim().slice(0, 500);
      let text;
      if (action === "tasks") text = JSON.stringify(openTasks(root, 50), null, 1);
      else if (action === "day") text = dayNote(root, date);
      else if (action === "entries") text = JSON.stringify(workEntries(inbox, date), null, 1);
      else if (action === "work") {
        if (!params.summary) throw new Error("A work entry needs a summary.");
        // The role is fixed by the launch, never chosen by the caller.
        text = leave(inbox, role, "work", [`role: ${role}`, `date: ${today()}`, `summary: ${one(params.summary)}`,
          params.project ? `project: ${one(params.project)}` : undefined,
          params.minutes ? `minutes: ${params.minutes}` : undefined]);
      } else if (action === "task") {
        if (!params.text) throw new Error("A task needs a description.");
        text = leave(inbox, role, "task", [one(params.text), params.due ? `due: ${one(params.due)}` : undefined,
          "", "A proposed task: add it with `task` if you want it."]);
      } else if (action === "journal-line") {
        if (!params.body) throw new Error("journal-line needs the single line to propose.");
        text = leave(inbox, role, "journal-line", [one(params.body), "", "A proposed line for today's note."]);
      } else if (action === "log-path") {
        text = path.join(days, `${today()}.md`);
      } else if (action === "log-append") {
        if (!params.title || !params.body) throw new Error("log-append needs a title and a body.");
        fs.mkdirSync(days, { recursive: true, mode: 0o750 });
        const file = path.join(days, `${today()}.md`);
        fs.appendFileSync(file, `\n## ${one(params.title)}\n\n${String(params.body).trim()}\n`, { mode: 0o640 });
        text = `appended to ${file}`;
      }
      return { content: [{ type: "text", text: text || "done" }], details: { journal: true, role } };
    },
  });
}
