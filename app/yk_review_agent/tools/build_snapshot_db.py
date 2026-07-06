from __future__ import annotations

import argparse
import json

from yk_review_agent.core.config import settings
from yk_review_agent.services.pgta_sqlite import PGTAExcelImporter, inspect_pgta_snapshot_db


def main() -> None:
    parser = argparse.ArgumentParser(description="Build snapshot SQLite databases from Excel sources.")
    parser.add_argument("--product", choices=["pgta", "all"], default="pgta")
    args = parser.parse_args()

    if args.product in {"pgta", "all"}:
        importer = PGTAExcelImporter(settings.snapshot_db_url)
        importer.rebuild()
        summary = inspect_pgta_snapshot_db(settings.snapshot_db_url)
        print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
