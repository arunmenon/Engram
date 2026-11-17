# Engram narrated recording

`record_opening.py` adapts the recording approach in
`ship-manager/walkthrough/videos/record_journey.py` for the Engram study guide.
It records real, isolated Chromium pages at 1920×1080, generates local Samantha
speech, and exports an MP4, sentence-level SRT captions, transcript, screenshots,
and timing manifest to a unique directory under `output/video/`.

Prerequisites: macOS `say` with Samantha, `ffmpeg`, `ffprobe`, and Python Playwright
with its Chromium binary. The rehearsal environment is `/tmp/engram-video-venv`:

```sh
/tmp/engram-video-venv/bin/python scripts/video/record_opening.py
```

To recreate that isolated environment:

```sh
python3 -m venv /tmp/engram-video-venv
/tmp/engram-video-venv/bin/pip install playwright
/tmp/engram-video-venv/bin/python -m playwright install chromium
```

The opening reads the local HTML guide directly. No server, sign-in, screen
sharing, QuickTime, live tenant activation, or desktop recording is needed.
The `SCENES` list pairs each observed navigation link with its narration.
Captions are approximate sentence timings, not forced-aligned speech.

Each scene records independently. Its audio delay is calculated from the final
video duration, speech duration, and one-second tail. This prevents navigation
delays accumulating across scenes. Inspect the exported frames and listen to the
preview before using it as final presentation footage. The opening is a short
rehearsal; workbench chapters require their own scripted steps and checks.

## Workbench chapters

`record_workbench.py` uses the running local UI at `127.0.0.1:5174`, its configured
backend and the existing private `.workbench/dev-token`. It reads the saved
Northstar incident pilot and PDLC reference story through the UI, revalidates
Northstar, and starts fresh Spanner sandbox runs. It does not approve a package
or activate a tenant. The agent material is explicitly narrated as saved history.

```sh
/tmp/engram-video-venv/bin/python scripts/video/record_workbench.py
/tmp/engram-video-venv/bin/python scripts/video/assemble_walkthrough.py \
  output/video/opening-YYYYMMDD-HHMMSS output/video/workbench-YYYYMMDD-HHMMSS
```

The workbench recorder checks expected report text and stops if a run differs;
it does not alter expected answers to make a recording pass. Each exported scene
has its own screenshot and timeline window. Sign-in and long processing waits
are omitted from the edited output. Source raw recordings remain local in that
run directory. The assembly includes selectable English subtitles and chapters.

The assembler accepts multiple workbench directories in playback order for
resumed takes. `record_results_detail.py` and `record_agent_detail.py` capture
closer views of the existing result and saved assistant history without starting
new sandbox or model jobs. Include each replacement scene only once.

Assembly checks every input for both video and audio, decodes each input
independently before joining, and runs a strict full-file decode on the export.
An interrupted recording may have an unfinalized tail; replace that scene rather
than accepting an audio-only clip. Keep the original scene manifest as evidence
when excluding an interrupted or superseded take.

The revised opening uses `docs/engram-pack-framework-overview.html`: six
explanatory screens introduce the purpose, composition, domain definitions,
runtime, workbench and readiness before product footage. The exact narration is
kept in `record_opening.py`. The historical study guide is not changed.

Use `assemble_walkthrough.py --output output/video/<new-cut>` to preserve an
already delivered cut. The November 4 framework revision reuses verified UI
clips and puts handoff last; `workbench-framework-order-20261104/scenes.json`
records the source paths and playback order. Reused footage retains the original
run evidence and does not imply another execution or model call.
