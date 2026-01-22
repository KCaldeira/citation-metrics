import time
import requests


class OpenAlexClient:
    BASE_URL = "https://api.openalex.org"
    MAX_RETRIES = 3

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
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp.json()

        raise RuntimeError(f"API rate limited after {self.MAX_RETRIES} retries")

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

        Returns list of dicts with cited_by_count and num_authors.
        """
        works = []
        cursor = "*"

        while cursor:
            data = self._request("/works", params={
                "filter": f"author.id:{author_id}",
                "per_page": "200",
                "cursor": cursor,
                "select": "id,cited_by_count,authorships",
            })

            for work in data.get("results", []):
                works.append({
                    "cited_by_count": work.get("cited_by_count", 0),
                    "num_authors": len(work.get("authorships", [])),
                })

            meta = data.get("meta", {})
            cursor = meta.get("next_cursor")

        return works
