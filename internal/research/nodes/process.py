import logging
from typing import Dict, Any
from pydantic import BaseModel

logger = logging.getLogger(__name__)


async def extract_facts(markdown: str, schema_model: type[BaseModel]) -> Dict[str, Any]:
    """
    Extract structured facts from markdown using Instructor.

    Args:
        markdown: Markdown content to process
        schema_model: Dynamic Pydantic schema model

    Returns:
        Structured facts as JSONB-compatible dict
    """
    raise NotImplementedError