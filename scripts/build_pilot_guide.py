"""Refresh the pilot chapter from versioned journey catalogs; no runtime operations."""

from __future__ import annotations

import html
import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUIDE = ROOT / "docs/guide/engram-architecture.html"
CATALOG = ROOT / "docs/review/spanner-compatibility/pilot-discovery-2026-10-15"


def inline(text: str, source: Path) -> str:
    text = html.escape(text)

    def link(match):
        name, target = match.groups()
        if not target.startswith(("https://", "http://", "#")):
            file, sep, anchor = target.partition("#")
            resolved = (source.parent / html.unescape(file)).resolve()
            if not resolved.is_relative_to(ROOT / "docs"):
                target = (
                    "https://github.com/arunmenon/Engram/blob/"
                    "feature/engram-memory-episodes/" + str(resolved.relative_to(ROOT))
                )
            else:
                target = os.path.relpath(resolved, GUIDE.parent)
            target += sep + anchor if sep else ""
        return f'<a href="{html.escape(target, quote=True)}">{name}</a>'

    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", link, text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    return re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)


def catalog(filename: str, prefix: str) -> list[dict]:
    source = CATALOG / filename
    text = source.read_text()
    matches = list(re.finditer(r"^### (" + prefix + r"\d+) — (.+)$", text, re.M))
    rows = []
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[m.end() : end].split("\n## ")[0].strip()
        families = list(re.finditer(r"^## (.+)$", text[: m.start()], re.M))
        family = families[-1].group(1)
        paragraphs = []
        for paragraph in body.split("\n\n"):
            if paragraph.strip():
                paragraphs.append("<p>" + inline(paragraph.strip(), source) + "</p>")
        rows.append(
            {"id": m.group(1), "title": m.group(2), "family": family, "detail": "".join(paragraphs)}
        )
    return rows


def main():
    entries = {
        "a": catalog("tenant-a-discovery.md", "A-"),
        "b": catalog("tenant-b-discovery.md", "B"),
        "c": catalog("shared-coverage-discovery.md", "C"),
    }
    assert [len(entries[x]) for x in ("a", "b", "c")] == [25, 24, 18]
    teaching = json.loads((GUIDE.parent / "pilot-journey-explanations.json").read_text())
    for key in ("a", "b", "c"):
        for row in entries[key]:
            row.update(teaching[row["id"]])
    template = (GUIDE.parent / "pilot-chapter.html").read_text()
    data = json.dumps(entries, ensure_ascii=False).replace("</", "<\\/")
    chapter = template.replace("@@PILOT_DATA@@", data)
    source = GUIDE.read_text()
    source = re.sub(r"<!-- pilot:start -->.*?<!-- pilot:end -->", "", source, flags=re.S)
    source = source.replace(
        "</main>", "<!-- pilot:start -->" + chapter + "<!-- pilot:end --></main>", 1
    )
    titles = re.findall(r'<section\b[^>]*class="page"[^>]*data-title="([^"]+)"', source)
    assert len(titles) == 27, len(titles)
    options = "".join(
        f'<option value="{i}">{i + 1}. {title}</option>' for i, title in enumerate(titles)
    )
    source = re.sub(
        r'(<select id="jump"[^>]*>).*?(</select>)',
        lambda m: m[1] + options + m[2],
        source,
        count=1,
        flags=re.S,
    )
    GUIDE.write_text(source)
    print(f"Built 27-page guide: 25 A journeys, 24 B journeys, 18 shared probes. {GUIDE}")


if __name__ == "__main__":
    main()
