def compute_h_index(values):
    """Compute the H-index from a list of numeric values.

    The H-index is the largest integer h such that at least h items
    have value >= h.
    """
    sorted_vals = sorted(values, reverse=True)
    h = 0
    for i, val in enumerate(sorted_vals):
        if val >= i + 1:
            h = i + 1
        else:
            break
    return h


def compute_all_metrics(works):
    """Compute all citation metrics from a list of works.

    Each work is a dict with keys:
        - cited_by_count: int
        - num_authors: int

    Returns a dict of metric names to values.
    """
    citation_counts = [w["cited_by_count"] for w in works]
    h_index = compute_h_index(citation_counts)

    fractional_values = [
        w["cited_by_count"] / w["num_authors"]
        for w in works
        if w["num_authors"] > 0
    ]
    fractional_h = compute_h_index(fractional_values)

    return {
        "h_index": h_index,
        "fractional_h_index": fractional_h,
    }
