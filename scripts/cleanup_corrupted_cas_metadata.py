"""Delete corrupted CAS test artifacts from a shared integration-test environment."""

from __future__ import annotations

import argparse

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

from albert import Albert, AlbertClientCredentials
from tests.cas_cleanup import (
    delete_corrupted_cas_in_recent_pages,
    delete_sup1894_cas_custom_fields,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--env-file",
        default=".env",
        help="Dotenv file to load before reading Albert credentials.",
    )
    parser.add_argument(
        "--max-clean-pages",
        type=int,
        default=5,
        help="Stop after this many consecutive recent pages with no corrupted CAS records.",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=50,
        help="Maximum number of CAS pages to scan.",
    )
    args = parser.parse_args()

    if load_dotenv is not None:
        load_dotenv(args.env_file)

    credentials = AlbertClientCredentials.from_env(
        client_id_env="ALBERT_CLIENT_ID_SDK",
        client_secret_env="ALBERT_CLIENT_SECRET_SDK",
        base_url_env="ALBERT_BASE_URL",
    )
    if credentials is None:
        raise SystemExit(
            "Missing ALBERT_CLIENT_ID_SDK, ALBERT_CLIENT_SECRET_SDK, or ALBERT_BASE_URL."
        )

    client = Albert(auth_manager=credentials, retries=3)
    removed_fields = delete_sup1894_cas_custom_fields(client)
    removed_cas = delete_corrupted_cas_in_recent_pages(
        client,
        max_clean_pages=args.max_clean_pages,
        max_pages=args.max_pages,
    )

    if removed_cas:
        print(f"Deleted {len(removed_cas)} corrupted CAS record(s): {removed_cas}")
    else:
        print("No corrupted CAS records found in recent pages.")

    if removed_fields:
        print(f"Deleted {len(removed_fields)} sup1894 custom field(s): {removed_fields}")
    else:
        print("No sup1894 CAS custom fields found.")


if __name__ == "__main__":
    main()
