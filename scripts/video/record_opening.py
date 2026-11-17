"""Engram opening recorder, adapted from ship-manager's record_journey.py.

Uses isolated Chromium captures, macOS say and ffmpeg. Each scene is finalized
separately and its narration is delayed until navigation has completed. No
application data is seeded or changed. Run with Python + playwright installed.
"""

import json
import subprocess
import time
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "output/video" / ("opening-" + datetime.now().strftime("%Y%m%d-%H%M%S"))
SCENES = [
    (
        "purpose",
        "What packs do",
        "Engram turns events into connected knowledge. An event is a report of something "
        "that happened. A graph represents things and the relationships between them. But "
        "records alone do not explain what counts as the same thing, which connections "
        "matter, or what a change means. An ontology makes those meanings explicit. A pack "
        "packages that understanding as definitions and rules that Engram can execute. The "
        "framework lets different domains use the same engine while keeping their "
        "interpretation explicit, versioned, and testable.",
    ),
    (
        "composition",
        "Core, add-ons and domain packs",
        "Begin with the shared foundation. Core is always present. It defines common "
        "concepts such as events, and interfaces that domain models can use. Memory and "
        "user are optional packs: memory adds beliefs, goals, and episodes; user adds "
        "profiles and preferences. A domain pack adds the vocabulary and rules of a "
        "business area. A tenant is the tenant context in which a compatible set of packs "
        "is selected. Dependencies and name collisions must be checked across that set. "
        "Pack selection defines the model. Authentication and database boundaries provide "
        "tenant isolation.",
    ),
    (
        "definition",
        "Inside a domain pack",
        "Only now do we introduce a domain example. Imagine an incident reported against a "
        "checkout service. The pack defines Incident and Service, including identity: "
        "incident forty-two in one account must not become incident forty-two in another. "
        "Event contracts define the required fields. Mapping rules create or update the "
        "incident and link it to its service. Lifecycle rules describe permitted state "
        "changes. Retrieval configuration guides which entities and relationships to "
        "consider for a question. Expected answers are reviewed evaluation material "
        "alongside the pack. A pack uses supported engine capabilities; it does not add "
        "arbitrary new processing code.",
    ),
    (
        "processing",
        "How events become answers",
        "Follow the same incident through the runtime. The API checks the event against "
        "admission rules and its contract. Accepted events enter the ledger, the retained "
        "event history. A worker applies mapping rules to build the graph, with evidence "
        "linking the result to its source. Retrieval then uses configured starting points "
        "and relationships to find relevant context. For example: which incidents affect "
        "checkout in the US account? Correct identity and retrieval scope matter together. "
        "A plausible connection is not enough. We must check the returned entities against "
        "the answer we intended.",
    ),
    (
        "workbench",
        "Create and test a pack",
        "The workbench is where an operator defines and tests that understanding. Start "
        "with the tenant scope, specifications, interface definitions, and representative "
        "events. The assistant proposes a model and mappings grounded in those inputs. The "
        "operator resolves questions about identity, lifecycle, and trust, then reviews the "
        "questions and expected answers. A sandbox run processes the examples through the "
        "engine. Compare three different things: the model says what is allowed, a mapping "
        "predicts what an event will change, and the observed graph shows what was actually "
        "stored. Passing a syntax check alone does not prove the model answers useful "
        "questions.",
    ),
    (
        "readiness",
        "Review and hand off",
        "A journey is an ordered story of events, checkpoints, and questions. We use "
        "journeys to test how understanding changes over time. Approval identifies a "
        "reviewed version and its evidence. Activation is a separate operational step that "
        "binds the runtime to the approved configuration. Intent readiness is another gate: "
        "the relevant evaluation must pass and be recorded on the target graph. An empty "
        "new tenant can therefore be activated while its intents remain pending. Now enter "
        "the workbench. We will inspect Northstar incident onboarding and run a prepared "
        "software-delivery journey. The assistant examples are saved authoring history; the "
        "sandbox results were freshly executed during recording. No production activation "
        "is shown.",
    ),
]


def run(*args):
    return subprocess.run(args, check=True, capture_output=True, text=True).stdout.strip()


def duration(path):
    return float(
        run(
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "csv=p=0",
            str(path),
        )
    )


def stamp(seconds):
    ms = round(seconds * 1000)
    return f"{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}"


def main():
    OUT.mkdir(parents=True)
    evidence, captions, clips = [], [], []
    offset = 0.0
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            for number, (anchor, label, narration) in enumerate(SCENES, 1):
                scene = OUT / f"{number:02}-{anchor}"
                scene.mkdir()
                audio = scene / "voice.aiff"
                run("say", "-v", "Samantha", "-r", "150", "-o", str(audio), narration)
                speech = duration(audio)
                context = browser.new_context(
                    viewport={"width": 1920, "height": 1080},
                    record_video_dir=str(scene),
                    record_video_size={"width": 1920, "height": 1080},
                )
                page = context.new_page()
                video = page.video
                started = time.monotonic()
                try:
                    page.goto(
                        (ROOT / "docs/engram-pack-framework-overview.html").as_uri(),
                        wait_until="load",
                    )
                    page.get_by_role("link", name=label, exact=True).click()
                    page.locator("#" + anchor).wait_for(state="visible")
                    page.screenshot(path=str(scene / "screen.png"))
                    lead = time.monotonic() - started
                    page.wait_for_timeout(round((speech + 1) * 1000))
                finally:
                    context.close()
                raw = Path(video.path())
                # The video capture clock may start a few frames after new_page.
                # Keep a small lead-in; mux each scene independently to avoid
                # accumulating navigation delays across the whole narration.
                length = duration(raw)
                delay = max(0, length - speech - 1)
                clip = scene / "scene.mp4"
                run(
                    "ffmpeg",
                    "-y",
                    "-v",
                    "error",
                    "-i",
                    str(raw),
                    "-i",
                    str(audio),
                    "-filter_complex",
                    f"[1:a]adelay={round(delay * 1000)}:all=1,apad[a]",
                    "-map",
                    "0:v:0",
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
                    "-movflags",
                    "+faststart",
                    str(clip),
                )
                # Sentence captions use proportional timings within the speech;
                # these are approximate, not word-aligned transcription.
                sentences = [s.strip() + "." for s in narration.split(".") if s.strip()]
                total = sum(len(s) for s in sentences)
                cursor = offset + delay
                for sentence in sentences:
                    end = cursor + speech * len(sentence) / total
                    captions.append(
                        f"{len(captions) + 1}\n{stamp(cursor)} --> {stamp(end)}\n{sentence}\n"
                    )
                    cursor = end
                evidence.append(
                    {
                        "scene": anchor,
                        "raw": str(raw),
                        "duration": length,
                        "speech_duration": speech,
                        "speech_delay": delay,
                        "action_duration": lead,
                    }
                )
                clips.append(clip)
                offset += length
                print(f"{anchor}: recorded {length:.1f}s", flush=True)
        finally:
            browser.close()
    listing = OUT / "clips.txt"
    listing.write_text("".join(f"file '{p}'\n" for p in clips))
    final = OUT / "engram-opening-narrated.mp4"
    join_clips(clips, final)
    (OUT / "captions.srt").write_text("\n".join(captions))
    (OUT / "transcript.txt").write_text("\n\n".join(s[2] for s in SCENES))
    (OUT / "manifest.json").write_text(
        json.dumps(
            {
                "voice": "Samantha (synthetic)",
                "caption_timing": "sentence-level approximate",
                "scenes": evidence,
            },
            indent=2,
        )
    )
    print(final, flush=True)


def join_clips(clips, output):
    """Decode each input independently; browser clips can change H.264 headers."""
    args = ["ffmpeg", "-y", "-v", "error", "-xerror"]
    for clip in clips:
        metadata = json.loads(
            run("ffprobe", "-v", "error", "-show_streams", "-of", "json", str(clip))
        )
        kinds = {stream["codec_type"] for stream in metadata["streams"]}
        if not {"video", "audio"} <= kinds:
            raise ValueError(f"Missing video or audio in {clip}")
        args += ["-threads", "2", "-i", str(clip)]
    filters = []
    for i in range(len(clips)):
        filters += [
            f"[{i}:v]setpts=PTS-STARTPTS,setsar=1[v{i}]",
            f"[{i}:a]asetpts=PTS-STARTPTS[a{i}]",
        ]
    filters += [
        "".join(f"[v{i}][a{i}]" for i in range(len(clips))) + f"concat=n={len(clips)}:v=1:a=1[v][a]"
    ]
    args += [
        "-filter_complex_threads",
        "1",
        "-filter_complex",
        ";".join(filters),
        "-map",
        "[v]",
        "-map",
        "[a]",
        "-c:v",
        "libx264",
        "-threads",
        "2",
        "-preset",
        "fast",
        "-crf",
        "20",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-movflags",
        "+faststart",
        str(output),
    ]
    run(*args)


if __name__ == "__main__":
    main()
