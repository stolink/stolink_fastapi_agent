"""자동 테스트 실행 스크립트 - Phase 1"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.db_query_service import get_db_service


async def find_project():
    """Neo4j에서 프로젝트 찾기"""
    db = await get_db_service()
    
    if not db._neo4j_driver:
        print("❌ Neo4j 연결 실패")
        return None
    
    try:
        async with db._neo4j_driver.session() as session:
            result = await session.run(
                """
                MATCH (c:Character)
                RETURN DISTINCT c.projectId as pid, count(c) as char_count
                ORDER BY char_count DESC
                LIMIT 5
                """
            )
            projects = []
            async for record in result:
                projects.append({
                    "id": record["pid"],
                    "character_count": record["char_count"]
                })
            
            return projects
    except Exception as e:
        print(f"❌ 프로젝트 조회 실패: {e}")
        return None


async def run_phase1_test(project_id):
    """Phase 1 테스트 실행"""
    print("\n" + "="*60)
    print("Phase 1: 적응형 RAG 자동 테스트")
    print("="*60)
    
    db = await get_db_service()
    
    try:
        # 1. 프로젝트 통계
        print(f"\n📊 프로젝트: {project_id}")
        print("\n1️⃣ 프로젝트 통계 조회 중...")
        stats = await db.get_project_stats(project_id)
        print(f"   캐릭터: {stats['character_count']}명")
        print(f"   이벤트: {stats['event_count']}개")
        print(f"   장소: {stats['setting_count']}개")
        
        # 2. 적응형 top_k
        print("\n2️⃣ 적응형 top_k 계산 중...")
        top_k = await db.get_adaptive_top_k(project_id)
        print(f"   기본 top_k: 10")
        print(f"   ✨ 계산된 top_k: {top_k}")
        
        if top_k > 10:
            print(f"   → 분량이 많아서 top_k가 {top_k - 10} 증가했습니다!")
        
        # 3. 실제 RAG 검색
        print("\n3️⃣ 적응형 RAG 검색 테스트 중...")
        result = await db.retrieve_relevant_history(
            project_id,
            [{"name": "테스트"}],
            [{"description": "테스트"}],
            top_k=None  # 적응형 사용
        )
        print(f"   실제 사용된 top_k: {result.get('top_k_used', 0)}")
        print(f"   검색 수행됨: {result.get('search_performed', False)}")
        
        print("\n" + "="*60)
        print("✅ Phase 1 테스트 성공!")
        print("="*60)
        return True
        
    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    print("\n🚀 맥락 유지 시스템 - 자동 테스트")
    print("="*60)
    
    # 1. 프로젝트 찾기
    print("\n🔍 Neo4j에서 프로젝트 검색 중...")
    projects = await find_project()
    
    if not projects:
        print("\n❌ 사용 가능한 프로젝트를 찾을 수 없습니다.")
        print("   Neo4j에 데이터가 있는지 확인하세요.")
        return
    
    print(f"\n✅ {len(projects)}개 프로젝트 발견!")
    for i, proj in enumerate(projects, 1):
        print(f"   {i}. {proj['id'][:8]}... (캐릭터: {proj['character_count']}명)")
    
    # 2. 첫 번째 프로젝트로 테스트
    selected = projects[0]
    print(f"\n→ 테스트 대상: {selected['id']}")
    
    # 3. Phase 1 실행
    success = await run_phase1_test(selected['id'])
    
    if success:
        print("\n💡 다음 단계:")
        print("   Phase 2-4 테스트: python tests/test_context_maintenance.py")
    
    return success


if __name__ == "__main__":
    asyncio.run(main())
