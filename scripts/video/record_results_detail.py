from pathlib import Path

import record_workbench as r
from playwright.sync_api import sync_playwright

r.OUT = r.OUT.with_name("results-detail-" + r.OUT.name.removeprefix("workbench-"))
r.OUT.mkdir(parents=True)
words = (
    "This fresh run reports an average answer score of one hundred percent, against a "
    "required one hundred percent, on Spanner. Both reviewed questions return their "
    "expected entities. This is evidence for these examples, not a guarantee for every "
    "possible question. The report and stored graph let us investigate a mismatch."
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
    page.get_by_text("Northstar Payments — incident pilot", exact=True).click()
    page.get_by_role("navigation").get_by_role("button", name="Test with examples").click()
    page.get_by_role("heading", name="Example checks passed", exact=True).wait_for()

    def action():
        page.get_by_role("heading", name="Example checks passed", exact=True).evaluate(
            "el=>el.scrollIntoView({block:'start'})"
        )

    cap.scene("09-example-results", words, action)
    c.close()
    b.close()
    cap.finish(Path(v.path()))
