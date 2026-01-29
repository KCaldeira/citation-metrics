import argparse
import sys

from citation_metrics.config import get_api_key
from citation_metrics.metrics import compute_all_metrics
from citation_metrics.openalex import OpenAlexClient


def main():
    parser = argparse.ArgumentParser(
        prog="citation-metrics",
        description="Compute alternative citation metrics for academic authors",
    )
    parser.add_argument(
        "identifier",
        nargs="?",
        default="0000-0002-4591-643X",
        help="Author ORCID or OpenAlex ID (default: 0000-0002-4591-643X)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show per-paper breakdown",
    )
    args = parser.parse_args()

    api_key = get_api_key()
    client = OpenAlexClient(api_key)

    try:
        author = client.get_author(args.identifier)
    except Exception as e:
        print(f"Error fetching author: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Author: {author['display_name']} ({author['id']})")

    works = client.get_works(author["id"])
    print(f"Papers: {len(works)}")

    if args.verbose:
        print("\nPer-paper breakdown (top 50 by citations):")
        print(f"  {'Citations':>10}  {'Authors':>8}  {'Fractional':>11}")
        print(f"  {'─'*10}  {'─'*8}  {'─'*11}")
        sorted_works = sorted(works, key=lambda w: w["cited_by_count"], reverse=True)
        for w in sorted_works[:50]:
            frac = w["cited_by_count"] / w["num_authors"] if w["num_authors"] > 0 else 0
            print(f"  {w['cited_by_count']:>10}  {w['num_authors']:>8}  {frac:>11.1f}")

    metrics = compute_all_metrics(works)

    def fmt(v):
        """Format as integer if whole, else 1 decimal place."""
        if v == int(v):
            return str(int(v))
        return f"{v:.1f}"

    num_papers = metrics['num_papers']
    frac_papers = metrics['fractional_papers']

    h = metrics['h_index']
    wh = metrics['weighted_h']
    cdh = metrics['citdiv_h']

    print()
    print(f"  H-index (computed):        {h:>4}")
    print(f"  H-index (OpenAlex):        {author['h_index_openalex']:>4}")
    print(f"  H / papers:              {metrics['h_per_paper']:>6.3f}  ({fmt(h)} / {fmt(num_papers)})")
    print()
    print(f"  Weighted H-index:          {wh:>4}")
    print(f"  Weighted H / frac papers:{metrics['weighted_h_per_frac_paper']:>6.3f}  ({fmt(wh)} / {fmt(frac_papers)})")
    print()
    print(f"  Cit-divided H-index:       {cdh:>4}")
    print(f"  Cit-divided H / papers:  {metrics['citdiv_h_per_paper']:>6.3f}  ({fmt(cdh)} / {fmt(num_papers)})")


if __name__ == "__main__":
    main()
