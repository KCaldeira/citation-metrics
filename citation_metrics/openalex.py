import time
import requests


class OpenAlexClient:
    BASE_URL = "https://api.openalex.org"
    MAX_RETRIES = 3

    MAILTO = "ken.caldeira@gatesventures.com"

    def __init__(self, api_key=None):
        self.api_key = api_key
        self.session = requests.Session()

    def _request(self, endpoint, params=None):
        """Make a request with retry on 429.

        Always identifies via the polite pool (mailto). The API key is optional
        and only raises rate limits. If a key is set but rejected (401, e.g. a
        stale key), the key is dropped and the request retried keyless so the
        tool keeps working via the free polite pool.
        """
        if params is None:
            params = {}
        params["mailto"] = self.MAILTO
        if self.api_key:
            params["api_key"] = self.api_key
        url = f"{self.BASE_URL}{endpoint}"

        for attempt in range(self.MAX_RETRIES):
            resp = self.session.get(url, params=params)
            if resp.status_code == 429:
                wait = 2 ** attempt
                time.sleep(wait)
                continue
            if resp.status_code == 401 and "api_key" in params:
                # Stale/invalid key: fall back to the keyless polite pool.
                self.api_key = None
                params.pop("api_key")
                continue
            resp.raise_for_status()
            return resp.json()

        raise RuntimeError(f"API request failed after {self.MAX_RETRIES} retries")

    def get_author(self, identifier):
        """Fetch author metadata.

        identifier: ORCID (e.g. '0000-0002-4375-4346') or OpenAlex ID (e.g. 'A5023888391')
        """
        if identifier.startswith("A") and identifier[1:].isdigit():
            endpoint = f"/authors/{identifier}"
        else:
            endpoint = f"/authors/orcid:{identifier}"

        data = self._request(endpoint)
        return {
            "id": data["id"].split("/")[-1],
            "display_name": data["display_name"],
            "works_count": data.get("works_count", 0),
            "h_index_openalex": data.get("summary_stats", {}).get("h_index"),
        }

    def get_works(self, author_id):
        """Fetch all works for an author using cursor pagination.

        Returns list of dicts with id, cited_by_count, num_authors,
        publication_year, title, and counts_by_year (dict of year -> citations).
        """
        works = []
        cursor = "*"

        while cursor:
            data = self._request("/works", params={
                "filter": f"author.id:{author_id}",
                "per_page": "200",
                "cursor": cursor,
                "select": "id,cited_by_count,authorships,publication_year,title,counts_by_year",
            })

            for work in data.get("results", []):
                works.append({
                    "id": work["id"].split("/")[-1],
                    "cited_by_count": work.get("cited_by_count", 0),
                    "num_authors": len(work.get("authorships", [])),
                    "publication_year": work.get("publication_year"),
                    "title": work.get("title"),
                    # OpenAlex returns [{"year": 2015, "cited_by_count": 12}, ...]
                    "counts_by_year": {
                        c["year"]: c["cited_by_count"]
                        for c in work.get("counts_by_year", [])
                    },
                })

            meta = data.get("meta", {})
            cursor = meta.get("next_cursor")

        return works
