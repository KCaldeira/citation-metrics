from citation_metrics.metrics import (
    compute_h_index,
    compute_weighted_h_index,
    compute_all_metrics,
    compute_citation_aging,
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


def test_citation_aging_window_math():
    # n=5, pub 2014, current 2026 -> age 12, qualifies (10 <= 12 <= 15)
    # first  = 2014..2018, second = 2019..2023
    cby = {2014: 2, 2015: 4, 2016: 6, 2017: 1, 2018: 3,
           2019: 5, 2020: 2, 2021: 1, 2022: 1, 2023: 1}
    rows = compute_citation_aging([_work("W1", 2014, cby)], n=5, current_year=2026)
    assert len(rows) == 1
    r = rows[0]
    assert r["first"] == 2 + 4 + 6 + 1 + 3      # 16
    assert r["second"] == 5 + 2 + 1 + 1 + 1     # 10
    assert abs(r["ratio"] - 16 / 10) < 1e-9


def test_citation_aging_age_filter():
    # 2020 paper: age 6 < 2n=10 -> excluded
    # 2009 paper: age 17 > 15 -> excluded
    works = [
        _work("Wyoung", 2020, {2020: 5, 2021: 5}),
        _work("Wold", 2009, {2010: 5, 2014: 5}),
    ]
    rows = compute_citation_aging(works, n=5, current_year=2026)
    assert rows == []


def test_citation_aging_infinite_ratio_sorts_first():
    # second window empty -> inf ratio, must sort to top
    finite = _work("Wfin", 2014, {2014: 1, 2019: 2})          # ratio 0.5
    rising = _work("Winf", 2015, {2015: 3})                   # second window empty -> inf
    rows = compute_citation_aging([finite, rising], n=5, current_year=2026)
    assert rows[0]["id"] == "Winf"
    assert rows[0]["ratio"] == float("inf")
    assert rows[1]["id"] == "Wfin"


def test_citation_aging_mean_lag():
    # pub 2014, cited {2014: 3, 2016: 1} -> (0*3 + 2*1)/4 = 0.5
    rows = compute_citation_aging(
        [_work("W1", 2014, {2014: 3, 2016: 1})], n=5, current_year=2026
    )
    assert abs(rows[0]["mean_lag"] - 0.5) < 1e-9


def test_citation_aging_zero_citations_mean_lag_none():
    rows = compute_citation_aging(
        [_work("W1", 2014, {})], n=5, current_year=2026
    )
    assert rows[0]["mean_lag"] is None
    assert rows[0]["ratio"] == float("inf")  # second == 0


def test_citation_aging_missing_year_skipped():
    rows = compute_citation_aging(
        [_work("W1", None, {2014: 5})], n=5, current_year=2026
    )
    assert rows == []
