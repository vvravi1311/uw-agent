from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Literal
from langchain_core.tools import tool

from pydantic import BaseModel, Field
from typing import Optional, List, Literal


class Application(BaseModel):
    applicationId: str = Field(..., description="Unique identifier for the application")
    receivedDate: str = Field(..., description="Date the application was received (YYYY-MM-DD)")
    requestedEffectiveDate: str = Field(..., description="Requested policy effective date")
    channel: Optional[Literal['AGENT','BROKER','DIRECT','MGA']] = Field(
        'AGENT', description="Sales channel through which the application was submitted"
    )
    carrierCode: Optional[str] = Field(
        None, description="Carrier identifier when supporting multiple carriers"
    )


class Applicant(BaseModel):
    firstName: Optional[str] = Field(None, description="Applicant's first name")
    lastName: Optional[str] = Field(None, description="Applicant's last name")
    dateOfBirth: str = Field(..., description="Applicant's date of birth (YYYY-MM-DD)")
    state: str = Field(..., description="State of residence (2-letter code)")
    zip: Optional[str] = Field(None, description="ZIP code of residence")
    tobaccoUse: Optional[bool] = Field(False, description="Whether the applicant uses tobacco")
    heightInches: Optional[int] = Field(None, description="Height in inches (used for BMI)")
    weightPounds: Optional[int] = Field(None, description="Weight in pounds (used for BMI)")
    partAEffectiveDate: str = Field(..., description="Medicare Part A effective date")
    partBEffectiveDate: str = Field(..., description="Medicare Part B effective date")
    currentlyOnMA: Optional[bool] = Field(
        False, description="Whether the applicant is currently enrolled in Medicare Advantage"
    )
    currentCoverageType: Optional[
        Literal['NONE','MEDIGAP','MA','EMPLOYER_GROUP','UNION','SELECT','OTHER']
    ] = Field('NONE', description="Type of existing coverage at time of application")
    medicareEligibilityDate: Optional[str] = Field(
        None, description="Date the applicant first became eligible for Medicare"
    )


class Coverage(BaseModel):
    requestedPlanLetter: Literal[
        'A','B','C','D','F','G','K','L','M','N','HDG','HDF'
    ] = Field(..., description="Requested Medigap plan letter")
    replacingCoverage: Optional[bool] = Field(
        False, description="Whether the applicant is replacing existing coverage"
    )
    replacingCoverageType: Optional[
        Literal['NONE','MEDIGAP','MA','SELECT','EMPLOYER_GROUP','UNION','OTHER']
    ] = Field('NONE', description="Type of coverage being replaced")
    priorCreditableCoverageMonths: Optional[int] = Field(
        0, description="Months of prior creditable coverage"
    )
    gapSinceCreditableCoverageEndDays: Optional[int] = Field(
        0, description="Days without coverage since creditable coverage ended"
    )


class RecentHospitalization(BaseModel):
    occurred: bool = Field(False, description="Whether a recent hospitalization occurred")
    dischargeDate: Optional[str] = Field(
        None, description="Date of hospital discharge, if applicable"
    )


class Health(BaseModel):
    conditions: List[str] = Field(
        default_factory=list, description="List of disclosed medical conditions"
    )
    medications: List[str] = Field(
        default_factory=list, description="List of current medications"
    )
    oxygenUse: Optional[bool] = Field(False, description="Whether the applicant uses oxygen")
    adlAssistance: Optional[bool] = Field(
        False, description="Whether the applicant needs help with Activities of Daily Living"
    )
    recentHospitalization: Optional[RecentHospitalization] = Field(
        default_factory=RecentHospitalization,
        description="Details of any recent hospitalization"
    )


class GiEvent(BaseModel):
    type: Literal[
        'MA_PLAN_TERMINATION','MA_MOVE_OUT_OF_SERVICE_AREA','MA_TRIAL_RIGHT_WITHIN_12M',
        'EMPLOYER_GROUP_ENDING','MEDIGAP_INSOLVENCY','SELECT_MOVE_OUT_OF_AREA',
        'CARRIER_RULE_VIOLATION_OR_MISLEADING'
    ] = Field(..., description="Type of Guaranteed Issue qualifying event")
    triggeringDate: str = Field(..., description="Date the GI event occurred")


class EvaluateRequest(BaseModel):
    application: Application = Field(..., description="Application metadata")
    applicant: Applicant = Field(..., description="Applicant demographic and Medicare details")
    coverage: Coverage = Field(..., description="Requested coverage information")
    giEvents: List[GiEvent] = Field(
        default_factory=list, description="List of applicable GI events"
    )
    health: Optional[Health] = Field(
        default_factory=Health, description="Applicant health and medical information"
    )
    context: Optional[dict] = Field(
        default_factory=dict, description="Additional contextual data for evaluation"
    )


class Reason(BaseModel):
    code: str = Field(..., description="Machine-readable reason code")
    message: str = Field(..., description="Human-readable explanation")


class RuleAudit(BaseModel):
    ruleId: str = Field(..., description="Identifier of the evaluated rule")
    outcome: Literal['FIRED','SKIPPED'] = Field(..., description="Rule evaluation outcome")
    details: Optional[str] = Field(None, description="Additional rule evaluation details")


class PlanRestrictions(BaseModel):
    allowedPlanLetters: List[str] = Field(
        default_factory=list, description="Plans the applicant is eligible for"
    )
    disallowedPlanLetters: List[str] = Field(
        default_factory=list, description="Plans the applicant is not eligible for"
    )
    notes: List[str] = Field(default_factory=list, description="Additional notes")


class WaitingPeriod(BaseModel):
    applies: bool = Field(False, description="Whether a waiting period applies")
    months: int = Field(0, description="Length of the waiting period in months")
    reason: Optional[str] = Field(None, description="Explanation for the waiting period")


class RatingGuidance(BaseModel):
    class_: Optional[Literal['PREFERRED','STANDARD','RATED']] = Field(
        default=None, alias='class', description="Recommended rating class"
    )
    suggestedFactor: Optional[float] = Field(
        None, description="Suggested rating factor (e.g., 1.15 for 15% rate-up)"
    )


class EvaluateResponse(BaseModel):
    decisionId: str = Field(..., description="Unique identifier for the evaluation")
    status: Literal['ACCEPT_NO_UW','ACCEPT_WITH_UW','DECLINE','PENDED'] = Field(
        ..., description="Final underwriting decision status"
    )
    underwritingRequired: bool = Field(
        ..., description="Whether manual underwriting is required"
    )
    reasons: List[Reason] = Field(
        default_factory=list, description="Reasons supporting the decision"
    )
    planRestrictions: PlanRestrictions = Field(
        default_factory=PlanRestrictions, description="Plan eligibility restrictions"
    )
    waitingPeriod: WaitingPeriod = Field(
        default_factory=WaitingPeriod, description="Waiting period determination"
    )
    ratingGuidance: Optional[RatingGuidance] = Field(
        None, description="Recommended rating class and factor"
    )
    requestsForInformation: List[str] = Field(
        default_factory=list, description="Additional information requested from applicant"
    )
    audit: Optional[dict] = Field(
        None, description="Full rule audit trail for transparency"
    )


class StateOverride(BaseModel):
    state: str = Field(..., description="State code the override applies to")
    continuousGi: bool = Field(False, description="Whether the state allows continuous GI rights")
    birthdayOrAnniversarySwitching: Optional[dict] = Field(
        None, description="Rules for switching plans during birthday/anniversary windows"
    )
    under65Access: Optional[Literal['NONE','LIMITED','ANY_AVAILABLE']] = Field(
        None, description="Medigap access rules for applicants under age 65"
    )
    notes: List[str] = Field(default_factory=list, description="Additional state-specific notes")


class DeclineCondition(BaseModel):
    code: str = Field(..., description="Unique decline condition code")
    label: str = Field(..., description="Short label for the decline condition")
    description: Optional[str] = Field(None, description="Detailed explanation")


class GiScenario(BaseModel):
    code: str = Field(..., description="GI scenario code")
    description: str = Field(..., description="Description of the GI scenario")
    lookbackDaysDefault: int = Field(
        63, description="Default lookback window for GI eligibility"
    )
    planLettersPermitted: List[str] = Field(
        default_factory=list, description="Plans permitted under this GI scenario"
    )
















# ..........................................................................................
# @tool
# def evaluate_endpoint(req: EvaluateRequest) -> EvaluateResponse:
#     """
#     Evaluate a Medicare application and return an underwriting decision.
#
#     Parameters
#     ----------
#     req : EvaluateRequest
#         The request payload containing the Medicare application details.
#
#     Returns
#     -------
#     EvaluateResponse
#         The underwriting decision including decisionId, status, and
#         whether manual underwriting is required.
#     """
#     try:
#         resp = evaluate(req)
#         return resp
#     except Exception as ex:
#         print(ex.message)
#
# def evaluate(payload: EvaluateRequest) -> dict:
#     app = payload.application
#     response = {
#         "decisionId": "decision_id based on application_id",
#         "status": "ACCEPT_NO_UW",
#         "underwritingRequired": 0
#     }
#     return response
#
# @tool
# def triple(temp: float) -> float:
#     """
#     param num: a number to triple
#     returns: the triple of the input number
#     """
#     return float(temp)*3
#
# # uw_tools =[triple,evaluate_endpoint]