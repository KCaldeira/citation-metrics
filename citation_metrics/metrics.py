import math


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


def compute_citation_lognormal(works, current_year, min_age=5, max_age=15):
    """Fit a log-normal to each paper's citation-age distribution.

    Considers papers published between max_age and min_age years ago, i.e.
    publication year Y with min_age <= (current_year - Y) <= max_age. The upper
    bound keeps papers within OpenAlex's ~15-year counts_by_year coverage so the
    early part of the curve is not truncated.

    A citation in calendar year y is assigned a citation age of
    max(y - Y, 0) + 0.5 years (the midpoint of the citing year, with any
    pre-/same-publication-year citation floored to age 0.5), which keeps the
    age positive so its log is defined. The log-normal maximum-likelihood fit
    is the weighted mean and standard deviation of ln(age):

        mu     = sum(c * ln(age)) / N
        sigma  = sqrt(sum(c * (ln(age) - mu)^2) / N)

    Reported per paper:
        mode   = exp(mu - sigma^2)   # most-likely citation age, in years
        log_sd = sigma               # shape parameter (std of ln age)

    Papers with fewer than 3 total citations, with all citations in a single
    year, or whose ages collapse to a single value (sigma == 0) are skipped
    (the fit would be undefined or degenerate).

    Each work is a dict with keys: id, title, publication_year, counts_by_year
    (a dict mapping year -> citation count).

    Returns a list of row dicts sorted by mode descending (latest-peaking
    papers first).
    """
    rows = []
    for w in works:
        y = w.get("publication_year")
        if y is None:
            continue
        age = current_year - y
        if not (min_age <= age <= max_age):
            continue

        cby = w["counts_by_year"]
        cited_years = [(yr, c) for yr, c in cby.items() if c > 0]
        total = sum(c for _, c in cited_years)
        if total < 3:                 # too few citations to fit
            continue
        if len(cited_years) < 2:       # all citations in a single year
            continue

        # citation age (years) at the midpoint of each citing year; pre-/same-
        # publication-year citations (yr <= Y) are floored to age 0.5
        samples = [(max(yr - y, 0) + 0.5, c) for yr, c in cited_years]
        mu = sum(c * math.log(t) for t, c in samples) / total
        var = sum(c * (math.log(t) - mu) ** 2 for t, c in samples) / total
        sigma = math.sqrt(var)
        if sigma == 0:                 # ages collapse to one value -> degenerate
            continue
        mode = math.exp(mu - sigma ** 2)

        rows.append({
            "id": w["id"],
            "title": w.get("title"),
            "publication_year": y,
            "n_citations": total,
            "mode": mode,
            "log_sd": sigma,
            "logmean": mu,
        })

    rows.sort(key=lambda r: r["mode"], reverse=True)
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
