from yk_review_agent.services.pgtsr_record_source import get_pgtsr_record_source


def test_pgtsr_sqlite_repository_loads_rows() -> None:
    repo = get_pgtsr_record_source()

    assert repo.records
    assert repo.stat_month_range[0] <= repo.stat_month_range[1]
    assert repo.hospitals


def test_pgtsr_sqlite_repository_normalizes_zero_age_to_missing() -> None:
    repo = get_pgtsr_record_source()

    assert any(record.patient_age is None for record in repo.records)
    assert any(record.spouse_age is None for record in repo.records)


def test_pgtsr_sqlite_repository_attaches_project_fields() -> None:
    repo = get_pgtsr_record_source()

    assert any(record.sr_clinical_type for record in repo.records)
    assert any(record.next_step_screening for record in repo.records)
