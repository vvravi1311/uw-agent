
from __future__ import annotations
from typing import Dict, List, Tuple
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from uw_models import (
    EvaluateRequest, WaitingPeriod, RatingGuidance
)
from langchain_core.tools import tool

# In-memory decision store for demo purposes
_DECISIONS: Dict[str, dict] = {}

# Data-driven configurations (loaded by main at startup)
STATE_OVERRIDES: Dict[str, dict] = {}
DECLINE_CONDITIONS: Dict[str, dict] = {}
GI_SCENARIOS: Dict[str, dict] = {}

# Constants
MACRA_CUTOFF = date(2020, 1, 1)
GI_DEFAULT_LOOKBACK_DAYS = 63
GI_BASE_PLANS = {"A","B","C","D","F","G","K","L"}
OPTIONAL_GI_PLANS = {"N"}  # May be carrier-dependent
ALL_PLANS = ["A","B","C","D","F","G","K","L","M","N","HDG","HDF"]


def _parse_date(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def _is_open_enrollment(applicant_dob: date, partb: date, asof: date) -> bool:
    age_years = relativedelta(asof, applicant_dob).years
    if age_years < 65:
        return False
    start = date(partb.year, partb.month, 1)
    end = start + relativedelta(months=+6) - relativedelta(days=+1)
    return start <= asof <= end


def _gi_applies(gi_events: List[dict], received: date) -> Tuple[bool, dict]:
    for ev in gi_events:
        trig = _parse_date(ev["triggeringDate"]) if isinstance(ev["triggeringDate"], str) else ev["triggeringDate"]
        diff = (received - trig).days
        if 0 <= diff <= GI_DEFAULT_LOOKBACK_DAYS:
            return True, ev
    return False, {}


def _apply_macra_filter(plan_letters: List[str], medicare_elig_date: date | None) -> List[str]:
    if medicare_elig_date and medicare_elig_date >= MACRA_CUTOFF:
        return [p for p in plan_letters if p not in ("C","F","HDF")]
    return plan_letters


def _compute_waiting_period(prior_months: int | None, gap_days: int | None, in_protected: bool) -> WaitingPeriod:
    if in_protected:
        return WaitingPeriod(applies=False, months=0)
    prior = prior_months or 0
    gap = gap_days or 0
    if gap <= GI_DEFAULT_LOOKBACK_DAYS and prior >= 6:
        return WaitingPeriod(applies=False, months=0)
    months = max(0, 6 - prior)
    if months == 0:
        return WaitingPeriod(applies=False, months=0)
    return WaitingPeriod(applies=True, months=months, reason="Pre-existing condition waiting period per federal baseline")


def _rating_guidance(tobacco: bool | None, height: int | None, weight: int | None, uw_required: bool) -> RatingGuidance:
    if height and weight:
        bmi = (weight / 2.20462) / ((height * 0.0254) ** 2)
    else:
        bmi = 25
    if not uw_required:
        cls = 'PREFERRED'
        factor = 1.0
    else:
        if tobacco or bmi >= 35:
            cls, factor = 'RATED', 1.25
        elif bmi >= 30:
            cls, factor = 'STANDARD', 1.10
        else:
            cls, factor = 'PREFERRED', 1.0
    return RatingGuidance(**{"class": cls}, suggestedFactor=factor)

@tool
def evaluate(payload: EvaluateRequest) -> dict:
    """
        Evaluate a Medicare application and return an underwriting decision.

        Parameters
        ----------
        request : EvaluateRequest
            The request payload containing the Medicare application details.

        Returns
        -------
        response: EvaluateResponse
            The underwriting decision including decisionId, status, Reasons supporting the decision, Plan eligibility restrictions, any Waiting period, rating Guidance, rule audit trail and
            whether manual underwriting is required.
        """

    app = payload.application
    appl = payload.applicant
    cov = payload.coverage

    asof = _parse_date(app.receivedDate)
    dob = _parse_date(appl.dateOfBirth)
    partb = _parse_date(appl.partBEffectiveDate)
    medicare_elig = _parse_date(appl.medicareEligibilityDate) if appl.medicareEligibilityDate else None

    state = (appl.state or '').upper()
    audit = []
    decision = None

    # R-600: State overrides first
    state_rule = STATE_OVERRIDES.get(state)
    if state_rule and state_rule.get('continuousGi'):
        allowed = _apply_macra_filter(ALL_PLANS, medicare_elig)
        decision = {
            "status": "ACCEPT_NO_UW",
            "underwritingRequired": False,
            "reasons": [{"code": "R-600", "message": f"State {state} continuous GI protections - no underwriting."}],
            "planRestrictions": {"allowedPlanLetters": allowed, "disallowedPlanLetters": []},
            "waitingPeriod": {"applies": False, "months": 0}
        }
        audit.append({"ruleId": "R-600", "outcome": "FIRED", "details": f"Continuous GI for {state}"})
    else:
        audit.append({"ruleId": "R-600", "outcome": "SKIPPED", "details": f"No continuous GI for {state}"})
        # R-100: Open Enrollment
        if _is_open_enrollment(dob, partb, asof):
            allowed = _apply_macra_filter(ALL_PLANS, medicare_elig)
            decision = {
                "status": "ACCEPT_NO_UW",
                "underwritingRequired": False,
                "reasons": [{"code": "R-100", "message": "Within 6-month Medigap Open Enrollment; underwriting not permitted."}],
                "planRestrictions": {"allowedPlanLetters": allowed, "disallowedPlanLetters": []},
                "waitingPeriod": {"applies": False, "months": 0}
            }
            audit.append({"ruleId": "R-100", "outcome": "FIRED", "details": "Age>=65 and within OE window."})
        else:
            audit.append({"ruleId": "R-100", "outcome": "SKIPPED", "details": "Outside OE window."})
            # R-200: GI
            gi_applies, gi_event = _gi_applies([g.model_dump() for g in payload.giEvents], asof)
            if gi_applies:
                allowed = sorted(GI_BASE_PLANS.union(OPTIONAL_GI_PLANS))
                allowed = _apply_macra_filter(allowed, medicare_elig)
                decision = {
                    "status": "ACCEPT_NO_UW",
                    "underwritingRequired": False,
                    "reasons": [{"code": "R-200", "message": f"Guaranteed Issue applies: {gi_event.get('type')} within lookback."}],
                    "planRestrictions": {"allowedPlanLetters": allowed, "disallowedPlanLetters": list(set(ALL_PLANS) - set(allowed)), "notes": ["Plan N availability may vary by carrier."]},
                    "waitingPeriod": {"applies": False, "months": 0}
                }
                audit.append({"ruleId": "R-200", "outcome": "FIRED", "details": "GI within lookback."})
                if medicare_elig and medicare_elig >= MACRA_CUTOFF:
                    audit.append({"ruleId": "R-210", "outcome": "FIRED", "details": "MACRA removed C/F for newly eligible."})
            else:
                audit.append({"ruleId": "R-200", "outcome": "SKIPPED", "details": "No GI event in lookback."})
                # R-300: Medigap cannot be combined with MA
                if appl.currentlyOnMA:
                    decision = {
                        "status": "PENDED",
                        "underwritingRequired": True,
                        "reasons": [{"code": "R-300", "message": "Currently on Medicare Advantage; require disenrollment or GI path."}],
                        "planRestrictions": {"allowedPlanLetters": [], "disallowedPlanLetters": []},
                        "waitingPeriod": {"applies": False, "months": 0},
                        "requestsForInformation": ["Proof of MA disenrollment effective date"]
                    }
                    audit.append({"ruleId": "R-300", "outcome": "FIRED", "details": "MA present without GI."})
                else:
                    audit.append({"ruleId": "R-300", "outcome": "SKIPPED", "details": "Not on MA."})
                    # R-400: Medical underwriting required
                    decision = {
                        "status": "ACCEPT_WITH_UW",
                        "underwritingRequired": True,
                        "reasons": [{"code": "R-400", "message": "Outside OE/GI; medical underwriting required."}],
                        "planRestrictions": {"allowedPlanLetters": ALL_PLANS, "disallowedPlanLetters": []},
                        "waitingPeriod": {"applies": False, "months": 0}
                    }
                    audit.append({"ruleId": "R-400", "outcome": "FIRED", "details": "Proceed to UW checks."})

    if not decision:
        decision = {
            "status": "PENDED",
            "underwritingRequired": True,
            "reasons": [{"code": "R-900", "message": "Insufficient data"}],
            "planRestrictions": {"allowedPlanLetters": [], "disallowedPlanLetters": []},
            "waitingPeriod": {"applies": False, "months": 0}
        }

    # R-700: MACRA check for requested plan (C/F/HDF)
    if payload.coverage.requestedPlanLetter in ("C","F","HDF") and (medicare_elig and medicare_elig >= MACRA_CUTOFF):
        audit.append({"ruleId": "R-700", "outcome": "FIRED", "details": "Requested C/F not allowed for newly eligible."})
        if decision["status"] in ("ACCEPT_NO_UW","ACCEPT_WITH_UW"):
            decision["status"] = "PENDED"
            decision.setdefault("requestsForInformation", [])
            decision["reasons"].append({"code": "R-700", "message": "Requested plan not available for newly eligible (MACRA). Suggest G/HDG."})
    else:
        audit.append({"ruleId": "R-700", "outcome": "SKIPPED", "details": "MACRA not applicable to requested plan."})

    # R-410: common automatic declines if UW path
    health = payload.health or {}
    conds = set([c.upper() for c in (health.conditions if hasattr(health, 'conditions') else [])])
    oxygen = bool(getattr(health, 'oxygenUse', False))
    if decision["underwritingRequired"] and decision["status"] != "PENDED":
        decline_hits = []
        for code, item in DECLINE_CONDITIONS.items():
            labels = [item.get('label','').upper(), item.get('description','').upper()]
            if any(lbl and any(lbl in c for c in conds) for lbl in labels):
                decline_hits.append(code)
        if ("CHF" in conds and oxygen) or ("ESRD" in conds) or ("ALZHEIMER" in conds) or ("DEMENTIA" in conds):
            decline_hits.append("AUTO")
        if decline_hits:
            decision["status"] = "DECLINE"
            decision["reasons"].insert(0, {"code": "R-410", "message": "Automatic decline based on health conditions."})
            audit.append({"ruleId": "R-410", "outcome": "FIRED", "details": f"Decline hits: {decline_hits}"})
        else:
            audit.append({"ruleId": "R-410", "outcome": "SKIPPED", "details": "No automatic decline condition matched."})

    # R-500: pre-existing waiting period
    in_protected = decision["status"] == "ACCEPT_NO_UW"
    if decision["status"] in ("ACCEPT_NO_UW","ACCEPT_WITH_UW"):
        wp = _compute_waiting_period(cov.priorCreditableCoverageMonths, cov.gapSinceCreditableCoverageEndDays, in_protected)
        decision["waitingPeriod"] = wp.model_dump()
        audit.append({"ruleId": "R-500", "outcome": "FIRED" if wp.applies else "SKIPPED", "details": f"Waiting period months={wp.months}"})

    # Rating guidance
    rg = _rating_guidance(appl.tobaccoUse, appl.heightInches, appl.weightPounds, decision["underwritingRequired"])
    decision["ratingGuidance"] = rg.model_dump(by_alias=True)

    # Assemble response
    decision_id = f"DEC-{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')[:-3]}"
    response = {
        "decisionId": decision_id,
        **decision,
        "audit": {
            "evaluatedAt": datetime.utcnow().isoformat() + 'Z',
            "matchedRules": audit
        }
    }

    _DECISIONS[decision_id] = response
    return response


def get_decision(decision_id: str) -> dict | None:
    return _DECISIONS.get(decision_id)

uw_tools =[evaluate]