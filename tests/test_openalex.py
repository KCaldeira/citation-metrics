from unittest.mock import patch, MagicMock
from citation_metrics.openalex import OpenAlexClient


def _make_response(json_data, status_code=200):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.raise_for_status.return_value = None
    return resp


def test_get_author_by_openalex_id():
    client = OpenAlexClient("test_key")
    mock_data = {
        "id": "https://openalex.org/A5023888391",
        "display_name": "Ken Caldeira",
        "works_count": 312,
        "summary_stats": {"h_index": 82},
    }
    with patch.object(client.session, "get", return_value=_make_response(mock_data)):
        author = client.get_author("A5023888391")

    assert author["id"] == "A5023888391"
    assert author["display_name"] == "Ken Caldeira"
    assert author["h_index_openalex"] == 82


def test_get_author_by_orcid():
    client = OpenAlexClient("test_key")
    mock_data = {
        "id": "https://openalex.org/A5023888391",
        "display_name": "Ken Caldeira",
        "works_count": 312,
        "summary_stats": {"h_index": 82},
    }
    with patch.object(client.session, "get", return_value=_make_response(mock_data)) as mock_get:
        client.get_author("0000-0002-4375-4346")

    call_url = mock_get.call_args[0][0]
    assert "orcid:0000-0002-4375-4346" in call_url


def test_get_works_pagination():
    client = OpenAlexClient("test_key")

    page1 = {
        "results": [
            {
                "id": "https://openalex.org/W1",
                "cited_by_count": 100,
                "authorships": [{"author": {}}, {"author": {}}],
                "publication_year": 2014,
                "title": "Paper One",
                "counts_by_year": [
                    {"year": 2015, "cited_by_count": 12},
                    {"year": 2016, "cited_by_count": 8},
                ],
            },
        ],
        "meta": {"next_cursor": "cursor2"},
    }
    page2 = {
        "results": [
            {
                "id": "https://openalex.org/W2",
                "cited_by_count": 50,
                "authorships": [{"author": {}}],
                "publication_year": 2013,
                "title": "Paper Two",
                "counts_by_year": [],
            },
        ],
        "meta": {"next_cursor": None},
    }

    with patch.object(client.session, "get", side_effect=[
        _make_response(page1),
        _make_response(page2),
    ]):
        works = client.get_works("A5023888391")

    assert len(works) == 2
    assert works[0] == {
        "id": "W1",
        "cited_by_count": 100,
        "num_authors": 2,
        "publication_year": 2014,
        "title": "Paper One",
        "counts_by_year": {2015: 12, 2016: 8},
    }
    assert works[1] == {
        "id": "W2",
        "cited_by_count": 50,
        "num_authors": 1,
        "publication_year": 2013,
        "title": "Paper Two",
        "counts_by_year": {},
    }


def test_retry_on_429():
    client = OpenAlexClient("test_key")

    rate_limited = MagicMock()
    rate_limited.status_code = 429

    success_data = {
        "id": "https://openalex.org/A5023888391",
        "display_name": "Test Author",
        "works_count": 10,
        "summary_stats": {"h_index": 5},
    }

    with patch.object(client.session, "get", side_effect=[
        rate_limited,
        _make_response(success_data),
    ]):
        with patch("citation_metrics.openalex.time.sleep"):
            author = client.get_author("A5023888391")

    assert author["display_name"] == "Test Author"


def test_stale_key_falls_back_to_keyless():
    client = OpenAlexClient("stale_key")

    unauthorized = MagicMock()
    unauthorized.status_code = 401

    success_data = {
        "id": "https://openalex.org/A5023888391",
        "display_name": "Test Author",
        "works_count": 10,
        "summary_stats": {"h_index": 5},
    }

    with patch.object(client.session, "get", side_effect=[
        unauthorized,
        _make_response(success_data),
    ]) as mock_get:
        author = client.get_author("A5023888391")

    assert author["display_name"] == "Test Author"
    # The key was dropped after the 401; the retry request carries no api_key.
    assert client.api_key is None
    retry_params = mock_get.call_args_list[1].kwargs["params"]
    assert "api_key" not in retry_params
    assert retry_params["mailto"] == OpenAlexClient.MAILTO
