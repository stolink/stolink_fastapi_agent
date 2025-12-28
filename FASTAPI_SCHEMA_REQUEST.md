# FastAPI AI Backend - JSON 응답 스키마 수정 요청

## 📌 요청 사항

Spring Boot 백엔드에서 AI 분석 결과를 파싱하여 저장하는 로직을 구현했습니다.  
현재 FastAPI에서 반환하는 JSON 응답에 몇 가지 수정이 필요합니다.

---

## ✅ 수정 필요 사항

### 1. JSON 형식 검증
- 모든 응답이 **유효한 JSON** 형식인지 확인
- `key=value` 형식이 아닌 `"key": value` 형식 사용

```diff
- {name=Arin, role=protagonist}
+ {"name": "Arin", "role": "protagonist"}
```

### 2. 필수 필드 누락 보완

| 위치 | 누락된 필드 | 설명 |
|------|-------------|------|
| `events[].description` | `description` | 이벤트 설명 필드 |
| `settings[].location_name` | `location_name` | 장소 이름 필드 |

### 3. 중복 필드 정리

`settings` 객체에 중복된 필드가 있습니다:

| 중복 필드 1 | 중복 필드 2 | 권장 필드 |
|-------------|-------------|-----------|
| `lighting_description` | `lighting` | 하나로 통일 |
| `atmosphere_keywords` | `atmosphere` | 하나로 통일 |
| `weather_condition` | `weather` | 하나로 통일 |
| `is_primary_location` | `is_primary` | 하나로 통일 |
| `story_significance` | `significance` | 하나로 통일 |
| `static_objects` | `notable_features` | 하나로 통일 |

---

## 📋 Spring Boot에서 기대하는 스키마

### Characters
```json
{
  "name": "Arin",
  "role": "protagonist",
  "status": "alive",
  "visual": {
    "appearance": ["drawing sword"],
    "attire": ["holding sword"],
    "age_group": "adult",
    "gender": "female"
  },
  "personality": {
    "core_traits": ["brave"],
    "flaws": [],
    "values": ["justice"]
  },
  "current_mood": {
    "emotion": "tense",
    "intensity": 7,
    "trigger": "confronting unknown threat"
  }
}
```

### Events
```json
{
  "event_id": "E001",
  "event_type": "action",
  "narrative_summary": "Arin draws her sword in the Dark Forest",
  "description": "Arin senses danger and draws her sword",  // 필수
  "participants": ["Arin"],
  "location_ref": "Dark Forest",
  "prev_event_id": null,
  "visual_scene": "...",
  "camera_angle": "medium shot",
  "importance": 6,
  "is_foreshadowing": false
}
```

### Settings
```json
{
  "setting_id": "loc_forest_01",
  "name": "Dark Forest",
  "location_name": "Dark Forest",  // 필수
  "location_type": "forest",
  "visual_prompt": "Dense, ancient forest...",
  "time_of_day": "night",
  "lighting_description": "Dim, pale moonlight...",
  "atmosphere_keywords": "ominous, tense, mysterious",
  "weather_condition": "foggy",
  "static_objects": ["ancient twisted trees", "thick ground fog"],
  "is_primary_location": true,
  "story_significance": "Site of the confrontation"
}
```

### Relationships
```json
{
  "source": "Arin",
  "target": "Kael",
  "relation_type": "ENEMY",
  "strength": 7,
  "description": "Arin and Kael are in a tense, adversarial relationship"
}
```

### Dialogues
```json
{
  "key_dialogues": [
    {
      "dialogue_id": "D001",
      "participants": ["Arin", "Kael"],
      "content": "Arin drew her sword...",
      "significance": "This dialogue sets the scene...",
      "subtext": "The text suggests a potential confrontation..."
    }
  ]
}
```

---

## 🔧 현재 Spring Boot 저장 현황

| 데이터 | 저장소 | 상태 |
|--------|--------|------|
| Characters | Neo4j | ✅ 구현 완료 |
| Relationships | Neo4j | ✅ 구현 완료 |
| Events | PostgreSQL | ✅ 구현 완료 |
| Settings | PostgreSQL | ✅ 구현 완료 |
| Dialogues | PostgreSQL | ✅ 구현 완료 |
| Emotions | Neo4j (Character 업데이트) | ✅ 구현 완료 |
| Job 상태 관리 | PostgreSQL | ✅ 구현 완료 |