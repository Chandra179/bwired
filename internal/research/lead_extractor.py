import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


def extract_citations(extracted_facts: Dict, markdown: str) -> List[Dict]:
    """
    Extract citations and references from extracted facts and markdown.

    Args:
        extracted_facts: Structured facts extracted from document
        markdown: Original markdown content

    Returns:
        List of extracted citations with metadata
    """
    raise NotImplementedError


def generate_sub_questions(concept: str, original_goal: str) -> List[str]:
    """
    Generate research questions for unknown concepts.

    Args:
        concept: The concept that needs more research
        original_goal: The original research goal

    Returns:
        List of research questions
    """
    raise NotImplementedError