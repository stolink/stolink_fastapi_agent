# AI Backend Changes - Spring Team Handoff

**Date**: 2026-01-04  
**Version**: Scalability Architecture Update

This document summarizes the recent changes to the AI Backend that may affect Spring Backend integration.

---

## 1. New: Streaming Architecture with Immediate DB Persistence

### What Changed
The AI server now processes documents in **batches (chapter by chapter)** and saves results to the database **immediately** after each batch, rather than accumulating everything in memory.

### Impact on Spring
**The AI server now writes directly to PostgreSQL and Neo4j during analysis.**

#### Tables Written by AI Server

| Table | Operation | Fields Written |
|-------|-----------|----------------|
| `characters` | UPSERT | `id`, `project_id`, `name`, `role`, `description`, `aliases_json` |
| `events` | UPSERT | `id`, `project_id`, `event_type`, `description`, `chapter`, `sequence_order`, `participants`, `location_ref` |
| `settings` | UPSERT | `id`, `project_id`, `name`, `location_type`, `description` |

#### Required Schema Changes

Ensure these columns exist (or create migration if missing):

```sql
-- characters table
ALTER TABLE characters ADD COLUMN IF NOT EXISTS aliases_json TEXT;

-- events table  
ALTER TABLE events ADD COLUMN IF NOT EXISTS chapter INT DEFAULT 0;
ALTER TABLE events ADD COLUMN IF NOT EXISTS sequence_order INT DEFAULT 0;
ALTER TABLE events ADD COLUMN IF NOT EXISTS participants TEXT; -- JSON array as string
ALTER TABLE events ADD COLUMN IF NOT EXISTS location_ref VARCHAR(255);
```

### Action Required
1. **Option A (Recommended)**: Accept AI writes to production tables. Spring should READ from these tables after callback rather than INSERT from callback payload.
2. **Option B (Future)**: Create `ai_staging_*` tables for AI writes, then migrate to production tables in Spring. (See `FUTURE_TASKS.md`)

---

## 2. New: Redis Dependency for Embedding Cache

### What Changed
Embedding generation now uses Redis to cache results (24-hour TTL). This significantly reduces API costs on repeated or retried analyses.

### Configuration Required

Add to your Docker Compose or environment:

```yaml
redis:
  image: redis:7-alpine
  ports:
    - "6379:6379"
```

Environment variables for AI Backend:
```
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
```

### Action Required
- **None for Spring Backend** (Redis is internal to AI server)
- Ensure Redis is running in your deployment environment

---

## 3. Enhanced: Callback Payload Structure

### Updated Fields in `DocumentAnalysisCallback`

The callback payload now includes additional fields:

```json
{
  "document_id": "uuid",
  "status": "COMPLETED",
  "characters": [...],
  "events": [...],
  "settings": [...],
  "plot_integration": {
    "main_plot": {...},
    "subplots": [...],
    "foreshadowing": [...]
  },
  "consistency_report": {
    "overall_score": 85,
    "issues": [...]
  },
  "validation": {...},
  "processing_time_ms": 12345
}
```

### New Fields

| Field | Type | Description |
|-------|------|-------------|
| `plot_integration` | Object | Plot analysis (only if `requires_deep_analysis=true`) |
| `consistency_report` | Object | Consistency check results |
| `validation` | Object | Validation results |

### Action Required
- Update `AICallbackController` to parse new optional fields
- Store `plot_integration` and `consistency_report` if needed

---

## 4. Important: Data Flow Change

### Before (Old Flow)
```
Spring sends RabbitMQ message
    → AI processes entire document
    → AI sends callback with ALL data
    → Spring saves to DB
```

### After (New Flow)
```
Spring sends RabbitMQ message
    → AI processes batch 1 → Saves to DB immediately
    → AI processes batch 2 → Saves to DB immediately
    → ...
    → AI sends callback (summary only, data already in DB)
    → Spring can READ from DB or use callback payload
```

### Implication
- Data appears in DB **before** callback arrives
- Callback payload is still complete, but DB is the source of truth
- If callback fails, partial data is already persisted (can be recovered)

---

## 5. Enhanced: Event Extraction with Past Context

### What Changed
Event extraction now includes **RAG-based past event retrieval**. When analyzing later chapters, the AI retrieves relevant past events via vector search and includes them in the prompt.

### New Prompt Section
```
=== RELEVANT PAST EVENTS (for causality/continuity) ===
- [E001] Jean Valjean steals bread
- [E005] Bishop Myriel forgives Jean
...
```

### Action Required
- **None** (internal AI improvement)
- Events should have better `prev_event_id` linking and causal relationships

---

## 6. Schema: Ensure Neo4j Properties Exist

The AI server writes to Neo4j with these properties:

### Character Node
```cypher
(:Character {
  id: "uuid",
  project_id: "uuid", 
  name: "Character Name",
  role: "Protagonist"
})
```

### Event Node
```cypher
(:Event {
  id: "uuid",
  project_id: "uuid",
  description: "...",
  chapter: 1
})
```

### Action Required
- Ensure your Neo4j queries/constraints accommodate these properties

---

## 7. Testing Recommendations

### Test 1: Verify DB Writes
1. Send analysis request for a test document
2. **Before callback arrives**, query PostgreSQL:
   ```sql
   SELECT * FROM characters WHERE project_id = 'your-project-id';
   ```
3. Confirm data appears incrementally

### Test 2: Verify Callback
1. Check callback payload contains all expected fields
2. Compare callback data with DB data (should match)

### Test 3: Redis Cache
1. Run same analysis twice
2. Second run should be significantly faster (embeddings cached)

---

## Summary of Action Items

| Priority | Task | Owner |
|----------|------|-------|
| 🔴 High | Verify PostgreSQL schema has required columns | Spring Team |
| 🔴 High | Ensure Redis is in deployment environment | DevOps |
| 🟠 Medium | Update callback handler for new optional fields | Spring Team |
| 🟢 Low | Consider staging table architecture (see FUTURE_TASKS.md) | Both Teams |

---

## Questions?

Contact the AI Backend team for clarification on any of these changes.
