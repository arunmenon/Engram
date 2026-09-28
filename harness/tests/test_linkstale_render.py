import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from linkstale import render as R  # noqa: E402

TPL = {"question_by_type": {"supersedes": "Does memory B supersede memory A?"},
       "options": {"A": None, "B": None},
       "rubrics": {"supersedes": {"A": "B replaces A", "B": "B does not replace A"}},
       "canary_question": "Which nonce appears in the neighbours?"}
RULE = {"first_person_markers": ["i", "we"], "evaluative_verbs": ["think", "prefer"], "attributed_patterns": [r"\b\w+ said\b"]}
ITEM = {"item_id": "t1", "thread_id": "th1", "decision_type": "supersedes", "targets": {"A": "a", "B": "b"}, "snapshot_excerpt": None,
        "neighbours": [{"text": f"Neighbour {i}. I think it is fine.", "originating_event_type": "user.message"} for i in range(5)]}


def test_arms_share_question_and_neighbour_text():
    rule = R.load_opinion_rule.__wrapped__(RULE) if hasattr(R.load_opinion_rule, "__wrapped__") else None
    import re
    RULE["_compiled"] = [re.compile(p, re.IGNORECASE) for p in RULE["attributed_patterns"]]
    reqs = {arm: R.render_request(TPL, ITEM, arm, ITEM["neighbours"], RULE, False, "m") for arm in ("A", "B", "C1", "C2")}
    qs = {json.dumps(r["questions"], sort_keys=True) for r in reqs.values()}
    assert len(qs) == 1
    assert "neighbours" not in reqs["A"]["state"] and "neighbours_text" not in reqs["A"]["state"]
    b = R.strip_labels(reqs["B"]["state"]["neighbours_text"])
    assert R.strip_labels(reqs["C1"]["state"]["neighbours"]) == b
    assert R.strip_labels(reqs["C2"]["state"]["neighbours"]) == b
    c2 = reqs["C2"]["state"]["neighbours"][0]
    assert c2["source_class"] == "user-stated"
    assert any(s["unverified"] for s in c2["sentences"])
