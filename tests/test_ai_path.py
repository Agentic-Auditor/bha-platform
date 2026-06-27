"""
Tests for the live AI narrative path (narratives.get_or_generate_narrative),
exercised with call_anthropic monkeypatched so no real API key/network is used.

Locks the v2 anti-hallucination contract:
  * AI output is used for summary/actions/etc.
  * `fact` is ALWAYS overridden deterministically from the answers (the model
    can never inject a hallucinated fact),
  * missing principle_benefit / consequence are backfilled from the static
    libraries,
  * derived fields (detail, cta_flag) are set,
  * any API/parse error falls back to the static narrative.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import narratives as N
from narratives import (get_or_generate_narrative, _fact_sentence, _consequence_text,
                        detect_patterns, DIM_PRINCIPLES)

QIDS = [f"{d}.{q}" for d in range(1, 8) for q in range(1, 7)]


class _FakeCursor:
    def fetchone(self):
        return None

    def fetchall(self):
        return []


class _FakeDB:
    def execute(self, *a, **k):
        return _FakeCursor()

    def commit(self):
        pass

    def close(self):
        pass


def _answers_weak():
    # all-zero -> RED everywhere, gives a non-empty deterministic fact
    return {q: 0 for q in QIDS}


def test_ai_output_used_but_fact_forced_and_v2_backfilled(monkeypatch):
    dim, light = "D1", "RED"
    answers = _answers_weak()
    patterns = detect_patterns(dim, answers)
    context = {"business_type": "restaurant", "age_bucket": "1-3y", "revenue_bucket": "<1M"}

    def fake_call(prompt):
        return {
            "summary": "AI summary line",
            "current_state": "AI current state",
            "root_cause": "AI root cause",
            "whats_working": "AI whats working",
            "actions": ["[สัปดาห์ 1] do x", "[เดือน 1] do y"],
            "industry_context": "AI industry context",
            "fact": "HALLUCINATED 999% growth",   # must be overridden
            "principle_benefit": "",                # empty -> backfilled
            "consequence": "",                      # empty -> backfilled (non-GREEN)
        }

    monkeypatch.setattr(N, "call_anthropic", fake_call)

    n = get_or_generate_narrative(dim, light, patterns, context, _FakeDB(), answers=answers)

    assert n["summary"] == "AI summary line"
    assert n["actions"] == ["[สัปดาห์ 1] do x", "[เดือน 1] do y"]
    # fact is deterministic, never the hallucinated value
    assert n["fact"] == _fact_sentence(dim, answers)
    assert "HALLUCINATED" not in n["fact"]
    # v2 fields backfilled from static libraries when the model omits them
    assert n["principle_benefit"] == DIM_PRINCIPLES[dim]
    assert n["consequence"] == _consequence_text(patterns, light)
    # derived fields
    assert n["detail"] == n["current_state"]
    assert n["cta_flag"] is True  # RED


def test_api_error_falls_back_to_static(monkeypatch):
    dim, light = "D3", "YELLOW"
    answers = {q: 1 for q in QIDS}
    patterns = detect_patterns(dim, answers)
    context = {"business_type": "service"}

    def boom(prompt):
        raise RuntimeError("API down")

    monkeypatch.setattr(N, "call_anthropic", boom)

    n = get_or_generate_narrative(dim, light, patterns, context, _FakeDB(), answers=answers)
    assert n.get("_source") == "static_fallback"
    assert n.get("summary")          # static content present
    assert n.get("fact") == _fact_sentence(dim, answers)
