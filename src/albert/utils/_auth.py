import os


def default_albert_base_url() -> str:
    return os.getenv("ALBERT_BASE_URL") or "https://app.albertinvent.com"
