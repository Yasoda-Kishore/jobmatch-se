from jobmatch.match.fit import (
    AdRequirements,
    calculate_fit,
    has_skill,
    split_skills,
    verified_quotes,
)
from jobmatch.match.profile import CandidateProfile
from jobmatch.match.service import unique_ads

AD = "We need a junior   ML engineer with PyTorch.\nSwedish is a plus."

PROFILE = CandidateProfile(
    target_roles=["ML Engineer"],
    skills=["Python", "PyTorch", "GitHub Actions CI/CD", "Docker"],
    experiences=[{"title": "Intern", "start": "2025-01", "end": "2025-12"}],  # exactly 1 year
    spoken_languages=["English"], education="BSc", summary="x",
)


def requirements(**changes):
    base = {"required_skills": ["Python", "PyTorch", "Kubernetes", "CI/CD"], "nice_to_have_skills": [],
            "min_years": None, "seniority": "junior", "requires_swedish": False, "key_quotes": []}
    return AdRequirements(**{**base, **changes})


def test_has_skill_matches_whole_words_only():
    assert has_skill(["GitHub Actions CI/CD"], "CI/CD")
    assert has_skill(["pytorch"], "PyTorch")
    assert not has_skill(["JavaScript"], "Java")


def test_split_skills_finds_matching_and_missing():
    have, missing = split_skills(PROFILE.skills, ["Python", "Kubernetes"])
    assert have == ["Python"] and missing == ["Kubernetes"]


def test_score_for_junior_role_with_three_of_four_skills():
    fit = calculate_fit(PROFILE, requirements())
    # 0.6 * 3/4 + 0.1 * 0.5 + 0.2 * 1.0 + 0.1 * 1.0 = 0.80
    assert fit["score"] == 80
    assert fit["missing_skills"] == ["Kubernetes"]
    assert "You have 3 of 4 required skills" in fit["reasons"]


def test_senior_role_asking_for_more_years_scores_lower():
    junior = calculate_fit(PROFILE, requirements())["score"]
    senior = calculate_fit(PROFILE, requirements(seniority="senior", min_years=5))["score"]
    assert senior < junior


def test_verified_quotes_drops_invented_ones():
    kept, dropped = verified_quotes(["junior ML engineer with PyTorch", "10 years of COBOL"], AD)
    assert kept == ["junior ML engineer with PyTorch"] and dropped == 1


def test_unique_ads_removes_duplicate_postings():
    ads = [
        {"id": "1", "title": "Junior Cloud RAN Developer", "employer": "Ericsson AB"},
        {"id": "2", "title": "junior cloud RAN developer ", "employer": "Ericsson AB"},
        {"id": "3", "title": "ML Engineer", "employer": None},
    ]
    assert [ad["id"] for ad in unique_ads(ads)] == ["1", "3"]