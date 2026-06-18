import math

from citation_metrics.metrics import (
    compute_h_index,
    compute_weighted_h_index,
    compute_all_metrics,
    compute_citation_lognormal,
)


def test_h_index_basic():
    # Papers with citations [10, 8, 5, 4, 3] -> h=4 (4 papers with >=4 citations)
    assert compute_h_index([10, 8, 5, 4, 3]) == 4


def test_h_index_all_high():
    assert compute_h_index([100, 100, 100]) == 3


def test_h_index_all_zero():
    assert compute_h_index([0, 0, 0]) == 0


def test_h_index_empty():
    assert compute_h_index([]) == 0


def test_h_index_single():
    assert compute_h_index([5]) == 1
    assert compute_h_index([0]) == 0


def test_h_index_unsorted_input():
    assert compute_h_index([3, 10, 5, 8, 4]) == 4


def test_weighted_h_index_single_author_papers():
    # All single-author: weighted H should equal standard H
    works = [
        {"cited_by_count": 10, "num_authors": 1},
        {"cited_by_count": 8, "num_authors": 1},
        {"cited_by_count": 5, "num_authors": 1},
        {"cited_by_count": 4, "num_authors": 1},
        {"cited_by_count": 3, "num_authors": 1},
    ]
    assert compute_weighted_h_index(works) == 4


def test_weighted_h_index_multi_author():
    # Each paper has 2 authors, so each contributes 0.5 to weight
    # Sorted by citations: [100, 50, 30, 10, 5]
    # Cumulative weights: [0.5, 1.0, 1.5, 2.0, 2.5]
    # Candidates: min(0,100)=0, min(1,50)=1, min(1,30)=1, min(2,10)=2, min(2,5)=2
    # Best = 2
    works = [
        {"cited_by_count": 100, "num_authors": 2},
        {"cited_by_count": 50, "num_authors": 2},
        {"cited_by_count": 30, "num_authors": 2},
        {"cited_by_count": 10, "num_authors": 2},
        {"cited_by_count": 5, "num_authors": 2},
    ]
    assert compute_weighted_h_index(works) == 2


def test_weighted_h_index_mixed_authors():
    # Paper 1: 100 citations, 1 author -> weight 1.0, cumW=1.0, candidate=min(1,100)=1
    # Paper 2: 50 citations, 10 authors -> weight 0.1, cumW=1.1, candidate=min(1,50)=1
    # Paper 3: 5 citations, 1 author -> weight 1.0, cumW=2.1, candidate=min(2,5)=2
    works = [
        {"cited_by_count": 100, "num_authors": 1},
        {"cited_by_count": 50, "num_authors": 10},
        {"cited_by_count": 5, "num_authors": 1},
    ]
    assert compute_weighted_h_index(works) == 2


def test_compute_all_metrics():
    works = [
        {"cited_by_count": 100, "num_authors": 2},
        {"cited_by_count": 50, "num_authors": 5},
        {"cited_by_count": 30, "num_authors": 1},
        {"cited_by_count": 10, "num_authors": 10},
        {"cited_by_count": 5, "num_authors": 2},
    ]
    metrics = compute_all_metrics(works)

    assert metrics["h_index"] == 5
    assert metrics["h_per_paper"] == 5 / 5

    # Weighted H: sorted by citations desc, weights = [0.5, 0.2, 1.0, 0.1, 0.5]
    # cumW: [0.5, 0.7, 1.7, 1.8, 2.3]
    # candidates: min(0,100), min(0,50), min(1,30), min(1,10), min(2,5) = 0,0,1,1,2
    assert metrics["weighted_h"] == 2
    # fractional_papers = 0.5 + 0.2 + 1.0 + 0.1 + 0.5 = 2.3
    assert abs(metrics["weighted_h_per_frac_paper"] - 2 / 2.3) < 1e-9

    # Citation-divided H: values = [50, 10, 30, 1, 2.5] -> sorted: [50, 30, 10, 2.5, 1]
    # h=3 (3 papers with value >= 3)
    assert metrics["citdiv_h"] == 3
    assert abs(metrics["citdiv_h_per_paper"] - 3 / 5) < 1e-9


def test_compute_all_metrics_zero_authors():
    works = [
        {"cited_by_count": 10, "num_authors": 0},
        {"cited_by_count": 5, "num_authors": 1},
    ]
    metrics = compute_all_metrics(works)
    assert metrics["h_index"] == 2
    assert metrics["citdiv_h"] == 1
    assert metrics["weighted_h"] == 1


def _work(work_id, year, counts_by_year, title="t"):
    return {
        "id": work_id,
        "title": title,
        "publication_year": year,
        "counts_by_year": counts_by_year,
    }


def test_lognormal_matches_untruncated_when_window_huge():
    # With a far-off truncation year the window is effectively complete, so the
    # truncated MLE must recover the closed-form untruncated log-moment estimates.
    cby = {2014: 1, 2015: 2, 2016: 1}   # ages 0.5, 1.5, 2.5
    rows = compute_citation_lognormal(
        [_work("W1", 2014, cby)],
        first_year=2010, last_year=2020, truncation_year=2200,
    )
    assert len(rows) == 1
    r = rows[0]
    assert r["n_citations"] == 4

    logs = [math.log(0.5), math.log(1.5), math.log(1.5), math.log(2.5)]
    mu = sum(logs) / 4
    var = sum((x - mu) ** 2 for x in logs) / 4
    assert abs(r["logmean"] - mu) < 1e-4
    assert abs(r["log_sd"] - math.sqrt(var)) < 1e-4
    assert abs(r["mode"] - math.exp(mu - var)) < 1e-4


def test_lognormal_truncation_raises_mode():
    # Same citations, but a tight truncation cuts off the right tail. The
    # truncation correction must push the estimated mode up vs. a wide window.
    cby = {2014: 1, 2015: 2, 2016: 1}
    wide = compute_citation_lognormal(
        [_work("W1", 2014, cby)],
        first_year=2010, last_year=2020, truncation_year=2200,
    )[0]
    tight = compute_citation_lognormal(
        [_work("W1", 2014, cby)],
        first_year=2010, last_year=2020, truncation_year=2016,
    )[0]
    assert tight["mode"] > wide["mode"]


def test_lognormal_flags_peak_beyond_window():
    # citations still rising right up to a tight truncation -> peak not observed
    cby = {2020: 1, 2021: 2, 2022: 4, 2023: 8}     # monotonically increasing
    rows = compute_citation_lognormal(
        [_work("W1", 2020, cby)],
        first_year=2011, last_year=2022, truncation_year=2023,
    )
    assert len(rows) == 1
    r = rows[0]
    assert r["peak_beyond_window"] is True
    # the fit stays finite (boxed), not a runaway value
    assert r["mode"] <= 40.0
    assert r["log_sd"] <= 3.0
    # the CI still gives a finite lower bound but an unbounded upper bound
    assert r["mode_ci_hi"] == float("inf")
    assert 0.0 < r["mode_ci_lo"] < r["mode"]


def test_lognormal_within_window_not_flagged():
    # clear peak well inside the window -> not flagged, finite two-sided CI
    cby = {2012: 1, 2013: 3, 2014: 6, 2015: 4, 2016: 2, 2017: 1}
    rows = compute_citation_lognormal(
        [_work("W1", 2012, cby)],
        first_year=2011, last_year=2022, truncation_year=2025,
    )
    assert len(rows) == 1
    r = rows[0]
    assert r["peak_beyond_window"] is False
    assert math.isfinite(r["mode_ci_hi"])
    assert r["mode_ci_lo"] < r["mode"] < r["mode_ci_hi"]


def test_lognormal_publication_year_filter():
    works = [
        _work("Wbefore", 2010, {2011: 2, 2013: 2, 2015: 2}),   # < first_year
        _work("Wafter", 2023, {2024: 2, 2025: 2, 2026: 2}),    # > last_year
    ]
    rows = compute_citation_lognormal(
        works, first_year=2011, last_year=2022, truncation_year=2025
    )
    assert rows == []


def test_lognormal_drops_citations_after_truncation_year():
    # 2026 citations are excluded; only 2 in-window citations remain -> skipped
    rows = compute_citation_lognormal(
        [_work("W1", 2018, {2019: 1, 2020: 1, 2026: 10})],
        first_year=2011, last_year=2022, truncation_year=2025,
    )
    assert rows == []


def test_lognormal_skips_few_citations():
    rows = compute_citation_lognormal(
        [_work("W1", 2018, {2019: 1, 2020: 1})],
        first_year=2011, last_year=2022, truncation_year=2025,
    )
    assert rows == []


def test_lognormal_skips_single_year():
    # all citations in one year -> degenerate, skipped
    rows = compute_citation_lognormal(
        [_work("W1", 2018, {2019: 5})],
        first_year=2011, last_year=2022, truncation_year=2025,
    )
    assert rows == []


def test_lognormal_missing_year_skipped():
    rows = compute_citation_lognormal(
        [_work("W1", None, {2018: 5, 2019: 5})],
        first_year=2011, last_year=2022, truncation_year=2025,
    )
    assert rows == []


def test_lognormal_pre_publication_citation_clamped():
    # citation in 2017 precedes pub year 2018 -> age floored to 0.5, no crash
    rows = compute_citation_lognormal(
        [_work("W1", 2018, {2017: 1, 2019: 2, 2020: 1})],
        first_year=2011, last_year=2022, truncation_year=2200,
    )
    assert len(rows) == 1
    logs = [math.log(0.5), math.log(1.5), math.log(1.5), math.log(2.5)]
    mu = sum(logs) / 4
    assert abs(rows[0]["logmean"] - mu) < 1e-4


def test_lognormal_sorted_by_mode_desc():
    # late-peaking paper should sort before early-peaking paper
    early = _work("Wearly", 2014, {2014: 5, 2015: 1})       # mass at low age
    late = _work("Wlate", 2014, {2018: 5, 2019: 1})         # mass at high age
    rows = compute_citation_lognormal(
        [early, late], first_year=2011, last_year=2022, truncation_year=2200
    )
    assert [r["id"] for r in rows] == ["Wlate", "Wearly"]
    assert rows[0]["mode"] > rows[1]["mode"]
