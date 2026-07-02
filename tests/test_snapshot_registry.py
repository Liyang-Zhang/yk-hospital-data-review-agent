from yk_review_agent.services.snapshot_service import snapshot_service


def test_snapshot_metadata_includes_registered_products_and_sources() -> None:
    metadata = snapshot_service.get_snapshot_metadata()

    assert "PGT-A" in metadata.registered_products
    assert "PGT-SR" in metadata.registered_products
    assert any(source.product_code == "PGT-M" for source in metadata.source_summaries)
    assert any(source.execution_status == "executable" for source in metadata.source_summaries)


def test_snapshot_readiness_uses_current_pgta_snapshot() -> None:
    readiness = snapshot_service.build_data_readiness(
        "pgt_total_volume",
        {
            "hospital_id": "中国人民解放军医院301医院",
            "hospital_name": "中国人民解放军医院301医院",
            "time_range": "当前快照全部时间",
            "breakdown": "overall",
            "focus": "summary",
        },
    )

    assert readiness is not None
    assert readiness.status == "ready"
    assert readiness.record_count > 0
