"""Tests for the FREE-results teasers: hard-floor danger items + the fields the
get_free_results endpoint derives (consequence for top risks)."""
import os, sys
import pytest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import narratives as N
import scoring
from report_model import assemble_report_model

ALL = ["D1","D2","D3","D4","D5","D6","D7"]
QIDS = [f"{d}.{q}" for d in range(1,8) for q in range(1,7)]

class _Cur:
    def fetchone(self): return None
    def fetchall(self): return []
class _DB:
    def execute(self,*a,**k): return _Cur()
    def commit(self): pass
    def close(self): pass

@pytest.fixture(autouse=True)
def _nokey(monkeypatch): monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

def test_hard_floor_labels_cover_all_dims():
    assert sorted(N.HARD_FLOOR_LABELS) == ALL

def test_hard_floor_items_order_limit_dedup_tolerant():
    assert [i["dim"] for i in N.hard_floor_items(["D5","D1","D7"],2)] == ["D5","D1"]
    assert N.hard_floor_items([],2) == []
    assert N.hard_floor_items(["flag D3"],2)[0]["dim"] == "D3"
    assert [i["dim"] for i in N.hard_floor_items(["D2","D2","D4"],2)] == ["D2","D4"]
    for i in N.hard_floor_items(["D6"],2):
        assert i["name"] and i["reason"]

def test_free_teasers_present_for_weak_business():
    answers = {q:0 for q in QIDS}            # all RED -> all red flags
    assessment = {"business_type":"restaurant","business_name":"X","email":"x@x.co"}
    model = assemble_report_model({}, assessment, answers, context={},
                                  assessment_id="A", narr_db=_DB(), bmark_db=_DB())
    hf = N.hard_floor_items(model["red_flags"], 2)
    assert len(hf) == 2 and all(x["reason"] for x in hf)
    # every top risk has a non-empty consequence (the field the endpoint surfaces)
    assert model["top_risks"]
    for d in model["top_risks"][:2]:
        assert model["narratives"][d].get("consequence")
