import os
from dotenv import load_dotenv


def get_api_key():
    """Load OpenAlex API key from environment or .env file.

    The key is optional: OpenAlex works without one via the free "polite pool"
    (identified by a mailto). A key only raises rate limits. Returns None when
    unset so the client falls back to keyless requests.
    """
    load_dotenv()
    return os.environ.get("OPENALEX_API_KEY") or None
