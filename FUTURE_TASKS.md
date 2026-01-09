# Future Tasks

This document outlines architectural improvements and refactoring tasks to be addressed in future iterations.

---

## 1. Separate AI Server DB Writes from Spring Server Tables

### Problem

Currently, the AI server directly writes to Spring's production tables (`characters`, `events`, `settings`) during the streaming analysis pipeline. This creates tight coupling between the two systems.

**Current Flow:**
```
AI Server ---(INSERT/UPSERT)---> PostgreSQL [characters, events, settings tables]
    |
    └---(Callback)---> Spring Server (may duplicate or ignore data)
```

**Issues:**
- **Schema Synchronization**: Any schema change in Spring entities requires corresponding updates to AI server's SQL queries in `db_query_service.py`.
- **Concurrency Conflicts**: Both systems may write to the same row simultaneously.
- **Responsibility Violation**: AI server bypasses Spring's business logic and validation.

### Proposed Solution

Introduce **temporary staging tables** exclusively for AI server writes. Spring server will then validate and migrate data to production tables.

**Target Flow:**
```
AI Server ---(INSERT)---> PostgreSQL [ai_staging_characters, ai_staging_events, ai_staging_settings]
    |
    └---(Callback: "analysis complete")---> Spring Server
                                                |
                                                ├── SELECT FROM ai_staging_*
                                                ├── Apply validation & business rules
                                                └── INSERT INTO [characters, events, settings]
```

### Implementation Steps

#### Phase 1: Create Staging Tables (PostgreSQL)

1. **Create new tables** with a simple, stable schema:
   ```sql
   CREATE TABLE ai_staging_characters (
       id UUID PRIMARY KEY,
       project_id UUID NOT NULL,
       document_id UUID NOT NULL,
       raw_data JSONB NOT NULL,  -- Store entire AI output as JSON
       created_at TIMESTAMP DEFAULT NOW(),
       processed BOOLEAN DEFAULT FALSE
   );

   CREATE TABLE ai_staging_events (
       id UUID PRIMARY KEY,
       project_id UUID NOT NULL,
       document_id UUID NOT NULL,
       raw_data JSONB NOT NULL,
       created_at TIMESTAMP DEFAULT NOW(),
       processed BOOLEAN DEFAULT FALSE
   );

   CREATE TABLE ai_staging_settings (
       id UUID PRIMARY KEY,
       project_id UUID NOT NULL,
       document_id UUID NOT NULL,
       raw_data JSONB NOT NULL,
       created_at TIMESTAMP DEFAULT NOW(),
       processed BOOLEAN DEFAULT FALSE
   );
   ```

2. **Advantages of JSONB**:
   - AI server writes raw extraction output without knowing Spring's entity structure.
   - Schema changes in Spring don't affect AI server.
   - Easy to add new fields without migrations.

#### Phase 2: Modify AI Server (`db_query_service.py`)

1. **Update `save_extraction_result`** to write to staging tables instead:
   ```python
   async def save_extraction_result(self, project_id, document_id, characters, events, settings):
       query = """
           INSERT INTO ai_staging_characters (id, project_id, document_id, raw_data)
           VALUES ($1, $2, $3, $4)
       """
       for char in characters:
           await conn.execute(query, uuid.uuid4(), project_id, document_id, json.dumps(char))
       # Similar for events and settings
   ```

2. **Remove Neo4j direct writes** from AI server (optional, if Spring handles graph sync).

#### Phase 3: Modify Spring Server

1. **Create `AIStagingService`** to process staging data:
   ```java
   @Service
   public class AIStagingService {
       public void processStagedCharacters(UUID documentId) {
           List<AIStagingCharacter> staged = stagingRepo.findByDocumentIdAndProcessedFalse(documentId);
           for (AIStagingCharacter s : staged) {
               CharacterEntity entity = mapper.map(s.getRawData());
               characterRepository.save(entity); // Apply JPA validation
               s.setProcessed(true);
               stagingRepo.save(s);
           }
       }
   }
   ```

2. **Call from AI callback handler**:
   ```java
   @PostMapping("/ai/callback/document-analysis")
   public void handleCallback(@RequestBody DocumentAnalysisCallback callback) {
       aiStagingService.processStagedCharacters(callback.getDocumentId());
       aiStagingService.processStagedEvents(callback.getDocumentId());
       // ...
   }
   ```

#### Phase 4: Cleanup

1. **Add scheduled job** to delete old processed staging data:
   ```java
   @Scheduled(cron = "0 0 3 * * ?") // Daily at 3 AM
   public void cleanupStagingTables() {
       stagingRepo.deleteByProcessedTrueAndCreatedAtBefore(LocalDateTime.now().minusDays(7));
   }
   ```

### Benefits After Migration

| Aspect | Before | After |
|--------|--------|-------|
| Schema coupling | AI and Spring share same table schema | Independent schemas |
| Failure recovery | Partial data may corrupt production | Staging data can be reprocessed |
| Validation | AI bypasses Spring validation | Spring validates all data |
| Debugging | Hard to trace data origin | Clear separation of AI vs Spring data |

### Estimated Effort

- **PostgreSQL DDL**: 1 hour
- **AI Server changes**: 2 hours
- **Spring Server changes**: 4 hours
- **Testing**: 2 hours
- **Total**: ~1 day

---

## 2. Implement Hierarchical Summarization

### Problem

Currently, rolling summaries are maintained during streaming but not persisted as structured hierarchical data.

### Proposed Solution

Create dedicated summarization agents:
- **Chapter Summarizer**: Runs after each chapter extraction
- **Volume Summarizer**: Runs after X chapters or explicit volume markers
- **Synopsis Generator**: Runs at the end of document analysis

Store summaries in dedicated tables:
```sql
CREATE TABLE document_summaries (
    id UUID PRIMARY KEY,
    document_id UUID NOT NULL,
    level VARCHAR(20) NOT NULL, -- 'chapter', 'volume', 'synopsis'
    sequence_order INT,
    summary_text TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Estimated Effort

- **Agent development**: 4 hours
- **DB schema**: 1 hour
- **Integration**: 2 hours
- **Total**: ~1 day

---

## 3. Add Event Embeddings to PostgreSQL pgvector

### Current State

Events have embeddings generated but are stored inline in the callback JSON. They are not queryable via pgvector.

### Proposed Solution

1. Add `embedding` column to `events` table (or staging table):
   ```sql
   ALTER TABLE events ADD COLUMN embedding vector(3072);
   ```

2. Index for similarity search:
   ```sql
   CREATE INDEX events_embedding_idx ON events USING ivfflat (embedding vector_cosine_ops);
   ```

### Estimated Effort

- **Migration**: 1 hour
- **Testing**: 1 hour
