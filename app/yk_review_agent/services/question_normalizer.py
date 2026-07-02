from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from yk_review_agent.services.pgta_detail_dataset import get_pgta_dataset


@dataclass(frozen=True)
class NormalizedQuestion:
    raw_message: str
    normalized_message: str


class QuestionNormalizer:
    def __init__(
        self,
        *,
        hospital_names: Iterable[str] | None = None,
        seed_alias_map: dict[str, str] | None = None,
    ) -> None:
        self._hospital_names = tuple(hospital_names) if hospital_names is not None else None
        self._seed_alias_map = dict(seed_alias_map or {"山西妇幼": "山西省妇幼保健院"})
        self._hospital_alias_map: dict[str, str] | None = None

    def normalize(self, message: str) -> NormalizedQuestion:
        normalized = message.strip()
        normalized = self._normalize_short_year(normalized)
        normalized = self._normalize_cross_month_range(normalized)
        normalized = self._normalize_age_expression(normalized)
        normalized = self._normalize_hospital_alias(normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return NormalizedQuestion(raw_message=message, normalized_message=normalized)

    def _normalize_short_year(self, text: str) -> str:
        return re.sub(r"(?<!20)(?<!\d)([2-3]\d)年", lambda m: f"20{m.group(1)}年", text)

    def _normalize_cross_month_range(self, text: str) -> str:
        def replace(match: re.Match[str]) -> str:
            year = match.group("year")
            start_month = match.group("start")
            end_month = match.group("end")
            return f"{year}年{start_month}月到{year}年{end_month}月"

        return re.sub(
            r"(?P<year>20\d{2})年(?P<start>[1-9]|1[0-2])月(?:到|至|-|~)(?P<end>[1-9]|1[0-2])月",
            replace,
            text,
        )

    def _normalize_age_expression(self, text: str) -> str:
        replacements: list[tuple[str, str]] = [
            (r"年龄(?:大于|高于|超过)(\d{2})岁", r"年龄>\1岁"),
            (r"(?:大于|高于|超过)(\d{2})岁", r">\1岁"),
            (r"(\d{2})岁及以上", r">=\1岁"),
            (r"(\d{2})岁以上", r">\1岁"),
            (r"年龄(?:小于|低于)(\d{2})岁", r"年龄<\1岁"),
            (r"(?:小于|低于)(\d{2})岁", r"<\1岁"),
            (r"(\d{2})岁及以下", r"<=\1岁"),
            (r"(\d{2})岁以下", r"<\1岁"),
            (r"(\d{2})\s*-\s*(\d{2})岁", r"\1-\2岁"),
            (r"未填写年龄|年龄未填写|年龄缺失", "未填写年龄"),
        ]
        normalized = text
        for pattern, replacement in replacements:
            normalized = re.sub(pattern, replacement, normalized)
        return normalized

    def _normalize_hospital_alias(self, text: str) -> str:
        alias_map = self._get_hospital_alias_map()
        normalized = text
        for alias, canonical in alias_map.items():
            if alias and alias in normalized and canonical not in normalized:
                normalized = normalized.replace(alias, canonical)
        return normalized

    def _get_hospital_alias_map(self) -> dict[str, str]:
        if self._hospital_alias_map is None:
            self._hospital_alias_map = self._build_hospital_alias_map()
        return self._hospital_alias_map

    def _build_hospital_alias_map(self) -> dict[str, str]:
        alias_map = dict(self._seed_alias_map)
        unique_aliases: dict[str, str] = {}
        collisions: set[str] = set()

        def variants(name: str) -> set[str]:
            candidate_set = {name}
            candidate_set.add(name.replace("省", ""))
            candidate_set.add(name.replace("市", ""))
            candidate_set.add(name.replace("医院", ""))
            candidate_set.add(name.replace("保健院", ""))
            if "妇幼保健院" in name:
                candidate_set.add(name.replace("妇幼保健院", "妇幼"))
            return {item.strip() for item in candidate_set if item and len(item.strip()) >= 3}

        hospital_names = self._hospital_names
        if hospital_names is None:
            hospital_names = [str(hospital["hospital_name"]).strip() for hospital in get_pgta_dataset().hospitals]

        for hospital_name in hospital_names:
            for alias in variants(hospital_name):
                if alias in collisions:
                    continue
                existing = unique_aliases.get(alias)
                if existing and existing != hospital_name:
                    unique_aliases.pop(alias, None)
                    collisions.add(alias)
                    continue
                unique_aliases[alias] = hospital_name

        alias_map.update(unique_aliases)
        return alias_map


question_normalizer = QuestionNormalizer()
