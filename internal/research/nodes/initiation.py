import logging
from typing import List
from pydantic import BaseModel
from ollama import AsyncClient

logger = logging.getLogger(__name__)


class QuestionsResponse(BaseModel):
    questions: List[str]


async def generate_seed_questions(goal: str, template: dict, count: int = 5) -> List[str]:
    """
    Generate initial seed questions based on research goal and template.

    Args:
        goal: Research goal
        template: Template with schema fields
        count: Number of questions to generate (3-5)

    Returns:
        List of seed question texts
    """
    template_fields = template.get("schema_json", {})
    fields_list = ", ".join(template_fields.keys()) if template_fields else "various aspects"
    
    prompt = f"""Generate {count} specific research questions that will help investigate this goal:

Goal: {goal}

The template has the following fields: {fields_list}

Each question should:
1. Be directly related to achieving the research goal
2. Focus on collecting information for one or more of the template fields
3. Be specific and answerable through web research
4. Be phrased as a clear question (not a statement)
5. Help uncover comprehensive information about the topic

Return exactly {count} questions as a JSON list of strings."""

    try:
        client = AsyncClient()
        
        response = await client.chat(
            model="llama3.2",
            messages=[
                {"role": "system", "content": "You are a research assistant that generates focused, specific questions for investigation. Always respond with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            format=QuestionsResponse.model_json_schema()
        )
        
        content = response.get("message", {}).get("content", "")
        import json
        parsed = json.loads(content)
        
        questions = parsed.get("questions", [])
        if len(questions) != count:
            logger.warning(f"Expected {count} questions, got {len(questions)}")
        
        logger.info(f"Generated {len(questions)} seed questions")
        return questions
        
    except Exception as e:
        logger.error(f"Failed to generate seed questions: {e}")
        raise