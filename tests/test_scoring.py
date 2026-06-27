import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from scoring import (
    calculate_score,
    DIM_QUESTIONS,
    DIM_MAX_RAW,
    RED_FLAG_QUESTIONS,
    DIM_WEIGHTS,
    BUSINESS_TYPE_WEIGHTS,
    ALL_DIMENSIONS,
)

# v2 constants
MAX_RAW = DIM_MAX_RAW   # 18  (6 questions × max 3)
RED_BOUNDARY = 33.3     # pct <= 33.3 → RED
YELLOW_BOUNDARY = 66.7  # pct <= 66.7 → YELLOW


def _make_answers(default_score=3):
    """Build a full 42-answer dict (6 questions × 7 dims) set to default_score."""
    answers = {}
    for questions in DIM_QUESTIONS.values():
        for q in questions:
            answers[q] = default_score
    return answers


# ─────────────────────────────────────────────
# Basic scenarios
# ─────────────────────────────────────────────

class TestBasicScenarios:
    def test_all_max_scores_is_strong(self):
        answers = _make_answers(3)
        result = calculate_score(answers)
        assert result["grade"] == "STRONG"
        assert result["overall"] == 100.0
        for d in ALL_DIMENSIONS:
            assert result["dim_light"][d] == "GREEN"
            assert result["dim_raw"][d] == MAX_RAW     # 18
            assert result["dim_pct"][d] == 100.0
        assert result["red_count"] == 0
        assert result["red_flags"] == []

    def test_all_zero_scores_is_critical(self):
        answers = _make_answers(0)
        result = calculate_score(answers)
        assert result["grade"] == "CRITICAL"
        assert result["overall"] == 0.0
        for d in ALL_DIMENSIONS:
            assert result["dim_light"][d] == "RED"
            assert result["dim_raw"][d] == 0
        assert result["red_count"] == 7

    def test_all_ones(self):
        answers = _make_answers(1)
        result = calculate_score(answers)
        # raw=6 per dim → pct=33.3 → RED (<=33.3 per spec v2)
        for d in ALL_DIMENSIONS:
            assert result["dim_pct"][d] == pytest.approx(33.3, abs=0.1)
            assert result["dim_light"][d] == "RED"
        assert result["overall"] == pytest.approx(33.3, abs=0.1)
        assert result["grade"] == "CRITICAL"

    def test_all_twos(self):
        answers = _make_answers(2)
        result = calculate_score(answers)
        # raw=12 per dim → pct=66.7 → YELLOW (<=66.7 per spec v2)
        for d in ALL_DIMENSIONS:
            assert result["dim_pct"][d] == pytest.approx(66.7, abs=0.1)
            assert result["dim_light"][d] == "YELLOW"
        assert result["overall"] == pytest.approx(66.7, abs=0.1)
        assert result["grade"] == "WATCH"


# ─────────────────────────────────────────────
# Traffic light threshold boundaries (pct-based, v2)
# ─────────────────────────────────────────────

class TestTrafficLightThresholds:
    def test_raw_6_is_red(self):
        """raw=6 → pct=33.3 → RED (boundary)"""
        answers = _make_answers(3)
        for q in DIM_QUESTIONS["D1"]:
            answers[q] = 1   # 6 × 1 = 6
        result = calculate_score(answers)
        assert result["dim_raw"]["D1"] == 6
        assert result["dim_pct"]["D1"] == pytest.approx(33.3, abs=0.1)
        assert result["dim_light"]["D1"] == "RED"

    def test_raw_5_is_red(self):
        """raw=5 → pct=27.8 → RED"""
        answers = _make_answers(3)
        qs = DIM_QUESTIONS["D1"]
        for q in qs[:5]:
            answers[q] = 1
        answers[qs[5]] = 0
        result = calculate_score(answers)
        assert result["dim_raw"]["D1"] == 5
        assert result["dim_light"]["D1"] == "RED"

    def test_raw_7_is_yellow(self):
        """raw=7 → pct=38.9 → YELLOW"""
        answers = _make_answers(3)
        qs = DIM_QUESTIONS["D1"]
        for q in qs[:5]:
            answers[q] = 1
        answers[qs[5]] = 2
        result = calculate_score(answers)
        assert result["dim_raw"]["D1"] == 7
        assert result["dim_pct"]["D1"] == pytest.approx(38.9, abs=0.1)
        assert result["dim_light"]["D1"] == "YELLOW"

    def test_raw_12_is_yellow(self):
        """raw=12 → pct=66.7 → YELLOW (upper YELLOW boundary)"""
        answers = _make_answers(3)
        for q in DIM_QUESTIONS["D1"]:
            answers[q] = 2   # 6 × 2 = 12
        result = calculate_score(answers)
        assert result["dim_raw"]["D1"] == 12
        assert result["dim_pct"]["D1"] == pytest.approx(66.7, abs=0.1)
        assert result["dim_light"]["D1"] == "YELLOW"

    def test_raw_13_is_green(self):
        """raw=13 → pct=72.2 → GREEN"""
        answers = _make_answers(3)
        qs = DIM_QUESTIONS["D1"]
        for q in qs[:5]:
            answers[q] = 2
        answers[qs[5]] = 3
        result = calculate_score(answers)
        assert result["dim_raw"]["D1"] == 13
        assert result["dim_pct"]["D1"] == pytest.approx(72.2, abs=0.1)
        assert result["dim_light"]["D1"] == "GREEN"

    def test_raw_18_is_green(self):
        """raw=18 → pct=100.0 → GREEN"""
        answers = _make_answers(3)
        result = calculate_score(answers)
        assert result["dim_raw"]["D1"] == 18
        assert result["dim_pct"]["D1"] == 100.0
        assert result["dim_light"]["D1"] == "GREEN"


# ─────────────────────────────────────────────
# Red Flag rules
# ─────────────────────────────────────────────

class TestRedFlags:
    def test_d1_red_flag_forces_red(self):
        """Q1.1=0 forces D1 to RED even if total is high"""
        answers = _make_answers(3)
        answers["1.1"] = 0
        result = calculate_score(answers)
        # raw = 15 (0+3+3+3+3+3), pct=83.3 → would be GREEN without flag
        assert result["dim_raw"]["D1"] == 15
        assert result["dim_light"]["D1"] == "RED"
        assert "D1" in result["red_flags"]

    def test_d2_red_flag(self):
        answers = _make_answers(3)
        answers["2.1"] = 0
        result = calculate_score(answers)
        assert result["dim_light"]["D2"] == "RED"
        assert "D2" in result["red_flags"]

    def test_d3_red_flag(self):
        answers = _make_answers(3)
        answers["3.1"] = 0
        result = calculate_score(answers)
        assert result["dim_light"]["D3"] == "RED"
        assert "D3" in result["red_flags"]

    def test_d4_red_flag(self):
        answers = _make_answers(3)
        answers["4.1"] = 0
        result = calculate_score(answers)
        assert result["dim_light"]["D4"] == "RED"
        assert "D4" in result["red_flags"]

    def test_d5_red_flag(self):
        answers = _make_answers(3)
        answers["5.1"] = 0
        result = calculate_score(answers)
        assert result["dim_light"]["D5"] == "RED"
        assert "D5" in result["red_flags"]

    def test_d6_red_flag_is_q62(self):
        """D6 red flag is Q6.2, not Q6.1"""
        answers = _make_answers(3)
        answers["6.2"] = 0
        result = calculate_score(answers)
        assert result["dim_light"]["D6"] == "RED"
        assert "D6" in result["red_flags"]

    def test_d6_q61_zero_is_not_red_flag(self):
        """Q6.1=0 is NOT a red flag for D6"""
        answers = _make_answers(3)
        answers["6.1"] = 0
        result = calculate_score(answers)
        assert "D6" not in result["red_flags"]
        assert result["dim_light"]["D6"] == "GREEN"

    def test_d7_both_red_flags(self):
        """D7 has two red flags: Q7.1 and Q7.2"""
        answers = _make_answers(3)
        answers["7.1"] = 0
        result = calculate_score(answers)
        assert result["dim_light"]["D7"] == "RED"
        assert "D7" in result["red_flags"]

        answers2 = _make_answers(3)
        answers2["7.2"] = 0
        result2 = calculate_score(answers2)
        assert result2["dim_light"]["D7"] == "RED"
        assert "D7" in result2["red_flags"]

    def test_red_flag_score_1_does_not_trigger(self):
        """Score 1 (not 0) should NOT trigger red flag"""
        answers = _make_answers(3)
        answers["1.1"] = 1
        result = calculate_score(answers)
        assert "D1" not in result["red_flags"]
        # raw=16 (1+3+3+3+3+3) → pct=88.9 → GREEN
        assert result["dim_raw"]["D1"] == 16
        assert result["dim_light"]["D1"] == "GREEN"


# ─────────────────────────────────────────────
# Composite override (≥3 RED → grade capped at WATCH)
# ─────────────────────────────────────────────

class TestCompositeOverride:
    def test_three_red_dims_caps_at_watch(self):
        """3+ RED dims → grade capped at WATCH even if overall >= 70"""
        answers = _make_answers(3)
        answers["1.1"] = 0  # D1 → RED
        answers["2.1"] = 0  # D2 → RED
        answers["3.1"] = 0  # D3 → RED
        result = calculate_score(answers)
        assert result["red_count"] >= 3
        assert result["grade"] in ("WATCH", "CRITICAL")

    def test_three_red_overall_65_is_watch(self):
        """3 RED + overall in WATCH range → WATCH"""
        answers = _make_answers(2)
        answers["1.1"] = 0
        answers["2.1"] = 0
        answers["3.1"] = 0
        result = calculate_score(answers)
        assert result["red_count"] >= 3
        if result["overall"] >= 40:
            assert result["grade"] == "WATCH"
        else:
            assert result["grade"] == "CRITICAL"

    def test_three_red_overall_below_40_is_critical(self):
        """3 RED + overall < 40 → CRITICAL"""
        answers = _make_answers(1)
        answers["1.1"] = 0
        answers["2.1"] = 0
        answers["3.1"] = 0
        result = calculate_score(answers)
        assert result["red_count"] >= 3
        if result["overall"] < 40:
            assert result["grade"] == "CRITICAL"

    def test_two_red_dims_no_cap(self):
        """Only 2 RED dims → normal grading (no cap)"""
        answers = _make_answers(3)
        answers["1.1"] = 0  # D1 → RED
        answers["2.1"] = 0  # D2 → RED
        result = calculate_score(answers)
        assert result["red_count"] == 2
        assert result["grade"] in ("HEALTHY", "STRONG")


# ─────────────────────────────────────────────
# Overall grade thresholds
# ─────────────────────────────────────────────

class TestGradeThresholds:
    def test_grade_boundaries(self):
        from scoring import _grade
        assert _grade(0, 0) == "CRITICAL"
        assert _grade(39.9, 0) == "CRITICAL"
        assert _grade(40, 0) == "WATCH"
        assert _grade(69.9, 0) == "WATCH"
        assert _grade(70, 0) == "HEALTHY"
        assert _grade(84.9, 0) == "HEALTHY"
        assert _grade(85, 0) == "STRONG"
        assert _grade(100, 0) == "STRONG"

    def test_composite_override_in_grade(self):
        from scoring import _grade
        assert _grade(80, 3) == "WATCH"
        assert _grade(90, 4) == "WATCH"
        assert _grade(30, 3) == "CRITICAL"


# ─────────────────────────────────────────────
# Business type weights
# ─────────────────────────────────────────────

class TestBusinessTypeWeights:
    def test_weights_sum_to_100(self):
        for btype, weights in BUSINESS_TYPE_WEIGHTS.items():
            total = sum(weights.values())
            assert total == pytest.approx(1.0, abs=0.001), f"{btype} weights sum to {total}"

        default_total = sum(DIM_WEIGHTS.values())
        assert default_total == pytest.approx(1.0, abs=0.001)

    def test_different_types_different_overall(self):
        """Same answers, different business types → different overall scores"""
        answers = _make_answers(3)
        for q in DIM_QUESTIONS["D1"]:
            answers[q] = 0   # D1 fully zeroed so weights have impact

        results = {}
        for btype in ["general", "restaurant", "brand", "oem", "startup"]:
            r = calculate_score(answers, btype)
            results[btype] = r["overall"]

        # Restaurant weights D1 at 25% (highest) → lowest overall
        # OEM weights D1 at 15% (lowest) → highest overall among typed
        assert results["restaurant"] < results["oem"]

    def test_business_type_does_not_affect_dim_lights(self):
        """Business type weights affect only overall, NOT per-dim lights"""
        answers = _make_answers(2)
        r_general = calculate_score(answers, "general")
        r_restaurant = calculate_score(answers, "restaurant")
        for d in ALL_DIMENSIONS:
            assert r_general["dim_light"][d] == r_restaurant["dim_light"][d]
            assert r_general["dim_raw"][d] == r_restaurant["dim_raw"][d]
            assert r_general["dim_pct"][d] == r_restaurant["dim_pct"][d]


# ─────────────────────────────────────────────
# Edge cases
# ─────────────────────────────────────────────

class TestEdgeCases:
    def test_missing_answers_default_to_zero(self):
        """Questions not in answers dict should default to 0"""
        answers = {}
        result = calculate_score(answers)
        assert result["overall"] == 0.0
        for d in ALL_DIMENSIONS:
            assert result["dim_raw"][d] == 0

    def test_partial_answers(self):
        """Only some questions answered — rest default to 0"""
        answers = {"1.1": 3, "1.2": 3}
        result = calculate_score(answers)
        # raw=6, pct=33.3 → RED boundary
        assert result["dim_raw"]["D1"] == 6
        assert result["dim_pct"]["D1"] == pytest.approx(33.3, abs=0.1)
        assert result["dim_light"]["D1"] == "RED"

    def test_dim_questions_has_six_per_dim(self):
        """Each dimension must have exactly 6 questions in v2"""
        for dim, questions in DIM_QUESTIONS.items():
            assert len(questions) == 6, f"{dim} has {len(questions)} questions, expected 6"

    def test_total_question_count(self):
        """Total scored questions must be 42"""
        total = sum(len(qs) for qs in DIM_QUESTIONS.values())
        assert total == 42

    def test_dim_max_raw_is_18(self):
        """DIM_MAX_RAW must equal 18 (6 questions × max score 3)"""
        assert DIM_MAX_RAW == 18
