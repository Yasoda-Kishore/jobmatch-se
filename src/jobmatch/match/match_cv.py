"""Find the best jobs for a CV: CV -> profile (LLM) -> search query -> hybrid search.

Run:  python -m jobmatch.match.match_cv path\\to\\cv.pdf [--city Stockholm] [--language en]
"""
import argparse
from pathlib import Path

from jobmatch.match.profile import build_search_query, extract_profile, read_pdf_text
from jobmatch.search.engine import search


def main() -> None:
    parser = argparse.ArgumentParser(description="Match a CV to job ads")
    parser.add_argument("cv", type=Path)
    parser.add_argument("--city")
    parser.add_argument("--language", choices=["sv", "en"])
    args = parser.parse_args()

    print("reading the CV and asking the LLM for a profile...")
    profile = extract_profile(read_pdf_text(args.cv))
    print(f"roles:  {', '.join(profile.target_roles)}")
    print(f"skills: {', '.join(profile.skills)}")
    print(f"years:  {profile.years_of_experience}")
    query = build_search_query(profile)
    print(f"query:  {query}\n")

    for rank, ad in enumerate(search(query, "hybrid", args.city, args.language, k=10), start=1):
        print(f"{rank:2}. [{ad['language']}] {ad['title']}  |  {ad['employer']}, {ad['city']}")


if __name__ == "__main__":
    main()