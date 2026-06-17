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


def compute_weighted_h_index(works):
    """Compute the weighted H-index.

    Sort papers by raw citations descending. Each paper counts as
    1/num_authors toward the paper count. Find the largest integer h
    such that papers with >= h citations have a total fractional
    weight >= h.
    """
    valid = [(w["cited_by_count"], w["num_authors"]) for w in works if w["num_authors"] > 0]
    valid.sort(key=lambda x: x[0], reverse=True)

    best_h = 0
    cumulative_weight = 0.0
    for citations, num_authors in valid:
        cumulative_weight += 1.0 / num_authors
        candidate = min(int(cumulative_weight), citations)
        if candidate > best_h:
            best_h = candidate
    return best_h


def compute_citation_aging(works, n, current_year, max_age=15):
    """Rank papers by how early vs. late citations compare.

    Considers only papers published between max_age and 2*n years ago, i.e.
    publication year Y with 2*n <= (current_year - Y) <= max_age. The lower
    bound guarantees a complete second n-year window; the upper bound keeps the
    paper within OpenAlex's ~15-year counts_by_year coverage.

    For each qualifying paper:
        - first  = citations in years Y .. Y+n-1 (includes publication year)
        - second = citations in years Y+n .. Y+2n-1
        - ratio  = first / second (inf when second == 0)
        - mean_lag = weighted mean of (citing_year - Y) over all citation years
                     available for the paper (None when the paper has no citations)

    Each work is a dict with keys: id, title, publication_year, counts_by_year
    (a dict mapping year -> citation count).

    Returns a list of row dicts sorted by ratio descending, so infinite-ratio
    papers (no second-window citations) appear first.
    """
    rows = []
    for w in works:
        y = w.get("publication_year")
        if y is None:
            continue
        age = current_year - y
        if not (2 * n <= age <= max_age):
            continue

        cby = w["counts_by_year"]
        first = sum(c for yr, c in cby.items() if y <= yr <= y + n - 1)
        second = sum(c for yr, c in cby.items() if y + n <= yr <= y + 2 * n - 1)
        total = sum(cby.values())
        mean_lag = (
            sum((yr - y) * c for yr, c in cby.items()) / total
            if total else None
        )
        ratio = float("inf") if second == 0 else first / second

        rows.append({
            "id": w["id"],
            "title": w.get("title"),
            "publication_year": y,
            "first": first,
            "second": second,
            "ratio": ratio,
            "mean_lag": mean_lag,
        })

    rows.sort(key=lambda r: r["ratio"], reverse=True)  # inf sorts to top
    return rows


def compute_all_metrics(works):
    """Compute all citation metrics from a list of works.

    Each work is a dict with keys:
        - cited_by_count: int
        - num_authors: int

    Returns a dict of metric names to values.
    """
    num_papers = len(works)
    fractional_papers = sum(
        1.0 / w["num_authors"] for w in works if w["num_authors"] > 0
    )

    # Standard H-index
    citation_counts = [w["cited_by_count"] for w in works]
    h_index = compute_h_index(citation_counts)
    h_per_paper = h_index / num_papers if num_papers > 0 else 0.0

    # Weighted H-index (Method 1): fractional paper counting
    weighted_h = compute_weighted_h_index(works)
    weighted_h_per_frac_paper = (
        weighted_h / fractional_papers if fractional_papers > 0 else 0.0
    )

    # Citation-divided H-index (Method 2): citations/authors then standard H
    fractional_values = [
        w["cited_by_count"] / w["num_authors"]
        for w in works
        if w["num_authors"] > 0
    ]
    citdiv_h = compute_h_index(fractional_values)
    citdiv_h_per_paper = citdiv_h / num_papers if num_papers > 0 else 0.0

    return {
        "h_index": h_index,
        "h_per_paper": h_per_paper,
        "weighted_h": weighted_h,
        "weighted_h_per_frac_paper": weighted_h_per_frac_paper,
        "citdiv_h": citdiv_h,
        "citdiv_h_per_paper": citdiv_h_per_paper,
        "num_papers": num_papers,
        "fractional_papers": fractional_papers,
    }
