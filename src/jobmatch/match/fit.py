"""Score how well a job ad fits a candidate.

The LLM only READS the ad and extracts its requirements.
Python CALCULATES the score with a fixed formula, so every number can be explained.
"""
import re
from typing import Literal

from pydantic import BaseModel, Field

from jobmatch.llm import chat_json
from jobmatch.match.profile import CandidateProfile


class AdRequirements(BaseModel):
    """Facts the LLM extracts from one job ad."""

    required_skills: list[str] = Field(description="Technical skills the ad requires, as short names like 'Python'")
    nice_to_have_skills: list[str] = Field(description="Skills the ad calls a plus, bonus or 'meriterande'")
    min_years: float | None = Field(description="Minimum years of experience the ad asks for, or null if not stated")
    seniority: Literal["junior", "mid", "senior", "unknown"] = Field(description="The level of the role")
    requires_swedish: bool = Field(description="True only if Swedish is REQUIRED, not just a plus")
    key_quotes: list[str] = Field(max_length=3, description="Up to 3 sentences copied word for word from the ad that state its main requirements")


READ_AD_PROMPT = """You read job ads and extract their requirements for a matching system.
Rules:
- Only use what is written in the ad. Never guess.
- Write skills as short names, like "Python", "PyTorch", "Kubernetes".
- A skill is "required" if the ad says must, required, krav, or expects it. "Plus", "bonus" or "meriterande" means nice to have.
- key_quotes must be copied word for word from the ad. If the ad is in Swedish, quote it in Swedish."""

SENIORITY_FIT = {"junior": 1.0, "unknown": 0.8, "mid": 0.5, "senior": 0.2}
WEIGHTS = {"required_skills": 0.6, "nice_to_have": 0.1, "experience": 0.2, "seniority": 0.1}


def skill_tokens(skill: str) -> set[str]:
    """'GitHub Actions CI/CD' -> {'github', 'actions', 'ci', 'cd'}."""
    return set(re.findall(r"[0-9a-zåäö+#]+", skill.lower()))


def has_skill(candidate_skills: list[str], wanted: str) -> bool:
    """True if one of the candidate's skills contains every word of the wanted skill, or the other way round.

    So 'CI/CD' matches 'GitHub Actions CI/CD', but 'Java' does not match 'JavaScript'.
    """
    want = skill_tokens(wanted)
    if not want:
        return False
    return any(want <= skill_tokens(s) or (skill_tokens(s) and skill_tokens(s) <= want) for s in candidate_skills)


def split_skills(candidate_skills: list[str], wanted: list[str]) -> tuple[list[str], list[str]]:
    """Return (skills the candidate has, skills the candidate is missing)."""
    have = [s for s in wanted if has_skill(candidate_skills, s)]
    missing = [s for s in wanted if not has_skill(candidate_skills, s)]
    return have, missing


def normalise(text: str) -> str:
    """Lowercase and single spaces, so small formatting differences don't matter."""
    return re.sub(r"\s+", " ", text).strip().lower()


def verified_quotes(quotes: list[str], ad_text: str) -> tuple[list[str], int]:
    """Keep only quotes that really appear in the ad. Return (kept, number dropped)."""
    ad = normalise(ad_text)
    kept = [q for q in quotes if q.strip() and normalise(q) in ad]
    return kept, len(quotes) - len(kept)


def calculate_fit(profile: CandidateProfile, req: AdRequirements) -> dict:
    """The scoring formula. Each part is a number from 0 to 1."""
    have, missing = split_skills(profile.skills, req.required_skills)
    nice_have, _ = split_skills(profile.skills, req.nice_to_have_skills)
    parts = {
        "required_skills": len(have) / len(req.required_skills) if req.required_skills else 0.5,
        "nice_to_have": len(nice_have) / len(req.nice_to_have_skills) if req.nice_to_have_skills else 0.5,
        "experience": 1.0 if not req.min_years else min(1.0, profile.years_of_experience / req.min_years),
        "seniority": SENIORITY_FIT[req.seniority],
    }
    score = round(100 * sum(WEIGHTS[name] * value for name, value in parts.items()))

    reasons = []
    if req.required_skills:
        reasons.append(f"You have {len(have)} of {len(req.required_skills)} required skills")
    if req.min_years:
        reasons.append(f"Asks for {req.min_years:g}+ years of experience; you have {profile.years_of_experience:g}")
    if req.seniority in ("mid", "senior"):
        reasons.append(f"This is a {req.seniority} role")
    if req.requires_swedish:
        reasons.append("Swedish is required")
    return {
        "score": score,
        "score_parts": {name: round(value, 2) for name, value in parts.items()},
        "matching_skills": have + nice_have,
        "missing_skills": missing,
        "requires_swedish": req.requires_swedish,
        "seniority": req.seniority,
        "reasons": reasons,
    }


def score_job(profile: CandidateProfile, title: str, ad_text: str) -> tuple[dict, int]:
    """Extract the ad's requirements with the LLM, then score them in Python."""
    req = chat_json(READ_AD_PROMPT, f"JOB AD: {title}\n{ad_text[:6000]}", AdRequirements)
    fit = calculate_fit(profile, req)
    fit["quotes"], dropped = verified_quotes(req.key_quotes, ad_text)
    return fit, dropped