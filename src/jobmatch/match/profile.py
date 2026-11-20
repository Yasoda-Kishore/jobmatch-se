"""Read a CV (PDF) and turn it into a structured candidate profile with the LLM."""
import io
import json
import sys
from datetime import date
from pathlib import Path

from pydantic import BaseModel, Field, computed_field
from pypdf import PdfReader

from jobmatch.llm import chat_json


class Experience(BaseModel):
    """One job or internship. The LLM copies the dates; Python does the maths."""

    title: str = Field(description="Job title, e.g. 'Machine Learning Intern'")
    start: str = Field(pattern=r"^\d{4}-\d{2}$", description="Start month as YYYY-MM")
    end: str = Field(pattern=r"^(\d{4}-\d{2}|present)$", description="End month as YYYY-MM, or 'present'")


class CandidateProfile(BaseModel):
    """What we need from a CV to search for jobs. No name, email or phone: we don't need them."""

    target_roles: list[str] = Field(description="Job titles this person fits, e.g. 'Machine Learning Engineer'")
    skills: list[str] = Field(description="Technical skills: programming languages, frameworks, tools, methods")
    experiences: list[Experience] = Field(description="Every job and internship in the CV, with its dates")
    spoken_languages: list[str] = Field(description="Human languages only, e.g. 'English', 'Swedish'. Never programming languages")
    education: str = Field(description="Highest degree and field, in one short line")
    summary: str = Field(description="Two sentences describing the candidate")

    @computed_field
    @property
    def years_of_experience(self) -> float:
        """Count every month worked once, even if two jobs overlap, then turn months into years."""
        months: set[tuple[int, int]] = set()
        today = date.today()
        for job in self.experiences:
            year, month = (int(x) for x in job.start.split("-"))
            end_year, end_month = (today.year, today.month) if job.end == "present" else (
                int(x) for x in job.end.split("-")
            )
            while (year, month) <= (end_year, end_month):
                months.add((year, month))
                year, month = (year + 1, 1) if month == 12 else (year, month + 1)
        return round(len(months) / 12, 1)


SYSTEM_PROMPT = """You read CVs and extract facts for a job-matching system.
Rules:
- Only use information that is written in the CV. Never invent skills or experience.
- List skills as short names, like "Python", "PyTorch", "Docker".
- Copy job dates exactly as months (YYYY-MM). Do not calculate anything.
- Do not include the person's name, email, phone number or address.
- Answer in English, even if the CV is in Swedish."""


def read_pdf_text(source: Path | bytes) -> str:
    """Get the plain text out of a PDF, from a file path or from uploaded bytes."""
    reader = PdfReader(io.BytesIO(source) if isinstance(source, bytes) else source)
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