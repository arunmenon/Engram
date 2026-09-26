# Consolidation as a separate phase: Supermemory "dreams", Dhravya Shah on dynamic triggering, Rauch's Brain / Hands / Files, Vercel Sandbox Drives

- **URL:** https://x.com/supermemory/status/2103513608399532143 ; https://x.com/DhravyaShah/status/2103522483630739793 ; https://x.com/rauchg/status/2102820148629614685 ; https://x.com/vercel_dev/status/2102791176378352115 ; https://vercel.com/changelog/drives-for-vercel-sandbox-are-now-in-public-beta
- **Type:** X post (x4) + vendor changelog
- **Author / org:** supermemory (company account); Dhravya Shah (supermemory founder, per the existing Supermemory note and his screenshot in images-transcribed.md); Guillermo Rauch (Vercel CEO); Vercel Developers
- **Date:** 2026-09-23 (vercel_dev 16:04 UTC, Rauch 17:59 UTC); 2026-09-25 (supermemory 15:55 UTC, DhravyaShah 16:30 UTC)
- **Retrieved:** 2026-09-26 (local copies: raw/evidence.json, raw/linked_posts.json; changelog fetched with curl and text-extracted; video thumbnail media/2103513608399532143-13_2103485515614056448.jpg, identical to media/linked-13_2103485515614056448.jpg)
- **Cited by evidence:** Consolidation as a separate phase from ingestion / 2026-09-23 rauchg; 2026-09-25 supermemory; 2026-09-25 DhravyaShah. (The fourth item in the trend, 2026-09-24 sergeonsamui on Hippo-memory, has its own note: `github-kitfunso-hippo-memory.md`.)
- **Relevance to a memory stack:** high for architecture (when to consolidate, what the unit is, and how storage is decoupled from the agent runtime), low for evidence strength: none of these sources publishes numbers for consolidation on vs off.

## TL;DR
- **Two-phase write at Supermemory.** "Status done means the chunks are indexed. Memories come from a second phase", where related documents are grouped "so memories form from coherent units, never one isolated write." Unit of consolidation = a group of related documents, not a single write.
- **Trigger, Supermemory:** adaptive. "When you go quiet, or enough new context has piled up, supermemory enters a dream cycle on its own." Shah: not cron, because cron means "lots of spiky traffic on infra"; "Supermemory automatically decides when is the right time to dream and learn." The idle length and the "enough context" amount are not stated.
- **Trigger, Rauch:** fixed schedule. "run a memory consolidation cron job every night ("dreaming")", reading and writing the agent's files "directly without 'booting up' the agent's full computer." Unit = the agent's files (memories, skills, repos) on a detachable Drive.
- **Dream operations (Supermemory):** merge fragments, reweight old facts against everything since, resolve contradictions, derive facts never stated in one place "each traceable to its sources". Output: new memories, a derivation graph, an updating user profile.
- **Drives (Vercel):** persistent storage mounted as a directory in a Sandbox; one read-write mount at a time, many concurrent read-only point-in-time snapshots; up to 4 Drives per sandbox, 1 TiB default, up to 16 TiB. The changelog only describes access by mounting in a sandbox; Rauch says the direct API is coming "very soon".

## What it claims / describes

### 1. @supermemory, 2026-09-25 15:55 UTC (33 likes, 2 reposts, 2 replies, 7,183 views), verbatim
> Usual memory systems learn the moment data flows in, then never look at it again.
>
> @supermemory 𝚍𝚛𝚎𝚊𝚖𝚜.
>
> Status done means the chunks are indexed. Memories come from a second phase, where related documents are grouped so memories form from coherent units, never one isolated write.
>
> When you go quiet, or enough new context has piled up, supermemory enters a dream cycle on its own. During a dream it:
>
> - merges fragments that belong together
> - reweights old facts against everything since
> - resolves contradictions
> - derives facts you never stated in one place, each traceable to its sources
>
> The output is new memories, a graph of derivations between them, and a picture of the user that updates as the evidence changes.
>
> If you use supermemory in any way, this already works. Dream away.

Attached video (thumbnail only stored): a white frame with a small grey label "DREAMING" and the caption "when you go quiet, it dreams". No data. The same post also appears in raw/linked_posts.json as the post Shah links.

### 2. @DhravyaShah, 2026-09-25 16:30 UTC (35 likes, 4 replies, 5,234 views), verbatim, quoting post 1
> dreaming is super powerful
>
> I don't think systems should do it on cron etc basis (lots of spiky traffic on infra). one interesting thing about supermemorys infrastructure is that dreaming is dynamic.
>
> Supermemory automatically decides when is the right time to dream and learn https://t.co/Njx6tpiFvw

### 3. @rauchg, 2026-09-23 17:59 UTC (2,249 likes, 134 reposts, 197 replies, 255,702 views), verbatim
> Muse, Instinct, OpenClaw, Claude Code…
> All successful agents have 3 key components:
>
> 🧠 Brain → model, harness (logic)
> 👐 Hands → tools, computer, browser
> 🗃️ Files → memories, skills, repos
>
> The 'easy' way is to throw all these in 1 stateful computer (a Mac Mini)
>
> Like, you run 𝚌𝚕𝚊𝚞𝚍𝚎 or 𝚏𝚡 in your mac, you keep it running all day with 𝚌𝚊𝚏𝚏𝚎𝚒𝚗𝚊𝚝𝚎, it has storage, and CLIs and apps installed.
>
> But if you want to cost-efficiently run agents in the cloud, you actually start breaking down these parts.
>
> 🧠 The harness can run in Fluid compute. To make it reliable across restarts, rollouts, crashes, you make its event log durable using Workflow.
>
> 👐 The hands can be a dedicated browser fleet like Browserbase/Kernel, a computer like Sandbox, and even more efficient lightweight tools like just-bash.
>
> 🗃️ 🆕 What was missing was a way to also decouple storage. Imagine you want to run a memory consolidation cron job every night ("dreaming"). You can read/write to the files directly without 'booting up' the agent's full computer.
>
> Today we're introducing the perfect companion to Sandbox: Drives. We shipped the computer for agents, now we're giving you the 'external disk' you can attach at will. It's early, and we'll be expanding capabilities here quickly.
>
> Btw, breaking apart the agent into these independent parts not only optimizes costs in a big way, it also *massively* improves security and auditability. I'd argue you can't even run a secure agent otherwise!

Same-author replies (verbatim):
- 19:07 UTC, to @giuseppegurgone: "It's designed and architected that way, we'll be exposing that API very soon. @tomlienard" (the question he answers is not in the capture; that it concerns direct file access without a sandbox is inference).
- 22:37 UTC, to @SeeLos @cramforce: "Running a computer only when needed < (cheaper than) Running a computer all the time. Especially when you only pay for Active CPU cycles on that computer, as is the case with Fluid"
- 20:51 UTC: "@shreypandya @pk_iv "I love hands, I have the best hands"" (no content).

### 4. @vercel_dev, 2026-09-23 16:04 UTC (363 likes, 270,443 views), verbatim (quoted by Rauch)
> Vercel Sandbox now has persistent storage with Drives, in public beta on every plan.
>
> ▪︎ Store agent workspaces, data, models, deps
> ▪︎ Read snapshots across parallel sandboxes
> ▪︎ Mount up to four Drives per sandbox
> ▪︎ Up to 16 TiB per Drive

### 5. Vercel changelog "Drives for Vercel Sandbox are now in public beta" (fetched text)
- "Drives for Vercel Sandbox are now available in public beta on Hobby, Pro, and Enterprise."
- "A Drive is persistent storage that you mount as a directory in a Vercel Sandbox. It isn't tied to a single sandbox, so you can reuse the same Drive across runs and different sandbox instances."
- "Use Drives to preserve an agent's workspace or on-disk memory, or to reuse datasets, models, and dependency trees."
- "A Drive supports one read-write mount at a time. After the Drive has been written to, multiple sandboxes can read from it concurrently by mounting point-in-time, read-only snapshots." "Each snapshot reflects the Drive at the moment it's mounted. Later writes aren't included; mount a new snapshot to access them."
- Limits: up to four Drives per sandbox at separate paths; default max 1 TiB (1 GiB on Hobby), configurable to 16 TiB. Each Drive stays in its creation region; sandboxes that mount it must run there and "can't use failover regions".
- Pricing in `iad1`: storage $0.05 per GB-month, reads $0.0015 per GB, writes $0.004 per GB. Hobby includes 15 GB storage and 30 GB each of reads and writes per month.

Code (verbatim from the changelog):
```ts
import { Sandbox, Drive } from '@vercel/sandbox';

const workspace = await Drive.getOrCreate({
  name: 'agent-workspace',
});

const sandbox = await Sandbox.create({
  mounts: { '/data': workspace },
});
```
```ts
// The Drive must have been written to at least once.
const [reviewSandbox, testSandbox] = await Promise.all([
  Sandbox.create({ mounts: { '/data': workspace.snapshot() } }),
  Sandbox.create({ mounts: { '/data': workspace.snapshot() } }),
]);
```

### When consolidation triggers and what the unit is (side by side)

| system | trigger | unit of consolidation | operations | output | source |
|---|---|---|---|---|---|
| Supermemory "dreams" | adaptive: "when you go quiet, or enough new context has piled up"; system "decides when is the right time" | a group of related documents ("coherent units, never one isolated write") | merge fragments, reweight old facts vs everything since, resolve contradictions, derive cross-document facts with source links | new memories, derivation graph, updating user profile | posts 1-2 |
| Rauch / Vercel layout | fixed: "cron job every night" | the agent's files (memories, skills, repos) on a Drive, accessed without booting the agent's computer | not stated | not stated | post 3 |
| Hippo-memory (for comparison, T4.E2) | SessionEnd hook, daily 6:15am runner, and auto at 50 new memories (`autoSleep.threshold: 50`) | episodic memories clustered by Jaccard >= 0.35, min cluster 2 | decay, replay, extraction, summaries, merge | semantic memories | `github-kitfunso-hippo-memory.md` |
| Hindsight (for comparison, T1) | after every retain, background, default on | batch of new facts, 8 facts per LLM call; recalls related observations (max 512 tokens) | create/update/delete observations with required reason; "PREFER UPDATE OVER CREATE" | observations with `proof_count` | `github-vectorize-io-hindsight.md` |

## Numbers

| metric | value | baseline | setup/benchmark | caveat |
|---|---|---|---|---|
| quality effect of dreaming | not stated | | | no before/after numbers in any post |
| idle time / context volume that triggers a dream | not stated | | | |
| Rauch cron cadence | nightly | | | example, "Imagine you want to..." |
| Drives per sandbox | up to 4 | | changelog | |
| Drive size | 1 TiB default (1 GiB Hobby), up to 16 TiB | | changelog | higher by request |
| read-write mounts per Drive | 1 at a time | | changelog | readers use snapshots |
| Drive pricing (iad1) | $0.05/GB-month, $0.0015/GB read, $0.004/GB write | | changelog | varies by region |
| Hobby allowance | 15 GB storage, 30 GB reads, 30 GB writes per month | | changelog | |
| Hippo sleep consolidation effect (cross-reference) | -3.6 pp hit@5 [-5.8, -1.4] slept vs never-slept | | Hippo's own LongMemEval audit | scorer-dependent; see hippo note |

## Mechanism details you could implement
- **Split ingestion from consolidation.** Ingestion ends when chunks are indexed ("status done"). A separate job forms memories from groups of related documents. Never form a memory from one isolated write (Supermemory's stated rule).
- **Trigger policy options** (from the sources): (a) nightly cron (Rauch); (b) idle-based: user "goes quiet"; (c) volume-based: "enough new context has piled up"; (d) Hippo's concrete numbers for (b)/(c)-style triggers: on session end, daily, or at 50 new memories. Supermemory combines (b) and (c) and argues against (a) for infra load.
- **Dream operations as a checklist:** merge fragments; reweight old facts against newer evidence; resolve contradictions; derive cross-document facts; keep a derivation edge from each derived fact to its sources.
- **Storage decoupling:** keep memory files on storage that a consolidation job can mount without starting the agent runtime. With Drives: one writer (the consolidation job or the agent, not both at once), many readers on point-in-time snapshots. Readers do not see later writes until they remount a new snapshot, which gives a natural "consolidated version" boundary (inference).

## Limitations, caveats, counter-evidence
- No source here publishes an evaluation of consolidation (LongMemEval, LoCoMo, token cost). The trend's watch item remains open.
- The only measured consolidation result in the catalogue is negative: Hippo's own audit found sleep consolidation cost recall (-3.6 pp hit@5 under its declared scorer; "No scorer here shows sleep helping recall"). This weakens the implied claim that a consolidation phase improves memory.
- Supermemory's trigger is described only qualitatively ("go quiet", "enough new context"). Whether adaptive triggering beats cron on quality is not addressed; Shah's argument is about infra load only.
- Rauch's "read/write to the files directly without booting up the agent's full computer" is not what the Drives changelog documents: the changelog describes Drives mounted into a Sandbox. Rauch's reply says the API will be exposed "very soon", so direct access was not available at launch (inference from the reply plus the changelog).
- Drives allow only one read-write mount at a time, so a nightly consolidation job and a live agent writing to the same Drive would conflict (inference from the changelog constraint).
- Supermemory and Vercel are vendors announcing features.

## Takeaways for tuning a memory stack
- Make "indexed" and "consolidated" two distinct states in your pipeline, and consolidate over groups of related items, not one write at a time.
- Choose a trigger explicitly: idle-based plus volume-based (Supermemory, Hippo's 50-memory threshold) or nightly cron (Rauch). If you choose adaptive, instrument it so you can compare against cron on quality, since nobody has published that comparison.
- Keep every derived memory linked to its sources so a later revocation or contradiction can find it (this also serves the staleness/provenance trend).
- Measure consolidation on vs off before trusting it; the one public ablation (Hippo) found it hurt recall.
- If memory lives in files, put it on storage a background job can open without the agent runtime, with a single writer.

## Open questions
- What idle duration and what amount of new context start a Supermemory dream?
- Does dreaming change retrieval quality, and on which benchmark?
- Can Drives be read and written without a Sandbox yet, and at what cost per consolidation run?

---
