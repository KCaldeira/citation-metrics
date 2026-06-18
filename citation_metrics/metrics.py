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


# Bounds that keep the right-truncated MLE well-posed. When citations are still
# rising at the truncation boundary the likelihood is non-identifiable and would
# otherwise drive (mu, sigma) -> infinity; these box the search to a plausible
# region. A fit that lands against the cap is flagged (peak_beyond_window).
_SIGMA_MIN = 0.05
_SIGMA_MAX = 3.0
_MODE_CAP = 40.0   # years


def _normal_cdf(z):
    """Standard normal CDF via the error function."""
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def _truncated_lognormal_neg_ll(params, samples, trunc_age):
    """Negative log-likelihood of a right-truncated log-normal.

    params = (mu, s) with sigma = exp(s) (so sigma stays positive). Each
    observed citation age t contributes f(t) / F(trunc_age), where f and F are
    the log-normal pdf and cdf; trunc_age is the largest observable age. The
    search is boxed to a plausible region (see _SIGMA_*/_MODE_CAP) to keep the
    estimate finite when the peak lies beyond the observation window.
    """
    mu, s = params
    sigma = math.exp(s)
    if not (_SIGMA_MIN <= sigma <= _SIGMA_MAX):
        return 1e300
    if mu - sigma * sigma > math.log(_MODE_CAP):   # mode beyond cap
        return 1e300
    z = (math.log(trunc_age) - mu) / sigma
    cdf = _normal_cdf(z)
    if cdf <= 1e-300:                      # window has ~no probability mass
        return 1e300
    log_norm = math.log(cdf)
    const = 0.5 * math.log(2.0 * math.pi)
    nll = 0.0
    for t, c in samples:
        lt = math.log(t)
        log_pdf = -lt - s - const - (lt - mu) ** 2 / (2.0 * sigma * sigma)
        nll += c * (log_pdf - log_norm)
    return -nll


def _nelder_mead(f, x0, step=0.3, tol=1e-10, max_iter=2000):
    """Minimal Nelder-Mead simplex minimizer for low-dimensional problems."""
    n = len(x0)
    simplex = [list(x0)]
    for i in range(n):
        xi = list(x0)
        xi[i] += step
        simplex.append(xi)
    fvals = [f(p) for p in simplex]

    for _ in range(max_iter):
        order = sorted(range(n + 1), key=lambda k: fvals[k])
        simplex = [simplex[k] for k in order]
        fvals = [fvals[k] for k in order]
        if abs(fvals[-1] - fvals[0]) <= tol * (abs(fvals[0]) + tol):
            break

        centroid = [sum(simplex[k][j] for k in range(n)) / n for j in range(n)]
        worst = simplex[-1]
        reflected = [centroid[j] + (centroid[j] - worst[j]) for j in range(n)]
        fr = f(reflected)

        if fvals[0] <= fr < fvals[-2]:
            simplex[-1], fvals[-1] = reflected, fr
        elif fr < fvals[0]:
            expanded = [centroid[j] + 2.0 * (reflected[j] - centroid[j]) for j in range(n)]
            fe = f(expanded)
            if fe < fr:
                simplex[-1], fvals[-1] = expanded, fe
            else:
                simplex[-1], fvals[-1] = reflected, fr
        else:
            contracted = [centroid[j] + 0.5 * (worst[j] - centroid[j]) for j in range(n)]
            fc = f(contracted)
            if fc < fvals[-1]:
                simplex[-1], fvals[-1] = contracted, fc
            else:
                for k in range(1, n + 1):
                    simplex[k] = [
                        simplex[0][j] + 0.5 * (simplex[k][j] - simplex[0][j])
                        for j in range(n)
                    ]
                    fvals[k] = f(simplex[k])

    best = min(range(n + 1), key=lambda k: fvals[k])
    return simplex[best]


def compute_citation_lognormal(works, first_year=2011, last_year=2022,
                               truncation_year=2025):
    """Fit a right-truncated log-normal to each paper's citation-age distribution.

    Considers papers with publication year Y in [first_year, last_year]. Only
    citations in years <= truncation_year are used, so the incomplete most
    recent year(s) are excluded.

    A citation in calendar year y is assigned a citation age of
    max(y - Y, 0) + 0.5 years (the midpoint of the citing year, treating Y as
    the start of the publication year; pre-/same-publication-year citations are
    floored to age 0.5). Because citations are observed only through the end of
    truncation_year, each paper's data is right-truncated at

        trunc_age = (truncation_year - Y) + 1.

    The log-normal parameters (mu, sigma) are estimated by maximizing the
    right-truncated likelihood (each observation weighted by f(t) / F(trunc_age),
    where f, F are the log-normal pdf/cdf). This corrects the downward bias that
    an uncorrected fit would have for younger papers, whose right tail extends
    beyond the observation window. The optimizer is warm-started from the
    untruncated log-moment estimates.

    Reported per paper:
        mode   = exp(mu - sigma^2)   # most-likely citation age, in years
        log_sd = sigma               # shape parameter (std of ln age)
        logmean = mu
        peak_beyond_window           # True if the estimated peak is past the
                                     # last observed age (still rising; the
                                     # mode is a lower bound, not identifiable)

    When citations are still rising at the truncation boundary the truncated
    likelihood is non-identifiable; the fit is boxed to a plausible region and
    such papers are flagged via peak_beyond_window.

    Papers with fewer than 3 in-window citations, with all in-window citations
    in a single year, or whose ages collapse to a single value are skipped.
    Estimates for very young (heavily truncated) papers are inherently
    higher-variance.

    Each work is a dict with keys: id, title, publication_year, counts_by_year
    (a dict mapping year -> citation count).

    Returns a list of row dicts sorted by mode descending (latest-peaking
    papers first).
    """
    rows = []
    for w in works:
        y = w.get("publication_year")
        if y is None or not (first_year <= y <= last_year):
            continue
        if truncation_year < y:           # nothing observable
            continue

        cby = w["counts_by_year"]
        cited_years = [
            (yr, c) for yr, c in cby.items() if c > 0 and yr <= truncation_year
        ]
        total = sum(c for _, c in cited_years)
        if total < 3:                     # too few citations to fit
            continue
        if len(cited_years) < 2:          # all citations in a single year
            continue

        # citation age (years) at the midpoint of each citing year; pre-/same-
        # publication-year citations (yr <= Y) are floored to age 0.5
        samples = [(max(yr - y, 0) + 0.5, c) for yr, c in cited_years]

        # warm start: untruncated log-moment (= untruncated MLE) estimates
        mu0 = sum(c * math.log(t) for t, c in samples) / total
        var0 = sum(c * (math.log(t) - mu0) ** 2 for t, c in samples) / total
        sigma0 = math.sqrt(var0)
        if sigma0 == 0:                   # ages collapse to one value
            continue

        trunc_age = (truncation_year - y) + 1
        # clamp the warm start into the feasible box before optimizing
        s0 = min(max(math.log(sigma0), math.log(_SIGMA_MIN)), math.log(_SIGMA_MAX))
        mu, s = _nelder_mead(
            lambda p: _truncated_lognormal_neg_ll(p, samples, trunc_age),
            [mu0, s0],
        )
        sigma = math.exp(s)
        mode = math.exp(mu - sigma ** 2)

        rows.append({
            "id": w["id"],
            "title": w.get("title"),
            "publication_year": y,
            "n_citations": total,
            "mode": mode,
            "log_sd": sigma,
            "logmean": mu,
            # peak estimated past the last observed age -> still rising; the
            # mode is not really identifiable and should be read as a lower bound
            "peak_beyond_window": mode > trunc_age,
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
