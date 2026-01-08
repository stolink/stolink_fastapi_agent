# 콜백 데이터 필드 출처 정리

## 질문: 콜백 데이터의 각 필드는 어디서 채워지나요?

```json
{
  "current_mood": {...},
  "style_context": {...},
  "aliases": [...],
  "faction": {...}
}
```

---

## 답변: Aggregator가 모든 Agent 결과를 병합합니다

### 전체 흐름

```
[6개 Agent] → [Aggregator] → [Callback Data]
   ↓              ↓              ↓
 추출           병합          전송
```

---

## 1. `current_mood` (현재 감정)

### 출처
**Agent**: `dialogue_mood.py`
**위치**: `app/agents/extraction/character/dialogue_mood.py`

### 추출 내용
```python
{
  "emotion": str,        # 불안, 긴장, 흥분 등
  "intensity": int,      # 1-10
  "trigger": str         # 감정 원인
}
```

### Aggregator 병합 (Line 788-792)
```python
"current_mood": dm_data.get("current_mood", {
    "emotion": None,
    "intensity": 5,
    "trigger": None,
})
```

**핵심**: 모든 캐릭터가 **씬별 감정** 추출됨 (필수)

---

## 2. `style_context` (스타일 컨텍스트)

### 출처
**Agent**: `appearance.py`
**위치**: `app/agents/extraction/character/appearance.py`

### 생성 로직 (Line 306-309)
```python
data["style_context"] = {
    "art_style": art_style,           # "Digital Illustration, Concept Art"
    "rendering_engine": rendering_engine,
}
```

### Aggregator 병합 (Line 777-780)
```python
"style_context": {
    "art_style": app_data.get("style_context", {}).get("art_style", "fantasy illustration"),
}
```

**핵심**: 이미지 생성 AI를 위한 **아트 스타일 메타데이터**

---

## 3. `aliases` (별칭)

### 출처
**Agent**: `identity.py`
**위치**: `app/agents/extraction/character/identity.py`

### 추출 내용 (Line 64)
```python
aliases: list[str] = Field(default_factory=list, description="Nicknames or titles")
```

**예시**: `"헤이즈 교수"` → `aliases: ["박사", "교수님"]`

### Aggregator 정제 (Line 763)
```python
"aliases": clean_character_aliases(
    id_data.get("aliases", []), 
    name, 
    canonical_names
)
```

**핵심**: LLM이 **다른 캐릭터 이름을 alias로 잘못 추출**하는 경우 제거 (`clean_character_aliases` 함수)

---

## 4. `faction` (소속)

### 출처 1: `identity.py` (faction 이름만)
```python
faction: Optional[str] = Field(None, description="Organization/group affiliation")
```

### 출처 2: `aggregator.py` (social 구조는 기본값)

#### SAFE_DEFAULTS (Line 46-54)
```python
SAFE_DEFAULTS = {
    "faction": {
        "social": {
            "rank": "COMMON",
            "influence": 0,
            "faction_reputation": {},
        }
    },
}
```

#### Aggregator 병합 (Line 753-760)
```python
"faction": {
    "name": id_data.get("faction") or None,  # Identity Agent에서 추출
    "social": {
        "rank": SAFE_DEFAULTS["faction"]["social"]["rank"],      # → "COMMON"
        "influence": SAFE_DEFAULTS["faction"]["social"]["influence"],  # → 0
        "faction_reputation": {},                                  # → {}
    }
}
```

**핵심**:
- `faction.name`: Identity Agent가 추출
- `faction.social`: **Aggregator가 기본값 주입** (게임 엔진용)

---

## 종합 요약표

| 필드 | Agent | Aggregator 역할 |
|------|-------|----------------|
| `current_mood` | dialogue_mood.py | 기본값 설정 (None 방지) |
| `style_context` | appearance.py | 기본 art_style 지정 |
| `aliases` | identity.py | 잘못된 alias 정제 |
| `faction.name` | identity.py | 그대로 전달 |
| `faction.social` | - | **SAFE_DEFAULTS 주입** |

---

## 핵심: Aggregator의 역할

**파일**: `app/agents/extraction/character/aggregator.py`
**함수**: `merge_character_data()` (Line 596-869)

### 3가지 역할
1. **병합**: 6개 Agent 결과를 캐릭터별로 통합
2. **정제**: 잘못된 데이터 제거 (e.g., aliases 정리)
3. **기본값 주입**: NULL 방지 (e.g., faction.social)

**결과** → Spring Callback으로 전송되는 최종 JSON!
