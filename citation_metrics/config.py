import os
from dotenv import load_dotenv


def get_api_key():
    """Load OpenAlex API key from environment or .env file."""
    load_dotenv()
    api_key = os.environ.get("OPENALEX_API_KEY")
    if not api_key:
        raise SystemExit(
            "Error: OPENALEX_API_KEY not set.\n"
            "Get a free key at https://openalex.org/settings/api\n"
            "Then set it in a .env file or as an environment variable."
        )
    return api_key
