# 캐릭터 추출 데이터 (최종 통합)

실제 Spring Callback 구조에 맞춘 통합 스키마.

---

## 최종 구조 (CharacterExtraction = FullCharacter)

```python
{
    "_id": "char-헤이즈 교수-001",
    "role": "supporting",
    "profile": {
        "character_id": "char-헤이즈 교수-001",
        "name": "헤이즈 교수",
        "age": null,
        "gender": "male",
        "race": "human",
        "mbti": null,
        "personality": {
            "core_traits": ["학구적", "신중함"],
            "flaws": ["우유부단"],
            "values": ["지식의 탐구"]
        },
        "backstory": "...",
        "faction": {
            "name": null,
            "social": {
                "rank": "COMMON",
                "influence": 0,
                "faction_reputation": {}
            }
        }
    },
    "aliases": ["박사"],
    "status": "alive",
    "appearance": {...},
    "relations": {
        "graph": [...],
        "event_refs": ["E002"],
        "location_context": "..."
    },
    "current_mood": {...},
    "embedding": [...]  # 자동 생성
}
```

---

## 변경 사항

| 항목 | 변경 |
|------|------|
| CharacterExtraction | FullCharacter와 통합 (alias) |
| meta | 제거됨 |
| embedding | 추가됨 (Neo4j용) |
| profile.personality | dict로 변경 (core_traits, flaws, values) |
| profile.faction | dict로 변경 (name, social) |

---

## 필드 출처

상세: [CALLBACK_FIELD_SOURCES.md](file:///c:/jungle/weapon/sto-link-AI-backend/docs/CALLBACK_FIELD_SOURCES.md)
