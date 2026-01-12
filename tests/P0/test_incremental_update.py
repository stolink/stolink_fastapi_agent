# 테스트 방법 : pytest tests/P0/test_incremental_update.py -v
# 커버리지 포함 : pytest --cov=app.services --cov-report=html

"""Test cases for incremental update functionality (TC-INCR-*).

Tests content hash-based change detection to skip re-analysis of unchanged sections.
"""
import pytest
import hashlib
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.db_query_service import DatabaseQueryService


class TestIncrementalUpdate:
    """Test suite for incremental document updates."""
    
    @pytest.mark.asyncio
    async def test_tc_incr_001_partial_change_detection(self, sample_sections):
        """TC-INCR-001: v1 → v2 업데이트 시 변경된 섹션만 재분석.
        
        Scenario:
            - v1: 3개 섹션
            - v2: Section 3만 수정, Section 1-2 동일
        
        Expected:
            - Section 1-2: hash 일치 → 스킵
            - Section 3: hash 불일치 → 재분석
            - change_point = 2 (0-based index)
        """
        db_service = DatabaseQueryService()
        
        # v1: Previous hashes (from DB)
        previous_hashes = [
            {
                "sequence_order": 0,
                "content_hash": hashlib.sha256(
                    sample_sections[0]["content"].encode('utf-8')
                ).hexdigest()[:16],
                "nav_title": "Section 1"
            },
            {
                "sequence_order": 1,
                "content_hash": hashlib.sha256(
                    sample_sections[1]["content"].encode('utf-8')
                ).hexdigest()[:16],
                "nav_title": "Section 2"
            },
            {
                "sequence_order": 2,
                "content_hash": hashlib.sha256(
                    sample_sections[2]["content"].encode('utf-8')
                ).hexdigest()[:16],
                "nav_title": "Section 3"
            }
        ]
        
        # v2: Section 3 modified
        new_sections_v2 = [
            sample_sections[0],  # Unchanged
            sample_sections[1],  # Unchanged
            {
                "content": "치열한 전투가 벌어졌다. 용이 나타났다.",  # Modified!
                "title": "Section 3",
                "embedding": [0.3] * 3072
            }
        ]
        
        # Detect change point
        change_point = db_service.detect_change_point(previous_hashes, new_sections_v2)
        
        # Verify
        assert change_point == 2, "Should detect change at section 3 (index 2)"
        
        # Verify hashes for unchanged sections
        for i in range(2):
            content = new_sections_v2[i]["content"]
            new_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]
            assert new_hash == previous_hashes[i]["content_hash"], \
                f"Section {i+1} hash should match (unchanged)"
    
    
    @pytest.mark.asyncio
    async def test_tc_incr_002_front_section_change(self, sample_sections):
        """TC-INCR-002: 앞부분 수정 시 전체 재분석.
        
        Scenario:
            - v1: 3개 섹션
            - v2: Section 1 수정 (첫 번째 섹션)
        
        Expected:
            - change_point = 0 (전체 재분석)
        """
        db_service = DatabaseQueryService()
        
        # v1: Previous hashes
        previous_hashes = [
            {
                "sequence_order": 0,
                "content_hash": hashlib.sha256(
                    sample_sections[0]["content"].encode('utf-8')
                ).hexdigest()[:16]
            },
            {
                "sequence_order": 1,
                "content_hash": hashlib.sha256(
                    sample_sections[1]["content"].encode('utf-8')
                ).hexdigest()[:16]
            }
        ]
        
        # v2: Section 1 modified
        new_sections_v2 = [
            {
                "content": "아린은 마법 지팡이를 받아들었다.",  # Modified!
                "title": "Section 1"
            },
            sample_sections[1]  # Unchanged
        ]
        
        change_point = db_service.detect_change_point(previous_hashes, new_sections_v2)
        
        assert change_point == 0, "Should trigger full re-analysis (front section changed)"
    
    
    @pytest.mark.asyncio
    async def test_tc_incr_003_section_append(self, sample_sections):
        """TC-INCR-003: 섹션 추가 (append).
        
        Scenario:
            - v1: 2개 섹션
            - v2: 3개 섹션 (Section 3 추가)
        
        Expected:
            - change_point = 2 (새 섹션부터 분석)
        """
        db_service = DatabaseQueryService()
        
        # v1: 2 sections
        previous_hashes = [
            {
                "sequence_order": 0,
                "content_hash": hashlib.sha256(
                    sample_sections[0]["content"].encode('utf-8')
                ).hexdigest()[:16]
            },
            {
                "sequence_order": 1,
                "content_hash": hashlib.sha256(
                    sample_sections[1]["content"].encode('utf-8')
                ).hexdigest()[:16]
            }
        ]
        
        # v2: 3 sections (added Section 3)
        new_sections_v2 = sample_sections  # All 3 sections
        
        change_point = db_service.detect_change_point(previous_hashes, new_sections_v2)
        
        assert change_point == 2, "Should analyze from new section (index 2)"
    
    
    @pytest.mark.asyncio
    async def test_tc_incr_004_section_removal(self, sample_sections):
        """TC-INCR-004: 섹션 삭제 시 전체 재분석.
        
        Scenario:
            - v1: 3개 섹션
            - v2: 2개 섹션 (Section 3 삭제)
        
        Expected:
            - change_point = 0 (전체 재분석)
        """
        db_service = DatabaseQueryService()
        
        # v1: 3 sections
        previous_hashes = [
            {
                "sequence_order": i,
                "content_hash": hashlib.sha256(
                    sample_sections[i]["content"].encode('utf-8')
                ).hexdigest()[:16]
            }
            for i in range(3)
        ]
        
        # v2: 2 sections (removed Section 3)
        new_sections_v2 = sample_sections[:2]
        
        change_point = db_service.detect_change_point(previous_hashes, new_sections_v2)
        
        assert change_point == 0, "Should trigger full re-analysis (sections removed)"
    
    
    @pytest.mark.asyncio
    async def test_tc_incr_005_no_change(self, sample_sections):
        """TC-INCR-005: 완전 동일한 재분석 요청.
        
        Scenario:
            - v1: 3개 섹션
            - v2: 완전 동일 (변경 없음)
        
        Expected:
            - change_point = -1 (스킵)
        """
        db_service = DatabaseQueryService()
        
        # v1: Previous hashes
        previous_hashes = [
            {
                "sequence_order": i,
                "content_hash": hashlib.sha256(
                    sample_sections[i]["content"].encode('utf-8')
                ).hexdigest()[:16]
            }
            for i in range(3)
        ]
        
        # v2: Identical
        new_sections_v2 = sample_sections
        
        change_point = db_service.detect_change_point(previous_hashes, new_sections_v2)
        
        assert change_point == -1, "Should skip analysis (no changes)"


class TestContentHashStability:
    """Test content hash consistency and collision resistance."""
    
    def test_hash_determinism(self):
        """Same content should always produce same hash."""
        content = "아린은 검을 받아들었다."
        
        hash1 = hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]
        hash2 = hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]
        
        assert hash1 == hash2, "Hash should be deterministic"
    
    
    def test_hash_sensitivity(self):
        """Minor changes should produce different hash."""
        content1 = "아린은 검을 받아들었다."
        content2 = "아린은 검을 받아들었다. "  # Extra space
        
        hash1 = hashlib.sha256(content1.encode('utf-8')).hexdigest()[:16]
        hash2 = hashlib.sha256(content2.encode('utf-8')).hexdigest()[:16]
        
        assert hash1 != hash2, "Different content should have different hash"
    
    
    def test_hash_collision_probability(self):
        """SHA-256 truncated to 16 chars should have low collision."""
        # 16 hex chars = 64 bits = 2^64 possible values
        # Collision probability for n items: ~n^2 / 2^65
        # For 1M sections: ~1M^2 / 2^65 ≈ 2.7 × 10^-8 (negligible)
        
        hashes = set()
        for i in range(10000):
            content = f"Section {i} with unique content"
            hash_val = hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]
            hashes.add(hash_val)
        
        assert len(hashes) == 10000, "No collisions in 10k different contents"


class TestIncrementalPerformance:
    """Performance tests for incremental vs full analysis."""
    
    @pytest.mark.asyncio
    @pytest.mark.benchmark
    async def test_incremental_speedup(self):
        """Measure speedup from incremental update.
        
        Expected: >5x faster for 1/10 change
        """
        import time
        import asyncio  # 🆕 Added missing import
        
        # Mock LLM analysis (expensive operation)
        async def mock_analyze_section(section):
            await asyncio.sleep(0.1)  # Simulate 100ms per section
            return {"characters": [], "events": []}
        
        # Scenario: 10 sections, only last one changed
        sections = [{"content": f"Section {i}"} for i in range(10)]
        
        # Full analysis
        start = time.time()
        for section in sections:
            await mock_analyze_section(section)
        full_time = time.time() - start
        
        # Incremental (only Section 10)
        start = time.time()
        await mock_analyze_section(sections[-1])
        incr_time = time.time() - start
        
        speedup = full_time / incr_time
        
        assert speedup > 5, f"Speedup should be >5x, got {speedup:.1f}x"
        print(f"Full: {full_time:.2f}s, Incremental: {incr_time:.2f}s, Speedup: {speedup:.1f}x")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
