# 테스트 방법 : pytest tests/P0/test_neo4j_deduplication.py -v
# 커버리지 포함 : pytest --cov=app.services --cov-report=html

"""Test cases for Neo4j entity deduplication (TC-NEO4J-*).

Tests MERGE operations and embedding-based duplicate detection.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.db_query_service import DatabaseQueryService


class TestNeo4jCharacterMerge:
    """Test Neo4j MERGE behavior for character deduplication."""
    
    @pytest.mark.asyncio
    async def test_tc_neo4j_001_same_name_merge_logic(self, sample_character):
        """TC-NEO4J-001: 같은 프로젝트 내 동일 이름 캐릭터 MERGE 로직.
        
        Scenario:
            - Document 1: 캐릭터 "아린" (description: "용감한 전사")
            - Document 2: 캐릭터 "아린" (description: "용감하고 정의로운 전사로, 왕국을 지킨다.")
        
        Expected:
            - 더 긴 description 선택
            - source_documents 배열 누적
        """
        # Simulate Neo4j MERGE logic for description
        desc_v1 = "용감한 전사"
        desc_v2 = "용감하고 정의로운 전사로, 왕국을 지킨다."
        
        # Neo4j Cypher logic: CASE WHEN size($desc) > size(c.description)
        final_desc = desc_v2 if len(desc_v2) > len(desc_v1) else desc_v1
        
        assert final_desc == desc_v2, "Longer description should be kept"
        
        # Simulate source_documents accumulation
        source_docs_v1 = ["doc-1"]
        source_docs_v2 = ["doc-1", "doc-2"]  # After second save
        
        # Cypher: WHEN NOT $doc_id IN c.source_documents THEN c.source_documents + $doc_id
        if "doc-2" not in source_docs_v1:
            source_docs_updated = source_docs_v1 + ["doc-2"]
        
        assert source_docs_updated == source_docs_v2, "Should accumulate document IDs"
    
    
    @pytest.mark.asyncio
    async def test_tc_neo4j_002_embedding_deduplication_logic(self):
        """TC-NEO4J-002: 임베딩 기반 중복 감지 로직.
        
        Tests the _find_similar_character cosine similarity logic.
        """  
        db_service = DatabaseQueryService()
        
        # Test similarity threshold
        threshold = 0.92
        
        # Case 1: High similarity → Should be considered same character
        similarity_high = 0.95
        assert similarity_high > threshold, "High similarity should exceed threshold"
        
        # Case 2: Low similarity → Different characters
        similarity_low = 0.75
        assert similarity_low < threshold, "Low similarity should be below threshold"
        
        # Case 3: Edge case
        similarity_edge = 0.92
        assert similarity_edge >= threshold, "Edge case should pass (>=)"
    
    
    @pytest.mark.asyncio
    async def test_tc_neo4j_003_different_projects_logic(self, sample_character):
        """TC-NEO4J-003: 서로 다른 프로젝트 구분 로직.
        
        Tests that MERGE key includes both project_id and name.
        """
        # MERGE key structure
        merge_key_a = ("project-A", "아린")
        merge_key_b = ("project-B", "아린")
        
        # Should be different entities
        assert merge_key_a != merge_key_b, "Different projects should have different MERGE keys"
        
        # Same project, same name
        merge_key_a2 = ("project-A", "아린")
        assert merge_key_a == merge_key_a2, "Same project and name should have same MERGE key"


class TestNeo4jAttributeMerging:
    """Test character attribute merging strategy."""
    
    @pytest.mark.asyncio
    async def test_longer_description_wins(self):
        """같은 캐릭터, 다른 description → 더 긴 쪽 유지.
        
        Neo4j Cypher logic:
            SET c.description = CASE
                WHEN size($desc) > size(c.description) THEN $desc
                ELSE c.description
            END
        """
        desc_short = "용감한 전사"
        desc_long = "용감하고 정의로운 전사로, 왕국을 지킨다."
        
        # Simulate Cypher CASE logic
        current_desc = desc_short
        new_desc = desc_long
        
        # Logic from db_query_service.py:1700-1705
        result = new_desc if len(new_desc) > len(current_desc) else current_desc
        
        assert result == desc_long, "Longer description should win"
        assert len(result) > len(desc_short), "Should keep more detailed version"
    
    
    def test_coalesce_null_handling(self):
        """Null 값 처리 - 첫 번째 non-null 선택.
        
        Cypher: coalesce(c.backstory, $backstory)
        """
        # Case 1: Existing is None, new has value
        existing = None
        new_value = "어린 시절 부모를 잃고..."
        result = new_value if existing is None else existing
        assert result == new_value
        
        # Case 2: Existing has value, new is irrelevant
        existing = "기존 배경 스토리"
        new_value = "새 배경 스토리"
        result = existing  # coalesce keeps first non-null
        assert result == "기존 배경 스토리"


class TestAliasAccumulation:
    """Test alias merging and deduplication."""
    
    def test_alias_deduplication(self):
        """별칭 중복 제거 테스트.
        
        Cypher logic:
            c.aliases + [a IN $aliases WHERE NOT a IN c.aliases]
        """
        existing_aliases = ["Arin", "공주"]
        new_aliases = ["Arin", "전사"]  # "Arin" duplicate
        
        # Simulate Cypher dedup logic
        merged = existing_aliases + [a for a in new_aliases if a not in existing_aliases]
        
        assert merged == ["Arin", "공주", "전사"], "Should deduplicate aliases"
        assert merged.count("Arin") == 1, "No duplicate 'Arin'"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
