import argparse
import csv
import sys

from citation_metrics.config import get_api_key
from citation_metrics.metrics import compute_all_metrics, compute_citation_lognormal
from citation_metrics.openalex import OpenAlexClient


def run_lognormal(args, author, works):
    """Fit a log-normal to each paper's citation-age distribution and report it."""
    first_year, last_year = args.first_year, args.last_year
    truncation_year = args.truncation_year
    rows = compute_citation_lognormal(works, first_year, last_year, truncation_year)

    print(
        f"\nLog-normal citation-age fit (right-truncated MLE): {len(rows)} papers "
        f"published {first_year}–{last_year}, citations through {truncation_year}"
    )
    print(
        "  Citation age = (citing_year - pub_year) + 0.5 yr. "
        "Mode = peak citation age (yr); LogSD = sigma of ln(age)."
    )
    print("  Skipped: papers with <3 in-window citations or all in one year.")
    print("  CI = 95% profile-likelihood interval on the peak; 'inf' = still rising")
    print("  (peak timing unbounded above); * marks those papers.")

    def fmt_ci(lo, hi):
        hi_s = "inf" if hi == float("inf") else f"{hi:.1f}"
        return f"{lo:.1f}-{hi_s}"

    header = (
        f"  {'Paper ID':<13} {'Pub':>4} {'Cites':>5} {'Mode':>7} {'LogSD':>6} "
        f"{'95% CI (yr)':>13}  Title"
    )
    print()
    print(header)
    print(f"  {'-' * 13} {'-' * 4} {'-' * 5} {'-' * 7} {'-' * 6} {'-' * 13}  {'-' * 5}")
    for r in rows:
        title = (r["title"] or "")[:48]
        mode = f"{r['mode']:.2f}" + ("*" if r["peak_beyond_window"] else "")
        ci = fmt_ci(r["mode_ci_lo"], r["mode_ci_hi"])
        print(
            f"  {r['id']:<13} {r['publication_year']:>4} {r['n_citations']:>5} "
            f"{mode:>7} {r['log_sd']:>6.2f} {ci:>13}  {title}"
        )

    csv_path = args.csv or f"lognormal_{author['id']}.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "paper_id", "publication_year", "n_citations",
            "mode_years", "mode_ci_lo", "mode_ci_hi",
            "log_sd", "logmean", "peak_beyond_window", "title",
        ])
        for r in rows:
            ci_hi = "inf" if r["mode_ci_hi"] == float("inf") else round(r["mode_ci_hi"], 4)
            writer.writerow([
                r["id"], r["publication_year"], r["n_citations"],
                round(r["mode"], 4), round(r["mode_ci_lo"], 4), ci_hi,
                round(r["log_sd"], 4), round(r["logmean"], 4),
                r["peak_beyond_window"], r["title"] or "",
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
        "--lognormal",
        action="store_true",
        help="Fit a log-normal to each paper's citation-age distribution",
    )
    parser.add_argument(
        "--first-year",
        type=int,
        default=2011,
        metavar="YEAR",
        help="Earliest publication year to include (default: 2011)",
    )
    parser.add_argument(
        "--last-year",
        type=int,
        default=2022,
        metavar="YEAR",
        help="Latest publication year to include (default: 2022)",
    )
    parser.add_argument(
        "--truncation-year",
        type=int,
        default=2025,
        metavar="YEAR",
        help="Last citation year treated as complete; later years are excluded "
             "and the fit is right-truncated here (default: 2025)",
    )
    parser.add_argument(
        "--csv",
        metavar="PATH",
        help="CSV output path for --lognormal (default: lognormal_<authorid>.csv)",
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

    if args.lognormal:
        run_lognormal(args, author, works)
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
