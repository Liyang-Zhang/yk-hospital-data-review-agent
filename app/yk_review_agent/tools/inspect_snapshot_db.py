from __future__ import annotations

import argparse
import json

from yk_review_agent.core.config import settings
from yk_review_agent.services.pgta_sqlite import inspect_pgta_snapshot_db
from yk_review_agent.services.pgtsr_sqlite import inspect_pgtsr_snapshot_db


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect snapshot SQLite databases.")
    parser.add_argument("--product", choices=["pgta", "pgtsr"], default="pgta")
    args = parser.parse_args()

    if args.product == "pgta":
        summary = inspect_pgta_snapshot_db(settings.snapshot_db_url)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    elif args.product == "pgtsr":
        summary = inspect_pgtsr_snapshot_db(settings.snapshot_db_url)
        print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
