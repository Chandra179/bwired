import logging
from typing import List
from pydantic import BaseModel
from ollama import AsyncClient

logger = logging.getLogger(__name__)


class QuestionsResponse(BaseModel):
    """
    Pydantic model for structured LLM response containing generated questions.
    
    This model is used with Ollama's structured output feature to ensure
    the LLM returns valid JSON with the expected format.
    """
    questions: List[str]


async def generate_seed_questions(goal: str, template: dict, count: int = 5) -> List[str]:
    """
    Generate initial seed questions based on research goal and template.

    This is the first node in the research pipeline. It uses the LLM to
    create targeted research questions that will guide the subsequent search
    and crawling phases. Questions are aligned with the template's schema
    to ensure extracted facts will match the expected structure.

    Args:
        goal: Research goal or topic to investigate
        template: Template dictionary containing schema_json with field definitions
        count: Number of questions to generate (default: 5)

    Returns:
        List of seed question texts that will be used for initial search

    Raises:
        Exception: If LLM fails to generate or parse response
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