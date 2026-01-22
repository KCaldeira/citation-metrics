from citation_metrics.metrics import compute_h_index, compute_all_metrics


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
    # Should work regardless of input order
    assert compute_h_index([3, 10, 5, 8, 4]) == 4


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
    # Fractional values: [50, 10, 30, 1, 2.5] -> sorted: [50, 30, 10, 2.5, 1]
    # h=3 (3 papers with fractional >= 3)
    assert metrics["fractional_h_index"] == 3


def test_compute_all_metrics_zero_authors():
    # Works with 0 authors should be excluded from fractional calculation
    works = [
        {"cited_by_count": 10, "num_authors": 0},
        {"cited_by_count": 5, "num_authors": 1},
    ]
    metrics = compute_all_metrics(works)
    assert metrics["h_index"] == 2
    # Only one work counted for fractional (the one with num_authors=1)
    assert metrics["fractional_h_index"] == 1
