import asyncio
import os
import sys

# Add project root to sys.path
sys.path.append(os.getcwd())

from app.agents.extraction.setting import setting_extraction_node
from app.agents.extraction.event import event_extraction_node

async def test():
    print("Testing Setting Extraction...")
    state = {
        "content": "아린은 어두운 숲에서 검을 들고 서 있었다. 숲은 안개로 가득했고 달빛이 희미하게 비쳤다.",
        "retry_count": 0,
        "consistency_report": {}
    }
    
    try:
        # Mocking LLM or running real one? Assuming user has .env set up.
        setting_result = await setting_extraction_node(state)
        settings = setting_result.get("extracted_settings", [])
        if settings:
            s = settings[0]
            print(f"Setting Output Keys: {list(s.keys())}")
            print(f"Location Name: {s.get('location_name')}")
            print(f"Lighting: {s.get('lighting')}")
            
            # Validation
            if "location_name" in s:
                print("✅ Field 'location_name' exists")
            else:
                print("❌ Field 'location_name' MISSING")
                
            if "lighting" in s:
                print("✅ Field 'lighting' exists (Correct keys used)")
            elif "lighting_description" in s:
                print("⚠️ Field 'lighting_description' found (Legacy key used)")
            
        else:
            print("❌ No settings extracted")

    except Exception as e:
        print(f"❌ Setting Extraction Failed: {e}")

    print("\nTesting Event Extraction...")
    try:
        # Need available chars/settings for context
        state["extracted_characters"] = [{"name": "아린"}]
        state["extracted_settings"] = [{"name": "Dark Forest"}]
        
        event_result = await event_extraction_node(state)
        events = event_result.get("extracted_events", [])
        if events:
            e = events[0]
            print(f"Event Output Keys: {list(e.keys())}")
            print(f"Description: {e.get('description')}")
            
            if "description" in e:
                print("✅ Field 'description' exists")
            else:
                print("❌ Field 'description' MISSING")
        else:
            print("❌ No events extracted")
            
    except Exception as e:
        print(f"❌ Event Extraction Failed: {e}")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(test())
