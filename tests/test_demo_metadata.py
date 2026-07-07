from yk_review_agent.api.routes.demo import demo_metadata


def test_demo_metadata_single_access_mode_is_locked_to_one_hospital() -> None:
    payload = demo_metadata(product_scope="PGT-A", access_mode="single")

    assert payload["can_access_all_hospitals"] is False
    assert payload["default_hospital"] is not None
    assert len(payload["hospitals"]) == 1
    assert payload["hospitals"][0]["hospital_id"] == payload["default_hospital"]["hospital_id"]


def test_demo_metadata_all_access_mode_exposes_multiple_hospitals() -> None:
    payload = demo_metadata(product_scope="PGT-SR", access_mode="all")

    assert payload["can_access_all_hospitals"] is True
    assert payload["default_hospital"] is not None
    assert len(payload["hospitals"]) > 1
