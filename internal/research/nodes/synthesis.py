import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


async def collect_facts(task_id: str) -> List[Dict]:
    """
    Query all completed nodes for a task and aggregate extracted facts.

    Args:
        task_id: Research task ID

    Returns:
        List of extracted facts from all completed nodes
    """
    raise NotImplementedError


async def flatten_to_table(facts_list: List[Dict]) -> str:
    """
    Convert list of facts to Markdown table format.

    Args:
        facts_list: List of fact dictionaries

    Returns:
        Markdown table string
    """
    raise NotImplementedError


async def build_lineage_graph(task_id: str) -> str:
    """
    Generate Mermaid.js diagram showing topic relationships.

    Args:
        task_id: Research task ID

    Returns:
        Mermaid diagram string
    """
    raise NotImplementedError


async def generate_narrative(facts_list: List[Dict], goal: str) -> str:
    """
    Generate a cohesive narrative report using extracted facts.

    Args:
        facts_list: List of extracted facts
        goal: Original research goal

    Returns:
        Narrative report as Markdown
    """
    raise NotImplementedError