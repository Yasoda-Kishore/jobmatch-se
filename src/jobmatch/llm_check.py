"""Check that the configured LLM works, and print the exact error if it doesn't.

Run:  python -m jobmatch.llm_check                      (short test texts)
      python -m jobmatch.llm_check path\\to\\cv.pdf       (your real CV and a real ad from the database)
"""
import sys
import time
from pathlib import Path

from jobmatch import llm
from jobmatch.match.fit import READ_AD_PROMPT, AdRequirements
from jobmatch.match.profile import SYSTEM_PROMPT, CandidateProfile, read_pdf_text

CV = "Jane Doe. Machine Learning Intern at Acme, 2024-03 to 2024-08. Skills: Python, PyTorch, SQL. Languages: English."
AD = "We are hiring a junior ML engineer. You must know Python and PyTorch. Docker is a plus. English required."


def real_texts(cv_path: Path) -> tuple[str, str]:
    from jobmatch.db import connect

    with connect() as conn:
        title, text = conn.execute("SELECT title, text FROM ads ORDER BY length(text) DESC LIMIT 1").fetchone()
    return f"CV:\n{read_pdf_text(cv_path)[:12000]}", f"JOB AD: {title}\n{text[:6000]}"


def run(name: str, system: str, text: str, schema) -> None:
    from jobmatch import monitoring

    stats = monitoring.start_request()
    started = time.perf_counter()
    try:
        result = llm.chat_json(system, text, schema)
        print(f"OK   {name} in {time.perf_counter() - started:.1f}s, {stats['llm_tokens_in']} tokens in, "
              f"{stats['llm_tokens_out']} out: {result.model_dump_json()[:120]}")
    except Exception as error:  # noqa: BLE001 - show any failure, whatever its type
        print(f"FAIL {name} after {time.perf_counter() - started:.1f}s: {type(error).__name__}: {error}")


if __name__ == "__main__":
    print(f"provider={llm.LLM_PROVIDER} model={llm.LLM_MODEL} json_mode={llm.LLM_JSON_MODE} "
          f"reasoning={llm.LLM_REASONING_EFFORT or 'default'}")
    if len(sys.argv) > 1:
        cv_text, ad_text = real_texts(Path(sys.argv[1]))
        run("CV profile (your CV)", SYSTEM_PROMPT, cv_text, CandidateProfile)
        run("Ad requirements (longest ad)", READ_AD_PROMPT, ad_text, AdRequirements)
    else:
        run("CV profile", "Extract the facts as JSON.", f"CV:\n{CV}", CandidateProfile)
        run("Ad requirements", "Extract the facts as JSON.", AD, AdRequirements)
