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

### Plot Integration (신규 추가)
```json
{
  "plot_summary": {
    "narrative": "Arin faces her fears in the forest.",
    "central_conflict": "Man vs Self"
  },
  "overall_tension": 7.5,
  "narrative_beats": [
    {
      "beat_id": 1,
      "text": "Arin enters the forest",
      "beat_type": "SETUP",
      "event_ref": "E001",
      "visual_prompt": "A woman walking into a dark forest"
    }
  ],
  "tension_curve": [5, 6, 7.5],
  "three_act_structure": [
    {
      "act": "setup",
      "event_ids": ["E001", "E002"],
      "purpose": "Establish the setting and characters"
    }
  ],
  "foreshadowing": [
    {
      "foreshadow_id": "F001",
      "source_event": "E002",
      "hint_text": "A rustle in the bushes",
      "predicted_outcome": "Possible ambush",
      "confidence": 8,
      "target_event": null
    }
  ],
  "multimedia_summary": {
    "beat_count": 2,
    "tension_curve_length": 3,
    "has_visual_prompts": true
  }
}
```

### Consistency Report (신규 추가)
```json
{
  "overall_score": 95,
  "requires_reextraction": false,
  "conflicts": [],
  "warnings": ["Minor timeout issue"],
  "resolution_summary": {
    "auto_fixable": 0,
    "ready_for_update": 0,
    "needs_human_review": 0,
    "total_conflicts": 0
  },
  "neo4j_validation": {
    "is_valid": true,
    "conflict_count": 0,
    "high_severity_count": 0
  }
}
```

### Validation (신규 추가)
```json
{
  "is_valid": true,
  "quality_score": 98,
  "action": "approve",
  "action_description": "Ready for callback to Spring Boot",
  "average_completeness": 99.5,
  "error_count": 0,
  "warning_count": 0,
  "execution_time_ms": 0.05,
  "data_completeness": {
    "extracted_characters": 100,
    "extracted_events": 100,
    "extracted_settings": 100
  },
  "validation_details": {
    "errors": [],
    "warnings": []
  }
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
| **Plot Integration** | PostgreSQL | ✅ **신규 추가** |
| **Consistency Report** | PostgreSQL | ✅ **신규 추가** |
| **Validation Result** | PostgreSQL | ✅ **신규 추가** |
| **Foreshadowing** | PostgreSQL | ✅ **신규 추가** |

---

## 📁 신규 추가된 엔티티

| 엔티티 | 테이블명 | 설명 |
|--------|----------|------|
| `PlotIntegration` | `plot_integrations` | 플롯 통합 데이터 (narrative_beats, tension_curve 등) |
| `ConsistencyReport` | `consistency_reports` | 일관성 보고서 (conflicts, warnings, overall_score) |
| `ValidationResult` | `validation_results` | 검증 결과 (quality_score, action, data_completeness) |
| `Foreshadowing` | `foreshadowing` | 복선 데이터 (기존 엔티티 활용, plot_integration.foreshadowing에서 추출) |

---

## ⚠️ 중요: Foreshadowing 필드 요구사항

`plot_integration.foreshadowing` 배열의 각 항목에 **반드시** 다음 필드가 포함되어야 합니다:

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `foreshadow_id` | string | ✅ | 복선 고유 ID (예: "F001") |
| `hint_text` | string | ✅ | 복선 힌트 텍스트 |
| `predicted_outcome` | string | ❌ | 예상 결과 |
| `confidence` | integer | ❌ | 신뢰도 (1-10, 7 이상이면 MAJOR로 분류) |