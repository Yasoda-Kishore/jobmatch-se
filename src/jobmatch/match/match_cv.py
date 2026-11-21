"""Find and score the best jobs for a CV.

Run:  python -m jobmatch.match.match_cv path\\to\\cv.pdf [--city Stockholm] [--language en] [--top 5]
"""
import argparse
from pathlib import Path

from jobmatch.match.profile import read_pdf_text
from jobmatch.match.service import match_cv_text


def main() -> None:
    parser = argparse.ArgumentParser(description="Match a CV to job ads")
    parser.add_argument("cv", type=Path)
    parser.add_argument("--city")
    parser.add_argument("--language", choices=["sv", "en"])
    parser.add_argument("--top", type=int, default=5, help="how many jobs the LLM scores")
    args = parser.parse_args()

    print("reading the CV, searching, and scoring jobs with the LLM (this takes a few minutes)...")
    result = match_cv_text(read_pdf_text(args.cv), args.city, args.language, args.top)
    profile = result["profile"]
    print(f"\nroles: {', '.join(profile['target_roles'])}   experience: {profile['years_of_experience']} years")
    print(f"query: {result['query']}")

    for rank, m in enumerate(result["matches"], start=1):
        swedish = "  [Swedish required]" if m["requires_swedish"] else ""
        print(f"\n{rank}. {m['score']}/100  {m['title']}  |  {m['employer']}, {m['city']}{swedish}")
        print(f"   score parts: {m['score_parts']}")
        print(f"   matching: {', '.join(m['matching_skills']) or '-'}")
        print(f"   missing:  {', '.join(m['missing_skills']) or '-'}")
        for reason in m["reasons"]:
            print(f"   - {reason}")
        for quote in m["quotes"]:
            print(f'     "{quote}"')
    print(f"\nquotes verified in the ad text: {result['quotes_verified']}")


if __name__ == "__main__":
    main()