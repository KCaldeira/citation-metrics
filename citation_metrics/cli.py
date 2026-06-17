import argparse
import csv
import datetime
import sys

from citation_metrics.config import get_api_key
from citation_metrics.metrics import compute_all_metrics, compute_citation_aging
from citation_metrics.openalex import OpenAlexClient


def run_aging(args, author, works):
    """Compute and display the citation-aging ratio metric."""
    n = args.window
    current_year = datetime.date.today().year
    rows = compute_citation_aging(works, n, current_year)

    lo, hi = current_year - 15, current_year - 2 * n
    print(
        f"\nCitation aging (window n={n}): "
        f"{len(rows)} papers published {lo}–{hi} "
        f"({2 * n}–15 years ago)"
    )
    print(
        "  First = citations in years Y..Y+{0}; Second = years Y+{1}..Y+{2}; "
        "Ratio = First/Second.".format(n - 1, n, 2 * n - 1)
    )

    def fmt_ratio(r):
        return "inf" if r == float("inf") else f"{r:.2f}"

    def fmt_lag(x):
        return "" if x is None else f"{x:.1f}"

    header = (
        f"  {'Paper ID':<13} {'Pub':>4} {'First':>6} {'Second':>6} "
        f"{'Ratio':>6} {'MeanLag':>7}  Title"
    )
    print()
    print(header)
    print(f"  {'-' * 13} {'-' * 4} {'-' * 6} {'-' * 6} {'-' * 6} {'-' * 7}  {'-' * 5}")
    for r in rows:
        title = (r["title"] or "")[:60]
        print(
            f"  {r['id']:<13} {r['publication_year']:>4} {r['first']:>6} "
            f"{r['second']:>6} {fmt_ratio(r['ratio']):>6} "
            f"{fmt_lag(r['mean_lag']):>7}  {title}"
        )

    csv_path = args.csv or f"aging_{author['id']}.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "paper_id", "publication_year",
            f"citations_first_{n}yr", f"citations_second_{n}yr",
            "ratio", "mean_lag_years", "title",
        ])
        for r in rows:
            ratio = "inf" if r["ratio"] == float("inf") else round(r["ratio"], 4)
            mean_lag = "" if r["mean_lag"] is None else round(r["mean_lag"], 3)
            writer.writerow([
                r["id"], r["publication_year"], r["first"], r["second"],
                ratio, mean_lag, r["title"] or "",
            ])
    print(f"\nWrote {len(rows)} rows to {csv_path}")


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
    parser.add_argument(
        "--aging",
        action="store_true",
        help="Compute the citation-aging ratio metric (first n years vs. next n years)",
    )
    parser.add_argument(
        "--window",
        type=int,
        default=5,
        metavar="N",
        help="Aging window size in years (default: 5)",
    )
    parser.add_argument(
        "--csv",
        metavar="PATH",
        help="CSV output path for --aging (default: aging_<authorid>.csv)",
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

    if args.aging:
        run_aging(args, author, works)
        return

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
