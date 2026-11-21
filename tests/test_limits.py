from jobmatch.api import limits


def test_each_visitor_gets_their_own_limit():
    limits._history.clear()
    assert [limits.allow("a", limit=2) for _ in range(3)] == [True, True, False]
    assert limits.allow("b", limit=2)  # another visitor is not affected


def test_old_matches_are_forgotten():
    limits._history.clear()
    assert limits.allow("c", limit=1, window_s=0.0)
    assert limits.allow("c", limit=1, window_s=0.0)  # the window is over, so it is allowed again
