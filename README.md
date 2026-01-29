# Citation Metrics

Compute alternative citation metrics for academic authors using the [OpenAlex API](https://openalex.org/).

## Metrics

- **H-index** - standard H-index (verified against OpenAlex's pre-computed value)
- **Weighted H-index** - each paper's credit = `1 / num_authors`, cumulative fractional authorship used
- **Cit-divided H-index** - each paper's value = `cited_by_count / num_authors`, then H-index applied

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## API Key Setup

Get a free API key at https://openalex.org/settings/api, then:

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

## Testing

```bash
pytest
```
