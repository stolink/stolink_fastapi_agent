"""
맥락 유지 시스템 테스트 스크립트

Phase 1-4 기능을 순차적으로 테스트합니다.
"""
import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.db_query_service import get_db_service
from app.services.context_builder import get_context_builder
from app.services.summary_service import get_summary_service
from app.services.hierarchical_context import get_hierarchical_context_manager


async def test_phase1_adaptive_rag():
    """Phase 1: 적응형 RAG 테스트"""
    print("\n" + "="*60)
    print("Phase 1: 적응형 RAG 테스트")
    print("="*60)
    
    db = await get_db_service()
    
    # 실제 프로젝트 ID로 변경 필요
    project_id = input("테스트할 프로젝트 ID를 입력하세요: ").strip()
    
    if not project_id:
        print("❌ 프로젝트 ID가 필요합니다")
        return False
    
    try:
        # 1. 프로젝트 통계 조회
        print("\n1️⃣ 프로젝트 통계 조회...")
        stats = await db.get_project_stats(project_id)
        print(f"   캐릭터: {stats['character_count']}명")
        print(f"   이벤트: {stats['event_count']}개")
        print(f"   장소: {stats['setting_count']}개")
        
        # 2. 적응형 top_k 계산
        print("\n2️⃣ 적응형 top_k 계산...")
        top_k = await db.get_adaptive_top_k(project_id)
        print(f"   계산된 top_k: {top_k}")
        
        # 3. RAG 검색 (적응형 top_k 사용)
        print("\n3️⃣ 적응형 RAG 검색...")
        dummy_chars = [{"name": "테스트캐릭터"}]
        dummy_events = [{"description": "테스트 이벤트"}]
        result = await db.retrieve_relevant_history(
            project_id, 
            dummy_chars, 
            dummy_events,
            top_k=None  # None이면 적응형 사용
        )
        print(f"   사용된 top_k: {result.get('top_k_used', 0)}")
        print(f"   ✅ Phase 1 성공!")
        return True
        
    except Exception as e:
        print(f"   ❌ Phase 1 실패: {e}")
        return False


async def test_phase2_entity_context():
    """Phase 2: 엔티티 중심 컨텍스트 테스트"""
    print("\n" + "="*60)
    print("Phase 2: 엔티티 중심 검색 테스트")
    print("="*60)
    
    project_id = input("테스트할 프로젝트 ID를 입력하세요: ").strip()
    
    if not project_id:
        print("❌ 프로젝트 ID가 필요합니다")
        return False
    
    char_names = input("테스트할 캐릭터 이름들 (쉼표 구분): ").strip()
    
    if not char_names:
        print("❌ 캐릭터 이름이 필요합니다")
        return False
    
    char_list = [name.strip() for name in char_names.split(",")]
    
    try:
        builder = await get_context_builder()
        
        print(f"\n1️⃣ '{', '.join(char_list)}' 컨텍스트 구축 중...")
        context = await builder.build_context(
            project_id=project_id,
            mentioned_characters=char_list,
            max_events_per_char=5,
            max_relationships=10
        )
        
        print(f"\n결과:")
        print(f"   캐릭터 히스토리: {len(context['character_histories'])}개")
        print(f"   관계: {len(context['relationships'])}개")
        print(f"   장소 컨텍스트: {len(context['setting_contexts'])}개")
        
        # 포맷팅 테스트
        print(f"\n2️⃣ LLM 프롬프트 포맷팅...")
        formatted = builder.format_context_for_llm(context)
        print(f"   포맷된 텍스트 길이: {len(formatted)} 문자")
        if formatted:
            print(f"\n   미리보기:")
            print("   " + formatted[:200].replace("\n", "\n   ") + "...")
        
        print(f"\n   ✅ Phase 2 성공!")
        return True
        
    except Exception as e:
        print(f"   ❌ Phase 2 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_phase3_summary():
    """Phase 3: 챕터 요약 테스트"""
    print("\n" + "="*60)
    print("Phase 3: 챕터 요약 테스트")
    print("="*60)
    
    service = await get_summary_service()
    
    print("\n⚠️  주의: 이 테스트는 document_summaries 테이블이 필요합니다.")
    proceed = input("계속하시겠습니까? (y/n): ").strip().lower()
    
    if proceed != 'y':
        print("   ⏭️  Phase 3 건너뜀")
        return None
    
    try:
        # 1. 요약 생성 테스트 (LLM 없이)
        print("\n1️⃣ 요약 생성 테스트...")
        dummy_content = "테스트용 챕터 내용입니다."
        dummy_entities = {
            "characters": [{"name": "캐릭터A"}, {"name": "캐릭터B"}],
            "events": [{"narrative_summary": "중요한 사건 발생"}],
            "settings": [{"name": "어둠의 숲"}]
        }
        
        summary = await service.generate_chapter_summary(
            dummy_content,
            dummy_entities
        )
        print(f"   생성된 요약: {summary}")
        
        # 2. 요약 저장 테스트
        project_id = input("\n프로젝트 ID (테스트용): ").strip()
        document_id = input("문서 ID (테스트용): ").strip()
        
        if project_id and document_id:
            print(f"\n2️⃣ 요약 저장 중...")
            summary_id = await service.save_summary(
                document_id=document_id,
                project_id=project_id,
                summary=summary,
                key_characters=["캐릭터A", "캐릭터B"]
            )
            
            if summary_id:
                print(f"   저장 성공! ID: {summary_id}")
                
                # 3. 요약 조회 테스트
                print(f"\n3️⃣ 요약 조회 중...")
                summaries = await service.get_summaries_for_project(project_id)
                print(f"   조회된 요약: {len(summaries)}개")
                
                print(f"\n   ✅ Phase 3 성공!")
                return True
            else:
                print(f"   ⚠️  저장 실패 (테이블 없음?)")
                return None
        else:
            print(f"   ⏭️  저장 테스트 건너뜀")
            return None
            
    except Exception as e:
        print(f"   ❌ Phase 3 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_phase4_hierarchical():
    """Phase 4: 계층적 컨텍스트 테스트"""
    print("\n" + "="*60)
    print("Phase 4: 계층적 컨텍스트 테스트")
    print("="*60)
    
    print("\n⚠️  주의: Phase 3이 완료되어야 합니다.")
    proceed = input("계속하시겠습니까? (y/n): ").strip().lower()
    
    if proceed != 'y':
        print("   ⏭️  Phase 4 건너뜀")
        return None
    
    try:
        manager = await get_hierarchical_context_manager()
        
        project_id = input("\n프로젝트 ID: ").strip()
        current_text = input("현재 분석 중인 텍스트 (샘플): ").strip()
        
        if not project_id or not current_text:
            print("   ❌ 프로젝트 ID와 텍스트가 필요합니다")
            return False
        
        print(f"\n1️⃣ 계층적 컨텍스트 구축 중...")
        context_text = await manager.get_context_for_analysis(
            project_id=project_id,
            current_text=current_text
        )
        
        print(f"\n결과:")
        print(f"   컨텍스트 길이: {len(context_text)} 문자")
        
        if context_text:
            print(f"\n   미리보기:")
            preview = context_text[:300].replace("\n", "\n   ")
            print("   " + preview + "...")
        else:
            print("   (비어있음 - 요약이 아직 없을 수 있음)")
        
        print(f"\n   ✅ Phase 4 성공!")
        return True
        
    except Exception as e:
        print(f"   ❌ Phase 4 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """전체 테스트 실행"""
    print("\n" + "🧪"*30)
    print(" 맥락 유지 시스템 테스트")
    print("🧪"*30)
    
    print("\n선택:")
    print("1. Phase 1만 테스트 (적응형 RAG)")
    print("2. Phase 2만 테스트 (엔티티 중심 검색)")
    print("3. Phase 3만 테스트 (챕터 요약)")
    print("4. Phase 4만 테스트 (계층적 컨텍스트)")
    print("5. 전체 테스트 (1→2→3→4)")
    
    choice = input("\n선택 (1-5): ").strip()
    
    results = {}
    
    if choice == "1":
        results["Phase 1"] = await test_phase1_adaptive_rag()
    elif choice == "2":
        results["Phase 2"] = await test_phase2_entity_context()
    elif choice == "3":
        results["Phase 3"] = await test_phase3_summary()
    elif choice == "4":
        results["Phase 4"] = await test_phase4_hierarchical()
    elif choice == "5":
        results["Phase 1"] = await test_phase1_adaptive_rag()
        results["Phase 2"] = await test_phase2_entity_context()
        results["Phase 3"] = await test_phase3_summary()
        results["Phase 4"] = await test_phase4_hierarchical()
    else:
        print("❌ 잘못된 선택입니다")
        return
    
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


if __name__ == "__main__":
    asyncio.run(main())
