from yk_review_agent.models.session import SessionCreateRequest
from yk_review_agent.services.session_store import session_store


def test_create_session_includes_snapshot_overview() -> None:
    session = session_store.create_session(
        SessionCreateRequest(
            user_id="demo-user",
            hospital_id="中国人民解放军医院301医院",
            hospital_name="中国人民解放军医院301医院",
            host_session_id="session-overview-test",
        )
    )

    assert session.overview is not None
    assert session.overview.hospital_name == "中国人民解放军医院301医院"
    assert session.overview.product_scope == "PGT-A"
    assert session.overview.embryo_count > 0
    assert session.overview.cycle_count > 0
    assert session.overview.snapshot_start
    assert session.overview.snapshot_end


def test_create_all_hospitals_session_uses_all_scope_overview() -> None:
    session = session_store.create_session(
        SessionCreateRequest(
            user_id="demo-user",
            hospital_id="中国人民解放军医院301医院",
            hospital_name="中国人民解放军医院301医院",
            host_session_id="session-all-hospitals-test",
            hospital_scope_mode="all",
            can_access_all_hospitals=True,
        )
    )

    assert session.hospital_scope_mode == "all"
    assert session.hospital_name == "全部医院"
    assert session.overview is not None
    assert session.overview.hospital_scope_mode == "all"
    assert "全部医院" in session.overview.summary
