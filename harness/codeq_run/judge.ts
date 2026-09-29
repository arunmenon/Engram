/**
 * E-20260928-19-r2 arm B scorer: genigrep's own JevJudge (engine at da10c5e) over the frozen pool.
 *
 *   GENIGREP_DIR=<genigrep checkout> bun codeq_run/judge.ts <jobs.json> <out.json>
 *
 * jobs.json: [{question_id, question, stage: "files" | "passages", files?: FileItem[], passages?: PassageItem[]}]
 * Only genigrep's engine scoring functions are used (JevClient, JevJudge, DEFAULT_CODE_SEARCH_CONFIG);
 * its MCP server, skill installer and AGENTS.md are not. Every Jev request is logged with its answers,
 * billed input tokens, cost and latency. Sub-questions are empty: the frozen questions carry none.
 */
import { readFileSync, writeFileSync } from "node:fs";

const genigrep = process.env.GENIGREP_DIR;
if (!genigrep) throw new Error("GENIGREP_DIR is not set");
const { JevClient } = await import(`${genigrep}/src/engine/client.ts`);
const { JevJudge } = await import(`${genigrep}/src/engine/code-search/judge.ts`);
const { DEFAULT_CODE_SEARCH_CONFIG } = await import(`${genigrep}/src/engine/code-search/config.ts`);

const apiKey = process.env.TYPESAFE_API_KEY;
if (!apiKey) throw new Error("TYPESAFE_API_KEY is not set");
const model = process.env.JEV_MODEL ?? "jev-1.13.0";

const [jobsPath, outPath] = process.argv.slice(2);
const jobs = JSON.parse(readFileSync(jobsPath!, "utf8"));
const client = new JevClient({ apiKey, model, timeoutMs: 60_000, maxRetries: 4, maxRetryAfterMs: 8_000, concurrency: 16 });

const results: unknown[] = [];
const questionConcurrency = 4;
let next = 0;
async function worker() {
  while (next < jobs.length) {
    const job = jobs[next++];
    const events: unknown[] = [];
    const judge = new JevJudge({
      client,
      config: DEFAULT_CODE_SEARCH_CONFIG,
      signal: new AbortController().signal,
      onEvent: (stage: string, data: Record<string, unknown>) => {
        const { state: _state, ...rest } = data;
        events.push({ stage, ...rest });
      },
    });
    const ctx = { question: job.question, subQuestions: [] as string[] };
    const started = performance.now();
    let scores: Record<string, unknown> = {};
    let error: string | null = null;
    try {
      if (job.stage === "files") {
        scores = Object.fromEntries(await judge.scoreFiles(job.files, ctx));
      } else {
        const passageScores = await judge.scorePassages(job.passages, ctx);
        scores = Object.fromEntries([...passageScores].map(([id, s]) => [id, s.rel]));
      }
    } catch (e) {
      error = String(e);
    }
    results.push({
      question_id: job.question_id, stage: job.stage, tag: job.tag ?? null, scores, error,
      model_reported: judge.model(), stats: judge.stats(), ms: Math.round(performance.now() - started), events,
    });
    process.stderr.write(`${job.question_id} ${job.stage} ${error ? "ERROR " + error : "ok"}\n`);
  }
}
await Promise.all(Array.from({ length: questionConcurrency }, worker));
writeFileSync(outPath!, JSON.stringify(results));
