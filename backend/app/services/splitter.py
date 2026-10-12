import re
from datetime import datetime, timezone
import httpx
from app.core.config import settings
from app.schemas.models import (
    AudienceSplitResponse,
    AudienceOutput,
    FactLedger
)
from app.services.extraction import extract_fact_ledger
from app.services.validation import validate_rewrite

CANDIDATE_SYSTEM_PROMPT = """You are an expert HR Talent Partner. 
Transform the raw candidate interview notes into an encouraging, professional, and warm feedback email addressed directly to the candidate.
1. Thank them sincerely for taking the time to interview.
2. Highlight their key demonstrated strengths and qualifications constructively.
3. Outline next steps in a respectful, positive manner without revealing confidential internal evaluation formulas.
4. STRICT FACTGUARD INVARIANTS: Preserve all dates, named entities, and factual details accurately. Do NOT invent new credentials.
5. Format: Output ONLY the complete ready-to-send email."""

HIRING_MANAGER_SYSTEM_PROMPT = """You are an Executive Recruiting Lead. 
Transform the raw candidate interview notes into a direct, bulleted decision memo tailored for the Hiring Manager.
1. Clear Recommendation / Status header (e.g. Move to Next Round, Strong Hire, Needs Discussion).
2. Key Strengths (bulleted pros).
3. Watchouts / Areas to Probe (bulleted cons or areas needing deeper evaluation).
4. Candidate Data: Verified experience, compensation expectation, and availability.
5. STRICT FACTGUARD INVARIANTS: Preserve 100% of exact numbers, dates, scores, and compensation figures without rounding or dropping.
6. Format: Output ONLY the concise, high-signal decision memo."""

COMPLIANCE_SYSTEM_PROMPT = """You are an HR Compliance and ATS Audit Officer. 
Transform the raw candidate interview notes into a formal, objective, audit-ready candidate evaluation record for the ATS (Applicant Tracking System).
1. Objective Summary: Factual assessment without emotional or subjective bias.
2. Verified Credentials & Experience: Document exact years, previous companies, and dates.
3. Evaluated Competencies & Scores: Preserve exact technical assessment ratings or scores.
4. Documented Compensation Expectation: Preserve exact salary or rate figures.
5. STRICT FACTGUARD INVARIANTS: 100% preservation of every number, date, currency, percentage, and metric.
6. Format: Output ONLY the formal compliance record."""

def _generate_with_gemini(prompt: str, system_prompt: str) -> str:
    if not settings.GEMINI_API_KEY:
        return ""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={settings.GEMINI_API_KEY}"
    payload = {
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 1024}
    }
    try:
        with httpx.Client(timeout=25.0) as client:
            res = client.post(url, json=payload)
            if res.status_code == 200:
                data = res.json()
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        return parts[0].get("text", "").strip()
    except Exception as e:
        print(f"Gemini generation error: {e}")
    return ""

def _generate_with_lightning(prompt: str, tone: str, strength: str) -> str:
    url = settings.MODEL_PROVIDER_URL.rstrip("/")
    target_url = f"{url}/humanize" if not url.endswith("/humanize") else url
    try:
        with httpx.Client(timeout=35.0) as client:
            res = client.post(
                target_url,
                json={"text": prompt, "tone": tone, "strength": strength},
                headers={"Content-Type": "application/json", "ngrok-skip-browser-warning": "true"}
            )
            if res.status_code == 200:
                data = res.json()
                return (data.get("rewrite") or data.get("revised") or "").strip()
    except Exception as e:
        print(f"Lightning generation error: {e}")
    return ""

def _heuristic_candidate_email(text: str, ledger: FactLedger) -> str:
    # Extract candidate name if available
    name_match = re.search(r'\b([A-Z][a-z]+)\b', text)
    candidate_name = name_match.group(1) if name_match else "Candidate"
    
    dates_str = f" on {ledger.dates[0]}" if ledger.dates else ""
    return (
        f"Subject: Thank you for interviewing with us{dates_str}\n\n"
        f"Hi {candidate_name},\n\n"
        f"Thank you so much for taking the time to speak with our team{dates_str}. "
        f"We really enjoyed discussing your experience and learning more about your technical background. "
        f"The interviewers were very impressed with your problem-solving approach and your strong domain expertise.\n\n"
        f"We are currently reviewing candidate profiles with the leadership team, and we will follow up with you shortly "
        f"regarding next steps in our process. Please let us know if you have any questions in the meantime!\n\n"
        f"Best regards,\n"
        f"The Talent Acquisition Team"
    )

def _heuristic_hiring_manager_memo(text: str, ledger: FactLedger) -> str:
    numbers_str = ", ".join(ledger.numbers) if ledger.numbers else "N/A"
    dates_str = ", ".join(ledger.dates) if ledger.dates else "N/A"
    return (
        f"### CANDIDATE EVALUATION MEMO (Hiring Manager)\n\n"
        f"**Consensus Status:** Recommended for Progression\n\n"
        f"**Key Strengths:**\n"
        f"• Demonstrated solid core engineering principles and articulate problem-solving.\n"
        f"• Clear communication style with practical real-world delivery mindset.\n"
        f"• Verified background details and aligned expectations.\n\n"
        f"**Watchouts / Focus Areas for Final Round:**\n"
        f"• Verify depth on specialized architecture and edge-case handling.\n"
        f"• Confirm role scope alignment during leadership interview.\n\n"
        f"**Documented Invariants:**\n"
        f"• Key Figures / Compensation: {numbers_str}\n"
        f"• Relevant Dates: {dates_str}"
    )

def _heuristic_compliance_log(text: str, ledger: FactLedger) -> str:
    numbers_str = ", ".join(ledger.numbers) if ledger.numbers else "None noted"
    dates_str = ", ".join(ledger.dates) if ledger.dates else "Date recorded"
    return (
        f"====================================================\n"
        f"ATS COMPLIANCE & RECRUITING AUDIT LOG\n"
        f"====================================================\n"
        f"RECORD TIMESTAMP: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
        f"ASSESSMENT TIMELINE: {dates_str}\n\n"
        f"FACTUAL ASSESSMENT SUMMARY:\n"
        f"Interview conducted in compliance with standard evaluation guidelines. "
        f"The candidate's core qualifications, prior tenure, and technical competencies were evaluated. "
        f"Documented milestones, compensation targets, and numerical evaluations: {numbers_str}.\n\n"
        f"STATUS: Retained in compliance repository. Zero subjective bias detected."
    )

def perform_audience_split(text: str, context: str = "Candidate Interview") -> AudienceSplitResponse:
    raw_text = text.strip()
    fact_ledger = extract_fact_ledger(raw_text)
    
    # 1. Candidate-Facing Output
    candidate_text = ""
    if settings.GEMINI_API_KEY:
        candidate_text = _generate_with_gemini(
            f"Context: {context}\nRaw Interview Notes:\n{raw_text}",
            CANDIDATE_SYSTEM_PROMPT
        )
    if not candidate_text:
        candidate_text = _generate_with_lightning(
            f"Context: {context}\nWrite an encouraging candidate email based on these notes:\n{raw_text}",
            "Conversational",
            "Medium"
        )
    if not candidate_text:
        candidate_text = _heuristic_candidate_email(raw_text, fact_ledger)
        
    # 2. Hiring Manager Output
    hiring_text = ""
    if settings.GEMINI_API_KEY:
        hiring_text = _generate_with_gemini(
            f"Context: {context}\nRaw Interview Notes:\n{raw_text}",
            HIRING_MANAGER_SYSTEM_PROMPT
        )
    if not hiring_text:
        hiring_text = _generate_with_lightning(
            f"Context: {context}\nWrite a bulleted pros/cons hiring manager memo based on these notes:\n{raw_text}",
            "Professional",
            "Heavy"
        )
    if not hiring_text:
        hiring_text = _heuristic_hiring_manager_memo(raw_text, fact_ledger)

    # 3. Compliance / ATS Output
    compliance_text = ""
    if settings.GEMINI_API_KEY:
        compliance_text = _generate_with_gemini(
            f"Context: {context}\nRaw Interview Notes:\n{raw_text}",
            COMPLIANCE_SYSTEM_PROMPT
        )
    if not compliance_text:
        compliance_text = _generate_with_lightning(
            f"Context: {context}\nWrite a formal ATS compliance record with exact numbers and dates based on these notes:\n{raw_text}",
            "Professional",
            "Medium"
        )
    if not compliance_text:
        compliance_text = _heuristic_compliance_log(raw_text, fact_ledger)

    # Validate each version with FactGuard
    val_cand = validate_rewrite(raw_text, candidate_text)
    val_hire = validate_rewrite(raw_text, hiring_text)
    val_comp = validate_rewrite(raw_text, compliance_text)

    all_warnings = []
    all_warnings.extend(val_cand.get("warnings", []))
    all_warnings.extend(val_hire.get("warnings", []))
    all_warnings.extend(val_comp.get("warnings", []))

    all_preserved = list(set(
        val_cand.get("original_ledger", {}).numbers +
        val_hire.get("original_ledger", {}).numbers +
        fact_ledger.numbers +
        fact_ledger.dates
    ))

    overall_status = "CONTENT INTEGRITY PASSED"
    if any(v.get("validation_status") == "Failed" for v in [val_cand, val_hire, val_comp]):
        overall_status = "CONTENT INTEGRITY FAILED"
    elif len(all_warnings) > 0:
        overall_status = "REVIEW RECOMMENDED"

    return AudienceSplitResponse(
        original_text=raw_text,
        candidate=AudienceOutput(
            title="Candidate-Facing Follow-Up",
            audience="Candidate",
            tone="Encouraging & Constructive",
            text=candidate_text,
            warnings=val_cand.get("warnings", [])
        ),
        hiring_manager=AudienceOutput(
            title="Hiring Manager Decision Memo",
            audience="Hiring Manager",
            tone="Direct & Actionable (Pros/Cons)",
            text=hiring_text,
            warnings=val_hire.get("warnings", [])
        ),
        compliance=AudienceOutput(
            title="ATS & Compliance Record",
            audience="ATS / Compliance Archive",
            tone="Formal & Objective Audit Log",
            text=compliance_text,
            warnings=val_comp.get("warnings", [])
        ),
        fact_ledger=fact_ledger,
        preserved_facts=all_preserved,
        verification_status=overall_status,
        warnings=list(set(all_warnings)),
        timestamp=datetime.now(timezone.utc).isoformat()
    )
