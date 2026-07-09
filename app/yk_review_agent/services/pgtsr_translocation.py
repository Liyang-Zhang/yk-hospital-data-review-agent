from __future__ import annotations

import re


NON_TYPICAL_BALANCED_REARRANGEMENT_LABEL = "其他非典型平衡重排"
LOW_SAMPLE_TRANSLOCATION_PAIR_LABEL = "其他低样本类型"

_TRANSLOCATION_PAIR_PATTERN = re.compile(r"t\(\s*([0-9xyXY]+)\s*;\s*([0-9xyXY]+)\s*\)")


def normalize_translocation_pair(text: str | None) -> str | None:
    if not text:
        return None
    match = _TRANSLOCATION_PAIR_PATTERN.search(text)
    if match is None:
        return None
    left = match.group(1).upper()
    right = match.group(2).upper()
    first, second = sorted((left, right), key=_chromosome_sort_key)
    return f"t({first};{second})"


def _chromosome_sort_key(chromosome: str) -> tuple[int, str]:
    if chromosome.isdigit():
        return (int(chromosome), chromosome)
    if chromosome == "X":
        return (23, chromosome)
    if chromosome == "Y":
        return (24, chromosome)
    return (99, chromosome)
