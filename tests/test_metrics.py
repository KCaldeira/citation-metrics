from citation_metrics.metrics import compute_h_index, compute_weighted_h_index, compute_all_metrics


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
