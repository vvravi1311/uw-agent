from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Literal
from langchain_core.tools import tool

class Application(BaseModel):
    state: str = Field(..., description="Two-letter US state code used for medicare underwriting rules")
    receivedDate: str = Field( ..., description="Date the medicare application was received, formatted as YYYY-MM-DD", pattern=r"^\d{4}-\d{2}-\d{2}$" )  # YYYY-MM-DD
    requestedEffectiveDate: str = Field( ..., description="Effective date of medicare policy, formatted as YYYY-MM-DD", pattern=r"^\d{4}-\d{2}-\d{2}$" )
    # channel: Optional[Literal['AGENT','BROKER','DIRECT','MGA']] = 'AGENT'
    # carrierCode: Optional[str] = None

class EvaluateRequest(BaseModel):
    application: Application

class EvaluateResponse(BaseModel):
    decisionId: str = Field(..., description="Two-letter US state code used for medicare underwriting rules")
    status: Literal['ACCEPT_NO_UW','ACCEPT_WITH_UW','DECLINE','PENDED'] = Field( ..., description=( "Underwriting decision status. " "ACCEPT_NO_UW = Approved without underwriting; " "ACCEPT_WITH_UW = Approved but requires underwriting; " "DECLINE = Application rejected; " "PENDED = Decision delayed pending additional information." ))
    underwritingRequired: bool = Field( ..., description=("Indicates whether the application requires manual underwriting review. " "Accepts boolean values or integer equivalents (0 = False, 1 = True)."))


@tool
def evaluate_endpoint(req: EvaluateRequest) -> EvaluateResponse:
    """
    Evaluate a Medicare application and return an underwriting decision.

    Parameters
    ----------
    req : EvaluateRequest
        The request payload containing the Medicare application details.

    Returns
    -------
    EvaluateResponse
        The underwriting decision including decisionId, status, and
        whether manual underwriting is required.
    """
    try:
        resp = evaluate(req)
        return resp
    except Exception as ex:
        print(ex.message)

def evaluate(payload: EvaluateRequest) -> dict:
    app = payload.application
    response = {
        "decisionId": "decision_id based on application_id",
        "status": "ACCEPT_NO_UW",
        "underwritingRequired": 0
    }
    return response

@tool
def triple(temp: float) -> float:
    """
    param num: a number to triple
    returns: the triple of the input number
    """
    return float(temp)*3

uw_tools =[triple,evaluate_endpoint]