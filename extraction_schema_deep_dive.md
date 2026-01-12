# 상세 추출 데이터 구조 (Comprehensive Extraction Data Structure)

시스템 로그와 코드베이스(`app/schemas/`) 분석 결과, **FastAPI Agent**는 각 문서를 처리할 때 다음과 같이 매우 상세하고 구조화된 데이터셋을 추출합니다.

이전에 확인하신 JSON은 요약본에 불과하며, 실제 추출 목표는 아래와 같은 심층 구조를 포함합니다:

## 1. 캐릭터 데이터 (`FullCharacter`)

시스템은 발견된 모든 캐릭터에 대해 RPG 수준의 완전한 프로필을 구축하려고 시도합니다.

### **핵심 신원 (Core Identity)**

- **profile**: 이름, 나이, 성별, 종족, 소속 세력, MBTI, 배경 이야기(Backstory).
- **role**: 주인공(Protagonist), 적대자(Antagonist), 조력자(Supporting), 멘토(Mentor) 등.
- **status**: 생존(Alive), 사망(Deceased), 불명(Unknown).
- **aliases**: 별명이나 이명 리스트.

### **정신 모델 (AI & 서사)**

- **personality**:
  - `core_traits`: 주요 성격 특성 (예: "용감한", "교활한").
  - `flaws`: 캐릭터의 결점.
  - `values`: 핵심 신념 (예: "정의", "생존").
- **current_mood**: 장면별 감정 상태 (`emotion`(감정), `intensity`(강도), `trigger`(원인)).
- **dialogue**: TTS/챗봇 연동 설정:
  - `tone`: 말투 (격식체, 반말 등).
  - `catchphrases`: 입버릇.
  - `forbidden_topics`: 기피하는 대화 주제.
  - `secret_keys`: 캐릭터가 알고 있는 숨겨진 정보.

### **시각 정보 (이미지 생성)**

- **appearance**:
  - `physique`: 체형.
  - `skin_tone`(피부색), `eyes`(눈), `nose`(코), `mouth`(입), `hair_style`(헤어스타일), `hair_color`(머리색).
  - `scars_tattoos`(흉터/문신), `cyberware`(신체 개조).
  - `attire`: 의상 및 장비 리스트.
- **visual** (구버전 호환): 단순화된 외형 태그 (예: "키가 큰", "망토를 입은").

### **게임 메카닉 (RPG 스탯)**

- **stats**: `str`(힘), `dex`(민첩), `int`(지능), `con`(체력), `attack`(공격력), `defense`(방어력), `level`(레벨), `exp`(경험치).
- **combat**: `elemental_resist`(속성 저항), `cc_resist`(군중제어 저항), `hitbox_radius`(충돌 크기), `aggro_radius`(인식 범위).
- **state**: `hp`/`hp_max`, `mp`/`mp_max`, `sp`(스태미나), `status_effects`(상태 이상).
- **social**: `faction_reputation`(세력 평판), `global_karma`(카르마), `rank`(계급), `influence`(영향력).
- **economy**: `gold`(소지금), `trade_status`(거래 가능 여부).

---

## 2. 이벤트 데이터 (`EventExtraction`)

이벤트는 단순 텍스트가 아니라 **그래프의 노드**로 추출됩니다.

- **신원**: `event_id` (E001...), `event_type` (액션, 대화, 회상 등).
- **서사 (Narrative)**:
  - `narrative_summary`: 한 문장 요약.
  - `description`: 상세 산문 설명.
- **그래프 연결 (Graph Connections)**:
  - `participants`: 참여한 캐릭터들의 **정확한** 이름 리스트.
  - `location_ref`: 특정 장소(Setting ID) 참조.
  - `prev_event_id`: 이전 이벤트 ID (사건의 연쇄).
- **메타데이터**: `timestamp` (상대적/절대적 시간), `importance` (중요도 1-10).
- **자동 보정**: `changes_made` 필드는 일관성 에이전트가 이벤트를 수정했는지 기록합니다.

---

## 3. 관계 데이터 (`Relationship`)

관계는 방향성과 이력을 가진 별도의 엔티티입니다.

- **노드**: `source` (캐릭터 A) -> `target` (캐릭터 B).
- **유형**: `ALLY`(동료), `ENEMY`(적), `FAMILY`(가족), `ROMANTIC`(연인), `MENTOR`(멘토), `BETRAYED`(배신) 등.
- **속성**:
  - `strength`: 관계의 강도 (1-10).
  - `bidirectional`: 양방향 여부 (예: 친구는 true, 멘토는 false).
  - `history`: 이전 관계 (예: "FORMER_ALLY").
  - `revealed_in_chapter`: 이 관계가 드러난 시점.

---

## 4. 장소/세계관 데이터 (`SettingExtraction`)

장소는 서사적 맥락과 시각적 생성을 위해 추출됩니다.

- **신원**: `setting_id`, `name` (그래프 키), `location_name`.
- **시각적 프롬프트 (Visual Prompt)**:
  - `visual_background`: Stable Diffusion/Midjourney용 전체 프롬프트.
  - `atmosphere`: 분위기 키워드 (예: "음산한", "평화로운").
  - `lighting`: 조명 묘사.
  - `time_of_day`: 새벽, 정오, 밤 등.
  - `art_style`: 생성될 아트 스타일 레퍼런스.
- **서사**: `description`(설명), `notable_features`(주요 특징), `significance`(중요성).

---

## 5. 고차원 분석 (High-Level Analysis)

시스템은 메타 분석 리포트도 생성합니다:

- **플롯 분석 (Plot Analysis)**: 전체적인 서사 구조 감지.
- **일관성 리포트 (Consistency Report)**:
  - `conflicts`: 감지된 모순 리스트 (`CHARACTER_TRAIT_CONFLICT`, `TIMELINE_CONFLICT` 등).
  - `severity`: 상(HIGH)/중(MEDIUM)/하(LOW) 점수 매기기.
  - `neo4j_validation`: 그래프 무결성 검사 결과.
- **검증 (Validation)**: 저장 전 최종 품질 평가.

**요약**: 이 추출 시스템은 초기 JSON에서 본 것보다 훨씬 풍부하며, 게임 개발이나 심층 서사 분석에 적합한 "세계관 바이블(World Bible)" 구조 전체를 대상으로 합니다.
