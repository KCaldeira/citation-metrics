# Citation Metrics

Compute alternative citation metrics for academic authors using the [OpenAlex API](https://openalex.org/).

## Metrics

- **H-index** - standard H-index (verified against OpenAlex's pre-computed value)
- **Fractional H-index** - each paper's credit = `cited_by_count / num_authors`, then the H-index algorithm is applied to those fractional values

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
citation-metrics 0000-0002-4375-4346

# By OpenAlex ID
citation-metrics A5023888391

# With per-paper breakdown
citation-metrics A5023888391 -v
```

Example output:

```
Author: Ken Caldeira (A5023888391)
Papers: 312

  H-index (computed):     82
  H-index (OpenAlex):     82
  Fractional H-index:     34
```

## Testing

```bash
pytest
```
