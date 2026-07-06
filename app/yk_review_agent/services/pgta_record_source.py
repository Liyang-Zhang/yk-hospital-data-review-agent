from __future__ import annotations

from functools import lru_cache
from typing import Protocol

from yk_review_agent.core.config import settings
from yk_review_agent.services.pgta_detail_dataset import get_pgta_dataset
from yk_review_agent.services.pgta_sqlite import PGTASQLiteRepository


class PGTARecordSource(Protocol):
    @property
    def records(self): ...

    @property
    def eligible_records(self): ...

    @property
    def stat_month_range(self): ...

    @property
    def hospitals(self): ...

    def filter_records(self, **kwargs): ...


@lru_cache(maxsize=1)
def get_pgta_record_source() -> PGTARecordSource:
    backend = (settings.snapshot_backend or "sqlite").strip().lower()
    if backend == "excel":
        return get_pgta_dataset()
    if backend != "sqlite":
        raise RuntimeError(f"Unsupported snapshot backend: {settings.snapshot_backend}")
    return PGTASQLiteRepository.from_settings()


def clear_pgta_record_source_cache() -> None:
    get_pgta_record_source.cache_clear()
    get_pgta_dataset.cache_clear()
