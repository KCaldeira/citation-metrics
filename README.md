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
- **`peak_beyond_window` flag (`*`)**: when citations are still rising at the truncation
  boundary the truncated fit is non-identifiable; the search is boxed to a plausible region
  and such papers are flagged. For them the reported mode is a **lower bound**, not a
  reliable point estimate.
- **Skipped**: papers with fewer than 3 in-window citations, all in-window citations in a
  single year, or a degenerate fit.

Example output:

```
Log-normal citation-age fit (right-truncated MLE): 125 papers published 2011–2022, citations through 2025
  Citation age = (citing_year - pub_year) + 0.5 yr. Mode = peak citation age (yr); LogSD = sigma of ln(age).
  Skipped: papers with <3 in-window citations or all in one year.
  * = peak beyond observed window (still rising; mode is a lower bound).

  Paper ID       Pub Cites    Mode  LogSD  Title
  ------------- ---- ----- ------- ------  -----
  W2093693868   2014   223  40.00*   1.73  Global and regional trends in greenhouse gas emissions fro
  ...
  W2029454019   2013   140    9.01   1.17  Effect of Temperature on Photosynthesis and Growth in Mari
  ...
```

## Testing

```bash
pytest
```
