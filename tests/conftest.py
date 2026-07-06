from __future__ import annotations

from pathlib import Path

import pytest

from yk_review_agent.core.config import settings
from yk_review_agent.services.intent_parser import intent_parser_service
from yk_review_agent.services.pgta_record_source import clear_pgta_record_source_cache
from yk_review_agent.services.pgta_sqlite import PGTAExcelImporter, PGTASourceConfig
from yk_review_agent.services.product_snapshot_registry import get_snapshot_registry
from yk_review_agent.services.question_normalizer import question_normalizer


@pytest.fixture(scope="session", autouse=True)
def use_trimmed_snapshot_bundle() -> None:
    snapshot_dir = Path(__file__).parent / "fixtures" / "snapshots"
    original_pgta_file = settings.pgta_detail_file
    original_snapshot_backend = settings.snapshot_backend
    original_snapshot_db_url = settings.snapshot_db_url
    original_pgtah_file = settings.pgtah_snapshot_file
    original_pgtsr_file = settings.pgtsr_snapshot_file
    original_pgtm_file = settings.pgtm_snapshot_file
    original_llm_api_key = settings.llm_api_key
    original_llm_agent = intent_parser_service._llm_agent
    snapshot_db_path = (snapshot_dir / "test-snapshot.db").resolve()

    settings.pgta_detail_file = str((snapshot_dir / "pgta-test-snapshot.xlsx").resolve())
    settings.snapshot_backend = "sqlite"
    settings.snapshot_db_url = f"sqlite+pysqlite:///{snapshot_db_path}"
    settings.pgtah_snapshot_file = str((snapshot_dir / "pgtah-test-snapshot.xlsx").resolve())
    settings.pgtsr_snapshot_file = str((snapshot_dir / "pgtsr-test-snapshot.xlsx").resolve())
    settings.pgtm_snapshot_file = str((snapshot_dir / "pgtm-test-snapshot.xlsx").resolve())
    settings.llm_api_key = ""
    intent_parser_service._llm_agent = None
    if snapshot_db_path.exists():
        snapshot_db_path.unlink()
    PGTAExcelImporter(
        settings.snapshot_db_url,
        source_configs=[
            PGTASourceConfig(
                snapshot_year=2025,
                snapshot_half="test",
                file_path=settings.pgta_detail_file,
                sheet_name="2025年-数据",
                column_map={},
            )
        ],
    ).rebuild()

    clear_pgta_record_source_cache()
    get_snapshot_registry.cache_clear()
    question_normalizer._hospital_alias_map = None
    yield
    settings.pgta_detail_file = original_pgta_file
    settings.snapshot_backend = original_snapshot_backend
    settings.snapshot_db_url = original_snapshot_db_url
    settings.pgtah_snapshot_file = original_pgtah_file
    settings.pgtsr_snapshot_file = original_pgtsr_file
    settings.pgtm_snapshot_file = original_pgtm_file
    settings.llm_api_key = original_llm_api_key
    intent_parser_service._llm_agent = original_llm_agent
    clear_pgta_record_source_cache()
    get_snapshot_registry.cache_clear()
    question_normalizer._hospital_alias_map = None
    if snapshot_db_path.exists():
        snapshot_db_path.unlink()
