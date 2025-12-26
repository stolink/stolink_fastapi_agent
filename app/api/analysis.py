"""Manual analysis trigger API (for testing)."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.schemas.messages import AnalysisTaskMessage, AnalysisContext
from app.services.analysis_service import run_analysis

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


class ManualAnalysisRequest(BaseModel):
    """Request for manual analysis trigger."""
    project_id: str
    document_id: str
    content: str
    callback_url: str = "http://localhost:8080/api/internal/ai/analysis/callback"


@router.post("/trigger")
async def trigger_analysis(request: ManualAnalysisRequest):
    """Manually trigger analysis (for testing without RabbitMQ).
    
    Args:
        request: Analysis request data
        
    Returns:
        Full analysis results including characters, events, relationships, etc.
    """
    import uuid
    
    job_id = str(uuid.uuid4())
    
    # Create task message
    task = AnalysisTaskMessage(
        job_id=job_id,
        project_id=request.project_id,
        document_id=request.document_id,
        content=request.content,
        context=AnalysisContext(),
        callback_url=request.callback_url
    )
    
    try:
        # Run analysis
        result = await run_analysis(task)
        
        return {
            "job_id": job_id,
            "status": "completed",
            "results": result  # Return full results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/debug")
async def debug_llm(request: ManualAnalysisRequest):
    """Debug endpoint to test raw LLM response."""
    from app.agents.llm import get_standard_llm
    
    llm = get_standard_llm()
    
    prompt = f"""다음 텍스트에서 등장하는 캐릭터를 JSON 형식으로 추출하세요.

텍스트: {request.content}

다음 형식으로 응답하세요:
{{
  "characters": [
    {{"name": "캐릭터이름", "role": "protagonist/antagonist/supporting", "traits": ["특성1", "특성2"]}}
  ]
}}
"""
    
    try:
        response = await llm.ainvoke(prompt)
        return {
            "status": "success",
            "raw_response": response.content,
            "response_type": type(response).__name__
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "error_type": type(e).__name__
        }
