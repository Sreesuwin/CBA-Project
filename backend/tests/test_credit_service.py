"""Credit engine tests.

The engine is a pure function, so it needs no database or app context - which is
exactly why it can be asserted against the blueprint's worked examples exactly.
"""

from decimal import Decimal

from app.models import Recommendation, RiskLevel
from app.services.credit_service import BASE_SCORE, assess, classify

# The three sample applicants from the project doc's demo section. Their inputs
# are chosen so the officer queue contains a spread of risk bands.
RAHUL = {
    "monthly_income": Decimal("65000"),
    "monthly_expenses": Decimal("26000"),
    "existing_emi": Decimal("8000"),
    "existing_loans": 1,
    "employment_years": 4,
}
ANANYA = {
    "monthly_income": Decimal("90000"),
    "monthly_expenses": Decimal("40000"),
    "existing_emi": Decimal("12000"),
    "existing_loans": 0,
    "employment_years": 7,
}
ARJUN = {
    "monthly_income": Decimal("28000"),
    "monthly_expenses": Decimal("18000"),
    "existing_emi": Decimal("14000"),
    "existing_loans": 3,
    "employment_years": 1,
}


def test_ananya_scores_as_the_blueprint_worked_example():
    result = assess(ANANYA)

    # 300 base +100 income +80 EMI +60 tenure +50 no loans
    assert result["score"] == 590
    assert result["risk"] is RiskLevel.HIGH
    assert result["recommendation"] is Recommendation.MANUAL_REVIEW
    assert result["reasons"] == [
        "High monthly income",
        "Low existing EMI burden",
        "Long employment history",
        "No existing loans",
    ]


def test_rahul_lands_in_the_moderate_score_band():
    result = assess(RAHUL)

    # 300 +70 +80 +40 +20
    assert result["score"] == 510
    assert result["recommendation"] is Recommendation.MANUAL_REVIEW


def test_arjun_is_rejected_by_the_engine():
    result = assess(ARJUN)

    # 300 +40 (minimum income) -50 (heavy EMI) +20 (short tenure) -40 (3 loans)
    assert result["score"] == 270
    assert result["risk"] is RiskLevel.VERY_HIGH
    assert result["recommendation"] is Recommendation.NOT_RECOMMENDED
    assert "High existing EMI burden" in result["reasons"]
    assert "Multiple existing loans" in result["reasons"]


def test_the_engine_ceiling_is_590():
    """A *perfect* applicant still scores 590, never the 700 needed for LOW.

    The blueprint's additive rules cap at 300+100+80+60+50 = 590, so its own
    ``LOW``/``MODERATE`` bands and the ``ELIGIBLE`` recommendation are
    unreachable. This is a flaw in the supplied policy, not in the engine; it is
    kept faithful to the blueprint and recorded in the progress log rather than
    silently "fixed" so the mentor can decide the intended thresholds.
    """
    perfect = assess(
        {
            "monthly_income": Decimal("200000"),
            "monthly_expenses": Decimal("30000"),
            "existing_emi": Decimal("0"),
            "existing_loans": 0,
            "employment_years": 10,
        }
    )

    assert perfect["score"] == 590
    assert perfect["recommendation"] is Recommendation.MANUAL_REVIEW


def test_the_engine_is_deterministic():
    assert assess(RAHUL) == assess(RAHUL)


def test_income_at_the_boundary_uses_the_higher_band():
    at_boundary = assess({**RAHUL, "monthly_income": Decimal("75000")})
    just_above = assess({**RAHUL, "monthly_income": Decimal("75000.01")})

    # 75000 is "Stable income" (+70), 75000.01 is "High monthly income" (+100)
    assert just_above["score"] - at_boundary["score"] == 30


def test_emi_ratio_boundary_is_inclusive_at_20_percent():
    result = assess(
        {"monthly_income": Decimal("100000"), "existing_emi": Decimal("20000")}
    )

    # ratio == 0.20 falls to the middle band (+40), not the low band (+80)
    assert "Low existing EMI burden" not in result["reasons"]


def test_zero_income_does_not_crash_the_engine():
    result = assess({"monthly_income": Decimal("0"), "existing_emi": Decimal("100")})

    assert result["risk"] is RiskLevel.VERY_HIGH  # a missing income is fatal


def test_missing_optional_fields_default_to_zero():
    result = assess({"monthly_income": Decimal("50000")})

    # 300 +70 (stable income) +80 (no EMI) +20 (new) +50 (no loans) = 520
    assert result["score"] == BASE_SCORE + 70 + 80 + 20 + 50
    assert result["recommendation"] is Recommendation.MANUAL_REVIEW


def test_classify_maps_every_band():
    assert classify(700)[0] is RiskLevel.LOW
    assert classify(650)[0] is RiskLevel.MODERATE
    assert classify(550)[0] is RiskLevel.HIGH
    assert classify(499)[0] is RiskLevel.VERY_HIGH
    assert classify(700)[1] is Recommendation.ELIGIBLE
    assert classify(550)[1] is Recommendation.MANUAL_REVIEW
    assert classify(100)[1] is Recommendation.NOT_RECOMMENDED


def test_score_is_never_negative():
    result = assess(
        {
            "monthly_income": Decimal("1"),
            "existing_emi": Decimal("99999"),
            "existing_loans": 9,
            "employment_years": 0,
        }
    )

    assert result["score"] >= 0
