import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from internal.config import load_config
from internal.storage.client import DatabaseClient
from internal.queue.task_queue import TaskQueue
from ollama import AsyncClient

logger = logging.getLogger(__name__)


class NarrativeResponse(BaseModel):
    """
    Pydantic model for structured LLM response containing generated narrative.
    
    Used with Ollama's structured output to ensure LLM returns proper
    narrative format. Currently used only for consistency pattern.
    """
    narrative: str


async def collect_facts(task_id: str, db_client: DatabaseClient) -> List[Dict[str, Any]]:
    """
    Query all completed nodes for a task and aggregate extracted facts.

    This function gathers all extracted facts from completed research nodes
    across all depths of the research tree. The facts are then used
    as source material for synthesis reports.

    Args:
        task_id: Research task UUID to collect facts from
        db_client: Database client instance for querying PostgreSQL

    Returns:
        List of dictionaries containing node metadata and extracted_facts.
        Each dict includes: node_id, node_type, url, question_text,
        depth_level, extracted_facts, created_at

    Note:
        Only nodes with status "completed" and non-null extracted_facts
        are included in the results.
    """
    logger.info(f"Collecting facts for task {task_id}")

    nodes = await db_client.get_completed_nodes_by_task(task_id)

    if not nodes:
        logger.warning(f"No completed nodes found for task {task_id}")
        return []

    facts_list = []
    for node in nodes:
        if node.extracted_facts:
            facts_list.append({
                "node_id": node.id,
                "node_type": node.node_type,
                "url": node.url,
                "question_text": node.question_text,
                "depth_level": node.depth_level,
                "extracted_facts": node.extracted_facts,
                "created_at": node.created_at.isoformat() if node.created_at else None
            })

    logger.info(f"Collected {len(facts_list)} fact entries from completed nodes")
    return facts_list


async def check_depth_limit_reached(task_id: str, depth_limit: int, db_client: DatabaseClient) -> bool:
    """
    Check if the depth limit has been reached for the task.

    Compares the maximum depth_level among all nodes in the research tree
    against the configured depth_limit. If max depth >= limit, the
    research is considered complete.

    Args:
        task_id: Research task UUID to check
        depth_limit: Maximum allowed depth level (usually 3)
        db_client: Database client instance for querying nodes

    Returns:
        True if any node has depth_level >= depth_limit, False otherwise
    """
    nodes = await db_client.get_nodes_by_task(task_id)

    if not nodes:
        return False

    max_depth = max((node.depth_level for node in nodes), default=0)

    if max_depth >= depth_limit:
        logger.info(f"Depth limit reached: {max_depth}/{depth_limit}")
        return True

    return False


async def check_queue_empty(task_queue: TaskQueue) -> bool:
    """
    Check if the task queue is empty.

    Simple check to determine if all queued research tasks have been
    processed. Empty queue indicates that all possible research paths
    have been explored (or depth limit has stopped further queuing).

    Args:
        task_queue: TaskQueue instance to check

    Returns:
        True if queue size is 0 (empty), False otherwise
    """
    queue_size = await task_queue.get_queue_size()
    is_empty = queue_size == 0

    if is_empty:
        logger.info("Task queue is empty")

    return is_empty


async def mark_synthesis_ready(task_id: str, db_client: DatabaseClient) -> bool:
    """
    Mark a research task as synthesis_ready.

    Updates the task status to "synthesis_ready", which signals to
    API that results can now be retrieved in various formats
    (table, graph, text). This status prevents further modifications
    to the research task.

    Args:
        task_id: Research task UUID to update
        db_client: Database client instance for updating tasks

    Returns:
        True if task was found and updated successfully, False otherwise
    """
    logger.info(f"Marking task {task_id} as synthesis_ready")

    task = await db_client.update_research_task(task_id, status="synthesis_ready")

    if task:
        logger.info(f"Task {task_id} marked as synthesis_ready")
        return True

    logger.error(f"Failed to mark task {task_id} as synthesis_ready: task not found")
    return False


async def check_synthesis_ready(
    task_id: str,
    depth_limit: int,
    db_client: DatabaseClient,
    task_queue: Optional[TaskQueue] = None
) -> bool:
    """
    Check if synthesis is ready for a task.

    Synthesis is ready when research is complete, which occurs when:
    1. Task queue is empty (all queued tasks processed), OR
    2. Depth limit has been reached (maximum recursion depth)

    When synthesis is ready, the task status is automatically updated
    to "synthesis_ready".

    Args:
        task_id: Research task UUID to check
        depth_limit: Maximum allowed depth level
        db_client: Database client instance for querying/updating
        task_queue: Optional TaskQueue instance (may not be available)

    Returns:
        True if synthesis is ready and task status was updated,
        False if research is still ongoing
    """
    logger.info(f"Checking synthesis readiness for task {task_id}")

    depth_reached = await check_depth_limit_reached(task_id, depth_limit, db_client)

    queue_empty = True
    if task_queue:
        queue_empty = await check_queue_empty(task_queue)

    if depth_reached or queue_empty:
        await mark_synthesis_ready(task_id, db_client)
        return True

    logger.info(f"Task {task_id} not ready for synthesis: depth_limit={depth_limit}, queue_empty={queue_empty}")
    return False


async def flatten_to_table(facts_list: List[Dict]) -> str:
    """
    Convert list of facts to Markdown table format.

    This synthesis format presents all extracted facts in a tabular view,
    with rows representing research nodes (sources) and columns
    representing template fields. This is useful for comparing
    information across multiple sources.

    Args:
        facts_list: List of dictionaries with node metadata and extracted_facts

    Returns:
        Markdown table string with header row and data rows
        Format: | Node | field1 | field2 | ... |

    Note:
        - URLs or question texts are truncated to 30 characters
        - Nested dicts/lists are stringified and truncated to 50 characters
        - Node IDs are used as fallback labels if no url/question
    """
    if not facts_list:
        return "No facts available."

    all_keys = set()
    for fact in facts_list:
        extracted = fact.get("extracted_facts", {})
        if isinstance(extracted, dict):
            all_keys.update(extracted.keys())

    if not all_keys:
        return "No extracted facts keys found."

    keys = sorted(all_keys)

    header_row = "| Node | " + " | ".join(keys) + " |"
    separator_row = "|------|" + "|".join(["--------" for _ in keys]) + "|"

    rows = [header_row, separator_row]

    for fact in facts_list:
        node_label = fact.get("url") or fact.get("question_text") or fact.get("node_id", "")[:8]
        if len(node_label) > 30:
            node_label = node_label[:27] + "..."

        extracted = fact.get("extracted_facts", {})
        values = []
        for key in keys:
            value = extracted.get(key, "")
            if isinstance(value, (list, dict)):
                value = str(value)[:50]
            if value is None:
                value = ""
            values.append(str(value)[:30])

        row = "| " + node_label + " | " + " | ".join(values) + " |"
        rows.append(row)

    return "\n".join(rows)


async def build_lineage_graph(task_id: str, db_client: DatabaseClient) -> str:
    """
    Generate Mermaid.js diagram showing topic relationships.

    This synthesis format visualizes the research tree as a graph,
    showing how nodes are connected through parent-child relationships.
    Each node is labeled with its URL, question text, or node type.

    Args:
        task_id: Research task UUID to visualize
        db_client: Database client instance for querying nodes

    Returns:
        Mermaid.js diagram string (graph TD format)
        Can be rendered in any Mermaid-compatible viewer

    Note:
        - Node IDs are truncated to 8 characters for readability
        - Labels are sanitized (quotes replaced, newlines removed)
        - Labels longer than 40 characters are truncated
    """
    nodes = await db_client.get_nodes_by_task(task_id)

    if not nodes:
        return "No nodes found to build graph."

    node_map = {node.id: node for node in nodes}

    lines = ["graph TD"]

    for node in nodes:
        label = node.url or node.question_text or node.node_type
        label = label.replace('"', "'").replace("\n", " ")
        if len(label) > 40:
            label = label[:37] + "..."

        lines.append(f'    {node.id[:8]}["{label} ({node.node_type})"]')

        if node.parent_node_id and node.parent_node_id in node_map:
            parent = node_map[node.parent_node_id]
            lines.append(f'    {parent.id[:8]} --> {node.id[:8]}')

    return "\n".join(lines)


async def generate_narrative(facts_list: List[Dict], goal: str) -> str:
    """
    Generate a cohesive narrative report using extracted facts.

    This synthesis format uses LLM to write a comprehensive research report
    based on the collected facts. The report is structured with
    Introduction, Key Findings, Connections, and Conclusion sections.
    The LLM is instructed to use ONLY the provided facts to reduce
    hallucinations and ensure factual accuracy.

    Args:
        facts_list: List of dictionaries with node metadata and extracted_facts
        goal: Original research goal (used for context)

    Returns:
        Narrative report as Markdown-formatted string

    Configuration:
        - Model: llama3.2 (default) or config.llm.model
        - Temperature: 0.3 (default) for focused, deterministic output
        - Max tokens: 4000 (default) for report length

    Note:
        The prompt includes explicit instructions to:
        1. Use only provided facts as source material
        2. Cite sources using (Source N) references
        3. Not make up or infer information
        4. Write in professional research style
    """
    if not facts_list:
        return "No facts available to generate narrative."

    config = load_config()
    client = AsyncClient()

    model_name = "llama3.2"
    temperature = 0.3
    max_tokens = 4000

    if config and config.llm:
        model_name = config.llm.model

    if config and config.synthesis:
        temperature = config.synthesis.llm_temperature
        max_tokens = config.synthesis.max_output_tokens

    facts_summary = ""
    for i, fact in enumerate(facts_list):
        extracted = fact.get("extracted_facts", {})
        facts_summary += f"\n\nSource {i+1} ({fact.get('node_type')}):\n"
        if isinstance(extracted, dict):
            for key, value in extracted.items():
                facts_summary += f"- {key}: {value}\n"

    prompt = f"""Write a comprehensive research report based on the following extracted facts.

Research Goal: {goal}

Extracted Facts:
{facts_summary}

Instructions:
1. Structure your report with the following sections:
    - Introduction: Brief overview of the research goal
    - Key Findings: Summarize the most important information discovered
    - Connections: Explain how different findings relate to each other
    - Conclusion: Summary of what was learned and any remaining questions

2. Use ONLY the provided extracted facts as your source material
3. Do not make up or infer information not present in the facts
4. Write in a clear, professional style suitable for a research report
5. Cite sources using (Source N) references where appropriate

Generate a cohesive narrative report in Markdown format."""

    try:
        response = await client.chat(
            model=model_name,
            messages=[
                {
                    "role": "system",
                    "content": "You are a research analyst who synthesizes information from extracted facts into comprehensive reports. Always respond with well-structured Markdown.",
                },
                {"role": "user", "content": prompt},
            ],
            options={
                "temperature": temperature,
                "num_predict": max_tokens,
            }
        )

        narrative = response.get("message", {}).get("content", "")
        logger.info(f"Generated narrative report ({len(narrative)} characters)")

        return narrative

    except Exception as e:
        logger.error(f"Failed to generate narrative: {e}")
        raise
