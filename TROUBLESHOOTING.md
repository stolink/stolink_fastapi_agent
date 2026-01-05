# StoLink AI Backend - Troubleshooting Guide

> **Last Updated**: 2026-01-01

ì´ ë¬¸ìë ê°ë° ê³¼ì ìì ë°ìí ì£¼ì ë¬¸ì ì í´ê²°ì±ì ê¸°ë¡í©ëë¤.

---

## ëª©ì°¨

1. [Setting Agent - ì¸ë¬¼/ì¬ê±´ í¼ì ë¬¸ì ](#1-setting-agent---ì¸ë¬¼ì¬ê±´-í¼ì-ë¬¸ì )
2. [Event Agent - ë°°ê²½ ë¬ì¬ í¼ì ë° ì°¸ì¡° ë§¤ì¹­ ë¬¸ì ](#2-event-agent---ë°°ê²½-ë¬ì¬-í¼ì-ë°-ì°¸ì¡°-ë§¤ì¹­-ë¬¸ì )
3. [Dialogue Agent - Production Level ìê·¸ë ì´ë](#3-dialogue-agent---production-level-ìê·¸ë ì´ë)
4. [Emotion Agent - Production Level ìê·¸ë ì´ë](#4-emotion-agent---production-level-ìê·¸ë ì´ë)
5. [Consistency Agent - Production Level ìê·¸ë ì´ë](#5-consistency-agent---production-level-ìê·¸ë ì´ë)
6. [Plot Integration Agent - Production Level ìê·¸ë ì´ë](#6-plot-integration-agent---production-level-ìê·¸ë ì´ë)
7. [Validator Agent - Production Level ìê·¸ë ì´ë](#7-validator-agent---production-level-ìê·¸ë ì´ë)
8. [Supervisor Agent - Production Level ìê·¸ë ì´ë](#8-supervisor-agent---production-level-ìê·¸ë ì´ë)
9. [Message Schema - íì´ë¸ë¦¬ë ìí¤íì² ìê·¸ë ì´ë](#9-message-schema---íì´ë¸ë¦¬ë-ìí¤íì²-ìê·¸ë ì´ë)
10. [JSON íì± ì¤ë¥ - Structured Output ëì](#10-json-íì±-ì¤ë¥-ë°-ì¤í¤ë§-ë¶ì¼ì¹---structured-output-ëì)
11. [Job ìí ìë°ì´í¸ API ì°ë](#11-job-ìí-ìë°ì´í¸-api-ì°ë)
12. [Character Agent - FullCharacter ì¤í¤ë§ íì¥](#12-character-agent---fullcharacter-ì¤í¤ë§-íì¥)
13. [FullCharacter ì¤í¤ë§ ì ì© - ì ì²´ ìì´ì í¸ í¸íì±](#13-fullcharacter-ì¤í¤ë§-ì ì©---ì ì²´-ìì´ì í¸-í¸íì±)
14. [Multi-Agent - JSON íì± ì¤ë¥ ë° AWS Throttling](#14-multi-agent---json-íì±-ì¤ë¥-ë°-aws-throttling)
15. [Character Agent - Hierarchical Multi-Agent System ë¦¬í©í ë§](#15-character-agent---hierarchical-multi-agent-system-ë¦¬í©í ë§)
16. [Appearance Agent - Production Level ìê·¸ë ì´ë](#16-appearance-agent---production-level-ìê·¸ë ì´ë)
17. [Story Extraction - íê¸/ìë¬¸ ìºë¦­í° ì¤ë³µ ë° ì¶ì¶ íì§ ê°ì ](#17-story-extraction---íê¸ìë¬¸-ìºë¦­í°-ì¤ë³µ-ë°-ì¶ì¶-íì§-ê°ì )
18. [Schema v2.0 ë¦¬í©í ë§ ë° Neo4j RAG êµ¬í](#18-schema-v20-ë¦¬í©í ë§-ë°-neo4j-rag-êµ¬í)
19. [ëì©ë ë°ì´í° ì²ë¦¬ ìí¤íì² ì¬ì¤ê³](#19-ëì©ë-ë°ì´í°-ì²ë¦¬-ìí¤íì²-ì¬ì¤ê³-architecture-redesign)
20. [ì±ë¥ ë³ëª© ë¶ì ë° ìµì í](#20-ì±ë¥-ë³ëª©-ë¶ì-ë°-ìµì í)

---



## 1. Setting Agent - ì¸ë¬¼/ì¬ê±´ í¼ì ë¬¸ì 

### ð ë ì§
2025-12-27

### ð´ ë¬¸ì  (Problem)
Setting Agentê° ë°°ê²½ë§ ì¶ì¶í´ì¼ íëë°, ìºë¦­í° ì´ë¦ê³¼ íëì í¬í¨í¨.

**ì¤í¨ ì¶ë ¥ ìì**:
```json
{
  "visual_background": "Seojin standing in a dark forest holding a sword..."
}
```

**ê¸°ë ì¶ë ¥**:
```json
{
  "visual_background": "Dark ancient forest, dense twisted trees, thick fog on ground..."
}
```

### ð¡ ìì¸ ë¶ì (Root Cause)
1. LLMì´ "Setting(ë°°ê²½)"ê³¼ "Scene(ì¥ë©´)"ì í¼ë
2. ë¨ìí "íì§ ë§(Don't)"ë¼ê³ ë§ ì§ìíë©´ ë¬´ìí¨
3. Gemini Flash/Llama 3 ë±ì íì¤í¸ ìì½ ì±í¥ì´ ê°í¨

### ð¢ í´ê²°ì± (Solution)

#### 1. Bad vs Good ìì (Few-shot Learning)
```
â BAD: "Seojin standing in a dark forest holding a sword."
â GOOD: "Dark ancient forest, dense twisted trees, thick fog on ground."
```

#### 2. íëëª ë³ê²½
| ë³ê²½ ì  | ë³ê²½ í |
|---------|---------|
| `description` | `static_visual_prompt` |
| `visual_background` | `static_visual_prompt` |

#### 3. Chain of Thought íë¡ì¸ì¤
```
1. IDENTIFY: íì¤í¸ìì ìºë¦­í° ì´ë¦/íë ëì¬ ì°¾ê¸°
2. REMOVE: ìì í ì ê±°
3. FOCUS: ë¨ì ë¬¼ë¦¬ì  íê²½ìë§ ì§ì¤
4. DESCRIBE: íì¤ì², ì¬ì§, ì¡°ëª, ììì¼ë¡ ë¬ì¬
5. CREATIVELY INFER: ê°ë¨í ë¬ì¬ë©´ ëíì¼ ì¶ê°
```

#### 4. íëí° ê²½ê³  ì¶ê°
```
PENALTY WARNING: If ANY character name or action verb is included, 
the output is INVALID and will be REJECTED.
```

### ð ìì ë íì¼
- `app/agents/extraction/setting.py` - íë¡¬íí¸ ì ë©´ ê°ì 
- `app/schemas/settings.py` - `is_primary`, `art_style` íë ì¶ê°

### â ê²°ê³¼
- ì¸ë¬¼/ì¬ê±´ ìì  ì ê±°ë¨
- ìì ë°°ê²½ ë°ì´í°(Clean Background Data) ìì± ì±ê³µ
- ì´ë¯¸ì§ ìì± AIì ì§ì  ì¬ì© ê°ë¥í íë¡¬íí¸ íì§ ë¬ì±

---

## 2. Event Agent - ë°°ê²½ ë¬ì¬ í¼ì ë° ì°¸ì¡° ë§¤ì¹­ ë¬¸ì 

### ð ë ì§
2025-12-27

### ð´ ë¬¸ì  (Problem)
1. `visual_scene`ì ë°°ê²½ ë¬ì¬ê° í¬í¨ë¨ (Setting Agentì ì¤ë³µ)
2. `participants`ê° Character Agentì ì´ë¦ê³¼ ì íí ë§¤ì¹­ëì§ ìì
3. `location_ref`ê° Setting Agentì ì´ë¦ê³¼ ë§¤ì¹­ëì§ ìì

**ì¤í¨ ì¶ë ¥ ìì**:
```json
{
  "visual_scene": "A man holding a sword in a dark forest with tall trees and fog.",
  "participants": ["the protagonist"],
  "location_ref": "A dark forest where trees are twisted"
}
```

**ê¸°ë ì¶ë ¥**:
```json
{
  "visual_scene": "A tall man with dark hair gripping a sword, tense posture, alert expression",
  "participants": ["ìì§"],
  "location_ref": "Dark Forest"
}
```

### ð¡ ìì¸ ë¶ì (Root Cause)
1. Event Agentìê² Character/Setting ì ë³´ê° ì ë¬ëì§ ìì
2. íë¡¬íí¸ì ëªíí ì­í  ë¶ë¦¬ ì§ì ìì
3. ì°¸ì¡°ì© ë°ì´í° ìì´ LLMì´ ìì²´ ìì±

### ð¢ í´ê²°ì± (Solution)

#### 1. Phase ë¶ë¦¬ (graph.py)
```python
# Phase 1: Character + Setting (ë³ë ¬)
# Phase 2: Event (ìì°¨ - Phase 1 ê²°ê³¼ ì°¸ì¡°)
```

#### 2. Bad vs Good ìì ì¶ê°
```
â BAD: visual_sceneì "dark forest with trees"
â GOOD: visual_sceneì "intense eye contact, low angle shot" (êµ¬ëë§)
```

#### 3. ì°¸ì¡° ë°ì´í° ì ë¬
```python
response = await chain.ainvoke({
    "story_text": state["content"],
    "available_characters": ["ìì§", "ì´ë¯¼í¸", ...],  # Character Agent ê²°ê³¼
    "available_settings": ["Dark Forest", ...],       # Setting Agent ê²°ê³¼
})
```

#### 4. íëí° ê²½ê³ 
```
If visual_scene contains "forest", "trees", "moon", "fog" - REJECTED
```

### ð ìì ë íì¼
- `app/agents/graph.py` - 2-Phase Extraction êµ¬í
- `app/agents/extraction/event.py` - íë¡¬íí¸ ì ë©´ ê°ì 
- `app/schemas/events.py` - (ì´ë¯¸ Production Level)

### â ê²°ê³¼
- Eventì `visual_scene`ìì ë°°ê²½ ë¬ì¬ ì ê±°
- `participants`ê° Character Agent ì´ë¦ê³¼ ì íí ë§¤ì¹­
- `location_ref`ê° Setting Agent ì´ë¦ê³¼ ì íí ë§¤ì¹­
- Neo4j ê·¸ëí ì£ì§ ìë ìì± ê°ë¥

---

## 3. Dialogue Agent - Production Level ìê·¸ë ì´ë

### ð ë ì§
2025-12-27

### ð´ ë¬¸ì  (Problem)
1. ê¸°ë³¸ì ì¸ íë¡¬íí¸ë§ ìì´ì ì¶ë ¥ êµ¬ì¡°ê° ë¨ìí¨
2. Character Agentì ì´ë¦ ë§¤ì¹­ì´ ì ë¨
3. Neo4j ì£ì§ ìì±ì íìí ìì±(formality, power, intimacy)ì´ ìì

**ê¸°ì¡´ ì¶ë ¥**:
```json
{
  "key_dialogues": ["..."],
  "speech_patterns": {}
}
```

### ð¡ ìì¸ ë¶ì (Root Cause)
1. Dialogue Agentê° Character Agent ê²°ê³¼ë¥¼ ì°¸ì¡°íì§ ìì
2. ì¤í¤ë§(`dialogues.py`)ì ìì¸ ëª¨ë¸ì´ ìì§ë§ íë¡¬íí¸ìì íì© ì í¨
3. ê´ê³ì±(speaker â listener)ì´ êµ¬ì¡°íëì§ ìì

### ð¢ í´ê²°ì± (Solution)

#### 1. Character ì°¸ì¡° ì ë¬
```python
available_characters = [c.get("name", "") for c in state.get("extracted_characters", [])]
response = await chain.ainvoke({
    "story_text": state["content"],
    "available_characters": json.dumps(available_characters)
})
```

#### 2. 3ì°¨ì ê´ê³ ëª¨ë¸ë§
- `formality`: "formal", "informal", "mixed"
- `power_dynamic`: "superior", "equal", "subordinate"
- `intimacy_level`: 1-10 ì ëí

#### 3. Neo4j ì£ì§ ìì± ì¶ì¶
```json
{
  "dialogue_relationships": [
    {
      "speaker": "íë",
      "listener": "ìì§",
      "formality_to_listener": "formal",
      "power_dynamic": "subordinate",
      "intimacy_level": 7
    }
  ]
}
```

### â ï¸ ì£¼ìì¬í­ (Data Integrity)

#### Enum ì í¨ì± ê²ì¦
LLMì´ "polite" ëì  "formal", "lower" ëì  "subordinate" ë± ì ìì´ë¥¼ ì¶ë ¥í  ì ìì.
â Pydantic ëë íì²ë¦¬ìì íì©ê° ê²ì¦ íì

#### ë¸ë í¤ ë¬´ê²°ì±
Character Agentê° "Seojin"(ìë¬¸), Dialogue Agentê° "ìì§"(íê¸) ì¶ë ¥ ì ë§¤ì¹­ ì¤í¨
â ì¼ê´ë ìë³ì(Identifier) ì¬ì© ê¶ì¥

### ð ìì ë íì¼
- `app/agents/extraction/dialogue.py` - íë¡¬íí¸ Production Level ìê·¸ë ì´ë
- `tests/test_agents/test_dialogue_analysis.ipynb` - íì¤í¸ ë¸í¸ë¶ ìì¸í

### â ê²°ê³¼
- `key_dialogues`: ì¤ì ëì¬ + ì¨ê²¨ì§ ìë¯¸(subtext) ì¶ì¶
- `speech_patterns`: ìºë¦­í°ë³ ë§í¬ í¹ì±
- `dialogue_relationships`: Neo4j ì£ì§ ìì± (formality, power, intimacy)
- Character Agent ì´ë¦ê³¼ ì íí ë§¤ì¹­

### ð¡ í¥í ê°ì  ì¬í­ (Future Enhancements)

#### 1. ì¹ë°ë(Intimacy) ë³ì ë¶ë¦¬
íì¬: ë¨ì¼ `intimacy_level` (1-10)
ë¬¸ì : ìê¿ì¹êµ¬ ì¤ì ìë íì¬ ì ëì ì´ë©´ ë®ê² ì¸¡ì ë¨

**ì ìë ë¶ë¦¬**:
```json
{
  "friendliness": 2,      // íì¬ ì°í¸ë (ë®ì)
  "bond_strength": 9      // ê´ê³ì ê¹ì´/ì­ì¬ (ëì)
}
```
â "ì£½ì´ê³  ì¶ì ë§í¼ ë¯¸ì°ë©´ìë ìë¡ë¥¼ ê°ì¥ ì ìë ì ì¦ ê´ê³" íí ê°ë¥

#### 2. ê¶ë ¥ ê´ê³ ë¹ëì¹­ì± ê²ì¦
AâBê° "superior"ë©´ BâAë "subordinate"ì¬ì¼ í¨
íì¬: LLMì´ ìí©ì ë°ë¼ ë¤ë¥´ê² íë¨ (íëê° ì´ë¯¼í¸ìê² ë§ìë íë = equal)

**ê²ì¦ ë¡ì§ ì¶ê° ì ì**:
```python
if power_ab == "superior" and power_ba != "subordinate":
    conflicts.append("Power asymmetry detected")
```

#### 3. ìë³ì ì¼ê´ì± ê°ì 
ì´ë¯¸ `available_characters` ì ë¬ë¡ í´ê²°ë¨
ì¶ê° ë³´ì: íë¡¬íí¸ì **"ìºë¦­í° ì´ë¦ì ë°ëì ì ê³µë ë¦¬ì¤í¸ íê¸°ë¥¼ ê·¸ëë¡ ë°ë¥¼ ê²"** ëªì

---

## 4. Emotion Agent - Production Level ìê·¸ë ì´ë

### ð ë ì§
2025-12-27

### ð´ ë¬¸ì  (Problem)
1. ê¸°ë³¸ì ì¸ íë¡¬íí¸ë¡ ì¶ë ¥ êµ¬ì¡°ê° ë¨ìí¨ (emotion, intensityë§)
2. Character Agentì ì´ë¦ ë§¤ì¹­ì´ ì ë¨
3. ê°ì  í¸ë¦¬ê±°, íí ë°©ì ë± ì»¨íì¤í¸ ë¶ì¡±

### ð¢ í´ê²°ì± (Solution)

#### 1. ê°ì  íë íì¥
- `primary_emotion`, `secondary_emotion`: ë³µí© ê°ì  íí
- `trigger`: ê°ì  ì ë° ìì¸
- `expression`: ë¬¼ë¦¬ì  íí ë°©ì
- `is_hidden`: ì¨ê²¨ì§ ê°ì  ì¬ë¶

#### 2. Neo4j ë¸ë ìì± ìë°ì´í¸
```json
{
  "neo4j_updates": [
    {
      "character_name": "ìì§",
      "property_updates": {
        "current_emotion": "ë¶ë¸",
        "emotion_intensity": 8,
        "emotion_valence": "negative"
      }
    }
  ]
}
```

### ð¡ í¥í ê°ì  ì¬í­ (Event Sourcing)

íì¬ ë°©ìì ìºë¦­í° ë¸ëì ìì±ì ë®ì´ì°ê¸°(Overwrite)í©ëë¤.
ê°ì  ë³íì ì­ì¬(History)ë¥¼ ì¶ì í´ì¼ íë¤ë©´:

**íì¬ (State Update)**:
```cypher
SET (Character).emotion = "ë¶ë¸"
```

**ê³ ëí (Event Graph)**:
```cypher
CREATE (c:Character)-[:FELT {timestamp: t, chapter: 3}]->(e:Emotion {type: "ë¶ë¸"})
```

â ì¤í ë¦¬ ì§íì ë°ë¥¸ ê°ì  ë³í ê¶¤ì (Trajectory) ë¶ì ê°ë¥

### ð ìì ë íì¼
- `app/agents/extraction/emotion.py` - íë¡¬íí¸ Production Level ìê·¸ë ì´ë
- `tests/test_agents/test_emotion_tracking.ipynb` - íì¤í¸ ë¸í¸ë¶ ìì¸í

### â ê²°ê³¼
- `emotion_states`: ìì¸ ê°ì  ë¶ì (trigger, expression, is_hidden)
- `neo4j_updates`: Character ë¸ë ìì± ìë°ì´í¸ì© JSON
- Character Agent ì´ë¦ê³¼ ì íí ë§¤ì¹­

---

## 5. Consistency Agent - Production Level ìê·¸ë ì´ë

### ð ë ì§
2025-12-27

### ð´ ë¬¸ì  (Problem)
1. Dialogue/Emotion Agent ê²°ê³¼ë¥¼ íì©íì§ ìì (Level 1 ë°ì´í° ë¯¸íµí©)
2. ê´ê³ ë°©í¥ì± ê²ì¦ ìì (BETRAYED/MENTORë ë¨ë°©í¥ì´ì´ì¼ í¨)
3. ì°¸ì¡° ë¬´ê²°ì± ê²ì¦ ìì (ì¡´ì¬íì§ ìë ìºë¦­í° ì°¸ì¡° ê°ë¥)
4. Neo4j-ready ì¶ë ¥ êµ¬ì¡° ìì

**ê¸°ì¡´ ê²ì¦ ë²ì**:
- Character trait ì¶©ëë§ ê°ì§
- ë¨ì ì ì ê³ì° (HIGH: -25, MEDIUM: -10)

### ð¡ ìì¸ ë¶ì (Root Cause)
1. ì´ê¸° êµ¬íìì Level 1 Agent ê²°ê³¼ íµí©ì ê³ ë ¤íì§ ìì
2. ê´ê³ ë°©í¥ì± ê·ì¹(BETRAYED: ë°°ì ìâí¼í´ì)ì´ íë¡¬íí¸ì ìì
3. íë¡ê·¸ëë§¤í± ê²ì¦ì´ trait ì¶©ëìë§ íì ë¨

### ð¢ í´ê²°ì± (Solution)

#### 1. Level 1 Agent ë°ì´í° íµí©
```python
dialogues = state.get("analyzed_dialogues", {})
emotions = state.get("tracked_emotions", {})
```

#### 2. ì¶©ë ì í íì¥
| ì¶©ë ì í | Severity | ì¤ëª |
|----------|----------|------|
| `CHARACTER_TRAIT_CONFLICT` | HIGH | ëª¨ìë ì±ê²© í¹ì± |
| `DIRECTION_CONFLICT` | MEDIUM | BETRAYED/MENTOR ë°©í¥ì± ì¤ë¥ |
| `REFERENTIAL_INTEGRITY_ERROR` | HIGH | ì¡´ì¬íì§ ìë ìºë¦­í° ì°¸ì¡° |
| `DIALOGUE_CONSISTENCY_CONFLICT` | LOW-MEDIUM | ëí í¨í´-ì±ê²© ë¶ì¼ì¹ |
| `EMOTION_CONSISTENCY_CONFLICT` | LOW-MEDIUM | ê°ì -íë ë¶ì¼ì¹ |

#### 3. íë¡ê·¸ëë§¤í± ê²ì¦ íì¥
```python
def validate_relationship_directions(relationships: list) -> list:
    """BETRAYED/MENTORë bidirectional=falseì¬ì¼ í¨"""
    ...

def validate_character_references(relationships: list, available_names: set) -> list:
    """ëª¨ë  source/targetì´ character listì ì¡´ì¬í´ì¼ í¨"""
    ...
```

#### 4. Neo4j-Ready ì¶ë ¥ ì¶ê°
```json
{
  "neo4j_validation": {
    "is_valid": true,
    "conflict_count": 0,
    "high_severity_count": 0
  }
}
```

### ð ìì ë íì¼
- `app/agents/analysis/consistency.py` - Production Level ì ë©´ ê°ì 
- `tests/test_agents/test_consistency_check.ipynb` - 7ê° íì¤í¸ ì¹ìì¼ë¡ íì¥

### â ê²°ê³¼
- Dialogue/Emotion ë°ì´í° êµì°¨ ê²ì¦
- ê´ê³ ë°©í¥ì± ìë ê²ì¦ (BETRAYED, MENTOR)
- ì°¸ì¡° ë¬´ê²°ì± ìë ê²ì¦
- Neo4j ê²ì¦ ê²°ê³¼ êµ¬ì¡°íë ì¶ë ¥

### ð¡ ì¶ê° ê¸°ë¥: ìë í´ê²° ì ëµ (Auto-Resolution Strategy)

ê° ì¶©ëì `suggested_action` ë° `final_value_candidate` íë ì ê³µ:

| Action | ì¤ëª |
|--------|------|
| `KEEP_DB_VALUE` | ê¸°ì¡´ DB ê° ì ì§ |
| `OVERWRITE_WITH_NEW` | ì ê°ì¼ë¡ ë®ì´ì°ê¸° (ì ìí) |
| `FLAG_FOR_HUMAN` | ì¸ê° ê²í  íì |
| `AUTO_FIX` | ìì¤í ìë ìì  ê°ë¥ |

**ð final_value_candidate êµ¬ì¡°** (AUTO_FIX ì):
```json
{
  "table": "relationships",
  "key": {"source": "ì´ë¯¼í¸", "target": "ìì§", "relation_type": "BETRAYED"},
  "update": {"bidirectional": false}
}
```
â ë³ë ì°ì° ìì´ ë°ë¡ UPDATE ì¿¼ë¦¬ì ë°ì¸ë© ê°ë¥!

**Resolution Summary ì¶ë ¥**:
```json
{
  "resolution_summary": {
    "auto_fixable": 2,
    "ready_for_update": 2,  // ð ë°ë¡ DB UPDATE ê°ë¥í ì
    "needs_human_review": 3,
    "total_conflicts": 6
  }
}
```

**ë°±ìë ë¡ì§ ìì**:
```python
for conflict in conflicts:
    if conflict['suggested_action'] == 'AUTO_FIX':
        fvc = conflict['final_value_candidate']
        # ë°ë¡ UPDATE ì¿¼ë¦¬ ì¤í ê°ë¥!
        db.execute(f\"\"\"
            UPDATE {fvc['table']} 
            SET {', '.join(f'{k}={v}' for k,v in fvc['update'].items())}
            WHERE source='{fvc['key']['source']}' AND target='{fvc['key']['target']}'
        \"\"\")
```

---

## 6. Plot Integration Agent - Production Level ìê·¸ë ì´ë

### ð ë ì§
2025-12-27

### ð´ ë¬¸ì  (Problem)
1. ê¸°ë³¸ì ì¸ íë¡¬íí¸ë¡ ë¨ì ìì½ë§ ì ê³µ
2. ë©í°ë¯¸ëì´ íì´íë¼ì¸ì íìí ìê³ì´ ë°ì´í° ìì
3. ì´ë²¤í¸/ìºë¦­í° ì°¸ì¡° ìì´ ìì²´ ì´ë¦ ìì±

**ê¸°ì¡´ ì¶ë ¥**:
```json
{
  "plot_summary": "...",
  "foreshadowing": ["..."],
  "tension_level": 5
}
```

### ð¡ ìì¸ ë¶ì (Root Cause)
1. Tensionì´ ë¨ì¼ ì«ìë¡ ìê° íë¦ì ë°ë¥¸ ë³í íí ë¶ê°
2. ë¹í¸ ë¨ì ë¶í  ìì´ ì»· ì°ì¶/ì½í ìì± íì© ë¶ê°
3. Event Agent ê²°ê³¼ ì°¸ì¡°íì§ ìì

### ð¢ í´ê²°ì± (Solution)

#### 1. Tension Curve ë°°ì´ ëì
```json
"tension_curve": [3, 5, 7, 8, 6]
```
â ì¤ëì¤ ë¹ëì(â), ëë¡­(â) íì´ë° ìë ìì± ê°ë¥

#### 2. Narrative Beats ë¶í 
```json
"narrative_beats": [
  {
    "beat_id": 1,
    "text": "ìì§ê³¼ íëê° ì´ëì´ ì²ìì ë§ë¨",
    "beat_type": "SETUP",
    "event_ref": "E001",
    "visual_prompt": "Two figures meeting in dark forest"
  }
]
```
- `beat_type`: SETUP, INCITING_INCIDENT, CLIMAX ë±
- `visual_prompt`: ì½í AI ì§ì  ìë ¥ ê°ë¥

#### 3. Multimedia Pipeline Summary
```json
{
  "multimedia_summary": {
    "beat_count": 5,
    "tension_curve_length": 5,
    "has_visual_prompts": true,
    "tension_range": {"min": 3, "max": 8, "peak_index": 3}
  }
}
```

### ð ìì ë íì¼
- `app/agents/analysis/plot.py` - Production Level ìê·¸ë ì´ë
- `tests/test_agents/test_plot_integration.ipynb` - 7ê° ì¹ìì¼ë¡ íì¥

### â ê²°ê³¼
- 3-Act êµ¬ì¡° + Foreshadowing + Neo4j ì£ì§
- Tension Curve ë°°ì´ (ì¤ëì¤/ì°ì¶ íì´ë°ì©)
- Narrative Beats (ì»· í¸ì§/ì½í íë¡¬íí¸ì©)
- Multimedia Summary (íì´íë¼ì¸ ê²ì¦ì©)

### ð¡ ì¶ê° ìì : Tension Curve ë¹ ë°°ì´ ë¬¸ì 

**ë¬¸ì **: LLMì´ `tension_curve`ë¥¼ ë¹ ë°°ì´ `[]`ë¡ ë°ííë ê²½ì° ë°ì

**í´ê²°**: íë¡ê·¸ëë§¤í± ë°±ì í¨ì ì¶ê°
```python
def generate_fallback_tension_curve(events: list) -> list:
    """ì´ë²¤í¸ importanceë¡ tension ìë ìì±"""
    return [max(1, min(10, e.get("importance", 5))) for e in events]

def generate_fallback_beats(events: list) -> list:
    """ì´ë²¤í¸ìì narrative beats ìë ìì±"""
    ...
```

**ê²°ê³¼ (ë¡ê·¸)**:
```
[PLOT] Generating fallback tension_curve from event importance
[PLOT] Beats: 5, Tension curve: [7, 9, 8, 8, 6]
```
â Raw Data ë°°ì´ì´ í­ì ë³´ì¥ë¨

---

## 7. Validator Agent - Production Level ìê·¸ë ì´ë

### ð ë ì§
2025-12-28

### ð´ ë¬¸ì  (Problem)
1. ê¸°ë³¸ì ì¸ True/False ê²ì¦ë§ ì ê³µ
2. ìë¬ ë°ì ì "ì´ëì, ì" ì ë³´ ìì
3. ì±ë¥ ëª¨ëí°ë§ ë¶ê°

### ð¢ í´ê²°ì± (Solution)

#### 1. êµ¬ì¡°íë ìë¬ ì¶ë ¥
```json
{
  "field": "extracted_characters[0].name",
  "code": "VAL_003",
  "message": "Required field 'name' is missing",
  "value": null
}
```

#### 2. ì¤í ìê° ë©í¸ë¦­
```json
"execution_time_ms": 12.5
```

### ð ìì ë íì¼
- `app/agents/validation/validator.py` - êµ¬ì¡°íë ìë¬, ì¤í ìê°
- `tests/test_agents/test_validator.ipynb` - íì¤í¸ ì¼ì´ì¤

### â ê²°ê³¼
- 8ê° ìì´ì í¸ ì¶ë ¥ ê°ë³ ê²ì¦
- êµ¬ì¡°íë ìë¬ ë¦¬í¬í¸ (field, code, message, value)
- ì¤í ìê° ë©í¸ë¦­

---

## 8. Supervisor Agent - Production Level ìê·¸ë ì´ë

### ð ë ì§
2025-12-28

### ð´ ë¬¸ì  (Problem)
1. ìì²­ ì¶ì  ë¶ê° - ë¹ëê¸° íê²½ìì ë¡ê·¸ ì¶ì  ì´ë ¤ì
2. Validation ì¤í¨ ì ë¬´í ë£¨í ê°ë¥ì±
3. ìµë ì¬ìë ì´ê³¼ ì ì²ë¦¬ ë°©ì ìì

### ð¢ í´ê²°ì± (Solution)

#### 1. Global Trace ID (ì ì­ ì¶ì  ID)
```python
def generate_trace_id() -> str:
    return f"req-{date_str}-{short_uuid}"
# ì¶ë ¥: "req-20251228-123456-a1b2c3d4"
```
â ëª¨ë  ë¡ê·¸ì ìì²­ ì¶ì  ID í¬í¨

#### 2. Supervisor State (ì¬ìë ëª¨ëí°ë§)
```json
{
  "trace_id": "req-20251228-123456-a1b2c3d4",
  "current_phase": "extraction",
  "retry_counts": {"extraction": 1, "analysis": 0},
  "max_retries": {"extraction": 3, "analysis": 2}
}
```

#### 3. Human Review Node
```python
if retry_count >= MAX_EXTRACTION_RETRIES:
    return "human_review"  # ì¬ë ê°ì ìì²­
```
â ìµë ì¬ìë (3í) ì´ê³¼ ì ì¬ë ê°ì

### ð ìì ë íì¼
- `app/agents/supervisor.py` - trace_id, supervisor_state, human_review_node
- `tests/test_agents/test_supervisor.ipynb` - 9ê° íì¤í¸ ì¼ì´ì¤

### â ê²°ê³¼
- **trace_id**: ì ì­ ìì²­ ì¶ì  ID
- **supervisor_state**: ì¬ìë íì ëª¨ëí°ë§
- **human_review**: ë¬´í ë£¨í ë°©ì§ + ì¬ë ê°ì ë¼ì°í

---

## 9. Message Schema - íì´ë¸ë¦¬ë ìí¤íì² ìê·¸ë ì´ë

### ð ë ì§
2025-12-28

### ð´ ë¬¸ì  (Problem)
1. `messages.py`ì `AnalysisContext`ê° ê¸°ë³¸ count ì ë³´ë§ í¬í¨
2. `rabbitmq_consumer.py`ê° Supervisorì ì°ëëì§ ìì
3. ìì´ì í¸ë¤ì´ ê¸°ì¡´ ìºë¦­í°/ì´ë²¤í¸ ë°ì´í°ì ì ê·¼ ë¶ê°
4. ë¶ì° ì¶ì ì ìí Global Trace ID ë¯¸ì§ì

**ê¸°ì¡´ ë©ìì§ ì¤í¤ë§**:
```python
class AnalysisContext(BaseModel):
    previous_chapters: list[str] = []
    existing_characters_count: int = 0  # countë§
    existing_events_count: int = 0      # countë§
```

**ê¸°ì¡´ ë°ì´í° ì ê·¼ ë¬¸ì **:
- ConsistencyChecker: ê¸°ì¡´ ìºë¦­í° ìì±ê³¼ ë¹êµ ë¶ê°
- RelationshipAnalyzer: ê¸°ì¡´ ê´ê³ ë°ì´í° ì°¸ì¡° ë¶ê°
- ì¼ê´ì± ê²ì¬ê° ëì¼ ë¬¸ì ë´ììë§ ê°ë¥

### ð¡ ìì¸ ë¶ì (Root Cause)
1. ì´ê¸° ì¤ê³ìì Spring Boot â FastAPI ë°©í¥ë§ ê³ ë ¤
2. FastAPIê° ê¸°ì¡´ ë°ì´í°ë¥¼ ì¡°íí  ë°©ë²ì´ ììì
3. ë©ìì§ í¬ê¸° ìµìíë¥¼ ìí´ countë§ ì ì¡íëë¡ ì¤ê³

### ð¢ í´ê²°ì± (Solution)

#### ìí¤íì² ê²°ì : íì´ë¸ë¦¬ë ë°©ì
ë ê°ì§ ì ê·¼ ë°©ìì ì¥ì ì ê²°í©:

| ìµì | ì¤ëª | ì¥ë¨ì  |
|------|------|--------|
| **A. Spring Boot ì ì¡** | ê¸°ì¡´ ë°ì´í°ë¥¼ ë©ìì§ì í¬í¨ | ë¹ ë¦, ë©ìì§ í¬ê¸° ì¦ê° |
| **B. FastAPI DB ì¡°í** | íìì ì§ì  DB ì¡°í | í­ì ìµì , ë¤í¸ìí¬ í |
| **â C. íì´ë¸ë¦¬ë** | ê²½ë ì°¸ì¡° ì ì¡ + íìì DB ì¡°í | ê· í ì¡í ì ê·¼ |

**íµì¬ ìì¹**:
- **ì½ê¸° (Read)**: FastAPIê° PostgreSQL/Neo4j ì§ì  ì¡°í
- **ì°ê¸° (Write)**: Spring Boot ì½ë°±ì íµí´ ì²ë¦¬

#### 1. ê²½ë ì°¸ì¡° ì¤í¤ë§ (`messages.py`)
```python
class ExistingCharacterRef(BaseModel):
    """ê²½ë ì°¸ì¡° - ì´ë¦ ë§¤ì¹­ì©"""
    id: str
    name: str
    role: Optional[str] = None

class ExistingRelationshipRef(BaseModel):
    """Neo4j ê´ê³ ê²½ë ì°¸ì¡°"""
    source_name: str
    target_name: str
    relation_type: str
    strength: int = 5

class AnalysisContext(BaseModel):
    """íì¥ë ì»¨íì¤í¸"""
    chapter_number: Optional[int] = None
    existing_characters: list[ExistingCharacterRef] = []
    existing_events: list[ExistingEventRef] = []
    existing_relationships: list[ExistingRelationshipRef] = []
    existing_settings: list[ExistingSettingRef] = []
    world_rules_summary: Optional[str] = None
```

#### 2. DB ì¡°í ìë¹ì¤ (`db_query_service.py`) - NEW
```python
class DatabaseQueryService:
    """ì½ê¸° ì ì© DB ì¡°í ìë¹ì¤"""
    
    async def get_character_details(self, project_id: str, name: str):
        """ìºë¦­í° ìì¸ ì ë³´ ì¡°í"""
        ...
    
    async def get_all_relationships(self, project_id: str):
        """Neo4j ê´ê³ ì ì²´ ì¡°í"""
        ...
    
    async def get_world_rules(self, project_id: str):
        """ì¸ê³ê´ ê·ì¹ ì¡°í"""
        ...
```

#### 3. RabbitMQ Consumer ê°í (`rabbitmq_consumer.py`)
```python
class RabbitMQConsumer:
    """íë¡ëì ë ë²¨ Consumer"""
    
    # ì°ê²° ì¬ìë ë¡ì§ (ìµë 5í)
    async def connect(self) -> None:
        for attempt in range(max_retries):
            try: ...
    
    # Global Trace ID ì í
    async def _process_message(self, message):
        trace_id = task_message.trace_id or self._generate_trace_id()
        bound_logger = logger.bind(trace_id=trace_id)
    
    # í¬ì¤ ì²´í¬
    async def health_check(self) -> dict:
        return {"connected": ..., "consuming": ...}
```

#### 4. Analysis Service íì´ë¸ë¦¬ë íµí© (`analysis_service.py`)
```python
async def run_analysis(task, trace_id, enrich_from_db=False):
    # 1. ë©ìì§ìì ì´ê¸° ìí ìì±
    initial_state = await create_initial_state_from_message(task, trace_id)
    
    # 2. íìì DBìì ì¶ê° ë°ì´í° ì¡°í
    if enrich_from_db:
        db_service = await get_db_service()
        initial_state = await enrich_state_with_db(initial_state, db_service)
    
    # 3. íì´íë¼ì¸ ì¤í
    final_state = await run_analysis_pipeline(...)
```

#### 5. State/Graph ìë°ì´í¸
```python
# state.py - ì íë ì¶ê°
trace_id: str = ""
chapter_number: Optional[int] = None
world_rules_summary: Optional[str] = None
existing_settings: list[dict] = []  # dict â list íì ë³ê²½

# graph.py - íë¼ë¯¸í° ì¶ê°
async def run_analysis_pipeline(
    ...,
    existing_settings: list = None,  # NEW
    trace_id: str = "",              # NEW
):
```

### ð ìì ë íì¼

| íì¼ | ë³ê²½ ë´ì© |
|------|----------|
| `app/schemas/messages.py` | ê²½ë ì°¸ì¡° ì¤í¤ë§ (ExistingCharacterRef, ExistingEventRef, ExistingRelationshipRef, ExistingSettingRef), trace_id ì§ì |
| `app/services/rabbitmq_consumer.py` | ì°ê²° ì¬ìë ë¡ì§, Global Trace ID ì í, graceful shutdown, í¬ì¤ ì²´í¬ |
| `app/services/db_query_service.py` | **[NEW]** PostgreSQL/Neo4j ì½ê¸° ì ì© ì¡°í ìë¹ì¤ |
| `app/services/analysis_service.py` | íì´ë¸ë¦¬ë íµí© - ë©ìì§ìì ì´ê¸° ìí ìì± + íìì DB ë³´ê° |
| `app/agents/state.py` | trace_id, chapter_number, world_rules_summary íë ì¶ê° |
| `app/agents/graph.py` | trace_id, existing_settings íë¼ë¯¸í° ì¶ê° |
| `pyproject.toml` | asyncpg>=0.30.0, neo4j>=5.26.0 ìì¡´ì± ì¶ê° |

### â ê²°ê³¼

**ë°ì´í° íë¦**:
```
Spring Boot ì ì¡: íì¤í¸ + ê²½ë ì°¸ì¡° (ì´ë¦, ID ë±)
         â
FastAPI ìì : AnalysisTaskMessage íì±
         â
[ì íì ] DB ë³´ê°: ì»¨íì¤í¸ê° ë¶ì¡±íë©´ PostgreSQL/Neo4j ì§ì  ì¡°í
         â
ìì´ì í¸ íì´íë¼ì¸ ì¤í: ìì¸ ë¶ì
         â
Spring Boot ì½ë°±: ê²°ê³¼ ì ì¡
```

**ì£¼ì ê°ì ì **:
- â ìì´ì í¸ê° ê¸°ì¡´ ìºë¦­í°/ì´ë²¤í¸/ê´ê³ ë°ì´í°ì ì ê·¼ ê°ë¥
- â ì¼ê´ì± ê²ì¬ê° ì ì²´ íë¡ì í¸ ë²ììì ê°ë¥
- â Global Trace IDë¡ ë¶ì° íê²½ ë¡ê·¸ ì¶ì  ê°ë¥
- â ì°ê²° ì¤í¨ ì ìë ì¬ìë

### â ï¸ ë¤ì ë¨ê³ (Implementation Checklist)

1. **ìì¡´ì± ì¤ì¹**:
   ```bash
   pip install asyncpg neo4j
   ```

2. **Spring Boot ë©ìì§ íì ìë°ì´í¸**:
   ìë¡ì´ `AnalysisContext` ì¤í¤ë§ì ë§ê² ë©ìì§ ìì±

3. **DB íì´ë¸ íì¸**:
   `characters`, `events`, `settings`, `world_rules` íì´ë¸ ì¡´ì¬ íì¸

4. **íê²½ ë³ì ì¤ì ** (`.env`):
   ```
   POSTGRES_HOST=localhost
   POSTGRES_PORT=5432
   POSTGRES_DB=stolink
   POSTGRES_USER=stolink
   POSTGRES_PASSWORD=stolink123
   
   NEO4J_URI=bolt://localhost:7687
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=stolink123
   ```

### ð¡ í¥í ê°ì  ì¬í­

#### 1. ìºì± ë ì´ì´ ì¶ê°
ìì£¼ ì¡°íëë ë°ì´í° (ìºë¦­í° ëª©ë¡ ë±)ë¥¼ Redis ìºì±:
```python
@cached(ttl=300)
async def get_all_characters(self, project_id: str):
    ...
```

#### 2. Connection Pooling ìµì í
íì¬: min_size=2, max_size=10
íë¡ëì: ëì ë¶ì ìì ìì ë°ë¼ ì¡°ì  íì

#### 3. Dead Letter Queue êµ¬í
ì²ë¦¬ ì¤í¨í ë©ìì§ë¥¼ ë³ë íë¡ ì´ë:
```python
# rabbitmq_consumer.pyì DLX ì¤ì  (TODO)
arguments={
    "x-dead-letter-exchange": "stolink.dlx",
    "x-dead-letter-routing-key": "stolink.analysis.failed"
}
```

### ð ì¶ê° ë²ê·¸ ìì : Callback URL ë¬´ì ë¬¸ì 

#### ë¬¸ì 
RabbitMQ ë©ìì§ìì `callback_url`ì `https://webhook.site/...`ë¡ ì¤ì í´ë í­ì `settings.spring_callback_url`ë¡ ìì²­ì´ ì ì¡ë¨.

**ìë¬ ë¡ê·¸**:
```
Callback request error error='All connection attempts failed' job_id=test-job-003
```

#### ìì¸
`callback_client.py`ê° ë©ìì§ì `callback_url`ì íë¼ë¯¸í°ë¡ ë°ì§ ìê³ , í­ì ì¤ì  íì¼ì ê¸°ë³¸ URLì ì¬ì©:

```python
# ê¸°ì¡´ ì½ë (ë¬¸ì )
callback_url = f"{self.base_url}/api/internal/ai/analysis/callback"
```

#### í´ê²°
1. `callback_client.py` - `callback_url` íë¼ë¯¸í° ì¶ê°:
```python
async def send_analysis_callback(
    self,
    ...,
    callback_url: Optional[str] = None  # NEW
) -> bool:
    if callback_url and callback_url.startswith("http"):
        url = callback_url  # ë©ìì§ì URL ì§ì  ì¬ì©
    else:
        url = f"{settings.spring_callback_url}/api/internal/ai/analysis/callback"
```

2. `analysis_service.py` - `task.callback_url` ì ë¬:
```python
callback_url = task.callback_url  # ë©ìì§ìì ì¶ì¶
await callback_client.send_analysis_callback(
    ...,
    callback_url=callback_url  # ì ë¬
)
```

#### íì¤í¸ ë°©ë²
1. RabbitMQ WebUIìì ë©ìì§ ë°í (callback_urlì webhook.siteë¡ ì¤ì )
2. webhook.siteìì ê²°ê³¼ ìì  íì¸

#### ìì ë íì¼
- `app/services/callback_client.py`
- `app/services/analysis_service.py`

---

## 10. JSON íì± ì¤ë¥ ë° ì¤í¤ë§ ë¶ì¼ì¹ - Structured Output ëì

### ð ë ì§
2025-12-29

### ð´ ë¬¸ì  (Problem)
1. LLMì´ JSON ëì  Markdown ì½ë ë¸ë¡(` ```json ... ``` `)ì¼ë¡ ê°ì¸ì ìëµ
2. `key=value` íì(Python repr)ì´ JSON ëì  ì¶ë ¥ëë ê²½ì° ë°ì
3. Spring Bootìì íì± ì¤í¨íë íë ì¡´ì¬ (`location_name`, `description` ëë½)

**ìë¬ ë¡ê·¸**:
```
Setting JSON parse error: Expecting property name enclosed in double quotes
Character JSON parse error: Invalid control character at: line 45 column 3
```

### ð¡ ìì¸ ë¶ì (Root Cause)
1. ìë `json.loads()` íì±ì ë¶ìì ì±
2. íë¡¬íí¸ ì§ìë§ì¼ë¡ë JSON íì ë³´ì¥ ë¶ê°
3. LLMì´ ê°íì ì¼ë¡ íì íë ëë½

### ð¢ í´ê²°ì± (Solution)

#### 1. `ChatBedrockConverse` + `with_structured_output()` ëì
```python
# llm.py
from langchain_aws import ChatBedrockConverse

def get_structured_llm(schema: Type[BaseModel]) -> ChatBedrockConverse:
    base_llm = get_bedrock_llm()
    return base_llm.with_structured_output(schema)
```

#### 2. ìì´ì í¸ ë¦¬í©í ë§
```python
# Before (ìë íì±)
response = await chain.ainvoke({"story_text": text})
content = response.content.strip()
if content.startswith("```"):
    content = content.split("```")[1]
result = json.loads(content)  # ìë¬ ê°ë¥!

# After (Structured Output)
structured_llm = get_structured_llm(SettingExtractionResult)
chain = PROMPT | structured_llm
result = await chain.ainvoke({"story_text": text})
# resultë ì´ë¯¸ Pydantic ê°ì²´ - íì± ë¶íì!
```

#### 3. ì¤í¤ë§ ìë°ì´í¸
| ì¤í¤ë§ | ì¶ê°/ë³ê²½ íë |
|--------|----------------|
| `SettingExtraction` | `location_name` ì¶ê° |
| `EventExtraction` | `description` íìí |
| `PlotIntegrationResult` | `foreshadow_id`, `hint_text` íìí |
| `ConsistencyReport` | `resolution_summary`, `neo4j_validation` ì¶ê° |
| `ValidationResult` | ì ê· ìì± |

### ð ìì ë íì¼
- `app/agents/llm.py` - `ChatBedrockConverse` + `get_structured_llm()` ì¶ê°
- `app/agents/extraction/character.py` - Structured Output ì ì©
- `app/agents/extraction/event.py` - Structured Output ì ì©
- `app/agents/extraction/setting.py` - Structured Output ì ì©
- `app/agents/analysis/plot.py` - Structured Output ì ì©
- `app/agents/analysis/consistency.py` - Structured Output ì ì©
- `app/schemas/plot.py` - Spring Boot í¸í êµ¬ì¡°ë¡ ì¬ìì±
- `app/schemas/consistency.py` - `ResolutionSummary`, `Neo4jValidation` ì¶ê°
- `app/schemas/validation.py` - ì ê· ìì±
- `app/schemas/callback.py` - `FullAnalysisResult` ìë°ì´í¸

### â ê²°ê³¼
| í­ëª© | ì  | í |
|------|---|---|
| JSON íì± ìë¬ | ê°íì  ë°ì | ë°ì ìì |
| Markdown ë¸ë¡ ì ê±° | íì | ë¶íì |
| íì ê²ì¦ | ìì | Pydantic ìë ê²ì¦ |
| íì íë ëë½ | ë°ì ê°ë¥ | ì¤í¤ë§ìì ê°ì  |

---

## 11. Job ìí ìë°ì´í¸ API ì°ë

### ð ë ì§
2025-12-29

### ð´ ë¬¸ì  (Problem)
ì¬ì©ììê² ë¶ì ììì ì¸ë°í ì§í ìíë¥¼ ì ê³µí  ì ììì. ê¸°ì¡´ìë PENDING â COMPLETED/FAILEDë§ íì.

### ð¡ ìì¸ ë¶ì (Root Cause)
FastAPIìì Spring Bootë¡ ì¤ê° ìíë¥¼ ìë°ì´í¸íë APIê° ììì.

### ð¢ í´ê²°ì± (Solution)

#### 1. Spring Boot íìì ì ê³µí API ì¤í
```http
POST /api/internal/ai/jobs/{jobId}/status
Content-Type: application/json

{
  "status": "ANALYZING",
  "message": "Character Agent ì¤í ì¤"
}
```

#### 2. CallbackClientì `update_job_status()` ë©ìë ì¶ê°
```python
async def update_job_status(
    self,
    job_id: str,
    status: str,
    message: str = None
) -> bool:
    url = f"{settings.spring_callback_url}/api/internal/ai/jobs/{job_id}/status"
    payload = {"status": status}
    if message:
        payload["message"] = message
    # ... HTTP POST ìì²­
```

#### 3. AnalysisServiceì ìí ìë°ì´í¸ íµí©
| ìì  | ìí | ë©ìì§ |
|------|------|--------|
| íì´íë¼ì¸ ìì ì | `ANALYZING` | "Starting multi-agent pipeline" |
| Validator ìì ì | `VALIDATING` | "Running validation and quality checks" |
| ìì¸ ë°ì ì | `FAILED` | ìë¬ ë©ìì§ (200ì ì í) |

### ð ìì ë íì¼
- `app/services/callback_client.py` - `update_job_status()` ë©ìë ì¶ê°
- `app/services/analysis_service.py` - ìí ìë°ì´í¸ í¸ì¶ íµí©

### â ê²°ê³¼
```
PENDING â PROCESSING â ANALYZING â VALIDATING â COMPLETED
                                            â FAILED
```

ì¬ì©ììê² ë ì¸ë°í ì§í ìí ì ê³µ ê°ë¥.

---

## 12. Character Agent - FullCharacter ì¤í¤ë§ íì¥

### ð ë ì§
2025-12-29

### ð´ ë¬¸ì  (Problem)

#### ë¬¸ì  1: ê¸°ì¡´ ì¤í¤ë§ íë ë¶ì¡±
- ê¸°ì¡´ `CharacterExtraction` ì¤í¤ë§ê° ê¸°ë³¸ ì ë³´ë§ í¬í¨ (name, role, visual, personality)
- ê²ì/ë¡¤íë ì´ì íìí ìì¸ íë ë¶ì¡± (age, race, faction, mbti, dialogue tone ë±)

#### ë¬¸ì  2: RelationshipType Enum ì¤ë¥
LLMì´ `FORMER_ALLY`ë¥¼ ì¶ë ¥íì¼ë Enumì ì ìëì§ ìì:
```
Input should be 'FRIEND', 'ENEMY', ... or 'UNKNOWN'
input_value='FORMER_ALLY'
```

#### ë¬¸ì  3: LLMì´ List íëì null ë°í
LLMì´ `null`ì ë°ííë©´ Pydantic `default_factory=list`ê° ë¬´ìëì´ ê²ì¦ ì¤ë¥ ë°ì:
```
Input should be a valid list [type=list_type, input_value=None, input_type=NoneType]
```
ìí¥ë°ì íë: `personality.flaws`, `personality.values`, `dialogue.catchphrases`, `relations.known_events` ë±

#### ë¬¸ì  4: CurrentMood íì íë ì¤ë¥
`CurrentMood.emotion`ì´ íì íë(`str = Field(...)`)ë¡ ì ìëì´ LLMì´ null ë°í ì ì¤ë¥:
```
Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
```

### ð¡ ìì¸ ë¶ì (Root Cause)
1. ì´ê¸° ì¤í¤ë§ê° ê¸°ë³¸ ì¤í ë¦¬ ë¶ìë§ ê³ ë ¤
2. `RelationshipType` Enumì `FORMER_ALLY`, `FORMER_ENEMY` ëë½
3. Pydantic v2ìì `default_factory`ë íëê° **ìì ë**ë§ ì ì©, LLMì´ **nullì ëªìì ì¼ë¡ ë°í**íë©´ ë¬´ìë¨
4. `CurrentMood` íëê° Optionalì´ ìë íìë¡ ì ìë¨

### ð¢ í´ê²°ì± (Solution)

#### 1. í¬ê´ì  ì¤í¤ë§ ìì± (`character_full.py`)
| í´ëì¤ | ì©ë |
|--------|------|
| `CharacterProfile` | ê¸°ë³¸ ì ë³´ (name, age, gender, race, faction, mbti, backstory) |
| `CharacterAppearance` | ì¸í ì ë³´ (physique, hair_color, attire, scars_tattoos) |
| `CharacterStats` | ë¥ë ¥ì¹ (str, dex, int, level, skills) |
| `DialogueConfig` | AI ëí ì¤ì  (tone, catchphrases, forbidden_topics) |
| `CombatConfig` | ì í¬ ì¤ì  (elemental_resist, attack_range) |
| **`FullCharacter`** | ì ëª¨ë  í´ëì¤ë¥¼ íµí©í ìì í ìºë¦­í° ëª¨ë¸ |

#### 2. RelationshipType Enum íì¥
```python
class RelationshipType(str, Enum):
    FRIEND = "FRIEND"
    ENEMY = "ENEMY"
    # ... ê¸°ì¡´ ê°ë¤ ...
    FORMER_ALLY = "FORMER_ALLY"   # ì¶ê°
    FORMER_ENEMY = "FORMER_ENEMY" # ì¶ê°
    NEUTRAL = "NEUTRAL"           # ì¶ê°
    UNKNOWN = "UNKNOWN"
```

#### 3. field_validatorë¡ nullâë¹ ë¦¬ì¤í¸ ë³í
```python
from pydantic import field_validator

def none_to_list(v):
    return v if v is not None else []

class DialogueConfig(BaseModel):
    catchphrases: list[str] = Field(default_factory=list)
    forbidden_topics: list[str] = Field(default_factory=list)
    
    @field_validator('catchphrases', 'forbidden_topics', mode='before')
    @classmethod
    def list_none_to_empty(cls, v):
        return none_to_list(v)
```

#### 4. CurrentMood íì íë â Optional ë³ê²½
```python
# Before (ì¤ë¥ ë°ì)
emotion: str = Field(..., description="Primary emotion")

# After (null íì©)
emotion: Optional[str] = Field(None, description="Primary emotion")
intensity: Optional[int] = Field(5, ge=1, le=10)
```

### ð ìì ë íì¼
- `app/schemas/character_full.py` - 11ê° ìë¸ í´ëì¤ + field_validator ì¶ê°
- `app/schemas/characters.py` - RelationshipType íì¥, field_validator ì¶ê°, CurrentMood Optional ë³ê²½
- `app/agents/extraction/character.py` - íë¡¬íí¸ íì¥, FullCharacterExtractionResult ì ì©

### â ê²°ê³¼
**ì ì¶ë ¥ íì**:
```json
{
  "profile": { "name": "ìë¦°", "age": 25, "gender": "female" },
  "role": "protagonist",
  "appearance": { "physique": "athletic", "hair_color": "black" },
  "personality": { "core_traits": ["brave"], "flaws": [], "values": [] },
  "dialogue": { "tone": "formal", "catchphrases": [] },
  "relations": { "relations": [{ "target": "ì¹´ì", "type": "FORMER_ALLY" }] }
}
```

**ê²ì¦ ì¤ë¥ í´ê²°**:
- â `FORMER_ALLY` â RelationshipType Enumì ì¶ê°ë¨
- â `null` â ë¹ ë¦¬ì¤í¸ `[]`ë¡ ìë ë³íë¨
- â `CurrentMood.emotion = null` â íì©ë¨

### ð¡ í¥í ê°ì  ì¬í­
1. **Spring Boot ì¤í¤ë§ ëê¸°í**: `FullCharacter` ì¤í¤ë§ë¥¼ Spring Boot DTOì ì¼ì¹ìí¤ê¸°
2. **ê²ì ì ì© íë ë¶ë¦¬**: ìì¤ ë¶ì ì `stats`, `combat` ì¹ì ë¹íì±í ìµì

---

## 13. Multi-Agent - FullCharacter ì¤í¤ë§ í¸íì± ë¬¸ì 

### ð ë ì§
2025-12-29

### ð´ ë¬¸ì  (Problem)
FullCharacter ì¤í¤ë§ ì ì© í Dialogue, Emotion, Relationship ë± ë¤ë¥¸ Agentìì JSON íì± ì¤ë¥ ë°ì:
```
Dialogue JSON parse error: Expecting value: line 1 column 1 (char 0)
Emotion JSON parse error: Expecting value: line 1 column 1 (char 0)
Relationship JSON parse error: Expecting value: line 1 column 1 (char 0)
```

ëí ìºë¦­í° ì´ë¦ì´ ì¶ì¶ëì§ ìì:
```json
{
  "profile": { "name": null, "age": null },
  "role": null
}
```

### ð¡ ìì¸ ë¶ì (Root Cause)
1. **ì¤í¤ë§ ê²½ë¡ ë³ê²½**: FullCharacterìì ìºë¦­í° ì´ë¦ì´ `profile.name`ì ì ì¥ë¨
2. **ê¸°ì¡´ Agent ì½ë ë¹í¸í**: ë¤ë¥¸ Agentë¤ì´ `c.get("name")`ì¼ë¡ ì ê·¼íì¬ `None` ë°í
3. **ë¹ ìºë¦­í° ë¦¬ì¤í¸ ì ë¬**: `available_characters = []`ê° LLMì ì ë¬ëì´ ë¶ì ì í ìëµ ìì±

```python
# ê¸°ì¡´ ì½ë (ë¹í¸í)
available_characters = [c.get("name", "") for c in characters if c.get("name")]
# â FullCharacterììë profile.nameì´ë¯ë¡ ë¹ ë¦¬ì¤í¸ ë°í
```

### ð¢ í´ê²°ì± (Solution)
ëª¨ë  Agentìì legacy ì¤í¤ë§ì FullCharacter ì¤í¤ë§ ëª¨ë ì§ìíëë¡ ìì :

```python
# ìì ë ì½ë (í¸í)
available_characters = []
for c in characters:
    name = c.get("name") or (c.get("profile", {}) or {}).get("name")
    if name:
        available_characters.append(name)
```

### ð ìì ë íì¼
| íì¼ | ìì  ìì¹ |
|------|----------|
| `app/agents/extraction/dialogue.py` | Line 142-150 |
| `app/agents/extraction/emotion.py` | Line 111-120 |
| `app/agents/analysis/relationship.py` | Line 174-183 |
| `app/agents/extraction/event.py` | Line 145-159 |
| `app/agents/analysis/plot.py` | Line 139-144 |
| `app/agents/analysis/consistency.py` | Line 82-88, 147-157 |
| `app/agents/validation/validator.py` | Line 120-130 |

### â ê²°ê³¼
- â ëª¨ë  Agentìì `profile.name` ê²½ë¡ ì§ì
- â Dialogue/Emotion/Relationship Agent ì ì ëì
- â JSON íì± ì¤ë¥ í´ê²°
- â ê¸°ì¡´ legacy ì¤í¤ë§ë íì í¸í ì ì§

---


## 14. Multi-Agent - JSON íì± ì¤ë¥ ë° AWS Throttling

### ð ë ì§
2025-12-29

### ð´ ë¬¸ì  (Problem)
1. **ThrottlingException**: AWS Bedrock API ìì²­ ì í ì´ê³¼
```
ThrottlingException: Too many requests, please wait before trying again.
```

2. **JSON íì± ì¤ë¥**: Dialogue, Emotion, Relationship Agentìì ë¹ ìëµ íì± ì¤í¨
```
Dialogue JSON parse error: Expecting value: line 1 column 1 (char 0)
Emotion JSON parse error: Expecting value: line 1 column 1 (char 0)
Relationship JSON parse error: Expecting value: line 1 column 1 (char 0)
```

### ð¡ ìì¸ ë¶ì (Root Cause)
1. **Throttling**: ë³ë ¬ë¡ ë¤ìì LLM í¸ì¶ â API ìì²­ ì í ì´ê³¼
2. **ë¹ ìëµ**: ìºë¦­í°ê° ìê±°ë íì¤í¸ì ëí/ê°ì /ê´ê³ê° ìì ë LLMì´ ë¹ ìëµ ë°í
3. **íì´íë¼ì¸ ì¤ë¨**: JSON íì± ì¤ë¥ê° ìë¬ë¡ ì íëì´ ì ì²´ íì´íë¼ì¸ì ìí¥

### ð¢ í´ê²°ì± (Solution)

#### 1. ë¹ ìºë¦­í° ë¦¬ì¤í¸ ì²´í¬ ì¶ê°
```python
if not available_characters:
    print("[DIALOGUE] No characters available, returning empty result")
    return {
        "analyzed_dialogues": {
            "key_dialogues": [],
            "speech_patterns": [],
            "dialogue_relationships": [],
            "neo4j_edges": []
        },
        ...
    }
```

#### 2. ë¹ LLM ìëµ ì²ë¦¬
```python
content = response.content.strip()
if not content:
    print("[DIALOGUE] Empty response from LLM")
    return {"analyzed_dialogues": {...}, ...}
```

#### 3. JSON ì¤ë¥ ì ë¹ ê²°ê³¼ ë°í (íì´íë¼ì¸ ì¤ë¨ ë°©ì§)
```python
except json.JSONDecodeError as e:
    print(f"[DIALOGUE] JSON parse error: {e}")
    return {
        "analyzed_dialogues": {
            "key_dialogues": [],
            "speech_patterns": [],
            ...
        },
        "messages": [{"role": "dialogue_agent", "content": "Failed to parse, returning empty"}]
    }
```

#### 4. ì§ì ë°±ì¤í ì¬ìë í¨ì (llm.py)
```python
async def retry_with_backoff(func, *args, **kwargs):
    for attempt in range(MAX_RETRIES):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            if "ThrottlingException" in str(e):
                delay = min(BASE_DELAY * (2 ** attempt), MAX_DELAY)
                await asyncio.sleep(delay)
            else:
                raise e
```

### ð ìì ë íì¼
| íì¼ | ìì  ë´ì© |
|------|----------|
| `app/agents/llm.py` | `retry_with_backoff` í¨ì ì¶ê° |
| `app/agents/extraction/dialogue.py` | ë¹ ë°ì´í°/JSON ì¤ë¥ ì²ë¦¬ |
| `app/agents/extraction/emotion.py` | ë¹ ë°ì´í°/JSON ì¤ë¥ ì²ë¦¬ |
| `app/agents/analysis/relationship.py` | ë¹ ë°ì´í°/JSON ì¤ë¥ ì²ë¦¬, ìºë¦­í° 2ëª ë¯¸ë§ ì¤íµ |

### â ê²°ê³¼
- â ë¹ ìºë¦­í° ë¦¬ì¤í¸ ì LLM í¸ì¶ ìì´ ë¹ ê²°ê³¼ ë°í
- â ë¹ LLM ìëµ ì JSON íì± ìë ìí¨
- â JSON ì¤ë¥ê° ìë¬ê° ìë ë¹ ê²°ê³¼ë¡ ì²ë¦¬ â íì´íë¼ì¸ ê³ì ì§í
- â ThrottlingException ì ì§ì ë°±ì¤í ì¬ìë ê°ë¥

---


## 15. Character Agent - Hierarchical Multi-Agent System ë¦¬í©í ë§

### ð ë ì§
2025-12-29

### ð´ ë¬¸ì  (Problem)

1. **ë¨ì¼ ìì´ì í¸ ê³¼ë¶í**: ê¸°ì¡´ `character.py`ê° `FullCharacter` ì¤í¤ë§ì 13ê° ì»´í¬ëí¸(~87ê° íë)ë¥¼ í ë²ì ì¶ì¶
2. **ì±ê²© vs ê°ì  í¼ë**: ì¼ìì  ê°ì (`ëë ¤ì`)ì´ ìêµ¬ì  ì±ê²© ê²°í¨(`flaws`)ì¼ë¡ ë¶ë¥ë¨
3. **ì¸ì´ ë¶ì¼ì¹**: íêµ­ì´ ìë ¥ìì ìì´ ë²ì­ ì¶ë ¥ (`ìíí` â `Dark Order`)
4. **Validator ê²½ë¡ ì¤ë¥**: `profile.name` ëì  ìµìì `name`ì ì°¾ì VAL_003 ì¤ë¥ ë°ì
5. **ë¹ëì¹­ ê´ê³ ë¯¸ì§ì**: ë°°ì  ê´ê³ìì ìë°©í¥ ëª¨ë ê°ì ì íì¼ë¡ ì¶ì¶

**complex.json ìì**:
```json
{
  "status": "WARNING",  // COMPLETEDì´ì´ì¼ í¨
  "extracted_characters": [{
    "personality": {
      "flaws": ["ëë ¤ì"]  // ì´ê²ì current_mood.emotionì´ì´ì¼ í¨
    },
    "profile": {
      "faction": "Dark Order"  // "ìíí"ì´ì´ì¼ í¨
    }
  }]
}
```

### ð¡ ìì¸ ë¶ì (Root Cause)

1. **LLM ì»¨íì¤í¸ íê³**: 87ê° íëë¥¼ ë¨ì¼ í¸ì¶ë¡ ì¶ì¶ â ì íë ì í
2. **íë¡¬íí¸ ë¶ëªí**: ì±ê²©(ìêµ¬) vs ê°ì (ì¼ì) êµ¬ë¶ ì§ì ìì
3. **ì¸ì´ ì§ì ëë½**: ì¶ë ¥ ì¸ì´ ê·ì¹ì´ íë¡¬íí¸ì ìì
4. **Validator ë¡ì§ ë²ê·¸**: ì¤ì²© íë ê²½ë¡(`profile.name`)ë¥¼ ì§ìíì§ ìì

### ð¢ í´ê²°ì± (Solution)

#### 1. Hierarchical Multi-Agent System ìí¤íì²

```mermaid
flowchart TB
    subgraph "Main Level"
        MS[Main Supervisor]
        CT[Character Team]
        EA[Event Agent]
        SA[Setting Agent]
    end
    
    subgraph "Character Team (Sub-Level)"
        CS[Character Supervisor]
        ID[Identity Agent]
        APP[Appearance Agent]
        PER[Personality Agent]
        REL[Relations Agent]
        DM[Dialogue/Mood Agent]
        ST[Stats Agent]
        AGG[Aggregator]
    end
    
    MS --> CT & EA & SA
    CT --> CS
    CS --> ID & APP & PER & REL & DM & ST
    ID & APP & PER & REL & DM & ST --> AGG
    AGG --> CT
```

**íµì¬ ê°ë**:
- Main Supervisor ìì¥ìì Character Teamì **íëì ìì´ì í¸**ì²ë¼ ë³´ì (ìº¡ìí)
- ë´ë¶ì ì¼ë¡ Character Supervisorê° 6ê° ìë¸ ìì´ì í¸ë¥¼ ê´ë¦¬

#### 2. ìë¸ ìì´ì í¸ ì­í  ë¶ë¦¬

| ìì´ì í¸ | ì±ì | ì£¼ì íë |
|----------|------|-----------|
| **Identity** | ê¸°ë³¸ ì ë³´ | name, age, role, faction, backstory |
| **Appearance** | ì¸í (ì´ë¯¸ì§ ìì±ì©) | hair, physique, attire, scars |
| **Personality** | ìêµ¬ ì±ê²© í¹ì± | core_traits, flaws, values |
| **Relations** | ìºë¦­í° ê° ê´ê³ | relationships, known_events |
| **Dialogue/Mood** | ëí ì¤íì¼ + ì¼ì ê°ì  | tone, catchphrases, current_mood |
| **Stats** | ê²ì ë°ì´í° (optional) | level, HP, skills |

#### 3. ì±ê²© vs ê°ì  ë¶ë¦¬ (Personality Agent)

```python
PERSONALITY_EXTRACTION_PROMPT = """
### CRITICAL DISTINCTION ###
â core_traits (PERSISTENT): brave, cunning, loyal
â flaws (PERSISTENT): impulsive, arrogant, vengeful
â NOT personality: fearful (in scary moment), anxious (before battle)

Example: "ë¨í¸íì§ë§ ì½ê°ì ëë ¤ìì´ ìì¬ ììë¤"
- core_traits: ["ë¨í¸í¨"] â
- flaws: [] (ëë ¤ì is situational, NOT a flaw)
"""
```

#### 4. ì¸ì´ ì¼ê´ì± (ëª¨ë  ìë¸ ìì´ì í¸)

```python
### LANGUAGE CONSISTENCY RULE ###
Output ALL text in the SAME language as the input.
If the story is in Korean, all values must be in Korean.
Do NOT translate (e.g., "ìíí" not "Dark Order").
```

#### 5. ë¹ëì¹­ ê´ê³ ì§ì (Relations Agent)

```python
### RELATIONSHIP ASYMMETRY ###
If A betrayed B:
- A â B: type="BETRAYER"
- B â A: type="FORMER_ALLY"
Create SEPARATE entries for each direction.
```

#### 6. Validator ì¤ì²© ê²½ë¡ ìì 

```python
# validator.py - ë³ê²½ ì 
"required_fields": ["name", "role"]

# validator.py - ë³ê²½ í
"required_fields": ["profile.name", "role"],
"nested_paths": True

def get_nested_value(data: dict, path: str):
    """Get value from nested dict using dot notation."""
    keys = path.split(".")
    value = data
    for key in keys:
        value = value.get(key) if isinstance(value, dict) else None
    return value
```

#### 7. í´ë°± ì ëµ (Team Entry Point)

```python
async def character_team_node(state: dict) -> dict:
    try:
        # Hierarchical ìì¤í ì¤í
        result = await character_team_graph.ainvoke(team_state)
        return result
    except Exception as e:
        # ì¤í¨ ì ë ê±°ì ë¨ì¼ ìì´ì í¸ë¡ í´ë°±
        print(f"[CHARACTER_TEAM] Fallback to legacy: {e}")
        return await legacy_character_extraction(state)
```

### ð ìì ë íì¼

#### ì ê· íì¼ (11ê°)
| íì¼ | ì¤ëª |
|------|------|
| `app/agents/extraction/character/__init__.py` | í¨í¤ì§ ì´ê¸°í |
| `app/agents/extraction/character/state.py` | CharacterTeamState ì ì |
| `app/agents/extraction/character/identity.py` | Identity Agent |
| `app/agents/extraction/character/appearance.py` | Appearance Agent |
| `app/agents/extraction/character/personality.py` | Personality Agent |
| `app/agents/extraction/character/relations.py` | Relations Agent |
| `app/agents/extraction/character/dialogue_mood.py` | Dialogue/Mood Agent |
| `app/agents/extraction/character/stats.py` | Stats Agent |
| `app/agents/extraction/character/aggregator.py` | ê²°ê³¼ ë³í© |
| `app/agents/extraction/character/supervisor.py` | ë´ë¶ ë¼ì°í |
| `app/agents/extraction/character/team.py` | ì§ìì  + í´ë°± |

#### ìì ë íì¼
| íì¼ | ìì  ë´ì© |
|------|----------|
| `app/agents/graph.py` | `character_team_node` importë¡ ë³ê²½ |
| `app/agents/validation/validator.py` | ì¤ì²© ê²½ë¡ ê²ì¦ (`profile.name`) |
| `app/agents/extraction/character.py` â `character_legacy.py` | í´ë°±ì©ì¼ë¡ ì´ë¦ ë³ê²½ |

#### íì¤í¸ íì¼
| íì¼ | ì¤ëª |
|------|------|
| `tests/test_agents/test_character_team.ipynb` | ê°ë³ ìì´ì í¸ + íµí© íì¤í¸ |

### â ê²°ê³¼

1. **ì±ë¥ í¥ì**: 87ê° íë â 6ê° ìì´ì í¸ë¡ ë¶ì° (ê° ~15ê° íë)
2. **ì íë í¥ì**: 
   - `ëë ¤ì`ì´ `current_mood.emotion`ì ì¬ë°ë¥´ê² ì¶ì¶
   - `ìíí`ê° íêµ­ì´ë¡ ì ì§
   - ë¹ëì¹­ ê´ê³ (BETRAYER/FORMER_ALLY) ì§ì
3. **Validator ì¤ë¥ í´ê²°**: `profile.name` ì¤ì²© ê²½ë¡ ê²ì¦ ì±ê³µ
4. **ìì ì±**: í´ë°± ì ëµì¼ë¡ ì¤í¨ ììë ê²°ê³¼ ë°í

### ð¡ í¥í ê°ì  ì¬í­

1. **ë³ë ¬ ì¤í**: íì¬ ìì°¨ ì¤í â asyncio.gatherë¡ 6ê° ìì´ì í¸ ëì ì¤í
2. **ìºì±**: ëì¼ íì¤í¸ì ëí ìë¸ ìì´ì í¸ ê²°ê³¼ ìºì±
3. **ë¤ë¥¸ ëë©ì¸ íì¥**: Event, Settingìë ëì¼í Hierarchical í¨í´ ì ì© ê°ë¥

---

## 16. Appearance Agent - Production Level ìê·¸ë ì´ë

### ð ë ì§
2025-12-29

### ð´ ë¬¸ì  (Problem)

Appearance Agent ì¶ë ¥ì `null` ê°ì´ ë§ì´ í¬í¨ëì´ ë¤ì ìì¤íìì ë¬¸ì  ë°ì:

```json
"skin_tone": null,
"nose": null,
"mouth": null,
"expression": null
```

| ìì¤í | ë¬¸ì  |
|--------|------|
| **Image Gen AI** | íë¡¬íí¸ì null í¬í¨ ì ì¼ê´ì± ìë ê²°ê³¼ |
| **Game Engine (C++/C#)** | NullReferenceException ë°ì |
| **Shader/UI** | ìì íì± ë¶ê° |

### ð¡ ìì¸ ë¶ì (Root Cause)

1. **Null ì²ë¦¬ ë¶ì¬**: ìë³¸ íì¤í¸ì ë¬ì¬ ìì¼ë©´ null ê·¸ëë¡ ë°í
2. **ìì ë¹ì ê·í**: "ê²ì", "ìë¹" ê°ì ìì°ì´ â ë ëë§ ìì§ìì íì± ë¶ê°
3. **íë¡¬íí¸ ë¶ì°**: ê°ë³ íë ì¡°í© ë¡ì§ì´ ë°±ìëìì ì¶ê° íì
4. **ì¤íì¼ ë¯¸ì§ì **: íí/ì¥ë¥´ ì ë³´ ìì´ ì´ë¯¸ì§ ìì± ì ì¼ê´ì± ìì¤

### ð¢ í´ê²°ì± (Solution)

4ê°ì§ Production ê¸°ë¥ ì¶ê°:

#### 1. Null Fallback Strategy

```python
ROLE_DEFAULTS = {
    "protagonist": {"physique": "athletic", "skin_tone": "fair", "expression": "determined"},
    "antagonist": {"physique": "imposing", "skin_tone": "pale", "expression": "cold"},
    "default": {"physique": "average", "skin_tone": "unspecified", "expression": "neutral"},
}

# null ëì  "unspecified" ëë role-based default ì¬ì©
if not result.get("physique"):
    result["physique"] = defaults.get("physique", "average")
```

#### 2. Color Normalization

ìì°ì´ ìì â êµ¬ì¡°íë ë°ì´í° (Hex + Category)

```python
COLOR_MAP = {
    "ê²ì": {"en": "black", "hex": "#000000", "category": "BLACK"},
    "ìë¹": {"en": "silver", "hex": "#C0C0C0", "category": "SILVER"},
    "íì": {"en": "gray", "hex": "#808080", "category": "GRAY"},
    # ... 20+ ìì
}
```

ì¶ë ¥:
```json
"hair_color_normalized": {
  "description": "ê²ì",
  "hex_code": "#000000",
  "category": "BLACK"
}
```

#### 3. Prompt Aggregation

Image AIì ë°ë¡ ì¬ì© ê°ë¥í íµí© íë¡¬íí¸ ìì±:

```python
def generate_visual_prompt(data: dict, style: str) -> str:
    parts = [
        data.get("physique"),
        f"{data.get('hair_color')} hair",
        f"{data.get('eyes')} eyes",
        # ... ëª¨ë  ìê°ì  ìì ê²°í©
    ]
    return ", ".join(parts) + f", {style}"
```

ì¶ë ¥:
```json
"full_visual_prompt": "athletic, fair skin, ê²ì hair, ê¸´ ë¨¸ë¦¬, sharp eyes, silver sword, fantasy illustration"
```

#### 4. Style Context

íí/ì¥ë¥´ ë©íë°ì´í° ì¶ê°:

```json
"style_context": {
  "art_style": "fantasy illustration",
  "rendering_engine": "Unreal Engine 5"
}
```

### ð ìì ë íì¼

| íì¼ | ìì  ë´ì© |
|------|----------|
| `app/agents/extraction/character/appearance.py` | COLOR_MAP, ROLE_DEFAULTS, post_process_appearance() ì¶ê° |
| `app/agents/extraction/character/aggregator.py` | ì íë (hair_color_normalized, full_visual_prompt, style_context) ë°ì |
| `tests/test_agents/test_character_appearance.ipynb` | Production íë ê²ì¦ íì¤í¸ ì¶ê° |

### â ê²°ê³¼

**Before:**
```json
{
  "hair_color": "ê²ì",
  "skin_tone": null,
  "expression": null
}
```

**After:**
```json
{
  "hair_color": "ê²ì",
  "hair_color_normalized": {
    "description": "ê²ì",
    "hex_code": "#000000",
    "category": "BLACK"
  },
  "skin_tone": "fair",
  "expression": "determined",
  "full_visual_prompt": "athletic, fair skin, ê²ì hair, sharp eyes, fantasy illustration",
  "style_context": {
    "art_style": "fantasy illustration",
    "rendering_engine": "Unreal Engine 5"
  }
}
```

1. **Null ì ê±°**: ëª¨ë  ì£¼ì íëì fallback ê° ì ì©
2. **ë ëë§ í¸í**: Hex ìì ì½ëë¡ Shader/UI ì§ì  ì°ë ê°ë¥
3. **Image AI ì°ë**: `full_visual_prompt`ë¥¼ DALL-E 3/Stable Diffusionì ë°ë¡ ì ë¬
4. **ì¼ê´ì±**: `style_context`ë¡ ìì±ë¬¼ í¤ ì¤ ë§¤ë ê³ ì 

---


## 17. Story Extraction - íê¸/ìë¬¸ ìºë¦­í° ì¤ë³µ ë° ì¶ì¶ íì§ ê°ì 

### ð ë ì§
2025-12-30

### ð´ ë¬¸ì  (Problem)

1. **íê¸/ìë¬¸ ìºë¦­í° ì¤ë³µ**: "ë² ë¼(Vera)"ê° "ë² ë¼"ì "Vera" ë ìºë¦­í°ë¡ ë¶ë¦¬ ì¶ì¶
2. **ì´ë²¤í¸ ì¶ì¶ ì¤í¨**: JSON string ë°í ì list_type ì í¨ì± ê²ì¬ ì¤ë¥
3. **ì¸ë²¤í ë¦¬ ì¤ë³µ**: `equipped_items`ì `bag_items`ì ëì¼ ìì´í ì¤ë³µ
4. **ìë/ì¡ì¸ìë¦¬ ëë½**: ë² ë¼ì ê²ì ìëê° appearanceìì ëë½
5. **Role ì¤ë¥**: ì ëì  íëíë ë² ë¼ê° "other"ë¡ ì¶ì¶ (antagonistì¬ì¼ í¨)
6. **Plot í ë£¨ìë¤ì´ì**: ì´ë²¤í¸ê° ìì ë ê°ìì event_ref (E001-E009) ìì±
7. **existing_characters ë¯¸ë°ì**: íì´ë¡ëì ê¸°ì¡´ ìºë¦­í° IDê° ë¬´ìë¨

### ð¡ ìì¸ ë¶ì (Root Cause)

1. ëª¨ë  sub-agentê° ëë¦½ì ì¼ë¡ ìºë¦­í° ì¶ì¶ â íê¸/ìë¬¸ í¼ì© ë°ì
2. LLMì´ JSON ë°°ì´ ëì  ë¬¸ìì´ ë°í â Pydantic ì í¨ì± ê²ì¬ ì¤í¨
3. íë¡¬íí¸ì equipped/bag ë¶ë¦¬ ê·ì¹ ìì
4. íë¡¬íí¸ì ìë, ë§ì¤í¬ ë± face accessory ì¶ì¶ ì§ì ìì
5. antagonist íë³ ì»¨íì¤í¸ í´ë£¨ ìì
6. Plot Agentê° ë¹ ì´ë²¤í¸ ë°°ì´ìë narrative_beats ìì± ìë
7. Aggregatorê° contextì existing_charactersë¥¼ ì°¸ì¡°íì§ ìì

### ð¢ í´ê²°ì± (Solution)

#### 1. ëª¨ë  ìºë¦­í° Sub-Agentì íê¸ ì´ë¦ ê·ì¹ ì¶ê°
```
### CRITICAL: NAME EXTRACTION RULE ###
When a character is introduced as "ë² ë¼(Vera)", use ONLY the Korean name.
â BAD: "name": "Vera"
â GOOD: "name": "ë² ë¼"
```

#### 2. EventExtractionResultì JSON string parser ì¶ê° (`events.py`)
```python
@field_validator('events', mode='before')
def parse_events_string(cls, v):
    if isinstance(v, str):
        return json.loads(cleaned_string)
    return v
```

#### 3. Inventory ì¤ë³µ ë°©ì§ ê·ì¹ ì¶ê° (`inventory.py`)
```
### CRITICAL: NO DUPLICATION RULE ###
An item can ONLY be in ONE place:
- HOLDING/WEARING â equipped_items ONLY
- IN A BAG/STORED â bag_items ONLY
```

#### 4. Face Accessory ì¶ì¶ ê·ì¹ ì¶ê° (`appearance.py`)
```
### IMPORTANT: FACE ACCESSORIES ###
- "ì¤ë¥¸ìª½ ëìë ê²ì ìë" â eyes: "wearing black eyepatch on right eye"
- "ì¼êµ´ì íí°" â scars_tattoos: ["facial scar"]
```

#### 5. Antagonist íë³ ê·ì¹ ì¶ê° (`identity.py`)
```
- Attacks/threatens the protagonist â antagonist
- Commands others to harm â antagonist
- "ëë¹ì´ ì´ê¸°ë¡ ë²ë©ìë¤" â role: "antagonist"
```

#### 6. Plot Agent ë¹ ì´ë²¤í¸ ê°ë ì¶ê° (`plot.py`)
```python
if not events:
    return {
        "plot_integration": {
            "narrative_beats": [],  # NO hallucinated event_refs
            "tension_curve": [],
            ...
        }
    }
```

#### 7. Aggregatorì existing_characters ë³í© ë¡ì§ ì¶ê°
```python
existing_characters = context.get("existing_characters") or []
for ec in existing_characters:
    existing_lookup[ec["name"]] = ec  # ID ì¬ì¬ì©

char_id = existing_lookup.get(name, {}).get("id") or f"char-{name}-{n}"
```

### ð ìì ë íì¼

| íì¼ | ìì  ë´ì© |
|------|----------|
| `app/schemas/events.py` | JSON stringâlist parser validator |
| `app/agents/extraction/character/identity.py` | íê¸ ì´ë¦ ê·ì¹ + antagonist íë³ |
| `app/agents/extraction/character/appearance.py` | íê¸ ì´ë¦ + face accessory + category ìë¬¸ì |
| `app/agents/extraction/character/personality.py` | íê¸ ì´ë¦ ê·ì¹ |
| `app/agents/extraction/character/dialogue_mood.py` | íê¸ ì´ë¦ ê·ì¹ |
| `app/agents/extraction/character/relations.py` | íê¸ ì´ë¦ ê·ì¹ + í ë£¨ìë¤ì´ì ë°©ì§ |
| `app/agents/extraction/character/inventory.py` | íê¸ ìì´íëª + ì¤ë³µ ë°©ì§ ê·ì¹ |
| `app/agents/extraction/character/stats.py` | íê¸ ì´ë¦ ê·ì¹ |
| `app/agents/analysis/plot.py` | ë¹ ì´ë²¤í¸ ê°ë |
| `app/agents/extraction/character/aggregator.py` | existing_characters ID ì¬ì¬ì© + category ìë¬¸ì |

### â ê²°ê³¼

| ë¬¸ì  | Before | After |
|------|--------|-------|
| ìºë¦­í° ì | 6ê° (ì¤ë³µ) | 3ê° |
| ì´ë²¤í¸ ì¶ì¶ | ì¤í¨ (list_type) | ì±ê³µ (E001-E005) |
| ì¸ë²¤í ë¦¬ | ì¤ë³µ ë°ì | ë¶ë¦¬ë¨ |
| ìë | ëë½ | ì¶ì¶ë¨ |
| Role | "other" | "antagonist" |
| Plot event_refs | í ë£¨ìë¤ì´ì | ë¹ ë°°ì´ |
| existing ID | ë¬´ìë¨ | ì¬ì¬ì©ë¨ |
| category ëìë¬¸ì | "UNSPECIFIED" | "unspecified" |
| ê´ê³ history | í ë£¨ìë¤ì´ì | ëªìì  ë°ì´í°ë§ |

#### 11. ëì  ì´ë¦ ì¤ë³µ ì ê±° (`aggregator.py`) - 2024-12-30

**ë¬¸ì **: íë¡¬íí¸ ê·ì¹ìë ë¶êµ¬íê³  sub-agentë¤ì´ íê¸/ìì´ ì´ë¦ì í¼ì©íì¬ ê°ì ì¸ë¬¼ì´ 2ê°ë¡ ì¶ì¶ë¨
- `identity.py` â "ë² ë¼", `stats.py` â "Vera" â 2ê° ìºë¦­í° ìì±

**í´ê²°ì± 1**: ì¤í ë¦¬ í¨í´ ê¸°ë° ëì  ë§¤í
```python
def extract_name_pairs_from_text(story_text: str) -> dict:
    """ì¤í ë¦¬ìì "ë² ë¼(Vera)" í¨í´ ìë ì¶ì¶"""
    pattern = r'([\uAC00-\uD7AF]+)\s*\(\s*([A-Za-z]+)\s*\)'
    # {"Vera": "ë² ë¼", "Lian": "ë¦¬ì", ...}
```

**í´ê²°ì± 2**: ìì­(Romanization) ê¸°ë° ë§¤ì¹­ (í¨í´ ìì ë í´ë°±)
```python
KOREAN_TO_ROMANIZATION = {
    "ë¦¬": ["ri", "li", "ree", "lee"],
    "ì": ["an", "ahn"],
    "ë² ": ["be", "ve", "bae"],
    "í°": ["ti", "tee"],
    "ì¤": ["o", "oh"],
    # ... +40ê° ìì 
}

def find_romanization_match(korean_names, english_names) -> dict:
    """'ë¦¬ì' â ['rian', 'lian', ...] ìì± í 'Lian'ê³¼ ë§¤ì¹­"""
```

**ìë ìë¦¬**:
1. ì¤í ë¦¬ìì `íê¸(ìë¬¸)` í¨í´ ê°ì§ â ëì  ë§¤í
2. í¨í´ ìë ìë¬¸ ì´ë¦ì ìì­ ë§¤ì¹­ì¼ë¡ íê¸ ì´ë¦ê³¼ ì°ê²°
3. ëª¨ë  ì´ë¦ ì ê·í í ê°ì ì¸ë¬¼ ë°ì´í° ë³í©

**ê²°ê³¼**: "ë¦¬ì"ë§ ëì¤ê³  "ë¦¬ì(Lian)" í¨í´ ìì´ë "Lian" ìë ë³í©

---

#### 12. ì¶ì¶ ì íë ê°ì  (`inventory.py`, `dialogue_mood.py`, `identity.py`) - 2024-12-30

**ë¬¸ì **: ì¤í ë¦¬ì ì¶ì¶ ê²°ê³¼ ê° ë¶ì¼ì¹ ë°ì
- ë¦¬ìì ë¨ê²ì´ `equipped_items`ì ëë½
- ë² ë¼ì "í©ê¸ë¹ ëë£¨ë§ë¦¬"ê° `quest_items`ì ëë½  
- "ì¥ìë¼ì²ë¼ ë¹ ë¥´ë¤"ê° ë² ë¼ê° ìë ë¦¬ìì `catchphrases`ì ìëª» ê·ì
- í°ì¤ê° "ì³ë ì¼êµ´ì ìë"ì¼ë¡ ë¬ì¬ëìì¼ë `age` ì¶ë¡  ìë¨

**í´ê²°ì±**:

1. **inventory.py - QUEST ìì´í ë° ë¬´ê¸° ì¶ì¶ ê°í**
```python
### CRITICAL: QUEST ITEMS ###
- í©ê¸ë¹ ëë£¨ë§ë¦¬ â QUEST item (ë² ë¼ ìì )
- ììì ì±ë°° â QUEST item (if possessed)

### WEAPON EXTRACTION ###
ë¨ê²ì ì¡ë¤/ë¤ë¤/ë½ë¤ â WEAPON equipped_items
Example: "ë¦¬ìì ì´ë¥¼ ìë¬¼ë©° ë¨ê²ì ê³ ì³ ì¡ìë¤" â ë¦¬ì has ë¨ê²
```

2. **dialogue_mood.py - catchphrase íì ê·ì ê·ì¹**
```python
### CRITICAL: CATCHPHRASE ATTRIBUTION ###
â ï¸ A catchphrase belongs to the SPEAKER, NOT the target!
Example: ë² ë¼ said "ì¬ì í ì¥ìë¼ì²ë¼ ë¹ ë¥´ë¤, ë¦¬ì."
â BAD: ë¦¬ì.catchphrases = ["ì¥ìë¼ì²ë¼ ë¹ ë¥´ë¤"]  
â GOOD: ë² ë¼.catchphrases = ["ì¥ìë¼ì²ë¼ ë¹ ë¥´ë¤"]
```

3. **identity.py - ëì´ ì¶ë¡  ê·ì¹**
```python
- age: Exact age or estimate if mentioned
  * "ì³ë ì¼êµ´ì ìë" â age inference: young/teen
  * "ìë" â infer age as teen (10-19)
  * "ë¸ì¸" â infer age as elderly (60+)
```

**ìì ë íì¼**:
- `app/agents/extraction/character/inventory.py`
- `app/agents/extraction/character/dialogue_mood.py`
- `app/agents/extraction/character/identity.py`

---

#### 13. Character Team Recursion Limit ë¬´í ë£¨í (`graph.py`, `identity.py`) - 2024-12-30

**ë¬¸ì **: `Recursion limit of 25 reached without hitting a stop condition`
- Character Agentê° ë¬´í ë£¨íì ë¹ ì ¸ `characters: []` ë°í
- Event Agentë ì±ê³µíì§ë§ ì°¸ì¡°í  ìºë¦­í°ê° ìì

**ìì¸ ë¶ì**:
1. `identity.py` ìì¸ ë°ì ì `completed_agents`ì "identity" ë¯¸ì¶ê°
2. Supervisorê° ê³ì `identity` ë¨ê³ë¡ ë¼ì°í â ë¬´í ë£¨í

**í´ê²°ì±**:
1. `identity.py` - ìì¸ ììë `completed_agents`ì "identity" ì¶ê°
2. `graph.py` - `recursion_limit=50` ì¤ì 

**ìì ë íì¼**: `app/agents/graph.py`, `app/agents/extraction/character/identity.py`

---

#### 14. age_group ë° role ì¶ë¡  ê°ì  (`aggregator.py`) - 2024-12-30

**ë¬¸ì **: 
- í°ì¤ê° "ì³ë ì¼êµ´ì ìë"ì¼ë¡ ë¬ì¬ëìì¼ë `visual.age_group: null`
- ëª¨ë  ìºë¦­í°ì `role: "other"` (protagonist/antagonist êµ¬ë¶ ìë¨)

**ìì¸ ë¶ì**:
1. aggregatorìì `age_group`ì´ í­ì `None`ì¼ë¡ íëì½ë©ë¨
2. role ì¶ë¡ ì´ Identity Agent ê²°ê³¼ìë§ ìì¡´ â ì¤í¨ ì "other" í´ë°±

**í´ê²°ì±**:

1. **age_group ì¶ë¡  í¨ì ì¶ê°**
```python
AGE_GROUP_KEYWORDS = {
    "teen": ["ìë", "ìë", "ì³ë", "teenager"],
    "child": ["ìì´", "ì´ë¦°ì´"],
    "elderly": ["ë¸ì¸", "í ìë²ì§"]
}

def infer_age_group(appearance_data, story_text):
    search_text = f"{visual_prompt} {story_text}".lower()
    for age_group, keywords in AGE_GROUP_KEYWORDS.items():
        if any(kw in search_text for kw in keywords):
            return age_group
    return None
```

2. **role ì¶ë¡  ì»¨íì¤í¸ ê¸°ë° ê°í**
```python
def infer_role_from_context(name, relations_data, story_text):
    # ENEMY ê´ê³ + ê³µê²© í¤ìë â antagonist
    # í¼í´/ëë§ í¤ìë â protagonist
```

**ìì ë íì¼**: `app/agents/extraction/character/aggregator.py`

---

#### 15. ìºë¦­í° ì¶ì¶ ì íë ë²ê·¸ ìì  (`aggregator.py`, `dialogue_mood.py`) - 2024-12-30

**ë¬¸ì **:
1. **role ë°ì **: ë¦¬ì(protagonist)ì´ "antagonist"ë¡, í°ì¤(supporting)ì´ "protagonist"ë¡ ì¶ì¶
2. **age_group ì¤ë¥**: ëª¨ë  ìºë¦­í°ê° "child"ë¡ ì¶ì¶ë¨
3. **catchphrase ê·ì ì¤ë¥**: ë² ë¼ê° í ë§ì´ ë¦¬ììê² ê·ìë¨
4. **appearance í¼ë**: ë² ë¼ì ê²ì ìëê° ë¦¬ììê²ë ì ì©ë¨

**ìì¸ ë¶ì**:
1. `infer_role_from_context`ê° ì ì²´ ì¤í ë¦¬ìì í¤ìë ê²ì â ëª¨ë  ìºë¦­í°ì ëì¼ role ì ì©
2. `infer_age_group`ì´ ì ì²´ ì¤í ë¦¬ìì "ìì´" í¤ìë ë¨¼ì  ë°ê²¬ â ëª¨ë "child"
3. LLMì´ ëì¬ ëìì íìë¡ ìëª» ê·ì
4. appearance ë°ì´í°ê° ìºë¦­í° ê° í¼í©ë¨ (ë³ë ìì  íì)

**í´ê²°ì±**:

1. **ìºë¦­í°ë³ ë¬¸ë§¥ ì¶ì¶ í¨ì ì¶ê°**
```python
def get_character_context(name: str, story_text: str, window: int = 100) -> str:
    # ìºë¦­í° ì´ë¦ ì£¼ë³ Â±window ë¬¸ìë§ ì¶ì¶
```

2. **age_group ì°ì ìì ê²ì**
```python
priority_order = ["teen", "elderly", "adult", "child"]  # childê° ë§ì§ë§
```

3. **role ì¶ë¡  ê°ì ** - ì¤ì½ì´ ê¸°ë°
```python
antagonist_score, protagonist_score = 0, 0
# í¤ìë ì¹´ì´í¸ í ë¹êµ
```

4. **catchphrase íì ê²ì¦**
```python
def validate_catchphrase_speaker(phrase, speaker_name, story_text):
    # ì¤í ë¦¬ìì ì¤ì  íìì¸ì§ íì¸
```

**ìì ë íì¼**: `app/agents/extraction/character/aggregator.py`, `app/agents/extraction/character/dialogue_mood.py`

---

#### 16. Role ë° Catchphrase ì¶ë¡  ë¡ì§ 2ì°¨ ê°ì  (`aggregator.py`, `dialogue_mood.py`) - 2024-12-30

**ë¬¸ì **:
1. **Role ì¶ë¡  ì¤í¨**: ë² ë¼(antagonist)ê° "protagonist"ë¡, ë¦¬ì(protagonist)ì´ "other"ë¡ ì¶ë¡ ë¨
2. **Catchphrase ê·ì ì¤í¨**: "ì¥ìë¼ì²ë¼ ë¹ ë¥´ë¤, ë¦¬ì" â ë¦¬ììê² ìëª» ê·ì (ë² ë¼ê° ë§í¨)

**ìì¸ ë¶ì**:
1. **Role**: ê´ê³ ì¤ëªìì `name.lower() in desc` ì¡°ê±´ì´ í¼í´ìë ê³µê²©ìë¡ ì¸ì
2. **Catchphrase**: ëì¬ ë´ìì ì¸ê¸ë ì´ë¦ì íìë¡ ì¤ì¸ (ë¦¬ìì ëì¬ ëì)

**í´ê²°ì±**:

1. **Role ì¶ë¡  ê°ì ** - ìì¹ ê¸°ë° ê³µê²©ì/í¼í´ì íë¨
```python
# ì´ë¦ ìì¹ < ê³µê²© ë¨ì´ ìì¹ â ê³µê²©ì
name_pos = desc.find(name.lower())
attack_pos = min([desc.find(kw) for kw in ["ê³µê²©", "ì£½ì´", "ìí"]])
if name_pos < attack_pos:
    antagonist_score += 3  # Attacker
```

2. **Catchphrase ê²ì¦ ê°ì ** - íì vs ëì êµ¬ë¶
```python
# ëì¬ ì(attribution)ì ì´ë¦ ìì¼ë©´ íì
# ëì¬ ììë§ ì´ë¦ ìì¼ë©´ ëì (ê±°ë¶)
speaker_in_attribution = speaker_name in context_before
speaker_only_in_dialogue = speaker_name in phrase_context and not speaker_in_attribution
if speaker_only_in_dialogue:
    return False  # Target, not speaker
```

**ìì ë íì¼**: `app/agents/extraction/character/aggregator.py`, `app/agents/extraction/character/dialogue_mood.py`

---

## ííë¦¿ (ì ì´ì ì¶ê° ì ì¬ì©)

```markdown
## N. [ìì´ì í¸ëª] - [ë¬¸ì  ìì½]

### ð ë ì§
YYYY-MM-DD

### ð´ ë¬¸ì  (Problem)
[ë¬¸ì  ì¤ëª]

### ð¡ ìì¸ ë¶ì (Root Cause)
[ìì¸]

### ð¢ í´ê²°ì± (Solution)
[í´ê²° ë°©ë²]

### ð ìì ë íì¼
- [íì¼ ëª©ë¡]

### â ê²°ê³¼
[ê²°ê³¼]
---

#### 18. Role ì¶ë¡  ë¯¸ì ì© ë° Catchphrase ê²ì¦ ì°í ë²ê·¸ ìì  - 2024-12-30

**ë¬¸ì **:
1. **Role ì¶ë¡  ë¯¸ì ì©**: `infer_role_from_context` í¨ìê° ì ìëì´ ììì§ë§, LLMì´ `protagonist`ë¥¼ ë°ííë©´ **ì¶ë¡  ìì²´ê° ì¤íëì§ ììì**.
2. **Catchphrase ê²ì¦ ì°í**: ëì¬ê° story_textìì ì°¾ìì§ì§ ìì¼ë©´ `True` (íµê³¼)ë¥¼ ë°ííì¬ **ìëª»ë ê·ìì´ ê·¸ëë¡ ì ì§ë¨**.

**ìì¸ ë¶ì**:
```python
# ê¸°ì¡´ ì½ë (aggregator.py)
if extracted_role == "other" or not extracted_role:
    inferred_role = infer_role_from_context(...)  # protagonistì¼ ë ì¤í ìë¨!
```
```python
# ê¸°ì¡´ ì½ë (dialogue_mood.py)
if phrase_pos == -1:
    return True  # ì°¾ì§ ëª»íë©´ ë¬´ì¡°ê±´ íµê³¼!
```

**í´ê²°ì±**:
1. **Role ì¶ë¡ **: LLM ê²°ê³¼ì ê´ê³ìì´ **í­ì** `infer_role_from_context` ì¤í. ê´ê³ ë°ì´í° ê¸°ë° ë¶ìì´ ë ì ë¢°ë ëì.
```python
# ìì ë ì½ë
inferred_role = infer_role_from_context(name, rel_data, story_text)
if inferred_role:
    final_role = inferred_role  # ì¶ë¡  ê²°ê³¼ ì°ì 
```

2. **Catchphrase ê²ì¦**: ëì¬ë¥¼ ì°¾ì§ ëª»íë©´ **ê±°ë¶**(False)ë¡ ë³ê²½. 3ë¨ê³ ê²ì ì ëµ ëì.
```python
# ìì ë ì½ë
if phrase_pos == -1:
    return False  # ê²ì¦ ë¶ê° ì ê±°ë¶
```

**ìì ë íì¼**: `aggregator.py`, `dialogue_mood.py`

---

#### 19. Multi-Tier ëª¨ë¸ ì ëµ ëì - 2024-12-30

**ë¬¸ì **: Claude 3 Haiku ëª¨ë¸ë§ ì¬ì©íì¬ ë³µì¡í ì¶ë¡ (Role, ê´ê³ ë¶ì)ìì ì íë ë¶ì¡±.

**í´ê²°ì±**: ìì´ì í¸ë³ ì¤ìëì ë°ë¼ 3ê° tier ëª¨ë¸ í ë¹.

| Tier | ëª¨ë¸ | ìì´ì í¸ |
|------|------|----------|
| basic | Claude 3 Haiku | inventory, stats |
| standard | Claude 3.5 Sonnet | personality, appearance |
| advanced | Claude 3.5 Sonnet v2 | identity, relations, dialogue_mood |

**ìì ë íì¼**: `llm.py`, ëª¨ë  character extraction ìì´ì í¸

---

#### 20. ì±ë¥ ìµì í - LLM Tier ë¤ì´ê·¸ë ì´ë (2025-12-30)

**ë¬¸ì **: 5500ì ìì¤ ë¶ìì ì½ 90ì´ ìì (ê³¼ëí ì²ë¦¬ ìê°).

**ìì¸ ë¶ì**: 
- ê°ë¨í ì¶ì¶ ìì(ì¸ë²¤í ë¦¬, ì±ê²©, ë°°ê²½)ìë ê³ ì±ë¥ ëª¨ë¸(Claude 3.5 Haiku) ì¬ì©
- LLM í¸ì¶ë¹ ìëµ ìê°ì´ ì±ë¥ ë³ëª©

**í´ê²°ì±**: ë¨ì ì¶ì¶ ìì´ì í¸ë¥¼ `basic` tier(Claude 3 Haiku)ë¡ ë¤ì´ê·¸ë ì´ë.

| ìì´ì í¸ | ë³ê²½ ì  | ë³ê²½ í | ì´ì  |
|---------|---------|---------|------|
| inventory | standard | **basic** | ìì´í ëª©ë¡ ì¶ì¶ì ë¨ì ìì |
| personality | standard | **basic** | ì±ê²© í¤ìë ë¶ë¥ë ë¨ì ìì |
| setting | standard | **basic** | ë°°ê²½ ë¬ì¬ ì¶ì¶ì ë¨ì ìì |
| stats | basic | basic (ì ì§) | ì´ë¯¸ ìµì íë¨ |
| identity | standard | standard (ì ì§) | Role ì¶ë¡ ì ëì ì íë íì |
| appearance | standard | standard (ì ì§) | ìê° íë¡¬íí¸ ìì±ì íì§ íì |
| dialogue_mood | advanced | advanced (ì ì§) | TTS íµí©ì ë³µì¡í ë¶ì íì |

**ìì ê°ì **: ì²ë¦¬ ìê° 20-30% ë¨ì¶ (90ì´ â 60-70ì´)

**ìì ë íì¼**: 
- `app/agents/extraction/character/inventory.py` - tier: standard â basic
- `app/agents/extraction/character/personality.py` - tier: standard â basic
- `app/agents/extraction/setting.py` - tier: standard â basic

---

#### 21. ì¬ì¶ì¶ ë£¨íë¡ ì¸í ì±ë¥ ì í (2025-12-30)

**ë¬¸ì **: 5500ì ìì¤ ë¶ì ìê°ì´ 90ì´ â 409ì´ë¡ 4.5ë°° ì¦ê°.

**ìì¸ ë¶ì**: 
- Consistency Checkì `requires_reextraction` ì¡°ê±´ì´ ëë¬´ ìê²©í¨
- ê¸°ì¡´ ì¡°ê±´: `score <= 50 OR HIGH severity >= 1` â ì¬ì¶ì¶ í¸ë¦¬ê±°
- HIGH severity 1ê°ë§ ìì´ë ì ì²´ íì´íë¼ì¸ ì¬ì¤í (ìµë 3í)

**ì¦ì**:
```
[trace-xxx] Consistency requires re-extraction
[trace-xxx] -> extraction (retry: 2/3)
```

**í´ê²°ì±**: ì¬ì¶ì¶ ìê³ê° ìí

| ì¡°ê±´ | ë³ê²½ ì  | ë³ê²½ í |
|------|---------|---------|
| ì ì ìê³ê° | â¤ 50 | **â¤ 30** |
| HIGH severity | â¥ 1ê° | **â¥ 2ê°** |

**ê¸°ë í¨ê³¼**: 
- ë¨ì¼ HIGH severity ë¬¸ì ë¡ë ì¬ì¶ì¶ ì í¨ (human_reviewë¡ ì²ë¦¬)
- ì¤ì ë¡ ì¬ê°í ë¬¸ì (ì ì 30 ì´í ëë HIGH 2ê° ì´ì)ë§ ì¬ì¶ì¶

**ìì ë íì¼**: 
- `app/agents/analysis/consistency.py` - requires_reextraction ìê³ê° ë³ê²½

---

#### 22. ì¢í© ì±ë¥ ìµì í (4ê°ì§ ë°©ì) - 2025-12-30

**ë¬¸ì **: 
1. Personality ì¶ì¶ íì§ ì í (ë¹ ë°°ì´ ë°í)
2. ìºë¦­í° ì´ë¦ ì¤ë³µ (íê¸/ìë¬¸ ëì¼ ì¸ë¬¼ 2ë² ì¶ì¶)
3. AI ìºë¦­í°(ARIA)ì ë¶íìí ìì´ì í¸ ì¤í
4. ì²ë¦¬ ìê° ~94ì´

**í´ê²°ì±**:

**ë°©ì 1: Personality Agent Tier ë³µì**
- ìì¸: `basic` tier(Haiku)ê° ë¹ ì±ê²© ë°°ì´ ë°í
- í´ê²°: `standard` tierë¡ ë³µì
- íì¼: `personality.py`

**ë°©ì 2: ìºë¦­í° ì´ë¦ ì ê·í**
- ìì¸: LLMì´ "ì¸ë¼"ì "Sera"ë¥¼ ë³ë ìºë¦­í°ë¡ ì¶ì¶
- í´ê²°: `identity.py`ì íì²ë¦¬ ë¡ì§ ì¶ê°
  - ì¤í ë¦¬ìì "ë² ë¼(Vera)" í¨í´ ê°ì§ â ìë¬¸ ì­ì 
  - íê¸-ë¡ë§ì ë³íì¼ë¡ ì¤ë³µ ê°ì§ (ë¦¬ì â Lian)
- íì¼: `identity.py`

**ë°©ì 3: AI ìºë¦­í° ìì´ì í¸ ì¤íµ**
- ìì¸: ARIA(ë ìíëí¸ AI)ìê²ë appearance/inventory/stats ì¤í
- í´ê²°:
  - `identity.py`: AI ìºë¦­í° ê°ì§ (`race`ì "ì¸ê³µì§ë¥", "ìíëí¸" ë±)
  - `supervisor.py`: AI ìºë¦­í°ë§ ìì ê²½ì° ë¬¼ë¦¬ì  ìì´ì í¸ ì¤íµ
- íì¼: `identity.py`, `supervisor.py`

**ë°©ì 4: ë°°ì¹ LLM í¸ì¶ (íì¸)**
- ë¶ì: ì´ë¯¸ ìì´ì í¸ë³ 1í LLM í¸ì¶ë¡ ëª¨ë  ìºë¦­í° ì²ë¦¬ ì¤
- ìí: ì¶ê° ë³ê²½ ë¶íì (ì´ë¯¸ ìµì íë¨)

**ìì í¨ê³¼**:
- íì§: Personality ë°ì´í° ì ì ì¶ì¶
- ì íë: ì¤ë³µ ìºë¦­í° ì ê±° (7ëª â 5ëª)
- ìë: AI ìºë¦­í° ì¤íµì¼ë¡ ~10-15ì´ ì ê°

**ìì ë íì¼**:
- `app/agents/extraction/character/personality.py` - tier: basic â standard
- `app/agents/extraction/character/identity.py` - ì´ë¦ ì ê·í + AI ê°ì§
- `app/agents/extraction/character/supervisor.py` - AI ìºë¦­í° ìì´ì í¸ ì¤íµ

---

#### 23. max_tokens í°ì´ë³ ìµì í - 2025-12-30

**ë¬¸ì **: ëª¨ë  LLM í¸ì¶ì `max_tokens=4096` ì¬ì©ì¼ë¡ ë¶íìí í í° ìì± ë° ì§ì° ë°ì.

**í´ê²°ì±**: í°ì´ë³ ìµì íë max_tokens ê¸°ë³¸ê° ì¤ì 

| Tier | ëª¨ë¸ | max_tokens | ì©ë |
|------|------|------------|------|
| basic | Claude 3 Haiku | **1024** | ë¨ì ë¶ë¥, ë¼ì°í |
| standard | Claude 3.5 Haiku | **2048** | ì¶ì¶, ìì½ |
| advanced | Claude 4.5 Haiku | 4096 | ë³µì¡í ë¶ì |

**ìë¦¬**:
- LLMì max_tokensê¹ì§ ìì±í  "ì¬ì "ë¥¼ ëê³  ì¶ë¡ 
- ìì max_tokens = ë ë¹ ë¥¸ í í° ìì± ìì
- ëë¶ë¶ì ìì´ì í¸ë 2048 í í° ë¯¸ë§ ìëµ

**êµ¬í**:
```python
# llm.py
model_configs = {
    "basic": {"model_id": "...", "default_max_tokens": 1024},
    "standard": {"model_id": "...", "default_max_tokens": 2048},
    "advanced": {"model_id": "...", "default_max_tokens": 4096},
}
effective_max_tokens = config.get("default_max_tokens", 4096)
```

**ìì í¨ê³¼**: ìì´ì í¸ë¹ 1-2ì´ ì ê° (ì´ 10-15ì´)

**ìì ë íì¼**: `app/agents/llm.py`

---

## 18. Schema v2.0 ë¦¬í©í ë§ ë° Neo4j RAG êµ¬í

### ð ë ì§
2025-12-31

### ð ë¬¸ì 
1. ë¶íìí íëë¤ë¡ ì¸í´ ì¶ë ¥ JSONì´ ë¹ëíê³  ì²ë¦¬ ìëê° ëë¦¼
2. Consistency ê²ì¬ê° íì¬ ì±í° ë´ììë§ ìíëì´ ì´ì  ì±í°ìì ëª¨ì ê°ì§ ë¶ê°
3. Dialogue/Emotion Agentê° Consistency ê²ì¬ì ì¤ì§ì  ê¸°ì¬ê° ìì

### ð¡ ìì¸ ë¶ì
- `stats`, `combat`, `state`, `economy` ë± ê²ì ì ì© íëê° ìì¤ ë¶ìì ë¶íì
- `dialogues`, `emotions` íëê° ê°ì°ì± ê²ì¬ìì ì°¸ì¡°ëì§ë§ ëªìì  ê²ì¬ ê·ì¹ ìì
- ì´ì  ìºë¦­í°/ì´ë²¤í¸ ë°ì´í°ë¥¼ ì¡°íí  RAG ìì¤í ë¶ì¬

### â í´ê²° ë°©ë²

#### 1. fix.md ê¸°ë° ì¤í¤ë§ ê°ìí
```
ì ê±°ë íë:
- Global: dialogues, emotions
- Characters: name(root), stats, combat, state, visual, economy, final_stats
- Events: is_foreshadowing, foreshadowing_tag
- Plot: foreshadowing, tension_curve, three_act_structure, narrative_beats

êµ¬ì¡° ë³ê²½:
- social â profile.faction.social ë§ì´ê·¸ë ì´ì
- plot_integration â plot ì´ë¦ ë³ê²½
```

#### 2. ìì´ì í¸ ì­ì 
- `dialogue.py`, `emotion.py` - Dialogue/Emotion Agent ì­ì 
- `stats.py` - Stats Agent ì­ì 
- ê´ë ¨ ì¤í¤ë§ íì¼ ì­ì  (`dialogues.py`, `emotions.py`)

#### 3. RelationType enum ê°ìí
```python
class RelationType(str, Enum):
    ROMANCE = "Romance"
    NORMAL = "Normal"
    FRIENDLY = "Friendly"
    HOSTILE = "Hostile"
    UNKNOWN = "Unknown"
```

#### 4. Neo4j RAG êµ¬í
```python
# db_query_service.pyì ì¶ê°
async def get_embedding(text: str) -> list[float]
async def search_similar_characters(project_id, embedding, top_k)
async def search_similar_events(project_id, embedding, top_k)
async def retrieve_relevant_history(project_id, characters, events)
```

#### 5. CROSS_CHAPTER_CONFLICT íì ì¶ê°
```
7. **CROSS_CHAPTER_CONFLICT** (HIGH)
   - Character marked "deceased" in previous chapter appears alive
   - Relationship type changes drastically without justification
   - Event contradicts previously established facts
```

#### 6. Character Embedding ìì±
```python
# aggregator.py
full_char = {
    ...
    "embedding": generate_character_embedding(name, traits, role),  # 1536-dim
}
```

#### 7. Event Embedding ìì± (ì¶ê°)
```python
# event.py - ê° ì´ë²¤í¸ë§ë¤ ìì±
event["embedding"] = generate_event_embedding(
    narrative_summary,  # "ìë¦°ì´ ë§ì¡±ê³¼ ì í¬ë¥¼ ììí¨"
    participants        # ["ìë¦°", "ë§ì¡± ì ì¬"]
)
```

### ð ìì ë íì¼
| íì¼ | ë³ê²½ ë´ì© |
|------|----------|
| `app/schemas/relationships.py` | RelationType 5ê° ê°ì¼ë¡ ë³ê²½ |
| `app/schemas/plot.py` | PlotIntegrationResult â PlotResult ê°ìí |
| `app/schemas/events.py` | foreshadowing íë ì ê±° |
| `app/schemas/callback.py` | dialogues/emotions ì ê±°, plot_integration â plot |
| `app/agents/extraction/character/aggregator.py` | SAFE_DEFAULTS ê°ìí, ìºë¦­í° embedding ìì± |
| `app/agents/extraction/character/supervisor.py` | stats ìì´ì í¸ ì ê±° |
| `app/agents/extraction/event.py` | **ì´ë²¤í¸ embedding ìì± ì¶ê°** |
| `app/agents/graph.py` | Dialogue/Emotion Agent í¸ì¶ ì ê±° |
| `app/agents/analysis/consistency.py` | CROSS_CHAPTER_CONFLICT + RAG íµí© |
| `app/agents/analysis/plot.py` | ê°ìíë PlotResult ì¬ì© |
| `app/services/db_query_service.py` | ë²¡í° ê²ì í¨ì ì¶ê° (RAG) |

### â ê²°ê³¼
- ì¶ë ¥ JSON í¬ê¸° 40-50% ê°ì
- Character Team: 7ê° â 6ê° ìë¸ìì´ì í¸
- **ìºë¦­í° + ì´ë²¤í¸ ëª¨ë embedding ìì±** â ì ì¬ ìí© ê²ì ê°ë¥
- Consistency ê²ì¬ìì ì´ì  ì±í° ìºë¦­í°/ì´ë²¤í¸ RAG ê²ì ê°ë¥
- Spring Bootìì embedding íë ê·¸ëë¡ Neo4jì ì ì¥íë©´ ë²¡í° ê²ì íì±í

### ð Spring Boot ìì íì
```cypher
-- Neo4j ë²¡í° ì¸ë±ì¤ ìì± (5.11+)
-- ìºë¦­í°ì©
CREATE VECTOR INDEX character_embedding IF NOT EXISTS
FOR (c:Character) ON (c.embedding)
OPTIONS {indexConfig: {`vector.dimensions`: 1536, `vector.similarity_function`: 'cosine'}}

-- ì´ë²¤í¸ì© (NEW!)
CREATE VECTOR INDEX event_embedding IF NOT EXISTS
FOR (e:Event) ON (e.embedding)
OPTIONS {indexConfig: {`vector.dimensions`: 1536, `vector.similarity_function`: 'cosine'}}
```

---

## ííë¦¿ (ì ì´ì ì¶ê° ì ì¬ì©)

```markdown
## N. [ìì´ì í¸ëª] - [ë¬¸ì  ìì½]

### ð ë ì§
[YYYY-MM-DD]

### ð ë¬¸ì 
[ë¬¸ì  ì¤ëª]

### ð¡ ìì¸ ë¶ì
[ìì¸]

### â í´ê²° ë°©ë²
[í´ê²° ë°©ë²]

### ð ìì ë íì¼
- [íì¼ ëª©ë¡]

### â ê²°ê³¼
[ê²°ê³¼]
```

---

## 19. ëì©ë ë°ì´í° ì²ë¦¬ ìí¤íì² ì¬ì¤ê³ (Architecture Redesign)

### ð ë ì§
2026-01-01

### ð¯ ëª©í
365ê° ì±í°(ëì©ë ìì¤) ìë¡ë ì **0.5ì´ ì´ë´ ì´ê¸° ìëµ** + **ë¹ëê¸° AI ë¶ì** ìí¤íì² ì¤ê³

---

## 1ï¸â£ ì ìë ìí¬íë¡ì° (Original Workflow)

### ìì¤í ìí¤íì² (3ë¨ê³)
1. **Ingestion (Spring)**: ìë³¸ ì ì¥ ë° 1ì°¨ ë¬¼ë¦¬ ë¶í  (ì´ê³ ì)
2. **Processing (Python)**: 2ì°¨ ë¼ë¦¬/ìë¯¸ ë¶í  ë° AI ë¶ì (ì ë°)
3. **Serving (Client)**: ê²°ê³¼ ìê°í (ì§ì° ë¡ë©)

### Phase 1: ìë¡ë ë° ì´ê³ ì ì´ê¸°í (Client â Spring) - **0.5ì´ ëª©í**
| ë¨ê³ | ìì | ì¤ëª |
|------|------|------|
| 1 | íì¼ ìì  | `POST /api/projects/upload` |
| 2 | S3 ì ì¥ | `raw/{uuid}.txt` ì¦ì ìë¡ë (Safety First) |
| 3 | Project ìì± | DB `project` íì´ë¸ ë ì½ë ìì± |
| 4 | Regex ë¶í  | Java ì ê·ìì¼ë¡ 365ê° ì±í° ë¶í  |
| 5 | Bulk Insert | `chapter` íì´ë¸ì 365ê° ë ì½ë í ë²ì ì ì¥ |
| 6 | ë©ìì§ ë°í | RabbitMQì 365ê° ë©ìì§ Fan-out |
| 7 | ìëµ ë¦¬í´ | `200 OK + projectId` (ì¬ì©ìë ì¦ì ì±í° ëª©ë¡ íì¸ ê°ë¥) |

### Phase 2: ë¹ëê¸° ì ë° ë¶ì (RabbitMQ â Python)
| ë¨ê³ | ìì | ì¤ëª |
|------|------|------|
| 1 | ë©ìì§ ìì  | ìì»¤(1~10)ê° `chapterId` ê°ì ¸ê° |
| 2 | DB ì¡°í | `chapter` íì´ë¸ìì content ì¡°í |
| 3 | Semantic Chunking | ë¬¸ì¥ ìë² ë© â ìë¯¸ ë¨ì ë¶í  |
| 4 | AI ìì½ | LLMì¼ë¡ `nav_title` ìì± |
| 5 | ì¹ì ì ì¥ | `section` íì´ë¸ì Bulk Insert |
| 6 | ìí ê°±ì  | `chapter.status = COMPLETED` |

### Phase 3: ê²°ê³¼ ì¡°í (Client â Spring)
- SSE/í´ë§ì¼ë¡ ì±í° ìí ì¤ìê° ê°±ì 
- ìë£ë ì±í° í´ë¦­ ì `GET /api/chapters/{id}/sections` í¸ì¶

---

## 2ï¸â£ ì¬ì©ì ì§ë¬¸ ë° ìëì´ ê°ë°ì ìëµ

### Q1: RabbitMQì contentë¥¼ ë´ë ê² vs DB ì¡°í?

**ìëµ: DB ì¡°í ë°©ì ìëì  ì ë¦¬ (Claim Check Pattern)**

| ê¸°ì¤ | Content í¬í¨ | IDë§ ì ì¡ |
|------|-------------|-----------|
| RabbitMQ ë¶í | ëì (OOM ìí) | ë®ì |
| ì¬ìë ë¹ì© | ëì | ë®ì (IDë§ ì¬ì ì¡) |
| ë°ì´í° ì¼ê´ì± | ë©ìì§ ìì  ê³ ì  | í­ì ìµì  |

**ê¶ì¥ Flow:**
```
RabbitMQ: {"projectId": 1, "chapterId": 101}  (ê°ë²¼ì)
     â
Python: SELECT content FROM chapter WHERE id=101
```

### Q2: ë¬¸ì¥ ìë² ë© vs Neo4j íì©?

**ìëµ: íì´ë¸ë¦¬ë ì ëµ ì¶ì²**

1. **ë¬¸ì¥ ìë² ë© ê¸°ë° Semantic Chunking** (Base)
   - ì/ë· ë¬¸ì¥ ì ì¬ë ê¸ë½ì  = ì¥ë©´ ì íì 
   - ì¬ëì´ ëë¼ë "ë¬¸ë¨ ì í"ì ê¸°ê³ì ì¼ë¡ íì§

2. **Neo4j ë©íë°ì´í° íê¹** (Enrichment)
   - ë¶í ë Sectionì ìºë¦­í°/ì´ë²¤í¸ í¤ìë ë§¤í
   - `relates_to: ['ì² ì', 'ìí¬']` íê·¸ ì¶ê°
   - RAG ê²ì ì ë©íë°ì´í° íí° íì©

---

## 3ï¸â£ ì¶ê° ê³ ë ¤ì¬í­ ë° ì§ë¬¸ (Antigravity ë¶ì)

### A. ì±í° ê° ìºë¦­í° ì¼ê´ì± ë¬¸ì 

**ì§ë¬¸**: 1ì¥ìì ì¶ì¶ë `char-ì´ì-001`ì´ 50ì¥ììë ëì¼ ì¸ë¬¼ë¡ ì¸ìëë?

**ë¶ì ê²°ê³¼**: â **ì´ë¯¸ ì§ìë¨**
```python
# aggregator.py (ë¼ì¸ 546-580)
existing_char = existing_lookup.get(canonical_name)
if existing_char:
    char_id = existing_char.get("id", ...)  # ID ì¬ì¬ì©
```

**ì¡°ê±´**: `existing_characters`ë¡ ì´ì  ì±í° ìºë¦­í° ì ë¬ íì

### B. ìì°¨ vs ë³ë ¬ ì²ë¦¬

| ë°©ì | ì¥ì  | ë¨ì  |
|------|------|------|
| ìì°¨ ì²ë¦¬ | ë§¥ë½ ì í | ëë¦¼ (180ë¶+) |
| ë³ë ¬ ì²ë¦¬ | ë¹ ë¦ | "ê·¸ë" ë± ëëªì¬ í´ì ë¶ê° |

### C. 0.5ì´ ëª©í ë¬ì± ê°ë¥ì±

**RabbitMQ ê¸°ë³¸ ì¤ì **: 365ê° ë©ìì§ ê°ë³ ë°í â **ë¶ê°ë¥**
**Batch ëª¨ë íì**: ë¤í¸ìí¬ ìë³µ 1íë¡ 365ê° ë°í â **ê°ë¥**

### D. ì¤ìê° ìí í´ë§

**ì¶ì²**: SSE + Redis Pub/Sub
- í´ë§ë³´ë¤ DB ë¶í ê°ì
- WebSocketë³´ë¤ êµ¬í ê°ë¨

### E. ì±í° ë¶í  Fallback

**ë¬¸ì **: ëª¨ë  ìì¤ì´ `ì 1ì¥`, `Chapter 1` í¨í´ì ë°ë¥´ì§ ìì

### F. Section ìë² ë© ì ì¥ì

**ì§ë¬¸**: ìºë¦­í°/ì´ë²¤í¸ë Neo4j, Section ìë² ë©ì ì´ëì?

---

## 4ï¸â£ ì¬ì©ì íì ì§ë¬¸ì ëí ëµë³

### Q1: ì±í°ë³ ë¶ì ì ëì¼ ìºë¦­í° ì¸ì íì¤í¸?

**ëµë³**: íì¬ ìì¤í ì´ë¯¸ `existing_characters` ê¸°ë° ID ì¬ì¬ì© ì§ì

**ìí¬íë¡ì°:**
```
ì±í° N ë¶ì ìë£ â DBì ìºë¦­í° ì ì¥
     â
ì±í° N+1 ë¶ì ìì²­ â DBìì ê¸°ì¡´ ìºë¦­í° ì¡°í â context.existing_charactersë¡ ì ë¬
     â
Pythonì´ ì´ë¦ ë§¤ì¹­ + ID ì¬ì¬ì©
```

### Q2: ìºë¦­í° ID ì¼ê´ì± ì ì§ ì ëµ?

**ì¶ì²: ìì°¨-ì¦ë¶ ë¶ì**
```json
POST /api/analysis/chapter/{chapterId}
{
  "content": "ì±í° 50 íì¤í¸...",
  "context": {
    "existing_characters": [
      {"id": "char-ì´ì-001", "name": "ì´ì", "aliases": ["Ian"]}
    ]
  }
}
```

### Q3: ìì°¨ vs ë³ë ¬?

**ì¶ì²: 2-Pass íì´ë¸ë¦¬ë ì ëµ**

| Pass | ë°©ì | ëª©ì  | ìë |
|------|------|------|------|
| 1ì°¨ | ë³ë ¬ (10 ìì»¤) | ê¸°ë³¸ ì¶ì¶ | ë¹ ë¦ (~20ë¶) |
| 2ì°¨ | ìì°¨ + ë³í© | ID íµí©, ê´ê³ ì°ê²° | ëë¦¼ (~5ë¶) |

**ì´ 25ë¶** (ìì°¨ë§ í  ê²½ì° 180ë¶+)

### Q4: 0.5ì´ ë©ìì§ ë°í?

**RabbitMQ Batch ëª¨ëë¡ ê°ë¥:**
```java
rabbitTemplate.invoke(operations -> {
    for (ChapterMessage msg : messages) {
        operations.convertAndSend(EXCHANGE, ROUTING_KEY, msg);
    }
    operations.waitForConfirms(5000);
    return true;
});
```

**ë¤ë¥¸ MQ ë¶íì** - RabbitMQ Batchë¡ ì¶©ë¶

### Q5: SSE ì¶ì² ì´ì ?

| ê¸°ì¤ | í´ë§ | SSE | WebSocket |
|------|------|-----|-----------|
| ìë² ë¶í | ëì | ë®ì | ë®ì |
| HTTP í¸í | â | â | â |
| ìë°©í¥ | â | â | â |
| ë³µì¡ë | ì¬ì | ë³´íµ | ì´ë ¤ì |

**SSE ì¶ì² ì´ì :**
1. ìí ìë¦¼ì **ìë²âí´ë¼ì´ì¸í¸ ë¨ë°©í¥**ì´ë©´ ì¶©ë¶
2. HTTP ê¸°ë°ì¼ë¡ **íë¡ì/ë¡ëë°¸ë°ì ì¹íì **
3. WebSocketë³´ë¤ **êµ¬í ê°ë¨**

### Q6: ì±í° ë¶í  Fallback?

**Cascading Fallback ì¶ì²:**
```java
public List<Chapter> splitChapters(String rawText) {
    // 1ì°¨: ëªìì  ë§ì»¤ (ì 1ì¥, Chapter 1)
    List<Chapter> chapters = splitByExplicitMarkers(rawText);
    if (!chapters.isEmpty()) return chapters;
    
    // 2ì°¨: ë¹ ì¤ + ì ëª© í¨í´ (### ëë **êµµì**)
    chapters = splitByParagraphHeaders(rawText);
    if (!chapters.isEmpty()) return chapters;
    
    // 3ì°¨: ë¹ ì¤ ê¸°ë°
    chapters = splitByDoubleNewline(rawText);
    if (chapters.size() >= 10) return chapters;
    
    // 4ì°¨: ê³ ì  ê¸ì ì + ë¬¸ì¥ ê²½ê³ ì¡´ì¤ (10,000ì)
    return splitByCharacterCount(rawText, 10000, true);
}
```

### Q7: Section ìë² ë© ì ì¥ì?

**ì¶ì²: PostgreSQL + pgvector**

| ìµì | ì¥ì  | ë¨ì  |
|------|------|------|
| **PostgreSQL + pgvector** | ì´ì ë¨ì, ê¸°ì¡´ ì¸íë¼ | 10M+ ì ì±ë¥ íê³ |
| Neo4j Vector | ê·¸ëí íµí© | ëë¦¼ |
| Qdrant | ìµê³  ì±ë¥ | ì¶ê° ì¸íë¼ |

**ì­í  ë¶ë¦¬:**
- **Neo4j**: ìºë¦­í°/ì´ë²¤í¸ ê´ê³ (ê·¸ëí ì¿¼ë¦¬)
- **PostgreSQL(pgvector)**: Section ìë² ë© (ìë¯¸ ê²ì)

**Section íì´ë¸ ì¤ê³:**
```sql
CREATE TABLE section (
    id BIGSERIAL PRIMARY KEY,
    chapter_id BIGINT NOT NULL,
    project_id BIGINT NOT NULL,
    nav_title VARCHAR(100),
    content TEXT NOT NULL,
    sequence_order INT NOT NULL,
    embedding vector(1536),              -- pgvector
    related_characters TEXT[],           -- Neo4j ë©íë°ì´í° íê¹
    related_events TEXT[]
);

CREATE INDEX idx_section_embedding ON section 
USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 100);
```

---

## 5ï¸â£ ìµì¢ ì¶ì² ìì½

### ìí¤íì² ê²°ì 

| í­ëª© | ì¶ì² |
|------|------|
| ë©ìì§ ì ì¡ | **Claim Check Pattern** (IDë§ ì ì¡, DBìì content ì¡°í) |
| ì±í° ë¶í  | **Cascading Fallback** (ëªìì  ë§ì»¤ â ë¹ ì¤ â ê³ ì  ê¸ìì) |
| ì²ë¦¬ ë°©ì | **2-Pass íì´ë¸ë¦¬ë** (ë³ë ¬ ì¶ì¶ â ê¸ë¡ë² ë³í©) |
| ë©ìì§ í | **RabbitMQ Batch ëª¨ë** (ë³ê²½ ë¶íì) |
| ìí í´ë§ | **SSE + Redis Pub/Sub** |
| ìë² ë© ì ì¥ | **PostgreSQL + pgvector** (Section) / **Neo4j** (Character/Event) |

### ìµì¢ ë°ì´í° íë¦

```
âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
â Phase 1: Ingestion (Spring) - 0.5ì´ ëª©í                         â
â                                                                 â
â  Client â Spring â S3 (ìë³¸) + PostgreSQL (chapters) + RabbitMQ â
âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
                              â
âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
â Phase 2: Processing (Python) - ë¹ëê¸°                            â
â                                                                 â
â  1ì°¨ Pass (ë³ë ¬): 10 ìì»¤ Ã 365 ì±í° â ê¸°ë³¸ ì¶ì¶ (~20ë¶)          â
â  2ì°¨ Pass (ìì°¨): ID íµí© + ê´ê³ ì°ê²° + ëª¨ì ê°ì§ (~5ë¶)          â
âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
                              â
âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
â Phase 3: Serving (Client)                                       â
â                                                                 â
â  SSEë¡ ìí ìì  â ìë£ë ì±í° í´ë¦­ â Section íì¤í¸ + ë©íë°ì´í° â
âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
```

### ì ì¥ì ì­í  ë¶ë¦¬

```
âââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
â                    ì ì¥ì ì­í  ë¶ë¦¬                     â
â                                                       â
â  âââââââââââââââââââ    âââââââââââââââââââ          â
â  â   PostgreSQL    â    â     Neo4j       â          â
â  â   + pgvector    â    â                 â          â
â  âââââââââââââââââââ    âââââââââââââââââââ          â
â          â                      â                    â
â   - project, chapter      - Character Node          â
â   - section + embedding   - Event Node              â
â   - ìë¯¸ ê²ì (RAG)        - Relationships          â
â                           - ê·¸ëí ì¿¼ë¦¬              â
âââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
```

---

### ð ê´ë ¨ íì¼ (í¥í êµ¬í ì)
- `app/agents/extraction/character/aggregator.py` - existing_characters íì© ë¡ì§
- `app/services/section_service.py` - ì ê· (Section ì ì¥ + ìë² ë©)
- `app/services/chunking_service.py` - ì ê· (Semantic Chunking)
- Spring Boot: `ChapterSplitService.java`, `RabbitMQBatchPublisher.java`

------

## 20. ì±ë¥ ë³ëª© ë¶ì ë° ìµì í

### ð ë ì§
2026-01-03

### ð´ ë¬¸ì  (Problem)

ëì©ë ë¬¸ì(3.21MB Les MisÃ©rables) ë¶ì ì **2ìê° 20ë¶ ì´ì** ìì.
ë¡ê·¸ ë¶ì ê²°ê³¼ 3ê°ì§ ì£¼ì ë³ëª© ë°ê²¬:

#### 1. ë¬´í ì¬ì²ë¦¬ ë£¨í
```
[trace-20260102-52c34f32] -> extraction  (11:39:27)
[trace-20260102-52c34f32] -> extraction  (11:42:50)  â 3ë¶ í ì¬ìë
[trace-20260102-52c34f32] -> extraction  (11:43:00)  â ë ì¬ìë
[trace-20260102-52c34f32] -> extraction  (11:46:47)  â ë¬´í ë°ë³µ
```
- **ìì¸**: Event=0ì¼ ë Validation ì¤í¨ â `retry_extraction` ë¬´í ë°ë³µ

#### 2. PostgreSQL Pool ë¯¸ì´ê¸°í
```
PostgreSQL pool not initialized
Document content not found: {document_id}
```
- **ìì¸**: DB ì°ê²° ì  Consumerê° ë©ìì§ ì²ë¦¬ ìë

#### 3. Neo4j ì°ê²° ëê¹
```
Failed vector search - Connection closed with incomplete handshake
```
- **ìì¸**: ëë ìì²­ì¼ë¡ ì°ê²° íììì

### ð¡ ìì¸ ë¶ì (Root Cause)

| ë³ëª© | íì¬ ì¤ì  | ë¬¸ì ì  |
|------|----------|--------|
| Event ì¶ì¶ ì¤í¨ | `required: True` | ì´ë²¤í¸ ìì¼ë©´ ì ì²´ ì¤í¨ |
| Retry Threshold | 50% | íì§ 50 ë¯¸ë§ì ë¬´í ì¬ì¶ì¶ |
| MAX_RETRIES | 3í | ëë¬´ ë§ì ì¬ìë |
| Prefetch Count | 10 | ëì ì²ë¦¬ë ì í |
| Embedding ëìì± | 5 | ìë² ë© ë³ëª© |
| Chunk í¬ê¸° | 2000ì | ëë¬´ ë§ì ì¹ì ìì± |

### ð¢ í´ê²°ì± (Solution)

#### 1. Validation ë¬´í ë£¨í ì°¨ë¨ (`validator.py`)
```python
# BEFORE
"extracted_events": {
    "required": True,
    "min_count": 1,
    "penalty_missing": 15,
}

# AFTER
"extracted_events": {
    "required": False,  # ì´ë²¤í¸ ì¤í¨í´ë ì§í
    "min_count": 0,
    "penalty_missing": 5,  # íëí° ê°ì
}
```

```python
# BEFORE: quality < 50 â retry_extraction
# AFTER: quality < 30 â retry_extraction (threshold ë®ì¶¤)
elif quality_score >= 30:
    action = "human_review"  # 50â30
```

#### 2. Retry íì ì í (`supervisor.py`)
```python
# BEFORE
MAX_EXTRACTION_RETRIES = 3

# AFTER
MAX_EXTRACTION_RETRIES = 2  # ì¬ìë 1í ê°ì
```

#### 3. DB ì°ê²° ëê¸° (`document_analysis_consumer.py`)
```python
async def start(self) -> None:
    # DB ìë¹ì¤ ì´ê¸°í ëê¸° ì¶ê°
    logger.info("Waiting for DB service to initialize...")
    db_service = await get_db_service()
    if not await db_service.ensure_postgres_connected():
        raise RuntimeError("Failed to connect to PostgreSQL")
    if not await db_service.ensure_neo4j_connected():
        logger.warning("Neo4j connection failed, will retry later")
    logger.info("DB service initialized")
    
    # RabbitMQ ì°ê²° (ì´íì ì¤í)
    ...
```

#### 4. ëì ì²ë¦¬ë ì¦ê° (`docker-compose.standalone.yml`)
```yaml
# BEFORE
CONSUMER_PREFETCH_COUNT: 10

# AFTER
CONSUMER_PREFETCH_COUNT: 20  # 2ë°° ì¦ê°
```

#### 5. Embedding ëìì± ì¦ê° (`embedding_service.py`)
```python
# BEFORE
max_concurrent: int = 5

# AFTER
max_concurrent: int = 10  # 2ë°° ì¦ê°
```

#### 6. Chunk í¬ê¸° ìµì í (`chunking_service.py`)
```python
# BEFORE
self.max_tokens_per_chunk = 2000
self.min_chunk_length = 500

# AFTER
self.max_tokens_per_chunk = 4000  # 2ë°° ì¦ê°
self.min_chunk_length = 800       # ìµì í¬ê¸° ì¦ê°
```

### ð ìì ë íì¼

| íì¼ | ë³ê²½ ë´ì© |
|------|----------|
| `app/agents/validation/validator.py` | events required=False, retry threshold 50â30 |
| `app/agents/supervisor.py` | MAX_EXTRACTION_RETRIES 3â2 |
| `app/services/document_analysis_consumer.py` | DB ì°ê²° ëê¸° ë¡ì§ ì¶ê° |
| `docker-compose.standalone.yml` | PREFETCH_COUNT 10â20 |
| `app/services/embedding_service.py` | max_concurrent 5â10 |
| `app/services/chunking_service.py` | max_tokens 2000â4000, min_chunk 500â800 |

### â ìì ê²°ê³¼

| í­ëª© | ì´ì  | ì´í | ê°ì ì¨ |
|------|------|------|--------|
| ì¬ìë íì | 3í | 2í | 33% â |
| ì´ë²¤í¸ 0ê° ì | ë¬´í ì¬ì¶ì¶ | ì ì ì§í | 100% í´ê²° |
| ëì ì²ë¦¬ë | 10 | 20 | 2x â |
| ìë² ë© ëìì± | 5 | 10 | 2x â |
| ì¹ì ì | ë§ì | ~50% ê°ì | 2x â |
| DB ë¯¸ì´ê¸°í | ëª¨ë  ë¬¸ì ì¤í¨ | ì°ê²° í ìì | 100% í´ê²° |

### ð¡ í¥í ê°ì  ì¬í­

1. **LLM í¸ì¶ ìºì±**: ëì¼ íì¤í¸ì ëí ì¤ë³µ í¸ì¶ ë°©ì§
2. **Batch LLM í¸ì¶**: ì¬ë¬ ë¬¸ìë¥¼ í ë²ì ì²ë¦¬
3. **Rate Limit ëì**: Gemini API ì¿¼í° ëª¨ëí°ë§ ë° ìë ì¡°ì 
4. **Connection Pool**: Neo4j/PostgreSQL ì°ê²° í ìµì í

---

## 21. Character Extraction - ëëªì´ì¸/ì ì¬ ì´ë¦ ì¤ë³µ ë¬¸ì 

### ð ë ì§
2026-01-03

### ð´ ë¬¸ì  (Problem)
ì¥ë¬¸ íì¤í¸ ë¶ì ì, ëì¼ ì¸ë¬¼ì´ ì´ë¦ íê¸° ì°¨ì´ë¡ ì¸í´ ë³ê°ì ìºë¦­í°ë¡ ë¶ë¦¬ë¨.
- ì: `Elara`(ìë¼ë¼)ì `Elara Vance`(ìë¼ë¼ ë°ì¤)ê° ê°ê° ìì±ë¨.
- ê²°ê³¼ì ì¼ë¡ ê´ê³(Relationship) ë°ì´í°ê° ë¶ì°ëê³  Neo4j ê·¸ëíê° ì§ì ë¶í´ì§.

### ð¡ ìì¸ ë¶ì (Root Cause)
1. ê¸°ì¡´ `aggregator.py`ë **ì íí ë¬¸ìì´ ì¼ì¹**ë **ì¬ì ì ì ìë ë³ì¹­(Alias)**ë§ ë³í©í¨.
2. LLMì´ ì¶ì¶ ìì ì ì´ë¦ì ì¡°ê¸ì© ë¤ë¥´ê²(Full Name vs First Name) ë°ííë ê²½ì°ë¥¼ ì²ë¦¬íì§ ëª»í¨.

### ð¢ í´ê²°ì± (Solution)
**Fuzzy Matching & Substring Merging** ë¡ì§ ëì (`app/agents/extraction/character/aggregator.py`)
1. **Jaro-Winkler Similarity**: ì ì¬ë 0.85 ì´ìì´ë©´ ëì¼ ì¸ë¬¼ë¡ ê°ì£¼.
2. **Substring Match**: í ì´ë¦ì´ ë¤ë¥¸ ì´ë¦ì ìì í í¬í¨ëë©´(ì: "Elara" in "Elara Vance") ë³í©.
3. **Canonical Name Selection**: ë³í© ì **ê°ì¥ ê¸´ ì´ë¦**ì ëí ì´ë¦ì¼ë¡ ì í (ì ë³´ëì´ ë§ì ìª½ ì°ì ).

### â ê²°ê³¼
- "Elara"ì "Elara Vance"ê° "Elara Vance"ë¡ ìë ë³í©ë¨.
- ì¤ë³µ ìºë¦­í° ë°ì 0ê±´.

---

## 22. Semantic Chunking - ì¥ë¬¸ íì¤í¸ ë¬¸ë§¥ ë¨ì 

### ð ë ì§
2026-01-03

### ð´ ë¬¸ì  (Problem)
5,000ì ì´ìì ì¥í¸ ìì¤ì í ë²ì ì²ë¦¬íê±°ë ë¨ì ê¸ì ìë¡ ìë¥´ë©´ ë¤ìê³¼ ê°ì ë¬¸ì  ë°ì:
1. ë¬¸ë§¥(Context) ë¨ì : ì¤ìí ì¥ë©´(Scene) ì¤ê°ì ìë ¤ì ì´ë²¤í¸ ì¶ì¶ ì¤í¨.
2. Token Limit ì´ê³¼: LLM ìë ¥ íê³ë¡ ë·ë¶ë¶ ë´ì© ëë½.

### ð¡ ìì¸ ë¶ì (Root Cause)
- ê³ ì  ê¸¸ì´(Fixed-size) ì²­í¹ ë°©ìì ìì¬ì íë¦(Narrative Flow)ì ê³ ë ¤íì§ ìì.

### ð¢ í´ê²°ì± (Solution)
**Semantic Chunking (ìë¯¸ ê¸°ë° ë¶í )** êµ¬í
1. **Embedding**: ë¬¸ë¨(Paragraph)ë³ë¡ ìë² ë© ë²¡í° ìì± (Gemini v1.5).
2. **Cosine Similarity**: ì¸ì  ë¬¸ë¨ ê° ì ì¬ë ê³ì°.
3. **Segmentation**: ì ì¬ëê° ê¸ê²©í ë¨ì´ì§ë êµ¬ê°(ìê³ê° 0.6 ë¯¸ë§)ì **ì¥ë©´ ì íì (Scene Break)**ì¼ë¡ íë¨íì¬ ì ë¨.
4. `event.py` íµí©: íì¤í¸ ê¸¸ì´ê° 4,000ìë¥¼ ëì ê²½ì°, Semantic Chunkingì ìííê³  ê° ì¹ìì ìì°¨ì ì¼ë¡ ì²ë¦¬íì¬ ì´ë²¤í¸ ID(E001...) ì°ìì± ë³´ì¥.

### â ê²°ê³¼
- 5,000ì ìì¤ì´ 6ê°ì ìë¯¸ ë¨ì ì¹ìì¼ë¡ ë¶í ë¨.
- ìì¬ ëê¹ ìì´ ì´ 46ê°ì ì´ë²¤í¸ê° E001~E046ì¼ë¡ ìë²½íê² ì¶ì¶ë¨.


---

## 21. Embedding Generation - Google API Key ì°¨ë¨ ë° Docker íê²½ ë³ì ê°±ì 

### ð ë ì§
2026-01-03

### ð´ ë¬¸ì  (Problem)
1.  **Google API Key Suspended**: ìë² ë© ìì± ìë ì `403 PERMISSION_DENIED` ëë "API keys with this specific Project ID have been suspended" ì¤ë¥ ë°ì. ì í¤ë¥¼ ë°ê¸ë°ìë ê³§ë°ë¡ ì°¨ë¨ë¨ (Leaked Key ê°ì§).
2.  **Env Var Not Updating**: `.env` íì¼ì ìì íê³  `docker restart`ë¥¼ ìííì¼ë ì»¨íì´ë ë´ë¶ìì ì´ì  í¤(`...NOV_0`)ê° ê³ì ì ì§ë¨.
3.  **Service Name Confusion**: `docker-compose up -d stolink-fastapi-agent` ëªë ¹ ì¤í¨ (No such service).

### ð¡ ìì¸ ë¶ì (Root Cause)
1.  **Leaked Key Detection**: Google Cloudë ê³µê° ì ì¥ì(Github ë±)ì ìë¡ëë ì´ë ¥ì´ ìë í¤ë¥¼ ìëì¼ë¡ ë¬´í¨íí¨. ëë íë¡ì í¸ ìì²´ê° Abuseë¡ ì¸í´ Flagëìì ê°ë¥ì±.
2.  **Docker Restart Limitations**: `docker restart`ë ì´ë¯¸ ìì±ë ì»¨íì´ëì ì¤ì ì ê·¸ëë¡ ì¬ì©íì¬ íë¡ì¸ì¤ë§ ì¬ììí¨. `.env` ë³ê²½ ì¬í­ì´ë `docker-compose.yml` ë³ê²½ ì¬í­ì ë°ìíë ¤ë©´ ì»¨íì´ëë¥¼ ì¬ìì±í´ì¼ í¨ (`up -d` usage).
3.  **Compose Service Name**: `stolink-fastapi-agent`ë `container_name`ì´ê³ , `docker-compose` ëªë ¹ì´ë `service name`ì¸ `ai-backend`ë¥¼ ì¸ìë¡ ë°ì.

### ð¢ í´ê²°ì± (Solution)

#### 1. Valid API Key íë³´
- ìì í ìë¡ì´ Google ê³ì  ëë Cleaní íë¡ì í¸ìì ì API Key ë°ê¸.
- `.env` íì¼ì ì ì©.

#### 2. Docker Container ì¬ìì± (Re-create)
- `.env` ë³ê²½ ì¬í­ì ë°ìíë ¤ë©´ ë°ëì `up` ëªë ¹ì´ë¥¼ ì¬ì©í´ì¼ í¨ (ê¸°ì¡´ ì»¨íì´ëê° ìì¼ë©´ ì¬ìì±ë¨).
```bash
docker-compose -f docker-compose.standalone.yml up -d ai-backend
```
- `docker restart`ë íê²½ë³ìë¥¼ ê°±ì íì§ ìì!

#### 3. Service Name íì¸
- `docker-compose.yml`ì `services` ì¹ì í¤ê° íì¸ (`ai-backend`).
- ëªë ¹ì´ ì¤í ì `container_name`ì´ ìë `service name` ì¬ì©.

### ð ê´ë ¨ íì¼
- `.env`
- `docker-compose.standalone.yml`
- `debug_embedding.py` (API Key ê²ì¦ì© ì¤í¬ë¦½í¸)

### â ê²°ê³¼
- 4ë²ì§¸ ìëìì ì í¨í API Key íë³´ ì±ê³µ.
- `debug_embedding.py`: Success! Embedding dim: 3072.
- `/api/search/similar`: Status 200 OK.


---

## 21. Embedding Generation - Google API Key ì°¨ë¨ ë° Docker íê²½ ë³ì ê°±ì 

### ð ë ì§
2026-01-03

### ð´ ë¬¸ì  (Problem)
1.  **Google API Key Suspended**: ìë² ë© ìì± ìë ì `403 PERMISSION_DENIED` ëë "API keys with this specific Project ID have been suspended" ì¤ë¥ ë°ì. ì í¤ë¥¼ ë°ê¸ë°ìë ê³§ë°ë¡ ì°¨ë¨ë¨ (Leaked Key ê°ì§).
2.  **Env Var Not Updating**: `.env` íì¼ì ìì íê³  `docker restart`ë¥¼ ìííì¼ë ì»¨íì´ë ë´ë¶ìì ì´ì  í¤(`...NOV_0`)ê° ê³ì ì ì§ë¨.
3.  **Service Name Confusion**: `docker-compose up -d stolink-fastapi-agent` ëªë ¹ ì¤í¨ (No such service).

### ð¡ ìì¸ ë¶ì (Root Cause)
1.  **Leaked Key Detection**: Google Cloudë ê³µê° ì ì¥ì(Github ë±)ì ìë¡ëë ì´ë ¥ì´ ìë í¤ë¥¼ ìëì¼ë¡ ë¬´í¨íí¨. ëë íë¡ì í¸ ìì²´ê° Abuseë¡ ì¸í´ Flagëìì ê°ë¥ì±.
2.  **Docker Restart Limitations**: `docker restart`ë ì´ë¯¸ ìì±ë ì»¨íì´ëì ì¤ì ì ê·¸ëë¡ ì¬ì©íì¬ íë¡ì¸ì¤ë§ ì¬ììí¨. `.env` ë³ê²½ ì¬í­ì´ë `docker-compose.yml` ë³ê²½ ì¬í­ì ë°ìíë ¤ë©´ ì»¨íì´ëë¥¼ ì¬ìì±í´ì¼ í¨ (`up -d` usage).
3.  **Compose Service Name**: `stolink-fastapi-agent`ë `container_name`ì´ê³ , `docker-compose` ëªë ¹ì´ë `service name`ì¸ `ai-backend`ë¥¼ ì¸ìë¡ ë°ì.

### ð¢ í´ê²°ì± (Solution)

#### 1. Valid API Key íë³´
- ìì í ìë¡ì´ Google ê³ì  ëë Cleaní íë¡ì í¸ìì ì API Key ë°ê¸.
- `.env` íì¼ì ì ì©.

#### 2. Docker Container ì¬ìì± (Re-create)
- `.env` ë³ê²½ ì¬í­ì ë°ìíë ¤ë©´ ë°ëì `up` ëªë ¹ì´ë¥¼ ì¬ì©í´ì¼ í¨ (ê¸°ì¡´ ì»¨íì´ëê° ìì¼ë©´ ì¬ìì±ë¨).
```bash
docker-compose -f docker-compose.standalone.yml up -d ai-backend
```
- `docker restart`ë íê²½ë³ìë¥¼ ê°±ì íì§ ìì!

#### 3. Service Name íì¸
- `docker-compose.yml`ì `services` ì¹ì í¤ê° íì¸ (`ai-backend`).
- ëªë ¹ì´ ì¤í ì `container_name`ì´ ìë `service name` ì¬ì©.

### ð ê´ë ¨ íì¼
- `.env`
- `docker-compose.standalone.yml`
- `debug_embedding.py` (API Key ê²ì¦ì© ì¤í¬ë¦½í¸)

### â ê²°ê³¼
- 4ë²ì§¸ ìëìì ì í¨í API Key íë³´ ì±ê³µ.
- `debug_embedding.py`: Success! Embedding dim: 3072.
- `/api/search/similar`: Status 200 OK.


## 21. Python NameError ë° API Quota ì¤ë¥ í´ê²°

### í³ ë ì§
2026-01-04

### í´´ ë¬¸ì  (Problem)
1. **NameError**: "Phase 1 agent failed: name 're' is not defined" ì¤ë¥ë¡ íì´íë¼ì¸ ì¤ë¨.
2. **API Quota**: Gemini ëª¨ë¸ í¸ì¶ ì `429 RESOURCE_EXHAUSTED` ì¤ë¥ ë°ì.

### í¿¡ ìì¸ ë¶ì (Root Cause)
1. `app/agents/extraction/setting.py`ìì `re` ëª¨ëì ì¬ì©íì¼ë import ë¬¸ì´ ëë½ë¨.
2. ëëì íì¤í¸ ì²ë¦¬ ì Gemini APIì ë¶ë¹/ì¼ì¼ í í° íëë¥¼ ì´ê³¼í¨.

### í¿¢ í´ê²°ì± (Solution)
1. **Import ì¶ê°**: `setting.py`ì `import re` ì¶ê°.
2. **ì¬ìë ë¡ì§ ì¤ìí**:
   - `app/agents/llm.py`ì `safe_ainvoke` í¨ì ì¶ê°.
   - Exponential Backoff ìê³ ë¦¬ì¦ ì ì© (ì¤í¨ ì ëê¸° ìê° ì ì§ì  ì¦ê°).
   - ëª¨ë  ìì´ì í¸(`setting.py`, `character/*.py`, `event.py`)ê° `chain.ainvoke` ëì  `safe_ainvoke`ë¥¼ ì¬ì©íëë¡ ë³ê²½.

### í³ ìì ë íì¼
- `app/agents/extraction/setting.py`
- `app/agents/llm.py`
- `app/agents/extraction/character/*.py`
- `app/agents/extraction/event.py`

### â ê²°ê³¼
- íì´íë¼ì¸ ì¤ë¨ ìì´ ìì£¼ ì±ê³µ.
- API Rate Limit ë°ì ì ìëì¼ë¡ ì¬ìëíì¬ ì±ê³µ ì²ë¦¬.

---

## 22. Data Consistency - ìºë¦­í° ë° ê´ê³ ì¶©ë í´ê²°

### í³ ë ì§
2026-01-04

### í´´ ë¬¸ì  (Problem)
1. **ìºë¦­í° ì¤ë³µ**: "The man"ê³¼ "The guest"ê° ë³ê°ì ì¸ë¬¼ë¡ ì¶ì¶ëê±°ë, ëì¼ ì¸ë¬¼ì´ IDë§ ë¤ë¥´ê² ì¤ë³µ ìì±ë¨.
2. **ê´ê³ ëª¨ì**: ëì¼í ë ì¸ë¬¼ ê´ê³ê° íìª½ì "ALLY", ë°ëìª½ì "BETRAYED"ë¡ ì ìë¨.
3. **íì§ ì í**: ì ë¬¸ì ë¡ ì¸í´ `result.json`ì Quality Scoreê° 55ì ì ë¶ê³¼í¨.

### í¿¡ ìì¸ ë¶ì (Root Cause)
1. **LLMì í´ì ëª¨í¸ì±**: ë§¥ë½ì ë°ë¼ í¸ì¹­ì´ ë°ëë ê²ì ë³ê° ì¸ë¬¼ë¡ ì¸ì.
2. **íë¡¬íí¸ ê°ì´ë ë¶ì¡±**: "ìì¬(Suspicion)" ë¨ê³ë¥¼ "ë°°ì (Betrayal)"ì¼ë¡ ê³¼í´ìíê±°ë, ê´ê³ ì í ì ìê° ëªííì§ ììì.

### í¿¢ í´ê²°ì± (Solution)
1. **Identity Agent íë¡¬íí¸ ê°ì **:
   - ë¤ì¤ í¸ì¹­(Aliases) ì²ë¦¬ ê·ì¹ ëªì ("The man" -> "The guest" ì ì£¼ ì´ë¦ ì ì§).
   - ì£¼ì¸ê³µê³¼ ìí¸ìì©íë ëªëªë ì¸ë¬¼ì 'other'ê° ìë 'supporting'ì¼ë¡ ë¶ë¥ ì ë.
2. **Relations Agent íë¡¬íí¸ ê°ì **:
   - `BETRAYED` ê´ê³ íì ì ì ì¶ê° ë° ê°ì´ëë¼ì¸ ì ì (ì¤ì§ì  ë°°ì  íìê° ìì ëë§ ì¬ì©).
   - "ìì¬" ë¨ê³ë `NEUTRAL` ëë `ENEMY` + `private_feeling: DISTRUST`ë¡ ì²ë¦¬íëë¡ ì§ì.

### í³ ìì ë íì¼
- `app/agents/extraction/character/identity.py`
- `app/agents/extraction/character/relations.py`

### â ê²°ê³¼
- **Quality Score**: 98/100 ë¬ì±
- **Consistency Score**: 100/100 (ì¶©ë 0ê±´)
- **ë°ì´í° ì íë**: ìºë¦­í° 7ëª, ì¬ê±´ 55ê°, ë°°ê²½ 5ê° ì ì ì¶ì¶ ë° ì¼ê´ì± íë³´.

---



## 23. Model Optimization - Balanced Load Strategy

### 📅 Date
2026-01-04

### 🔴 Problem
- **TPM Instability**: `gemini-2.0-flash-lite` and `2.5-flash-lite` caused high TPM spikes and rate limiting issues during parallel execution.
- **Load Concentration**: Moving all agents to `Advanced` (Gemini 2.5 Flash) risks hitting the specific rate limit for that model tier due to high concurrency.

### 🟡 Root Cause
- **Lite Models**: While cost-effective, they showed instability under the high-throughput demands of the parallel extraction phase.
- **Single Tier Bottleneck**: Relying solely on `Advanced` for all parallel tasks (Appearance, Personality, Relations, Dialogue, Setting) concentrates too much load on a single quota.

### 🟢 Solution
- **Balanced Tier Strategy**: Distribute the parallel workload between `Advanced` (Gemini 2.5 Flash) and `Premium` (Gemini 3 Flash) to leverage separate rate limit quotas.
- **Tier Reassignment**:
  - **Reasoning Heavy (Premium)**: `Relations`, `Personality`, `Dialogue`, `Identity`. (Use Gemini 3's superior reasoning and separate quota).
  - **Extraction Heavy (Advanced)**: `Appearance`, `Setting`, `Event`. (Use Gemini 2.5 Flash's high speed and context window).

### 📁 Modified Files
- `app/agents/extraction/character/relations.py` (Premium)
- `app/agents/extraction/character/personality.py` (Premium)
- `app/agents/extraction/character/dialogue_mood.py` (Premium)
- `app/agents/extraction/character/appearance.py` (Advanced)
- `app/agents/extraction/setting.py` (Advanced)
- `app/agents/extraction/event.py` (Advanced)

### ✅ Result
- **Optimized Throughput**: Load is split across model tiers, reducing the risk of hitting a single model's rate limit.
- **Stabilized Pipeline**: High-performance models ensure extraction quality and stability.


## 24. Senior Developer Consultation: Scalability Architecture for Large Texts

### 📅 Date
2026-01-04

### 📝 Consultation Summary
From the perspective of a Senior Developer with 20+ years of experience, to process large-scale novels like *Les Misérables* (over 500k words) without issues, the following **4 Key Architectures** must be considered.

The current "Load All -> Chunk -> Parallel Process" approach is efficient for short texts but risks **Memory Explosion, Context Window Overflow, and Data Inconsistency** for massive volumes.

#### 1. 🚀 Streaming Pipeline (Chapter-wise Processing)
**Risk**: Carrying the entire extracted text and results in `AnalysisState` memory is dangerous.
**Proposal**: Introduce **Chapter-wise Processing**.
- Do not load the entire book into the LLM at once. Process it **chapter by chapter using a Queue** (Sequential/Parallel).
- **State Management**: Keep only the 'Current Chapter' and a 'Rolling Summary' in memory. Persist completed data to DB (Neo4j/Postgres) immediately and release memory.

#### 2. 🔗 Global Entity Resolution (Phase 3)
**Risk**: In long novels, the same character is called by hundreds of different names (e.g., Jean Valjean = Mayor Madeleine = Prisoner 24601). Parallel chapter processing may extract them as different people.
**Proposal**: Add **Phase 3: Global Reconciliation**.
- After all chapters are processed, a **dedicated Post-processing Agent** is needed to merge duplicate entities by comparing embeddings of all extracted characters.
- A dedicated LLM Step is required to judge "Are these the same person?".

#### 3. 🧠 RAG-based Dynamic Context
**Risk**: In later chapters, early events are often causes. Passing the full `existing_events` list incurs huge token costs and confuses the LLM.
**Proposal**: Introduce **Vector Search (RAG)**.
- Dynamically inject **only the top 5-10 relevant past events** into the prompt by querying "Find past events related to this incident".
- Enables deep causal reasoning while saving `Context Window`.

#### 4. 📉 Cost & Speed Optimization
**Proposal**:
- **Caching**: Embedding generation is expensive. Cache embedding results in Redis using paragraph hashes as keys.
- **Hierarchical Summarization**: Pre-generate summaries in layers (Chapter -> Volume -> Full Synopsis). Provide "Overall Plot Context" lightly to the LLM during detailed analysis.

### 🏁 Conclusion
You don't need to change everything immediately, but I recommend refactoring little by little with the philosophy of **"Split Data, Process, and Merge (Map-Reduce)"**. In particular, **Entity Resolution** logic will determine the quality of the long-novel service.
