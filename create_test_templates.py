import asyncio
import sys
sys.path.append('/home/mando/Work/bwired')

from internal.storage.client import DatabaseClient
from internal.config import load_config

async def create_test_templates():
    """Create test templates in the database"""
    
    config = load_config("config.yaml")
    
    db_client = DatabaseClient(
        database_url=config.postgres.url,
        pool_size=config.postgres.pool_size,
        max_overflow=config.postgres.max_overflow
    )
    
    await db_client.init_db()
    
    templates = [
        {
            "name": "academic_paper",
            "description": "Template for academic research papers",
            "schema_json": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "authors": {"type": "array", "items": {"type": "string"}},
                    "publication_date": {"type": "string"},
                    "abstract": {"type": "string"},
                    "key_findings": {"type": "array", "items": {"type": "string"}},
                    "methodology": {"type": "string"},
                    "conclusions": {"type": "string"}
                }
            }
        },
        {
            "name": "technology_analysis",
            "description": "Template for technology trend analysis",
            "schema_json": {
                "type": "object",
                "properties": {
                    "technology_name": {"type": "string"},
                    "description": {"type": "string"},
                    "current_state": {"type": "string"},
                    "key_players": {"type": "array", "items": {"type": "string"}},
                    "use_cases": {"type": "array", "items": {"type": "string"}},
                    "challenges": {"type": "array", "items": {"type": "string"}},
                    "future_outlook": {"type": "string"}
                }
            }
        },
        {
            "name": "market_research",
            "description": "Template for market research analysis",
            "schema_json": {
                "type": "object",
                "properties": {
                    "market_name": {"type": "string"},
                    "market_size": {"type": "string"},
                    "growth_rate": {"type": "string"},
                    "key_competitors": {"type": "array", "items": {"type": "string"}},
                    "market_segments": {"type": "array", "items": {"type": "string"}},
                    "trends": {"type": "array", "items": {"type": "string"}},
                    "opportunities": {"type": "array", "items": {"type": "string"}}
                }
            }
        }
    ]
    
    print("Creating test templates...")
    for template_data in templates:
        template = await db_client.create_template(
            name=template_data["name"],
            description=template_data["description"],
            schema_json=template_data["schema_json"]
        )
        print(f"✓ Created template: {template_data['name']} (ID: {template.id})")
    
    print("\nYou can now use these template IDs in your API requests!")
    
    await db_client.close()

if __name__ == "__main__":
    asyncio.run(create_test_templates())
