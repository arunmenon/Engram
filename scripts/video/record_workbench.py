"""Record the actual saved workbench, refresh sandbox evidence, narrate results.

Uses the existing local operator credential privately. Raw capture includes a
masked login and waits; only explicitly marked scene windows enter final video.
"""

import json
import sys
import time
from datetime import datetime
from pathlib import Path

from playwright.sync_api import expect, sync_playwright
from record_opening import ROOT, duration, join_clips, run, stamp

OUT = ROOT / "output/video" / ("workbench-" + datetime.now().strftime("%Y%m%d-%H%M%S"))


class Capture:
    def __init__(self, page):
        self.page = page
        self.epoch = time.monotonic()
        self.scenes = []

    def scene(self, name, words, action=lambda: None):
        folder = OUT / name
        folder.mkdir()
        voice = folder / "voice.aiff"
        run("say", "-v", "Samantha", "-r", "150", "-o", str(voice), words)
        speech = duration(voice)
        start = time.monotonic() - self.epoch
        action()
        self.page.screenshot(path=str(folder / "screen.png"))
        delay = time.monotonic() - self.epoch - start
        self.page.wait_for_timeout(round((speech + 0.5) * 1000))
        end = time.monotonic() - self.epoch
        self.scenes.append(
            dict(
                name=name,
                text=words,
                start=start,
                end=end,
                delay=delay,
                speech=speech,
                folder=str(folder),
            )
        )
        print(f"Recorded {name}", flush=True)
        (OUT / "scenes.json").write_text(json.dumps(self.scenes, indent=2))

    def finish(self, raw):
        clips, captions = [], []
        offset = 0
        for s in self.scenes:
            folder = Path(s["folder"])
            clip = folder / "scene.mp4"
            length = s["end"] - s["start"]
            run(
                "ffmpeg",
                "-y",
                "-v",
                "error",
                "-ss",
                str(s["start"]),
                "-i",
                str(raw),
                "-i",
                str(folder / "voice.aiff"),
                "-filter_complex",
                f"[1:a]adelay={round(s['delay'] * 1000)}:all=1,apad[a]",
                "-map",
                "0:v",
                "-map",
                "[a]",
                "-t",
                str(length),
                "-c:v",
                "libx264",
                "-preset",
                "fast",
                "-crf",
                "20",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                str(clip),
            )
            clips.append(clip)
            sentences = [v.strip() + "." for v in s["text"].split(".") if v.strip()]
            total = sum(map(len, sentences))
            cursor = offset + s["delay"]
            for sentence in sentences:
                end = cursor + s["speech"] * len(sentence) / total
                captions.append(
                    f"{len(captions) + 1}\n{stamp(cursor)} --> {stamp(end)}\n{sentence}\n"
                )
                cursor = end
            offset += duration(clip)
        listing = OUT / "clips.txt"
        listing.write_text("".join(f"file '{p}'\n" for p in clips))
        join_clips(clips, OUT / "engram-workbench-narrated.mp4")
        (OUT / "captions.srt").write_text("\n".join(captions))
        (OUT / "transcript.txt").write_text("\n\n".join(s["text"] for s in self.scenes))
        print("FINAL " + str(OUT / "engram-workbench-narrated.mp4"), flush=True)


def main():
    OUT.mkdir(parents=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            record_video_dir=str(OUT / "raw"),
            record_video_size={"width": 1920, "height": 1080},
        )
        page = ctx.new_page()
        video = page.video
        cap = Capture(page)
        try:
            page.goto("http://127.0.0.1:5174/workbench.html")
            page.get_by_label("Operator access token").fill(
                (ROOT / ".workbench/dev-token").read_text().strip()
            )
            page.get_by_role("button", name="Open workspace").click()
            page.get_by_text("Northstar Payments — incident pilot", exact=True).wait_for()

            def nav(name):
                page.get_by_role("navigation").get_by_role("button", name=name).click()
                page.get_by_role("heading", name=name, exact=True).wait_for()
                page.get_by_role("heading", name=name, exact=True).evaluate(
                    "el => el.scrollIntoView({block: 'start'})"
                )

            def focus(locator):
                locator.evaluate("el => el.scrollIntoView({block: 'start'})")

            def all_customers():
                page.get_by_role("button", name="All tenants").click()
                page.get_by_text("Northstar Payments — incident pilot", exact=True).wait_for()

            def open_northstar():
                page.get_by_text("Northstar Payments — incident pilot", exact=True).click()
                nav("Tenant setup")

            if "--resume-after-examples" not in sys.argv:
                cap.scene(
                    "01-tenants",
                    "This is the operator workbench. A tenant draft brings together "
                    "source material, "
                    "a proposed pack, questions, and test evidence. Prepared stories "
                    "let us explore an "
                    "existing model before authoring our own. These workspaces are "
                    "separate from deployed "
                    "tenants. Creating a draft does not provision a production database or "
                    "activate a tenant.",
                )
                cap.scene(
                    "02-tenant-scope",
                    "Northstar is a synthetic incident example for a payments business. Its "
                    "scope is deliberately "
                    "narrow: checkout incidents in US and EU accounts. The environment labels "
                    "this training draft. "
                    "The operator also decides whether its inputs may be sent to the "
                    "configured model. "
                    "Permission and sensitivity review happen before requesting authoring.",
                    open_northstar,
                )

                def packs():
                    page.get_by_text(
                        "Advanced · existing packs and optional roots", exact=True
                    ).click()
                    focus(
                        page.get_by_text("Advanced · existing packs and optional roots", exact=True)
                    )

                cap.scene(
                    "03-pack-selection",
                    "A tenant can compose a domain pack with shared foundations. "
                    "Core is required. "
                    "Memory and user are optional. This incident model does not need "
                    "those add-ons. "
                    "The selected bundle must have compatible dependencies and names. Runtime "
                    "authentication "
                    "and database binding are separate controls.",
                    packs,
                )
                cap.scene(
                    "04-grounding-inputs",
                    "Authoring begins with evidence. Specifications explain the business "
                    "rules. Interface "
                    "schemas define available fields. Sample events show concrete values "
                    "and missing-field "
                    "cases. This draft has three saved sources. The assistant uses them to "
                    "propose a model; "
                    "it cannot infer reliable identities from a few example names alone.",
                    lambda: nav("What describes their world?"),
                )
                cap.scene(
                    "05-saved-assistant-model",
                    "This is saved assistant-authored work, not a new model call in this scene. "
                    "Incident identity "
                    "includes account and incident ID. Service identity includes account and "
                    "name. That keeps "
                    "two checkout services in different accounts distinct. The diagram "
                    "describes allowed "
                    "relationships. It does not show a graph stored by a test run.",
                    lambda: nav("How Engram understands them"),
                )
                page.get_by_role("button", name="Check this pack with Engram", exact=True).click()
                expect(
                    page.get_by_role("button", name="Check this pack with Engram", exact=True)
                ).to_be_enabled(timeout=120000)
                cap.scene(
                    "06-model-decisions",
                    "The operator reviews the evidence, assumptions, and limitations. Identity "
                    "and lifecycle "
                    "are consequential decisions. A pack check verifies supported structure and "
                    "references; "
                    "it does not prove that the tenant model is correct. The current model "
                    "has been checked "
                    "again against this engine before refreshing its examples.",
                    lambda: focus(
                        page.get_by_text("Decisions to review · 0 unanswered", exact=True)
                    ),
                )
                cap.scene(
                    "07-reviewed-answers",
                    "Questions make the intended answers explicit. Here the operator "
                    "selects readable "
                    "incident names from the samples. US checkout and EU checkout have "
                    "different starting "
                    "services and different expected incidents. These expectations "
                    "are reviewed before "
                    "execution. Explicit starting points restrict discovery; they do not "
                    "establish a security boundary.",
                    lambda: nav("Questions to answer"),
                )
                nav("Test with examples")
                button = page.get_by_role("button", name="Run the examples", exact=True)
                expect(button).to_be_enabled(timeout=30000)
                cap.scene(
                    "08-start-examples",
                    "We now run the reviewed examples in a dedicated Spanner sandbox. "
                    "This exercises "
                    "processing, stored graph changes, and the reviewed questions. "
                    "The waiting period "
                    "is shortened in this video. No production tenant is activated.",
                    lambda: button.click(),
                )
                expect(button).to_be_enabled(timeout=900000)
                report = page.locator("main").inner_text()
                (OUT / "northstar-result.txt").write_text(report)
                if "Example checks passed" not in report or "100.0%" not in report:
                    raise RuntimeError(
                        "Northstar run did not produce the expected passing report; "
                        "inspect evidence"
                    )
                cap.scene(
                    "09-example-results",
                    "This fresh run reports an average answer score of one hundred "
                    "percent, against a "
                    "required one hundred percent, on Spanner. Both reviewed "
                    "questions return their "
                    "expected entities. This is evidence for these examples, not a "
                    "guarantee for every "
                    "possible question. The report and stored graph let us investigate a mismatch.",
                    lambda: focus(
                        page.get_by_role("heading", name="Example checks passed", exact=True)
                    ),
                )

            else:
                open_northstar()
                nav("Test with examples")

            def rejected():
                page.get_by_label("Executed event").select_option(index=5)
                focus(page.get_by_label("Executed event"))

            cap.scene(
                "10-rejected-event",
                "The examples include a rejected event. Rejection is an expected outcome here, "
                "so it must remain visible rather than disappearing into a "
                "passing count. The event "
                "selector lets an operator compare handling and the graph after each step.",
                rejected,
            )
            cap.scene(
                "11-handoff",
                "Handoff binds the reviewed pack to its evidence. The composed "
                "bundle is shown here, "
                "along with its change classification. Approval is separate from activation. This "
                "workbench does not restart services or activate tenants. We leave the approval "
                "button untouched during this walkthrough.",
                lambda: nav("Approve and hand off"),
            )
            all_customers()
            page.get_by_text("PDLC · references journey", exact=True).click()
            page.get_by_role("heading", name="Run this story", exact=True).wait_for()
            cap.scene(
                "12-prepared-pdlc",
                "Now compare a prepared software-delivery story. Its ontology, event sequence and "
                "expected outcomes already exist. This reference-boundary story "
                "checks that connected "
                "evidence does not expand into unrelated siblings, and that references preserve "
                "complete identities. It starts with an empty sandbox graph.",
            )
            runbutton = page.get_by_role("button", name="Run story again", exact=True)
            cap.scene(
                "13-run-pdlc",
                "We replay the saved story through the same sandbox workflow. No authoring agent "
                "is needed to execute it. The pack and expected outcomes stay pinned. The database "
                "wait is shortened here; we will inspect the actual completed report.",
                lambda: runbutton.click(),
            )
            expect(runbutton).to_be_enabled(timeout=900000)
            report = page.locator("main").inner_text()
            (OUT / "pdlc-result.txt").write_text(report)
            if "13 passed · 0 failed · 0 unsupported · 0 errors" not in report:
                raise RuntimeError("PDLC run differs from expected report; inspect evidence")
            cap.scene(
                "14-pdlc-results",
                "The fresh reference story reports thirteen passed checks, no failed checks, no "
                "unsupported checks and no errors, on Spanner. These are sandbox semantics. This "
                "report does not verify HTTP authentication or all behavior of a deployed service.",
                lambda: focus(page.get_by_role("heading", name="All checks passed", exact=True)),
            )
            cap.scene(
                "15-pdlc-timeline",
                "The timeline connects each input with its checks and stored graph. We can inspect "
                "one step instead of relying only on the final total. Different prepared stories "
                "cover implementation, planning and release behavior; each needs its own result.",
                lambda: focus(page.get_by_role("heading", name="Story timeline", exact=True)),
            )
            all_customers()
            page.get_by_text(
                "Retry the final ticket-linking event without changing reference-boundary graph",
                exact=True,
            ).click()
            page.get_by_role("heading", name="Run this story", exact=True).wait_for()
            cap.scene(
                "16-agent-authored-story",
                "Ontology authoring changes the model. Story authoring creates examples to test a "
                "model. This separately saved story was created with the assistant in an earlier "
                "session. It adds an exact retry to the reference scenario. We are showing saved "
                "authoring history, not claiming a new generation happened in this recording.",
            )
            cap.scene(
                "17-agent-workflow",
                "The assistant workflow asks for a situation and domain rules, "
                "proposes an outline, "
                "then generates events and expected outcomes after review. The operator resolves "
                "assumptions and reviews answers before saving a new story. The baseline stays "
                "separate. A failing test is a reason to investigate, not to rewrite expectations "
                "until the result turns green.",
                lambda: page.get_by_text(
                    "Create a new story with the assistant", exact=True
                ).click(),
            )
        finally:
            ctx.close()
            browser.close()
        cap.finish(Path(video.path()))


if __name__ == "__main__":
    main()
