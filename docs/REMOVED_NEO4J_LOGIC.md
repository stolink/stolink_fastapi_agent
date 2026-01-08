# Neo4j 저장 로직 정리 (제거됨)

> **날짜**: 2026-01-07
> **이유**: AI Backend에서 Neo4j 저장을 담당하므로, Spring Backend에서 중복 저장 로직 제거

## 제거된 Repository 및 Entity

### Neo4j Repositories
- `CharacterRepository` - Neo4j 캐릭터 노드 저장
- `EventNeo4jRepository` - Neo4j 이벤트 노드 저장
- `SettingNeo4jRepository` - Neo4j 설정(장소) 노드 저장

### Neo4j Node Classes
- `Character` (node) - `com.stolink.backend.domain.character.node.Character`
- `Event` (node) - `com.stolink.backend.domain.event.node.Event`
- `Setting` (node) - `com.stolink.backend.domain.setting.node.Setting`

---

## 제거된 메서드별 Neo4j 로직

### 1. saveCharacters() - 캐릭터 저장
```java
// Neo4j 저장 로직 (제거됨)
Optional<Character> existingChar = characterRepository.findByNameAndProjectId(name, projectId);
if (existingChar.isPresent()) {
    Character character = existingChar.get();
    character.setRole(role);
    character.setStatus(status);
    updateCharacterJsonFields(character, charData);
    characterRepository.save(character);
} else {
    Character character = Character.builder()
        .projectId(projectId)
        .name(name)
        .role(role)
        .status(status)
        .build();
    updateCharacterJsonFields(character, charData);
    characterRepository.save(character);
}
```

### 2. saveRelationships() - 관계 저장
```java
// Neo4j 저장 로직 (제거됨)
Character sourceChar = characterRepository.findByNameAndProjectId(sourceName, projectId)
    .orElseGet(() -> {
        Character placeholder = Character.builder()
            .projectId(projectId).name(sourceName).role("unknown").status("unknown").build();
        return characterRepository.save(placeholder);
    });

Character targetChar = characterRepository.findByNameAndProjectId(targetName, projectId)
    .orElseGet(() -> {
        Character placeholder = Character.builder()
            .projectId(projectId).name(targetName).role("unknown").status("unknown").build();
        return characterRepository.save(placeholder);
    });

characterRepository.createRelationship(
    sourceChar.getId(), targetChar.getId(),
    relationType.toLowerCase(), strength, description, bidirectional);
```

### 3. saveEvents() - 이벤트 저장
```java
// Neo4j 저장 로직 (제거됨)
List<Event> existingEvents = eventNeo4jRepository.findAllByProjectIdAndEventId(projectId, eventId);
Event event = existingEvents.isEmpty() 
    ? Event.builder().projectId(projectId).eventId(eventId).build()
    : existingEvents.get(0);

event.setEventType(eventType);
event.setNarrativeSummary(narrativeSummary);
// ... 기타 필드 설정
eventNeo4jRepository.save(event);

// Edge 생성
eventNeo4jRepository.createHappenedAtEdge(projectId, eventId, locationRef);
```

### 4. saveSettings() - 설정(장소) 저장
```java
// Neo4j 저장 로직 (제거됨)
List<Setting> existingSettings = settingNeo4jRepository.findAllByProjectIdAndName(projectId, name);
Setting setting = existingSettings.isEmpty()
    ? Setting.builder().projectId(projectId).settingId(settingId).name(name).build()
    : existingSettings.get(0);

setting.setLocationType(locationType);
setting.setVisualPrompt(visualPrompt);
// ... 기타 필드 설정
settingNeo4jRepository.save(setting);
```

### 5. updateEmotions() - 감정 업데이트 (전체 제거)
```java
// Neo4j 전용 메서드 (전체 제거됨)
private void updateEmotions(Map<String, Object> result, String projectId) {
    List<Map<String, Object>> neo4jUpdates = emotionsData.get("neo4j_updates");
    for (Map<String, Object> update : neo4jUpdates) {
        Character character = characterRepository.findByNameAndProjectId(name, projectId);
        character.setCurrentMoodJson(objectMapper.writeValueAsString(propertyUpdates));
        characterRepository.save(character);
    }
}
```

### 6. updateCharacterJsonFields() - 캐릭터 JSON 필드 업데이트 (전체 제거)
```java
// Neo4j Character 노드 전용 메서드 (전체 제거됨)
private void updateCharacterJsonFields(Character character, CharacterDTO charData) {
    character.setAge(profile.getAge());
    character.setGender(profile.getGender());
    character.setProfileJson(objectMapper.writeValueAsString(profile));
    // ... 기타 JSON 필드 설정
}
```

---

## 유지되는 PostgreSQL 저장 로직

| 메서드 | 저장 대상 | Repository |
|--------|----------|------------|
| `saveCharacterToPostgres()` | CharacterEntity | CharacterJpaRepository |
| `saveRelationshipToPostgres()` | RelationshipEntity | RelationshipRepository |
| `saveEventToPostgres()` | EventEntity | EventJpaRepository |
| `saveSettingToPostgres()` | SettingEntity | SettingRepository |

---

## 참고: AI Backend가 Neo4j 저장 담당

AI Backend (FastAPI)에서 분석 결과를 Neo4j에 직접 저장하므로,
Spring Backend에서는 PostgreSQL 저장만 담당합니다.

**아키텍처**:
```
AI Backend (FastAPI)
  └── Neo4j 저장 담당 (Characters, Events, Settings, Relationships)

Spring Backend
  └── PostgreSQL 저장 담당 (CharacterEntity, EventEntity, SettingEntity, RelationshipEntity 등)
```
