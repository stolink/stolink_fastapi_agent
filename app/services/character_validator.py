"""Character Consistency Validator.

캐릭터 행동의 일관성을 검증합니다.
Phase 6-3 of Context Maintenance System.
"""
import structlog
from typing import Any, Optional

logger = structlog.get_logger()


class CharacterConsistencyValidator:
    """캐릭터 일관성 검증기.
    
    과거 행동 패턴과 성격을 기반으로 새로운 행동의 일관성을 검증합니다.
    """
    
    def __init__(self, db_service, llm_service=None):
        """Initialize with services.
        
        Args:
            db_service: DatabaseQueryService instance
            llm_service: Optional LLM service for validation
        """
        self._db_service = db_service
        self._llm_service = llm_service
    
    async def validate_character_actions(
        self,
        project_id: str,
        extracted_events: list[dict]
    ) -> list[dict]:
        """추출된 이벤트의 캐릭터 행동 일관성 검증.
        
        Args:
            project_id: Project UUID
            extracted_events: 추출된 이벤트 리스트
        
        Returns:
            검증 결과가 추가된 이벤트 리스트
        """
        validated_events = []
        
        for event in extracted_events:
            participants = event.get("participants", [])
            description = event.get("description", "") or event.get("narrative_summary", "")
            
            if not participants or not description:
                validated_events.append(event)
                continue
            
            # 각 참여자별 일관성 검증
            all_warnings = []
            all_suggestions = []
            
            for participant in participants[:3]:  # 최대 3명까지만
                try:
                    validation = await self.validate_character_action(
                        character_name=participant,
                        proposed_action=description,
                        project_id=project_id
                    )
                    
                    if not validation.get("is_consistent", True):
                        all_warnings.extend(validation.get("warnings", []))
                        all_suggestions.extend(validation.get("suggestions", []))
                        
                        logger.warning(
                            "Character inconsistency detected",
                            character=participant,
                            action=description[:50]
                        )
                except Exception as e:
                    logger.error("Validation failed", character=participant, error=str(e))
            
            # 이벤트에 검증 결과 추가
            if all_warnings:
                event["consistency_warnings"] = all_warnings
            if all_suggestions:
                event["consistency_suggestions"] = all_suggestions
            
            validated_events.append(event)
        
        return validated_events
    
    async def validate_character_action(
        self,
        character_name: str,
        proposed_action: str,
        project_id: str
    ) -> dict:
        """개별 캐릭터 행동의 일관성 검증.
        
        Args:
            character_name: 캐릭터 이름
            proposed_action: 제안된 행동 설명
            project_id: Project UUID
        
        Returns:
            {
                "is_consistent": bool,
                "confidence": float,
                "warnings": list[str],
                "suggestions": list[str]
            }
        """
        # 1. 캐릭터 프로필 조회
        profile = await self._get_character_profile(character_name, project_id)
        
        if not profile:
            return {
                "is_consistent": True,  # 프로필 없으면 통과
                "confidence": 0.0,
                "warnings": [],
                "suggestions": []
            }
        
        # 2. 과거 행동 패턴 조회
        past_actions = await self._get_character_actions(character_name, project_id)
        
        # 3. 규칙 기반 간단한 검증
        rule_based_result = self._rule_based_validation(profile, proposed_action)
        
        # 4. LLM 기반 검증 (선택적)
        if self._llm_service and not rule_based_result["is_consistent"]:
            return await self._llm_based_validation(
                character_name, profile, past_actions, proposed_action
            )
        
        return rule_based_result
    
    def _rule_based_validation(
        self,
        profile: dict,
        proposed_action: str
    ) -> dict:
        """규칙 기반 간단한 검증.
        
        Args:
            profile: 캐릭터 프로필
            proposed_action: 제안된 행동
        
        Returns:
            검증 결과
        """
        warnings = []
        suggestions = []
        
        # 성격 키워드 체크
        personality_traits = profile.get("personality", "").lower()
        action_lower = proposed_action.lower()
        
        # 예시: 온화한 캐릭터가 폭력적 행동
        if "온화" in personality_traits or "gentle" in personality_traits:
            if any(word in action_lower for word in ["공격", "때리", "죽이", "attack", "kill"]):
                warnings.append(f"캐릭터는 '온화한' 성격이지만 폭력적 행동을 함")
                suggestions.append("극도로 화가 났거나 불가피한 상황임을 명시하세요")
        
        # 논리적 캐릭터가 충동적 행동
        if "논리" in personality_traits or "logical" in personality_traits:
            if any(word in action_lower for word in ["충동적", "갑자기", "suddenly", "impulsive"]):
                warnings.append(f"캐릭터는 '논리적' 성격이지만 충동적 행동을 함")
                suggestions.append("행동의 논리적 근거를 제시하세요")
        
        is_consistent = len(warnings) == 0
        
        return {
            "is_consistent": is_consistent,
            "confidence": 0.7 if is_consistent else 0.3,
            "warnings": warnings,
            "suggestions": suggestions
        }
    
    async def _llm_based_validation(
        self,
        character_name: str,
        profile: dict,
        past_actions: list[str],
        proposed_action: str
    ) -> dict:
        """LLM 기반 심층 검증."""
        prompt = f"""
캐릭터: {character_name}
성격: {profile.get('personality', 'Unknown')}
과거 행동:
{chr(10).join(f"- {action}" for action in past_actions[:5])}

제안된 새로운 행동:
{proposed_action}

이 행동이 캐릭터와 일관성이 있는지 평가하세요:
1. 일관성 여부 (yes/no)
2. 신뢰도 (0.0-1.0)
3. 경고사항 (있으면)
4. 개선 제안 (있으면)

JSON 형식으로 답변하세요:
{{
    "is_consistent": true/false,
    "confidence": 0.8,
    "warnings": ["경고1", "경고2"],
    "suggestions": ["제안1"]
}}
"""
        
        try:
            response = await self._llm_service.generate(prompt)
            # JSON 파싱 (간단히 구현)
            import json
            result = json.loads(response)
            return result
        except Exception as e:
            logger.error("LLM validation failed", error=str(e))
            return {
                "is_consistent": True,
                "confidence": 0.5,
                "warnings": [],
                "suggestions": []
            }
    
    async def _get_character_profile(
        self,
        character_name: str,
        project_id: str
    ) -> Optional[dict]:
        """캐릭터 프로필 조회."""
        if not self._db_service._neo4j_driver:
            return None
        
        try:
            async with self._db_service._neo4j_driver.session() as session:
                result = await session.run(
                    """
                    MATCH (c:Character {projectId: $pid, name: $name})
                    RETURN c.role as role, c.backstory as backstory,
                           c.profileJson as profile_json
                    """,
                    pid=project_id,
                    name=character_name
                )
                record = await result.single()
                
                if not record:
                    return None
                
                import json
                profile_json = record.get("profile_json")
                profile = json.loads(profile_json) if profile_json else {}
                
                return {
                    "role": record.get("role"),
                    "backstory": record.get("backstory"),
                    "personality": profile.get("personality", "")
                }
        except Exception as e:
            logger.error("Failed to get character profile", error=str(e))
            return None
    
    async def _get_character_actions(
        self,
        character_name: str,
        project_id: str,
        limit: int = 5
    ) -> list[str]:
        """캐릭터의 과거 행동 조회."""
        if not self._db_service._neo4j_driver:
            return []
        
        try:
            async with self._db_service._neo4j_driver.session() as session:
                result = await session.run(
                    """
                    MATCH (c:Character {projectId: $pid, name: $name})-[:PARTICIPATES_IN]->(e:Event)
                    RETURN e.narrativeSummary as summary, e.description as description
                    ORDER BY e.chapter DESC, e.sequenceOrder DESC
                    LIMIT $limit
                    """,
                    pid=project_id,
                    name=character_name,
                    limit=limit
                )
                
                actions = []
                async for record in result:
                    action = record.get("summary") or record.get("description", "")
                    if action:
                        actions.append(action)
                
                return actions
        except Exception as e:
            logger.error("Failed to get character actions", error=str(e))
            return []


# Singleton
_validator: Optional[CharacterConsistencyValidator] = None


async def get_character_validator(db_service=None, llm_service=None) -> CharacterConsistencyValidator:
    """Get or create character validator singleton."""
    global _validator
    
    if _validator is None or db_service is not None:
        if db_service is None:
            from app.services.db_query_service import get_db_service
            db_service = await get_db_service()
        _validator = CharacterConsistencyValidator(db_service, llm_service)
    
    return _validator
