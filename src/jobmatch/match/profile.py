"""Read a CV (PDF) and turn it into a structured candidate profile with the LLM."""
import json
import sys
from pathlib import Path

from pydantic import BaseModel, Field
from pypdf import PdfReader

from jobmatch.llm import chat_json


class CandidateProfile(BaseModel):
    """What we need from a CV to search for jobs. No name, email or phone: we don't need them."""

    target_roles: list[str] = Field(description="Job titles this person fits, e.g. 'Machine Learning Engineer'")
    skills: list[str] = Field(description="Technical skills: languages, frameworks, tools, methods")
    years_of_experience: float = Field(description="Total years of professional work, internships included")
    languages: list[str] = Field(description="Spoken languages, e.g. 'English', 'Swedish'")
    education: str = Field(description="Highest degree and field, in one short line")
    summary: str = Field(description="Two sentences describing the candidate")


SYSTEM_PROMPT = """You read CVs and extract facts for a job-matching system.
Rules:
- Only use information that is written in the CV. Never invent skills or experience.
- List skills as short names, like "Python", "PyTorch", "Docker".
- Do not include the person's name, email, phone number or address.
- Answer in English, even if the CV is in Swedish."""


def read_pdf_text(path: Path) -> str:
    """Get the plain text out of a PDF file."""
    reader = PdfReader(path)
    return "\n".join(page.extract_text() or "" for page in reader.pages).strip()


def extract_profile(cv_text: str) -> CandidateProfile:
    """Ask the LLM to turn CV text into a CandidateProfile."""
    if not cv_text:
        raise ValueError("the CV has no readable text (is it a scanned image?)")
    return chat_json(SYSTEM_PROMPT, f"CV:\n{cv_text[:12000]}", CandidateProfile)


def build_search_query(profile: CandidateProfile, max_skills: int = 8) -> str:
    """Turn a profile into one search query: the main role plus the top skills."""
    role = profile.target_roles[0] if profile.target_roles else ""
    return " ".join([role, *profile.skills[:max_skills]]).strip()


if __name__ == "__main__":
    profile = extract_profile(read_pdf_text(Path(sys.argv[1])))
    print(json.dumps(profile.model_dump(), indent=2, ensure_ascii=False))
    print("\nsearch query:", build_search_query(profile))