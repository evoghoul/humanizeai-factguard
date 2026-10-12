from pydantic import BaseModel, Field
from typing import List, Optional

class AnalyzeRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=10000)

class AnalyzeResponse(BaseModel):
    robotic_score: float # Heuristic score 0-1
    detected_phrases: List[str]
    repetitive_patterns: List[str]
    explanation: str

class HumanizeRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=10000)
    content_type: str = Field(..., pattern="^(recruiter feedback|candidate communication|interview questions|summaries)$")
    tone: str = Field(..., pattern="^(Professional|Polished|Conversational)$")
    strength: str = Field(..., pattern="^(light|medium|heavy)$")

class FactLedger(BaseModel):
    names: List[str] = []
    organizations: List[str] = []
    dates: List[str] = []
    numbers: List[str] = []
    technical_terms: List[str] = []
    claims: List[str] = []
    negations: List[str] = []
    uncertainty: List[str] = []
    important_evidence: List[str] = []

class ValidationCheck(BaseModel):
    name: str
    status: str
    details: str

class ValidateRequest(BaseModel):
    original_text: str = Field(..., min_length=1, max_length=10000)
    rewritten_text: str = Field(..., min_length=1, max_length=10000)

class ValidateResponse(BaseModel):
    original_text: str
    rewritten_text: str
    detected_issues: List[str]
    change_summary: str
    validation_checks: List[ValidationCheck]
    warnings: List[str]
    validation_status: str

class HumanizeResponse(BaseModel):
    original_text: str
    rewritten_text: str
    fact_ledger: FactLedger
    detected_issues: List[str]
    change_summary: str
    validation_checks: List[ValidationCheck]
    warnings: List[str]
    validation_status: str

class RefineOptions(BaseModel):
    writingMode: Optional[str] = "Clarity Improvement"
    context: Optional[str] = "General Communication"
    tone: Optional[str] = "Professional"
    intensity: Optional[str] = "Balanced"

class RefineRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=12000)
    options: Optional[RefineOptions] = Field(default_factory=RefineOptions)

class RefineFinding(BaseModel):
    category: str
    phrase: str
    explanation: str

class RefineChange(BaseModel):
    original: str
    revised: str
    reason: str

class RefineStructuralCheck(BaseModel):
    paragraphsPreserved: bool = True
    listsPreserved: bool = True
    negationsPreserved: bool = True
    numbersPreserved: bool = True
    details: List[str] = []

class RefineVerification(BaseModel):
    status: str
    preserved: List[str] = []
    missing: List[str] = []
    added: List[str] = []
    warnings: List[str] = []
    claims: List[str] = []
    structural: Optional[RefineStructuralCheck] = None

class RefineResponse(BaseModel):
    id: str
    timestamp: str
    original: str
    revised: str
    options: RefineOptions
    findings: List[RefineFinding] = []
    changes: List[RefineChange] = []
    verification: RefineVerification

class HumanizeSimpleRequest(BaseModel):
    text: str = Field(min_length=1, max_length=10000)
    tone: Optional[str] = "Standard"
    strength: Optional[str] = "Medium"

class HumanizeSimpleResponse(BaseModel):
    original: str
    rewrite: str
    warnings: List[str] = []
    needs_review: bool = False


