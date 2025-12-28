# AI Pipeline Output 스키마 문서

> 이 문서는 Multi-Agent Pipeline의 출력 JSON 구조를 설명합니다.

---

## 📋 최상위 구조

| 필드 | 타입 | 설명 |
|------|------|------|
| `job_id` | string | 작업 고유 ID |
| `project_id` | string | 프로젝트 ID |
| `document_id` | string | 문서 ID |
| `status` | string | 처리 상태: `completed`, `failed`, `human_review` |

---

## 1. extracted_characters (캐릭터 추출)

**에이전트**: Character Extraction Agent (Level 1)

```json
{
  "name": "Seojin",           // 캐릭터 이름 (Neo4j 노드 키)
  "role": "protagonist",      // protagonist, antagonist, supporting
  "status": "alive",          // alive, dead, unknown
  
  "visual": {
    "appearance": ["tall", "dark hair"],  // 외모 특징
    "attire": ["holding sword"],          // 복장/소지품
    "age_group": "adult",                 // child, teen, adult, elderly
    "gender": "male"                      // male, female, unknown
  },
  
  "personality": {
    "core_traits": ["skilled swordsman"],  // 핵심 성격
    "flaws": [],                           // 결점
    "values": ["justice"]                  // 가치관
  },
  
  "relationships": [{
    "target": "Minho",           // 대상 캐릭터
    "type": "ENEMY",             // ALLY, ENEMY, FAMILY, ROMANTIC, MENTOR
    "history": "former_friend",  // 관계 배경
    "strength": 8                // 관계 강도 (1-10)
  }],
  
  "current_mood": {
    "emotion": "tense",          // 현재 감정
    "intensity": 8,              // 강도 (1-10)
    "trigger": "confronting..."  // 감정 유발 원인
  }
}
```

**용도**: 
- PostgreSQL 저장 (캐릭터 테이블)
- Neo4j 노드 생성 `(:Character {name, role, ...})`
- 이미지 생성 프롬프트 (visual 필드)

---

## 2. extracted_settings (배경 추출)

**에이전트**: Setting Extraction Agent (Level 1)

```json
{
  "setting_id": "loc_dark_forest",  // 배경 고유 ID
  "name": "Dark Forest",            // 배경 이름 (Neo4j 노드 키)
  "location_type": "forest",        // forest, city, indoor, etc.
  
  "static_visual_prompt": "Dense ancient forest...",  // 🎨 이미지 생성용 프롬프트
  
  "time_of_day": "night",              // dawn, day, dusk, night
  "lighting_description": "dim...",     // 조명 묘사
  "atmosphere_keywords": "ominous...",  // 분위기 키워드
  "weather_condition": "foggy",         // clear, cloudy, rainy, foggy
  
  "static_objects": ["ancient trees", "fog"],  // 정적 오브젝트
  
  "is_primary_location": true,           // 주요 배경 여부
  "story_significance": "Site of..."     // 스토리 중요도
}
```

**용도**:
- `static_visual_prompt` → 배경 이미지 생성 AI에 직접 입력
- Neo4j 노드 생성 `(:Setting {name, location_type, ...})`

---

## 3. extracted_events (이벤트 추출)

**에이전트**: Event Extraction Agent (Level 1)

```json
{
  "event_id": "E001",                    // 이벤트 고유 ID
  "event_type": "action",                // action, dialogue, confrontation, etc.
  "narrative_summary": "Seojin stands...", // 이벤트 요약
  
  "participants": ["Seojin"],            // 참여 캐릭터 (Character.name 참조)
  "location_ref": "Dark Forest",         // 배경 참조 (Setting.name 참조)
  
  "prev_event_id": null,                 // 이전 이벤트 (시간순 연결)
  
  "visual_scene": "A tall man...",       // 🎨 이미지 생성용 (인물+구도만)
  "camera_angle": "medium shot",         // 카메라 앵글
  
  "importance": 5,                       // 중요도 (1-10)
  "is_foreshadowing": false              // 복선 여부
}
```

**참조 무결성**:
- `participants` → `extracted_characters[].name`과 정확히 매칭
- `location_ref` → `extracted_settings[].name`과 정확히 매칭

**용도**:
- 시간순 이벤트 시퀀스 구성
- 삽화 생성 (`visual_scene` + `Setting.static_visual_prompt` 합성)

---

## 4. analyzed_dialogues (대화 분석)

**에이전트**: Dialogue Analysis Agent (Level 1)

### key_dialogues
```json
{
  "dialogue_id": "D001",
  "participants": ["Hana", "Seojin"],
  "content": "우리가 이곳에서...",       // 대사 원문
  "significance": "Hana's anxiety...",   // 대사 의미
  "subtext": "Fear of Minho"             // 숨은 의도
}
```

### speech_patterns (말투 패턴)
```json
{
  "character_name": "Minho",
  "formality_level": "informal",         // formal, informal, mixed
  "speech_characteristics": ["cynical"], // 말투 특성
  "unique_phrases": ["The truth is..."]  // 특징적 표현
}
```

### dialogue_relationships (대화 관계)
```json
{
  "speaker": "Hana",
  "listener": "Seojin",
  "formality_to_listener": "formal",     // 공손도
  "power_dynamic": "subordinate",        // superior, equal, subordinate
  "intimacy_level": 7                    // 친밀도 (1-10)
}
```

**용도**:
- Neo4j 엣지 속성: `(:Character)-[:SPEAKS_TO {formality, power, intimacy}]->(:Character)`
- TTS 음성 생성 시 톤/스타일 결정

---

## 5. tracked_emotions (감정 추적)

**에이전트**: Emotion Tracking Agent (Level 1)

```json
{
  "emotion_id": "EM001",
  "character": "Seojin",
  "primary_emotion": "긴장감",          // 주요 감정
  "secondary_emotion": "결연함",        // 부차 감정
  "intensity": 8,                       // 강도 (1-10)
  "valence": "negative",                // positive, negative, neutral
  "trigger": "이민호와의 대치",          // 감정 유발 원인
  "expression": "단단한 표정...",        // 물리적 표현
  "is_hidden": false                    // 숨겨진 감정 여부
}
```

### neo4j_updates
```json
{
  "character_name": "Seojin",
  "property_updates": {
    "current_emotion": "긴장감",
    "emotion_intensity": 8,
    "emotion_valence": "negative"
  }
}
```

**용도**:
- 캐릭터 노드 속성 업데이트
- 캐릭터 표정 이미지 생성

---

## 6. relationship_graph (관계 분석)

**에이전트**: Relationship Analysis Agent (Level 2)

```json
{
  "source": "Minho",
  "target": "Seojin",
  "relation_type": "BETRAYED",           // FRIENDLY, ENEMY, BETRAYED, MENTOR, etc.
  "strength": 9,                         // 관계 강도 (1-10)
  "description": "Minho betrayed...",    // 관계 설명
  "bidirectional": false,                // 양방향 여부
  "evolved_from": "FRIENDLY"             // 이전 관계 타입
}
```

**방향성 규칙**:
- `BETRAYED`: 배신자 → 피해자 (단방향)
- `MENTOR`: 멘토 → 멘티 (단방향)
- `FRIENDLY`: 양방향 가능

**용도**:
- Neo4j 관계 생성: `(:Character)-[:BETRAYED]->(:Character)`

---

## 7. consistency_report (일관성 검증)

**에이전트**: Consistency Check Agent (Level 2)

```json
{
  "overall_score": 80,                   // 일관성 점수 (0-100)
  
  "conflicts": [{
    "type": "RELATIONSHIP_CONFLICT",
    "description": "Minho's relationship...",
    "severity": "MEDIUM",                // HIGH, MEDIUM, LOW
    "affected_elements": ["Minho", "Seojin"],
    "resolution_hint": "Set the relationship...",
    "suggested_action": "AUTO_FIX",      // AUTO_FIX, FLAG_FOR_HUMAN
    "final_value_candidate": {           // AUTO_FIX 시 적용할 값
      "bidirectional": false
    }
  }],
  
  "requires_reextraction": false,        // 재추출 필요 여부
  
  "resolution_summary": {
    "auto_fixable": 1,                   // 자동 수정 가능
    "needs_human_review": 2,             // 사람 검토 필요
    "total_conflicts": 3
  }
}
```

**용도**:
- `AUTO_FIX` → Spring Boot에서 자동 수정 적용
- `FLAG_FOR_HUMAN` → 관리자 대시보드에 표시

---

## 8. plot_integration (플롯 통합)

**에이전트**: Plot Integration Agent (Level 2)

### narrative_beats (내러티브 비트)
```json
{
  "beat_id": 1,
  "text": "Seojin stands alone...",
  "beat_type": "SETUP",                  // SETUP, INCITING_INCIDENT, CLIMAX, etc.
  "event_ref": "E001",                   // Event ID 참조
  "visual_prompt": "A tall man..."       // 삽화용 프롬프트
}
```

### tension_curve (텐션 커브)
```json
"tension_curve": [3, 5, 7, 9, 7]  // 각 비트별 긴장도
```

### three_act_structure (3막 구조)
```json
{
  "act": "setup",                        // setup, confrontation, resolution
  "event_ids": ["E001", "E002"],
  "purpose": "Establish the characters..."
}
```

### foreshadowing (복선)
```json
{
  "foreshadow_id": "F001",
  "source_event": "E004",
  "hint_text": "Minho's past betrayal...",
  "predicted_outcome": "The reason...",
  "confidence": 8
}
```

**용도**:
- 오디오 BGM 타이밍 (`tension_curve`)
- 삽화 생성 순서 (`narrative_beats`)
- 복선 추적 (`foreshadowing`)

---

## 9. validation_result (검증 결과)

**에이전트**: Validator Agent (Level 3)

```json
{
  "is_valid": true,                      // 최종 유효성
  "quality_score": 86,                   // 품질 점수 (0-100)
  
  "action": "approve",                   // approve, human_review, retry_extraction
  "action_description": "Ready for callback...",
  
  "data_completeness": {
    "extracted_characters": 100,         // 각 에이전트별 완성도 (%)
    "extracted_events": 100,
    ...
  },
  "average_completeness": 100.0,
  
  "validation_details": {
    "errors": [{                         // 🔴 에러 목록
      "field": "extracted_events[0].description",
      "code": "VAL_003",
      "message": "Required field 'description' is missing"
    }],
    "warnings": [],                      // 🟡 경고 목록
    "per_field": {...}                   // 필드별 상세 검증
  },
  
  "error_count": 5,
  "warning_count": 0,
  "execution_time_ms": 0.06              // 검증 실행 시간
}
```

**Action 분기**:
| Action | 설명 | Spring Boot 처리 |
|--------|------|------------------|
| `approve` | 통과 | Neo4j/PostgreSQL 저장 |
| `human_review` | 사람 검토 | 관리자 대시보드 표시 |
| `retry_extraction` | 재추출 | AI 파이프라인 재실행 |

---

## 🔗 데이터 흐름

```
┌─────────────────────────────────────────────────────────────┐
│                    Spring Boot Backend                       │
│                                                             │
│  1. extracted_characters → PostgreSQL (characters 테이블)    │
│  2. extracted_settings   → PostgreSQL (settings 테이블)      │
│  3. extracted_events     → PostgreSQL (events 테이블)        │
│  4. relationship_graph   → Neo4j (관계 엣지)                  │
│  5. analyzed_dialogues   → Neo4j (SPEAKS_TO 엣지)            │
│  6. tracked_emotions     → Neo4j (캐릭터 노드 속성)           │
│  7. plot_integration     → PostgreSQL (플롯 메타데이터)       │
│  8. validation_result    → 로깅/모니터링                      │
│                                                             │
│  → Image Generation Queue (visual_scene + static_visual_prompt) │
└─────────────────────────────────────────────────────────────┘
```
