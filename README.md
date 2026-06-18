# Citation Metrics

Compute alternative citation metrics for academic authors using the [OpenAlex API](https://openalex.org/).

## Metrics

- **H-index** - standard H-index (verified against OpenAlex's pre-computed value)
- **Weighted H-index** - each paper's credit = `1 / num_authors`, cumulative fractional authorship used
- **Cit-divided H-index** - each paper's value = `cited_by_count / num_authors`, then H-index applied
- **Log-normal citation-age fit** - fits a log-normal to each paper's citation-age
  distribution and reports the **mode** (peak citation age, in years) and the **log
  standard deviation** (sigma of `ln(age)`); see below

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## API Key Setup

An API key is **optional**. OpenAlex works without one via the free "polite pool"
(requests are identified by a `mailto`); a key only raises rate limits. If a key is set
but rejected (e.g. stale), the tool automatically drops it and falls back to the keyless
polite pool.

To use a key, get a free one at https://openalex.org/settings/api, then:

```bash
cp .env.example .env
# Edit .env and add your key
```

## Usage

```bash
# By ORCID
citation-metrics 0000-0002-4591-643X

# By OpenAlex ID
citation-metrics A5052404353

# With per-paper breakdown
citation-metrics A5052404353 -v
```

Example output:

```
Author: Ken Caldeira (A5052404353)
Papers: 304

  H-index (computed):          80
  H-index (OpenAlex):          80
  H / papers:               0.263  (80 / 304)

  Weighted H-index:            32
  Weighted H / frac papers: 0.335  (32 / 95.6)

  Cit-divided H-index:         39
  Cit-divided H / papers:   0.128  (39 / 304)
```

## Log-normal citation-age fit

Fits a **right-truncated log-normal** to each paper's distribution of citation ages and
reports, per paper, the **mode** (most-likely citation age, in years) and the **log
standard deviation** (sigma of `ln(age)`). Results print as a table and are written to a
CSV (`lognormal_<authorid>.csv`).

```bash
citation-metrics A5052404353 --lognormal

# Tune the publication-year window, truncation year, and output path
citation-metrics A5052404353 --lognormal \
    --first-year 2011 --last-year 2022 --truncation-year 2025 --csv out.csv
```

How it works:

- **Papers considered**: publication year in `[--first-year, --last-year]`
  (default 2011-2022).
- **Truncation**: only citations in years `<= --truncation-year` (default 2025) are used,
  so the incomplete most-recent year(s) are excluded.
- **Citation age**: a citation in calendar year `y` for a paper published in year `Y` is
  assigned an age of `max(y - Y, 0) + 0.5` years (the midpoint of the citing year, treating
  `Y` as the start of the publication year; pre-/same-publication-year citations are floored
  to 0.5 so the log is defined).
- **Fit**: the log-normal parameters are estimated by maximizing the **right-truncated**
  likelihood (each observation weighted by `f(t) / F(trunc_age)`, with the truncation age
  `trunc_age = (truncation_year - Y) + 1`). This corrects the downward bias an uncorrected
  fit would have for younger papers whose right tail extends beyond the observation window.
  Implemented in pure Python (normal CDF via `math.erf`, Nelder-Mead optimizer); no SciPy
  or NumPy dependency.
- **Confidence interval on the peak timing**: a 95% **profile-likelihood** interval for the
  mode (`mode_ci_lo`, `mode_ci_hi`) is reported for every paper. This stays informative even
  when the point estimate is non-identifiable: for a paper still rising at the truncation
  boundary it yields a finite lower bound with an unbounded upper bound (`mode_ci_hi = inf`,
  i.e. "the peak is at least `mode_ci_lo` years out, 95% confidence"); for a paper that has
  peaked within the window it yields a normal two-sided interval.
- **`peak_beyond_window` flag (`*`)**: True when `mode_ci_hi` is unbounded (no finite upper
  confidence limit on the peak). For these papers the mode point estimate is only a **lower
  bound**; the search is boxed to a plausible region to keep it finite.
- **Skipped**: papers with fewer than 3 in-window citations, all in-window citations in a
  single year, or a degenerate fit.

Example output:

```
Log-normal citation-age fit (right-truncated MLE): 125 papers published 2011–2022, citations through 2025
  Citation age = (citing_year - pub_year) + 0.5 yr. Mode = peak citation age (yr); LogSD = sigma of ln(age).
  Skipped: papers with <3 in-window citations or all in one year.
  CI = 95% profile-likelihood interval on the peak; 'inf' = still rising
  (peak timing unbounded above); * marks those papers.

  Paper ID       Pub Cites    Mode  LogSD   95% CI (yr)  Title
  ------------- ---- ----- ------- ------ -------------  -----
  W2093693868   2014   223  40.00*   1.73      17.8-inf  Global and regional trends in greenhouse gas emi
  ...
  W2811133697   2018  2090    9.05   1.09       7.0-14.2  Net-zero emissions energy systems
  ...
```

## Testing

```bash
pytest
```
