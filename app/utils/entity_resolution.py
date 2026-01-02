"""Entity Resolution utilities for character name matching.

Fuzzy Matching을 사용하여 동일 캐릭터를 식별합니다.
- 정확 일치
- 한글-영문 매핑
- 별칭(aliases) 교차 매칭
- rapidfuzz 기반 퍼지 매칭
"""
from enum import Enum
from dataclasses import dataclass
from typing import Optional
import re

try:
    from rapidfuzz import fuzz
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    RAPIDFUZZ_AVAILABLE = False


class MatchClassification(Enum):
    """매칭 결과 분류"""
    AUTO_MERGE = "AUTO_MERGE"      # 자동 병합 (95점 이상)
    NEEDS_REVIEW = "NEEDS_REVIEW"  # 사용자 검증 필요 (80-94점)
    DIFFERENT = "DIFFERENT"        # 별개 캐릭터 (80점 미만)


@dataclass
class MatchResult:
    """매칭 결과"""
    is_same: bool
    score: float  # 0-100
    classification: MatchClassification
    match_reason: str


# 한글-영문 매핑 테이블 (예시)
KOREAN_ENGLISH_MAPPING = {
    "이안": ["Ian", "ian"],
    "아린": ["Arin", "arin"],
    "카엘": ["Kael", "kael"],
    "나비": ["Nabi", "nabi"],
    "유민재": ["Yoo Minjae", "Minjae"],
    # 추가 매핑...
}

# 역방향 매핑 생성
ENGLISH_KOREAN_MAPPING = {}
for korean, english_list in KOREAN_ENGLISH_MAPPING.items():
    for english in english_list:
        ENGLISH_KOREAN_MAPPING[english.lower()] = korean


def normalize_name(name: str) -> str:
    """이름 정규화 - 공백, 대소문자 처리"""
    if not name:
        return ""
    # 앞뒤 공백 제거, 연속 공백을 단일 공백으로
    normalized = re.sub(r'\s+', ' ', name.strip())
    return normalized.lower()


def is_korean_english_match(name1: str, name2: str) -> bool:
    """한글-영문 매핑 확인"""
    n1_lower = name1.lower().strip()
    n2_lower = name2.lower().strip()
    
    # name1이 한글인 경우
    if name1 in KOREAN_ENGLISH_MAPPING:
        if n2_lower in [e.lower() for e in KOREAN_ENGLISH_MAPPING[name1]]:
            return True
    
    # name2가 한글인 경우
    if name2 in KOREAN_ENGLISH_MAPPING:
        if n1_lower in [e.lower() for e in KOREAN_ENGLISH_MAPPING[name2]]:
            return True
    
    # 영문에서 한글 역매핑
    korean1 = ENGLISH_KOREAN_MAPPING.get(n1_lower)
    korean2 = ENGLISH_KOREAN_MAPPING.get(n2_lower)
    
    if korean1 and korean1 == name2:
        return True
    if korean2 and korean2 == name1:
        return True
    if korean1 and korean2 and korean1 == korean2:
        return True
    
    return False


def calculate_similarity_score(name1: str, name2: str) -> float:
    """rapidfuzz를 사용한 유사도 점수 계산 (0-100)"""
    if not RAPIDFUZZ_AVAILABLE:
        # rapidfuzz 없으면 단순 비교
        return 100.0 if normalize_name(name1) == normalize_name(name2) else 0.0
    
    n1 = normalize_name(name1)
    n2 = normalize_name(name2)
    
    if not n1 or not n2:
        return 0.0
    
    # 정확 일치
    if n1 == n2:
        return 100.0
    
    # 가중 평균 (ratio 50%, partial_ratio 30%, token_sort_ratio 20%)
    ratio_score = fuzz.ratio(n1, n2)
    partial_score = fuzz.partial_ratio(n1, n2)
    token_sort_score = fuzz.token_sort_ratio(n1, n2)
    
    weighted_score = (ratio_score * 0.5) + (partial_score * 0.3) + (token_sort_score * 0.2)
    
    return weighted_score


def classify_match(score: float) -> MatchClassification:
    """점수에 따른 분류"""
    if score >= 95:
        return MatchClassification.AUTO_MERGE
    elif score >= 80:
        return MatchClassification.NEEDS_REVIEW
    else:
        return MatchClassification.DIFFERENT


def is_same_character(
    name1: str,
    name2: str,
    aliases1: Optional[list[str]] = None,
    aliases2: Optional[list[str]] = None
) -> MatchResult:
    """두 캐릭터가 동일인인지 판별.
    
    Args:
        name1: 캐릭터1 이름
        name2: 캐릭터2 이름
        aliases1: 캐릭터1 별칭 목록
        aliases2: 캐릭터2 별칭 목록
    
    Returns:
        MatchResult: 매칭 결과
    """
    aliases1 = aliases1 or []
    aliases2 = aliases2 or []
    
    # 1. 정확 일치
    if normalize_name(name1) == normalize_name(name2):
        return MatchResult(
            is_same=True,
            score=100.0,
            classification=MatchClassification.AUTO_MERGE,
            match_reason="exact_match"
        )
    
    # 2. 한글-영문 매핑 확인
    if is_korean_english_match(name1, name2):
        return MatchResult(
            is_same=True,
            score=100.0,
            classification=MatchClassification.AUTO_MERGE,
            match_reason="korean_english_mapping"
        )
    
    # 3. 별칭 교차 매칭
    all_names1 = [name1] + aliases1
    all_names2 = [name2] + aliases2
    
    for n1 in all_names1:
        for n2 in all_names2:
            if normalize_name(n1) == normalize_name(n2):
                return MatchResult(
                    is_same=True,
                    score=100.0,
                    classification=MatchClassification.AUTO_MERGE,
                    match_reason="alias_match"
                )
            if is_korean_english_match(n1, n2):
                return MatchResult(
                    is_same=True,
                    score=95.0,
                    classification=MatchClassification.AUTO_MERGE,
                    match_reason="alias_korean_english_match"
                )
    
    # 4. Fuzzy Matching
    best_score = 0.0
    for n1 in all_names1:
        for n2 in all_names2:
            score = calculate_similarity_score(n1, n2)
            best_score = max(best_score, score)
    
    classification = classify_match(best_score)
    is_same = classification in (MatchClassification.AUTO_MERGE, MatchClassification.NEEDS_REVIEW)
    
    return MatchResult(
        is_same=is_same,
        score=best_score,
        classification=classification,
        match_reason="fuzzy_match"
    )


def find_matching_characters(
    new_character: dict,
    existing_characters: list[dict],
    threshold: float = 80.0
) -> list[tuple[dict, MatchResult]]:
    """신규 캐릭터와 매칭되는 기존 캐릭터 찾기.
    
    Args:
        new_character: 신규 캐릭터 (name, aliases 필드 필요)
        existing_characters: 기존 캐릭터 목록
        threshold: 최소 점수 임계값
    
    Returns:
        매칭된 (캐릭터, 결과) 튜플 목록
    """
    matches = []
    
    new_name = new_character.get("name", "")
    new_aliases = new_character.get("aliases", [])
    
    for existing in existing_characters:
        existing_name = existing.get("name", "")
        existing_aliases = existing.get("aliases", [])
        
        result = is_same_character(new_name, existing_name, new_aliases, existing_aliases)
        
        if result.score >= threshold:
            matches.append((existing, result))
    
    # 점수 높은 순으로 정렬
    matches.sort(key=lambda x: x[1].score, reverse=True)
    
    return matches


def merge_character_aliases(
    aliases1: list[str],
    aliases2: list[str]
) -> list[str]:
    """두 별칭 목록 병합 (중복 제거)"""
    merged = set()
    
    for alias in aliases1 + aliases2:
        normalized = alias.strip()
        if normalized:
            merged.add(normalized)
    
    return sorted(list(merged))
