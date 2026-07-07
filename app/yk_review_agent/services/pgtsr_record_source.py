from __future__ import annotations

from functools import lru_cache
from typing import Protocol

from yk_review_agent.services.pgtsr_sqlite import PGTSRSQLiteRepository


class PGTSRRecordSource(Protocol):
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
def get_pgtsr_record_source() -> PGTSRRecordSource:
    return PGTSRSQLiteRepository.from_settings()


def clear_pgtsr_record_source_cache() -> None:
    get_pgtsr_record_source.cache_clear()
