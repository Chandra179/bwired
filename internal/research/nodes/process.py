import logging
import json
from typing import Dict, Any
from pydantic import BaseModel
from ollama import AsyncClient
from internal.config import load_config

logger = logging.getLogger(__name__)


async def extract_facts(markdown: str, schema_model: type[BaseModel]) -> Dict[str, Any]:
    """
    Extract structured facts from markdown using Ollama with structured output.

    This is the core function for the Process node. It uses LLM with
    structured output (via Ollama's format parameter) to extract
    information from markdown according to a dynamic schema template.
    The extracted facts are stored in PostgreSQL as JSONB for flexible querying.

    Args:
        markdown: Markdown content to process and extract from
        schema_model: Dynamic Pydantic model created from template's schema_json

    Returns:
        Structured facts as JSONB-compatible dictionary matching schema structure

    Raises:
        ValueError: If LLM response cannot be parsed as valid JSON
        Exception: If LLM fails to generate a response
    """
    config = load_config()
    client = AsyncClient()

    model_name = "llama3.2"
    if config and config.llm:
        model_name = config.llm.model

    schema_info = schema_model.model_json_schema()
    fields_desc = ", ".join(schema_info.get("properties", {}).keys())

    prompt = f"""Extract structured information from the following markdown content.

Field types to extract:
{fields_desc}

Content to analyze:
{markdown}

Instructions:
1. Extract relevant information for each field
2. If information for a field is not found, use null or empty values as appropriate
3. For list fields, extract all relevant items
4. For nested fields, extract the complete sub-structure
5. Only extract information explicitly stated in the text
6. Do not make up or infer information not present in the text

Return the extracted data in the specified JSON format."""

    content = ""
    try:
        response = await client.chat(
            model=model_name,
            messages=[
                {
                    "role": "system",
                    "content": "You are a precise information extractor. Extract structured data from text following the provided schema exactly. Always respond with valid JSON matching the schema.",
                },
                {"role": "user", "content": prompt},
            ],
            format=schema_model.model_json_schema(),
        )

        content = response.get("message", {}).get("content", "")
        parsed = json.loads(content)
        logger.info(f"Extracted facts: {list(parsed.keys())}")
        
        return parsed

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response as JSON: {e}")
        logger.error(f"Raw content: {content}")
        raise ValueError(f"Invalid JSON response from LLM: {e}")
    except Exception as e:
        logger.error(f"Failed to extract facts: {e}")
        raise