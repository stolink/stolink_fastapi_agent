"""DB 마이그레이션: document_summaries 테이블 생성"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.db_query_service import get_db_service


async def create_table():
    """document_summaries 테이블 생성"""
    sql = """
    CREATE TABLE IF NOT EXISTS document_summaries (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        document_id UUID NOT NULL,
        project_id UUID NOT NULL,
        level INT NOT NULL DEFAULT 3,
        summary TEXT NOT NULL,
        key_characters TEXT[] DEFAULT '{}',
        key_events TEXT[] DEFAULT '{}',
        created_at TIMESTAMP DEFAULT NOW(),
        
        UNIQUE(document_id, level)
    );

    CREATE INDEX IF NOT EXISTS idx_summaries_project_level 
    ON document_summaries(project_id, level);
    """
    
    db = await get_db_service()
    
    if not db._pg_pool:
        print("❌ PostgreSQL 연결 실패")
        return False
    
    try:
        async with db._pg_pool.acquire() as conn:
            await conn.execute(sql)
        print("✅ document_summaries 테이블 생성 완료!")
        return True
    except Exception as e:
        if "already exists" in str(e):
            print("✅ document_summaries 테이블이 이미 존재합니다")
            return True
        print(f"❌ 테이블 생성 실패: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(create_table())
    sys.exit(0 if success else 1)
