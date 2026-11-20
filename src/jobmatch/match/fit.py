"""Score how well one job ad fits a candidate, with reasons that must be quoted from the ad."""
import re

from pydantic import BaseModel, Field

from jobmatch.llm import chat_json
from jobmatch.match.profile import CandidateProfile


class Reason(BaseModel):
    claim: str = Field(description="One short reason, e.g. 'The role needs PyTorch, which the candidate has'")
    quote: str = Field(description="Words copied exactly from the job ad that prove the claim")


class JobFit(BaseModel):
    score: int = Field(ge=0, le=100, description="0-100. 80+ strong fit, 50-79 partial fit, under 50 weak fit")
    matching_skills: list[str] = Field(description="Skills the ad asks for that the candidate has")
    missing_skills: list[str] = Field(description="Skills the ad asks for that the candidate does not have")
    requires_swedish: bool = Field(description="True only if the ad says Swedish is required")
    reasons: list[Reason] = Field(max_length=3, description="Up to 3 reasons, each with a quote from the ad")


FIT_PROMPT = """You are a strict technical recruiter. Judge how well a job ad fits a candidate.
Rules:
- Compare the ad's requirements with the candidate profile. Use only facts from these two texts.
- Senior roles that ask for many more years than the candidate has get a lower score.
- Every reason must include a quote copied word for word from the job ad.
- If the ad is in Swedish, quote it in Swedish, but write the claims in English."""


def normalise(text: str) -> str:
    """Lowercase and single spaces, so small formatting differences don't matter."""
    return re.sub(r"\s+", " ", text).strip().lower()


def verify_reasons(fit: JobFit, ad_text: str) -> tuple[list[Reason], int]:
    """Keep only reasons whose quote really appears in the ad. Return (kept, number dropped)."""
    ad = normalise(ad_text)
    kept = [r for r in fit.reasons if r.quote.strip() and normalise(r.quote) in ad]
    return kept, len(fit.reasons) - len(kept)


def score_job(profile: CandidateProfile, title: str, ad_text: str) -> tuple[JobFit, int]:
    """Ask the LLM for a JobFit, then remove reasons with invented quotes."""
    candidate = profile.model_dump_json(exclude={"summary"})
    user = f"CANDIDATE:\n{candidate}\n\nJOB AD: {title}\n{ad_text[:6000]}"
    fit = chat_json(FIT_PROMPT, user, JobFit)
    fit.reasons, dropped = verify_reasons(fit, ad_text)
    return fit, dropped