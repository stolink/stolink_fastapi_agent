"""Phase 2-4 자동 전체 테스트"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def run_all_tests():
    """Phase 1-4 전체 자동 테스트"""    
    print("\n" + "🧪"*30)
    print(" 맥락 유지 시스템 - 전체 자동 테스트")
    print("🧪"*30)
    
    results = {}
    
    # Phase 1
    try:
        from tests.auto_test_phase1 import run_phase1_test, find_project
        
        projects = await find_project()
        if projects:
            project_id = projects[0]['id']
            print(f"\n📋 테스트 프로젝트: {project_id[:8]}...")
            results["Phase 1"] = await run_phase1_test(project_id)
        else:
            print("\n❌ 프로젝트를 찾을 수 없습니다")
            return
    except Exception as e:
        print(f"\n❌ Phase 1 실패: {e}")
        results["Phase 1"] = False
    
    if not results.get("Phase 1"):
        print("\n⚠️  Phase 1 실패로 인해 나머지 테스트를 건너뜁니다")
        return
    
    # Phase 2
    try:
        from app.services.context_builder import get_context_builder
        
        print("\n" + "="*60)
        print("Phase 2: 엔티티 중심 검색 자동 테스트")
        print("="*60)
        
        builder = await get_context_builder()
        
        # 첫 번째 프로젝트의 캐릭터 이름을 가져옴
        from app.services.db_query_service import get_db_service
        db = await get_db_service()
        
        char_names = []
        async with db._neo4j_driver.session() as session:
            result = await session.run(
                """
                MATCH (c:Character {projectId: $pid})
                RETURN c.name as name
                LIMIT 3
                """,
                pid=project_id
            )
            async for record in result:
                char_names.append(record["name"])
        
        if not char_names:
            print("   ⚠️  캐릭터가 없어서 건너뜀")
            results["Phase 2"] = None
        else:
            print(f"\n1️⃣ 캐릭터 '{', '.join(char_names)}' 컨텍스트 구축 중...")
            context = await builder.build_context(
                project_id=project_id,
                mentioned_characters=char_names
            )
            
            print(f"   캐릭터 히스토리: {len(context['character_histories'])}개")
            print(f"   관계: {len(context['relationships'])}개")
            
            formatted = builder.format_context_for_llm(context)
            print(f"\n2️⃣ LLM 프롬프트 포맷팅 완료 ({len(formatted)} 문자)")
            
            results["Phase 2"] = True
            print("   ✅ Phase 2 성공!")
            
    except Exception as e:
        print(f"   ❌ Phase 2 실패: {e}")
        import traceback
        traceback.print_exc()
        results["Phase 2"] = False
    
    # Phase 3
    try:
        from app.services.summary_service import get_summary_service
        import uuid
        
        print("\n" + "="*60)
        print("Phase 3: 챕터 요약 자동 테스트")
        print("="*60)
        
        service = await get_summary_service()
        
        # 요약 생성
        print("\n1️⃣ 요약 생성 중...")
        dummy_entities = {
            "characters": [{"name": c} for c in char_names[:3]],
            "events": [{"narrative_summary": "테스트 이벤트"}],
            "settings": [{"name": "테스트 장소"}]
        }
        
        summary = await service.generate_chapter_summary(
            "테스트 챕터 내용",
            dummy_entities
        )
        print(f"   생성된 요약: {summary}")
        
        # 요약 저장
        print("\n2️⃣ 요약 저장 중...")
        test_doc_id = str(uuid.uuid4())
        summary_id = await service.save_summary(
            document_id=test_doc_id,
            project_id=project_id,
            summary=summary,
            key_characters=char_names[:2]
        )
        
        if summary_id:
            print(f"   저장 성공! ID: {summary_id[:8]}...")
            
            # 요약 조회
            print("\n3️⃣ 요약 조회 중...")
            summaries = await service.get_summaries_for_project(project_id)
            print(f"   조회된 요약: {len(summaries)}개")
            
            results["Phase 3"] = True
            print("   ✅ Phase 3 성공!")
        else:
            print("   ⚠️  저장 실패 (테이블 없음?)")
            results["Phase 3"] = None
            
    except Exception as e:
        print(f"   ❌ Phase 3 실패: {e}")
        import traceback
        traceback.print_exc()
        results["Phase 3"] = False
    
    # Phase 4
    try:
        from app.services.hierarchical_context import get_hierarchical_context_manager
        
        print("\n" + "="*60)
        print("Phase 4: 계층적 컨텍스트 자동 테스트")
        print("="*60)
        
        manager = await get_hierarchical_context_manager()
        
        print("\n1️⃣ 계층적 컨텍스트 구축 중...")
        sample_text = " ".join(char_names)
        context_text = await manager.get_context_for_analysis(
            project_id=project_id,
            current_text=sample_text
        )
        
        print(f"   컨텍스트 길이: {len(context_text)} 문자")
        if context_text:
            print(f"\n   미리보기:")
            preview = context_text[:200].replace("\n", "\n   ")
            print("   " + preview + "...")
        
        results["Phase 4"] = True
        print("   ✅ Phase 4 성공!")
        
    except Exception as e:
        print(f"   ❌ Phase 4 실패: {e}")
        import traceback
        traceback.print_exc()
        results["Phase 4"] = False
    
    # 결과 요약
    print("\n" + "="*60)
    print("테스트 결과 요약")
    print("="*60)
    
    for phase, result in results.items():
        if result is True:
            status = "✅ 성공"
        elif result is False:
            status = "❌ 실패"
        else:
            status = "⏭️  건너뜀"
        print(f"{phase}: {status}")
    
    print("\n" + "="*60)
    
    success_count = sum(1 for r in results.values() if r is True)
    total_count = len(results)
    print(f"\n📊 최종 결과: {success_count}/{total_count} 성공")
    
    if success_count == total_count:
        print("\n🎉 모든 테스트 성공!")
    elif success_count > 0:
        print("\n⚠️  일부 테스트 성공")
    else:
        print("\n❌ 모든 테스트 실패")


if __name__ == "__main__":
    asyncio.run(run_all_tests())
