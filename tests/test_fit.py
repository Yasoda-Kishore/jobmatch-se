from jobmatch.match.fit import JobFit, Reason, verify_reasons
from jobmatch.match.service import unique_ads

AD = "We need a junior   ML engineer with PyTorch.\nSwedish is a plus."


def make_fit(*quotes):
    return JobFit(
        score=80, matching_skills=[], missing_skills=[], requires_swedish=False,
        reasons=[Reason(claim="c", quote=q) for q in quotes],
    )


def test_verify_reasons_keeps_real_quotes_even_with_different_spacing():
    kept, dropped = verify_reasons(make_fit("junior ML engineer with PyTorch"), AD)
    assert len(kept) == 1 and dropped == 0


def test_verify_reasons_drops_invented_quotes():
    kept, dropped = verify_reasons(make_fit("Swedish is a plus", "10 years of Kubernetes"), AD)
    assert [r.quote for r in kept] == ["Swedish is a plus"]
    assert dropped == 1


def test_unique_ads_removes_duplicate_postings():
    ads = [
        {"id": "1", "title": "Junior Cloud RAN Developer", "employer": "Ericsson AB"},
        {"id": "2", "title": "junior cloud RAN developer ", "employer": "Ericsson AB"},
        {"id": "3", "title": "ML Engineer", "employer": None},
    ]
    assert [ad["id"] for ad in unique_ads(ads)] == ["1", "3"]