# FastAPI AI Backend - Request/Response 스키마 명세

> **Last Updated**: 2025-12-28

---

## 📤 Spring Boot → FastAPI (요청)

### Queue 정보

| 항목 | 값 |
|------|-----|
| **Queue Name** | `stolink.analysis.queue` |
| **Durable** | `true` |

### 요청 메시지 스키마

```json
{
  "job_id": "job-uuid-001",
  "project_id": "550e8400-e29b-41d4-a716-446655440000",
  "document_id": "doc-uuid-123",
  "content": "소설 텍스트 내용...",
  "callback_url": "http://localhost:8080/api/internal/ai/analysis/callback",
  "trace_id": "trace-20251228-abc123",
  "context": {
    "chapter_number": 3,
    "total_chapters": 10,
    "existing_characters": [
      {"id": "char-001", "name": "아린", "role": "protagonist"}
    ],
    "existing_events": [],
    "existing_relationships": [
      {"source_name": "아린", "target_name": "카엘", "relation_type": "ALLY", "strength": 7}
    ],
    "existing_settings": [],
    "world_rules_summary": "마법은 왕국에서 금지됨"
  }
}
```

### 필수/선택 필드

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `job_id` | string | ✅ | 고유 작업 ID |
| `project_id` | string | ✅ | 프로젝트 UUID |
| `document_id` | string | ✅ | 문서 UUID |
| `content` | string | ✅ | 분석할 소설 텍스트 |
| `callback_url` | string | ✅ | 결과 수신 URL (전체 경로) |
| `trace_id` | string | ❌ | 분산 추적용 ID |
| `context` | object | ❌ | 기존 데이터 참조 |

---

## 📥 FastAPI → Spring Boot (응답)

### Callback 응답 스키마

```json
{
  "jobId": "job-uuid-001",
  "status": "COMPLETED",
  "result": {
    "characters": [...],
    "events": [...],
    "relationships": [...],
    "settings": {...},
    "dialogues": {...},
    "emotions": {...},
    "consistency_report": {...},
    "plot_integration": {...},
    "validation": {...},
    "metadata": {...}
  },
  "error": null
}
```

### Status 값

| Status | 설명 |
|--------|------|
| `COMPLETED` | 분석 성공 |
| `WARNING` | 분석 완료 (일부 경고) |
| `FAILED` | 분석 실패 |

---

## 📋 상세 응답 스키마

### Characters

```json
{
  "name": "아린",
  "aliases": ["그림자 검사"],
  "role": "protagonist",
  "status": "alive",
  "visual": {
    "appearance": ["검은 머리", "날카로운 눈매"],
    "attire": ["검을 든 모습", "여행자 복장"],
    "age_group": "young_adult",
    "gender": "female"
  },
  "personality": {
    "core_traits": ["용감함", "정의로움"],
    "flaws": ["충동적"],
    "values": ["정의", "가족"]
  },
  "relationships": [
    {
      "target": "카엘",
      "type": "ALLY",
      "strength": 7,
      "description": "오랜 동료"
    }
  ],
  "current_mood": {
    "emotion": "긴장",
    "intensity": 7,
    "trigger": "미지의 위협 감지"
  },
  "motivation": "가족의 복수",
  "first_appearance": "어두운 숲"
}
```

### Events

```json
{
  "event_id": "E001",
  "event_type": "action",
  "narrative_summary": "아린이 어두운 숲에서 검을 꺼내 듦",
  "description": "아린이 위험을 감지하고 검을 뽑음",
  "participants": ["아린"],
  "location_ref": "어두운 숲",
  "prev_event_id": null,
  "visual_scene": "긴장된 자세로 검을 쥔 여성, 경계하는 표정",
  "camera_angle": "medium shot",
  "timestamp": {
    "relative": null,
    "absolute": null,
    "chapter": 3,
    "sequence_order": 1
  },
  "importance": 6,
  "is_foreshadowing": false,
  "foreshadowing_tag": null
}
```

### Settings

```json
{
  "setting_id": "loc_forest_01",
  "name": "어두운 숲",
  "location_type": "forest",
  "parent_location": null,
  "visual_background": "고대의 뒤틀린 나무들, 짙은 안개가 지면을 덮음, 달빛이 나뭇잎 사이로 스며듦",
  "atmosphere": "불길함, 긴장감, 신비로움",
  "time_of_day": "night",
  "lighting": "희미한 달빛, 그림자가 짙음",
  "weather": "안개",
  "art_style": "Dark Fantasy, Realistic, Cinematic Lighting",
  "description": "저주받은 고대 숲",
  "notable_features": ["고대 뒤틀린 나무", "짙은 안개", "이끼 낀 바위"],
  "significance": "대결의 장소",
  "is_primary": true
}
```

### Relationships

```json
{
  "source": "아린",
  "target": "카엘",
  "relation_type": "ALLY",
  "strength": 7,
  "description": "긴장된 동맹 관계",
  "bidirectional": true,
  "revealed_in_chapter": 1
}
```

### Dialogues

```json
{
  "key_dialogues": [
    {
      "speaker": "카엘",
      "listener": "아린",
      "line": "돌아가, 아린. 이건 네가 감당할 일이 아니야.",
      "subtext": "카엘은 아린을 보호하려 함",
      "emotion": "걱정"
    }
  ],
  "speech_patterns": {
    "아린": {
      "formality": "informal",
      "speech_style": "직접적, 단호함",
      "notable_phrases": []
    }
  },
  "dialogue_relationships": [
    {
      "speaker": "카엘",
      "listener": "아린",
      "formality_to_listener": "informal",
      "power_dynamic": "equal",
      "intimacy_level": 7
    }
  ]
}
```

### Emotions

```json
{
  "emotion_states": [
    {
      "character_name": "아린",
      "primary_emotion": "긴장",
      "secondary_emotion": "결연함",
      "intensity": 7,
      "trigger": "미지의 위협 감지",
      "expression": "눈을 가늘게 뜨고 검을 꽉 쥠",
      "is_hidden": false
    }
  ],
  "scene_mood": "긴장, 불안",
  "neo4j_updates": [
    {
      "character_name": "아린",
      "property_updates": {
        "current_emotion": "긴장",
        "emotion_intensity": 7,
        "emotion_valence": "negative"
      }
    }
  ]
}
```

### Consistency Report

```json
{
  "overall_score": 85,
  "conflicts": [
    {
      "type": "CHARACTER_TRAIT_CONFLICT",
      "severity": "MEDIUM",
      "source": "extracted",
      "existing": "신중함",
      "new": "충동적",
      "character": "아린",
      "suggested_action": "FLAG_FOR_HUMAN"
    }
  ],
  "requires_reextraction": false,
  "neo4j_validation": {
    "is_valid": true,
    "conflict_count": 0
  }
}
```

### Plot Integration

```json
{
  "act_structure": {
    "current_act": 1,
    "act_name": "SETUP",
    "act_progress": 30
  },
  "tension_curve": [3, 5, 7, 8, 6],
  "narrative_beats": [
    {
      "beat_id": 1,
      "text": "아린과 카엘이 어두운 숲에서 만남",
      "beat_type": "SETUP",
      "event_ref": "E001",
      "visual_prompt": "두 인물이 어두운 숲에서 마주함"
    }
  ],
  "foreshadowing": [
    {
      "tag": "FS001",
      "description": "카엘의 경고가 미래 위험을 암시",
      "payoff_hint": "카엘이 알고 있는 것이 있음"
    }
  ],
  "multimedia_summary": {
    "beat_count": 5,
    "tension_curve_length": 5,
    "has_visual_prompts": true,
    "tension_range": {"min": 3, "max": 8, "peak_index": 3}
  }
}
```

### Metadata

```json
{
  "processing_time_ms": 15234,
  "tokens_used": 12500,
  "trace_id": "trace-20251228-abc123",
  "agents_executed": [
    "character",
    "event", 
    "setting",
    "dialogue",
    "emotion",
    "relationship",
    "consistency",
    "plot",
    "validator"
  ]
}
```

---

## 🔧 Spring Boot 저장 현황

| 데이터 | 저장소 | 상태 |
|--------|--------|------|
| Characters | Neo4j | ✅ 구현 완료 |
| Relationships | Neo4j | ✅ 구현 완료 |
| Events | PostgreSQL | ✅ 구현 완료 |
| Settings | PostgreSQL | ✅ 구현 완료 |
| Dialogues | PostgreSQL | ✅ 구현 완료 |
| Emotions | Neo4j (Character 업데이트) | ✅ 구현 완료 |
| Job 상태 관리 | PostgreSQL | ✅ 구현 완료 |

---

## ⚠️ 주의사항

1. **callback_url은 전체 URL**
   - ✅ `http://localhost:8080/api/internal/ai/analysis/callback`
   - ❌ `/api/internal/ai/analysis/callback`

2. **필드명 규칙**
   - 요청: `snake_case` (job_id, project_id)
   - 응답: `camelCase` for jobId, `snake_case` for result 내부

3. **context는 선택사항**
   - 없어도 기본 분석 가능
   - 제공하면 일관성 검사 품질 향상