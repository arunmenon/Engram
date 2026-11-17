from pathlib import Path

import record_workbench as r
from playwright.sync_api import sync_playwright

r.OUT = r.OUT.with_name("agent-detail-" + r.OUT.name.removeprefix("workbench-"))
r.OUT.mkdir(parents=True)
words = (
    "The assistant workflow asks for a situation and domain rules, proposes an outline, "
    "then generates events and expected outcomes after review. The operator resolves "
    "assumptions and reviews answers before saving a new story. The baseline stays "
    "separate. A failing test is a reason to investigate, not to rewrite expectations "
    "until the result turns green. This screen contains saved authoring history."
)
with sync_playwright() as p:
    b = p.chromium.launch()
    c = b.new_context(
        viewport={"width": 1920, "height": 1080},
        record_video_dir=str(r.OUT / "raw"),
        record_video_size={"width": 1920, "height": 1080},
    )
    page = c.new_page()
    v = page.video
    cap = r.Capture(page)
    page.goto("http://127.0.0.1:5174/workbench.html")
    page.get_by_label("Operator access token").fill(
        (r.ROOT / ".workbench/dev-token").read_text().strip()
    )
    page.get_by_role("button", name="Open workspace").click()
    page.get_by_text("PDLC · references journey", exact=True).click()
    page.get_by_role("heading", name="Run this story", exact=True).wait_for()

    def action():
        s = page.get_by_text("Create a new story with the assistant", exact=True)
        s.click()
        s.evaluate("el => el.scrollIntoView({block:'start'})")

    cap.scene("17-agent-workflow", words, action)
    c.close()
    b.close()
    cap.finish(Path(v.path()))
