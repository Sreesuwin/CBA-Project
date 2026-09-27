"""Rule-based credit assessment engine.

This is the heart of the platform and it is deliberately a **pure function**:
it takes the applicant's financials in, returns a score, risk level,
recommendation and a list of human-readable reasons, and touches no database,
no request and no clock. That is what makes it deterministic, explainable and
trivially unit-testable - the blueprint's worked examples can be asserted
exactly.

The rules below mirror §13/§14 of the project blueprint. They are a transparent
business-rule simulation for an apprenticeship, **not** a real credit score and
not suitable for actual lending.
"""

from decimal import Decimal

from ..models import Recommendation, RiskLevel

BASE_SCORE = 300
MAX_SCORE = 1000

# (reason, condition) thresholds kept as named constants so the policy is
# readable and the tests can refer to the same numbers.
HIGH_INCOME = Decimal("75000")
STABLE_INCOME = Decimal("40000")
MIN_INCOME = Decimal("25000")
LOW_EMI_RATIO = Decimal("0.20")
ACCEPTABLE_EMI_RATIO = Decimal("0.40")
EXPERIENCED_YEARS = 5
SETTLED_YEARS = 2


def _as_decimal(value) -> Decimal:
    """Coerce anything numeric (int, float, str, Decimal) to Decimal.

    Money and ratios are compared as exact decimals; doing this in binary float
    would make a ratio of exactly 0.20 land on the wrong side of the boundary.
    """
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value or 0))


def assess(financials) -> dict:
    """Score an applicant's financials.

    ``financials`` is any mapping with ``monthly_income``, ``existing_emi``,
    ``employment_years`` and ``existing_loans`` (a ``FinancialDetails`` model,
    a marshmallow-loaded dict, or a plain dict all work).

    Returns ``{score, risk, recommendation, reasons}``.
    """
    income = _as_decimal(get(financials, "monthly_income"))
    emi = _as_decimal(get(financials, "existing_emi"))
    years = int(get(financials, "employment_years") or 0)
    loans = int(get(financials, "existing_loans") or 0)

    score = BASE_SCORE
    reasons = []

    # --- Income band --------------------------------------------------------
    if income > HIGH_INCOME:
        score += 100
        reasons.append("High monthly income")
    elif income >= STABLE_INCOME:
        score += 70
        reasons.append("Stable income")
    elif income >= MIN_INCOME:
        score += 40
    else:
        score -= 50
        reasons.append("Income below the minimum requirement")

    # --- Existing EMI burden -------------------------------------------------
    # A zero/absent income cannot be divided by; treat it as a maximum burden
    # rather than crashing. The API rejects zero income on the way in.
    emi_ratio = (emi / income) if income else Decimal("1")
    if emi_ratio < LOW_EMI_RATIO:
        score += 80
        reasons.append("Low existing EMI burden")
    elif emi_ratio <= ACCEPTABLE_EMI_RATIO:
        score += 40
    else:
        score -= 50
        reasons.append("High existing EMI burden")

    # --- Employment stability -----------------------------------------------
    if years > EXPERIENCED_YEARS:
        score += 60
        reasons.append("Long employment history")
    elif years >= SETTLED_YEARS:
        score += 40
    else:
        score += 20

    # --- Existing loan count -------------------------------------------------
    if loans == 0:
        score += 50
        reasons.append("No existing loans")
    elif loans <= 2:
        score += 20
    else:
        score -= 40
        reasons.append("Multiple existing loans")

    score = max(0, min(score, MAX_SCORE))
    risk, recommendation = classify(score)
    return {
        "score": score,
        "risk": risk,
        "recommendation": recommendation,
        "reasons": reasons,
    }


def classify(score: int):
    """Map a numeric score to (risk level, recommendation)."""
    if score >= 700:
        return RiskLevel.LOW, Recommendation.ELIGIBLE
    if score >= 600:
        return RiskLevel.MODERATE, Recommendation.ELIGIBLE
    if score >= 500:
        return RiskLevel.HIGH, Recommendation.MANUAL_REVIEW
    return RiskLevel.VERY_HIGH, Recommendation.NOT_RECOMMENDED


def get(source, field):
    """Read ``field`` from a mapping or a model instance.

    Supporting both keeps the engine usable directly on a ``FinancialDetails``
    row and on a plain dict in the tests and seed script.
    """
    if isinstance(source, dict):
        return source.get(field)
    return getattr(source, field, None)
