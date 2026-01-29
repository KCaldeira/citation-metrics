#!/usr/bin/env python3
"""
Fetch ORCID IDs of all authors from papers cited in a given author's 2025 publications.
"""

import time
import requests
from citation_metrics.config import get_api_key


class OpenAlexClient:
    BASE_URL = "https://api.openalex.org"
    MAX_RETRIES = 5

    def __init__(self, api_key):
        self.api_key = api_key
        self.session = requests.Session()

    def _request(self, endpoint, params=None):
        """Make a request with retry on 429."""
        if params is None:
            params = {}
        params["api_key"] = self.api_key
        url = f"{self.BASE_URL}{endpoint}"

        for attempt in range(self.MAX_RETRIES):
            resp = self.session.get(url, params=params)
            if resp.status_code == 429:
                wait = 2 ** attempt
                print(f"  Rate limited, waiting {wait}s...")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp.json()

        raise RuntimeError(f"API rate limited after {self.MAX_RETRIES} retries")

    def get_author_openalex_id(self, orcid):
        """Get OpenAlex ID from ORCID."""
        data = self._request(f"/authors/orcid:{orcid}")
        return data["id"].split("/")[-1]

    def get_works_by_years(self, author_id, start_year, end_year):
        """Fetch works from a year range for an author, including referenced_works."""
        works = []
        cursor = "*"

        while cursor:
            data = self._request("/works", params={
                "filter": f"author.id:{author_id},publication_year:{start_year}-{end_year}",
                "per_page": "200",
                "cursor": cursor,
                "select": "id,title,publication_year,referenced_works",
            })

            for work in data.get("results", []):
                works.append({
                    "id": work.get("id", "").split("/")[-1],
                    "title": work.get("title", "Unknown"),
                    "referenced_works": [w.split("/")[-1] for w in work.get("referenced_works", [])],
                })

            meta = data.get("meta", {})
            cursor = meta.get("next_cursor")

        return works

    def get_work_authors(self, work_id):
        """Fetch authors for a specific work, returning ORCID IDs where available."""
        try:
            data = self._request(f"/works/{work_id}", params={
                "select": "id,title,authorships",
            })
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                return []
            raise

        authors = []
        for authorship in data.get("authorships", []):
            author = authorship.get("author", {})
            author_id = author.get("id", "").split("/")[-1] if author.get("id") else None
            orcid = author.get("orcid")
            if orcid:
                orcid = orcid.replace("https://orcid.org/", "")
            authors.append({
                "openalex_id": author_id,
                "orcid": orcid,
                "display_name": author.get("display_name"),
            })
        return authors


def main():
    author_id = "A5052404353"  # Ken Caldeira's OpenAlex ID

    print(f"Fetching data for OpenAlex ID: {author_id}")
    api_key = get_api_key()
    client = OpenAlexClient(api_key)

    # Get 2025 works
    print("\nFetching 2025 publications...")
    works = client.get_works_by_years(author_id, 2025, 2025)
    print(f"Found {len(works)} publications in 2025")

    if not works:
        print("No publications found.")
        return

    # Collect all referenced work IDs
    all_referenced_ids = set()
    for work in works:
        print(f"\n  '{work['title'][:60]}...' cites {len(work['referenced_works'])} papers")
        all_referenced_ids.update(work['referenced_works'])

    print(f"\nTotal unique referenced papers: {len(all_referenced_ids)}")

    # Fetch authors for each referenced work
    print("\nFetching author information for cited papers...")
    all_orcids = set()
    all_authors = []  # List of (orcid, openalex_id, name) tuples

    for i, work_id in enumerate(all_referenced_ids):
        if (i + 1) % 50 == 0:
            print(f"  Processed {i + 1}/{len(all_referenced_ids)} cited papers...")

        authors = client.get_work_authors(work_id)
        for author in authors:
            if author['orcid']:
                all_orcids.add(author['orcid'])
                all_authors.append((author['orcid'], author['openalex_id'], author['display_name']))

    print(f"\nProcessed all {len(all_referenced_ids)} cited papers")

    # Deduplicate authors
    unique_authors = {}
    for orcid, openalex_id, name in all_authors:
        if orcid not in unique_authors:
            unique_authors[orcid] = (openalex_id, name)

    # Output results
    print(f"\n{'='*60}")
    print(f"RESULTS: Found {len(unique_authors)} unique authors with ORCID IDs")
    print(f"{'='*60}\n")

    # Write to file
    output_file = "cited_author_orcids.txt"
    with open(output_file, "w") as f:
        f.write("# ORCID IDs of authors from papers cited in 2025 publications (OpenAlex ID: A5052404353)\n")
        f.write(f"# Total unique authors with ORCID: {len(unique_authors)}\n")
        f.write("# Format: ORCID_ID | OpenAlex_ID | Display_Name\n\n")

        for orcid in sorted(unique_authors.keys()):
            openalex_id, name = unique_authors[orcid]
            f.write(f"{orcid} | {openalex_id} | {name}\n")

    print(f"Results written to: {output_file}")

    # Also print first 20 as sample
    print("\nSample (first 20 authors):")
    for orcid in sorted(unique_authors.keys())[:20]:
        openalex_id, name = unique_authors[orcid]
        print(f"  {orcid} - {name}")

    if len(unique_authors) > 20:
        print(f"  ... and {len(unique_authors) - 20} more (see {output_file})")


if __name__ == "__main__":
    main()
