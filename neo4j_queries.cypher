// =============================================
// Neo4j 전체 데이터 조회 쿼리
// =============================================
// 실행 방법:
//   1. Neo4j Browser (http://localhost:7474) 에서 실행
//   2. 또는 docker exec로 실행:
//      docker exec stolink-neo4j cypher-shell -u neo4j -p "stolink123" "쿼리내용"
// =============================================
// =============================================
// 1. 모든 Character 노드 조회
// =============================================
MATCH (c:Character)
RETURN c.characterId, c.name, c.role, c.projectId
ORDER BY c.projectId, c.name;

// =============================================
// 2. 모든 Event 노드 조회
// =============================================
MATCH (e:Event)
RETURN e.eventId, e.description, e.chapter, e.projectId
ORDER BY e.projectId, e.chapter, e.eventId;

// =============================================
// 3. 모든 Character 간 관계 조회 (ALLY, ENEMY 등)
// =============================================
MATCH (a:Character)-[r]->(b:Character)
RETURN
  a.name AS source,
  type(r) AS relationship_type,
  r.description AS description,
  r.strength AS strength,
  b.name AS target,
  a.projectId AS projectId
ORDER BY a.projectId, a.name;

// =============================================
// 4. 모든 PARTICIPATES_IN 관계 조회 (캐릭터 → 이벤트)
// =============================================
MATCH (c:Character)-[r:PARTICIPATES_IN]->(e:Event)
RETURN
  c.name AS character_name,
  e.eventId AS event_id,
  e.description AS event_description,
  c.projectId AS projectId
ORDER BY c.projectId, e.eventId, c.name;

// =============================================
// 5. 이벤트별 참여자 집계
// =============================================
MATCH (c:Character)-[:PARTICIPATES_IN]->(e:Event)
RETURN
  e.eventId AS event_id,
  e.description AS event_description,
  collect(c.name) AS participants,
  e.projectId AS projectId
ORDER BY e.projectId, e.eventId;

// =============================================
// 6. 전체 그래프 시각화 (모든 노드와 관계)
// =============================================
MATCH (n)-[r]->(m)
RETURN n, r, m
LIMIT 100;

// =============================================
// 7. 특정 프로젝트 데이터만 조회 (PROJECT_ID 교체 필요)
// =============================================
MATCH (c:Character {projectId: "YOUR_PROJECT_ID"})
RETURN c;

MATCH (e:Event {projectId: "YOUR_PROJECT_ID"})
RETURN e;

// =============================================
// 8. 통계 정보
// =============================================
MATCH (c:Character)
WITH count(c) AS character_count
MATCH (e:Event)
WITH character_count, count(e) AS event_count
MATCH ()-[r:PARTICIPATES_IN]->()
WITH character_count, event_count, count(r) AS participates_count
MATCH (a:Character)-[rel]->(b:Character)
RETURN
  character_count,
  event_count,
  participates_count,
  count(rel) AS character_relations;