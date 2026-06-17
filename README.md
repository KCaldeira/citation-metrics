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

Fits a log-normal to each paper's distribution of citation ages and reports, per paper,
the **mode** (most-likely citation age, in years) and the **log standard deviation**
(sigma of `ln(age)`). Results print as a table and are written to a CSV
(`lognormal_<authorid>.csv`).

```bash
citation-metrics A5052404353 --lognormal

# Tune the age band and output path
citation-metrics A5052404353 --lognormal --min-age 5 --max-age 15 --csv out.csv
```

How it works:

- **Papers considered**: published `--min-age` to `--max-age` years ago (default 5-15).
  The upper bound keeps each paper within OpenAlex's ~15-year `counts_by_year` coverage so
  the early part of the curve is not truncated.
- **Citation age**: a citation in calendar year `y` for a paper published in year `Y` is
  assigned an age of `max(y - Y, 0) + 0.5` years (the midpoint of the citing year;
  pre-/same-publication-year citations are floored to 0.5 so the log is defined).
- **Fit**: closed-form log-normal maximum-likelihood estimate (weighted mean and standard
  deviation of `ln(age)`); `mode = exp(mu - sigma^2)`. No SciPy dependency.
- **Skipped**: papers with fewer than 3 citations, all citations in a single year, or a
  degenerate fit (`sigma == 0`).

Example output:

```
Log-normal citation-age fit: 116 papers published 2011-2021 (5-15 years ago)
  Citation age = (citing_year - pub_year) + 0.5 yr. Mode = peak citation age (yr); LogSD = sigma of ln(age).
  Skipped: papers with <3 citations or all citations in one year.

  Paper ID       Pub Cites   Mode  LogSD  Title
  ------------- ---- ----- ------ ------  -----
  W1097101551   2015   128   5.49   0.45  Impacts of global warming on residential heating and cooli
  W2046376516   2011   185   5.34   0.54  Dependence of climate forcing and response on the altitude
  ...
```

## Testing

```bash
pytest
```
