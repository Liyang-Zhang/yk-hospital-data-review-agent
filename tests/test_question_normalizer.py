from yk_review_agent.services.question_normalizer import QuestionNormalizer


def test_normalizer_expands_short_year_cross_month_and_age_phrases() -> None:
    normalizer = QuestionNormalizer(
        hospital_names=["山西省妇幼保健院"],
    )

    normalized = normalizer.normalize("山西妇幼在25年7月到10月大于35岁患者的整倍体率")

    assert normalized.normalized_message == "山西省妇幼保健院在2025年7月到2025年10月>35岁患者的整倍体率"


def test_normalizer_handles_missing_age_alias_without_workbook_scan() -> None:
    normalizer = QuestionNormalizer(hospital_names=["中国人民解放军医院301医院"])

    normalized = normalizer.normalize("301医院年龄未填写患者的送检量")

    assert "未填写年龄" in normalized.normalized_message
