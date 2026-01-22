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
            {"id": "W1", "cited_by_count": 100, "authorships": [{"author": {}}, {"author": {}}]},
        ],
        "meta": {"next_cursor": "cursor2"},
    }
    page2 = {
        "results": [
            {"id": "W2", "cited_by_count": 50, "authorships": [{"author": {}}]},
        ],
        "meta": {"next_cursor": None},
    }

    with patch.object(client.session, "get", side_effect=[
        _make_response(page1),
        _make_response(page2),
    ]):
        works = client.get_works("A5023888391")

    assert len(works) == 2
    assert works[0] == {"cited_by_count": 100, "num_authors": 2}
    assert works[1] == {"cited_by_count": 50, "num_authors": 1}


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
