"""Join verified narrated clips, subtitles and chapter metadata without re-recording."""

import argparse
import json
import re
from pathlib import Path

from record_opening import ROOT, duration, join_clips, run, stamp


def seconds(value):
    h, m, s, ms = map(int, re.split("[:,]", value))
    return h * 3600 + m * 60 + s + ms / 1000


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("opening", type=Path)
    parser.add_argument("workbench", type=Path, nargs="+")
    parser.add_argument("--output", type=Path, help="Directory for this review cut")
    args = parser.parse_args()
    opening = args.opening.resolve()
    workbenches = [p.resolve() for p in args.workbench]
    workbench = workbenches[-1]
    out = (
        args.output.resolve()
        if args.output
        else ROOT / "output/video" / ("assembled-" + workbench.name.removeprefix("workbench-"))
    )
    out.mkdir(parents=True, exist_ok=True)
    folders = [opening, *workbenches]
    videos = [
        opening / "engram-opening-narrated.mp4",
        *[folder / "engram-workbench-narrated.mp4" for folder in workbenches],
    ]
    captions, offset = [], 0.0
    for folder, video in zip(folders, videos, strict=True):
        for block in (folder / "captions.srt").read_text().strip().split("\n\n"):
            lines = block.splitlines()
            a, b = lines[1].split(" --> ")
            captions.append(
                f"{len(captions) + 1}\n{stamp(seconds(a) + offset)} --> "
                f"{stamp(seconds(b) + offset)}\n" + "\n".join(lines[2:])
            )
        offset += duration(video)
    subtitle = out / "engram-walkthrough.srt"
    subtitle.write_text("\n\n".join(captions) + "\n")
    entries, at = [], 0.0
    manifest = json.loads((opening / "manifest.json").read_text())
    for scene in manifest["scenes"]:
        entries.append((at, at + scene["duration"], scene["scene"].title()))
        at += scene["duration"]
    at = duration(videos[0])
    for workbench in workbenches:
        for scene in json.loads((workbench / "scenes.json").read_text()):
            length = duration(Path(scene["folder"]) / "scene.mp4")
            entries.append(
                (at, at + length, scene["name"].split("-", 1)[1].replace("-", " ").title())
            )
            at += length
    metadata = out / "chapters.txt"
    metadata.write_text(
        ";FFMETADATA1\ntitle=Engram operator walkthrough — narrated rehearsal\n"
        + "\n".join(
            f"[CHAPTER]\nTIMEBASE=1/1000\nSTART={round(a * 1000)}\n"
            f"END={round(b * 1000)}\ntitle={name}\n"
            for a, b, name in entries
        )
    )
    listing = out / "clips.txt"
    listing.write_text("".join(f"file '{v}'\n" for v in videos))
    joined = out / "joined.mp4"
    join_clips(videos, joined)
    final = out / "engram-walkthrough.mp4"
    run(
        "ffmpeg",
        "-y",
        "-v",
        "error",
        "-i",
        str(joined),
        "-i",
        str(subtitle),
        "-i",
        str(metadata),
        "-map",
        "0:v",
        "-map",
        "0:a",
        "-map",
        "1:0",
        "-map_metadata",
        "2",
        "-map_chapters",
        "2",
        "-c:v",
        "copy",
        "-c:a",
        "copy",
        "-c:s",
        "mov_text",
        "-metadata:s:s:0",
        "language=eng",
        "-movflags",
        "+faststart",
        str(final),
    )
    (out / "transcript.txt").write_text(
        "\n\n".join((folder / "transcript.txt").read_text() for folder in folders)
    )
    run("ffmpeg", "-v", "error", "-xerror", "-i", str(final), "-f", "null", "-")
    print(final)


if __name__ == "__main__":
    main()
