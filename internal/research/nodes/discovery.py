import logging
from typing import List, Dict, Any, Optional
import numpy as np

from internal.research.lead_extractor import (
    extract_leads,
    extract_and_prioritize_links,
    generate_sub_questions
)
from internal.config import load_config
from internal.queue import TaskQueue

logger = logging.getLogger(__name__)


async def discovery_node(
    extracted_facts: Dict,
    markdown: str,
    original_goal: str,
    question_text: str,
    question_vector: Optional[np.ndarray],
    embedder,
    depth_limit: int,
    current_depth: int,
    task_queue: Optional[TaskQueue] = None
) -> Dict[str, Any]:
    """
    Process extracted facts to identify leads, prioritize links, and generate new research tasks.

    This is the recursive discovery node that:
    1. Extracts conceptual leads (unanswered concepts) from extracted facts using LLM
    2. Extracts and prioritizes all links from markdown content
    3. Generates sub-questions for each conceptual lead
    4. Queues new tasks (scout for sub-questions, process for prioritized links)

    The node uses semantic similarity scoring to prioritize links, comparing
    the question vector with link anchor text embeddings. Links below the
    priority threshold are pruned to reduce search noise.

    Args:
        extracted_facts: Facts extracted from current page (JSONB dict)
        markdown: Original markdown content containing links and references
        original_goal: Original research goal (passed to sub-question generation)
        question_text: The research question text being answered
        question_vector: The embedding vector of the question (for link scoring)
        embedder: DenseEmbedder instance for calculating cosine similarities
        depth_limit: Maximum research depth level (from task config)
        current_depth: Current depth level (0 = seed questions)
        task_queue: Optional TaskQueue for pushing new research tasks

    Returns:
        Dictionary containing:
        - prioritized_links: List of links that passed threshold with scores
        - sub_questions: List of new research questions for conceptual leads
        - leads: List of identified conceptual leads (unanswered concepts)
        - statistics: Processing statistics including pruned links count

    Note:
        If depth_limit is reached, no new tasks are queued even if leads are found.
        This prevents infinite recursion in the research tree.
    """
    logger.info(f"Running discovery node at depth {current_depth}/{depth_limit}")
    
    config = load_config()
    priority_threshold = None
    if config and config.research:
        priority_threshold = config.research.priority_threshold
    
    # Extract both citations (external links) and conceptual leads (unanswered concepts)
    leads_result = await extract_leads(extracted_facts, markdown)
    
    # Extract all links from markdown, score by relevance to original question
    links_result = await extract_and_prioritize_links(
        markdown=markdown,
        question_text=question_text,
        question_vector=question_vector,
        embedder=embedder,
        depth_limit=depth_limit,
        current_depth=current_depth,
        priority_threshold=priority_threshold
    )
    
    # Generate sub-questions for each conceptual lead
    sub_questions = []
    conceptual_leads = leads_result.get("conceptual_leads", [])
    
    for concept in conceptual_leads:
        try:
            questions = await generate_sub_questions(concept, original_goal, count=3)
            sub_questions.extend(questions)
        except Exception as e:
            logger.warning(f"Failed to generate sub-questions for concept '{concept}': {e}")
    
    # Queue new tasks if not at depth limit
    if task_queue:
        for link in links_result["prioritized_links"]:
            try:
                await task_queue.push_task(
                    task_type="process",
                    priority=link["priority_score"],
                    payload={
                        "url": link["url"],
                        "parent_question": question_text,
                        "depth": current_depth + 1
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to push process task for URL '{link['url']}': {e}")
        
        for question in sub_questions:
            try:
                await task_queue.push_task(
                    task_type="scout",
                    priority=0.8,
                    payload={
                        "question": question,
                        "original_goal": original_goal,
                        "depth": current_depth + 1
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to push scout task for question '{question}': {e}")
    
    result = {
        "prioritized_links": links_result["prioritized_links"],
        "sub_questions": sub_questions,
        "leads": conceptual_leads,
        "statistics": {
            "total_links": links_result["statistics"]["total_links"],
            "prioritized_links": links_result["statistics"]["prioritized_links"],
            "pruned_links": links_result["statistics"]["pruned_links"],
            "conceptual_leads": len(conceptual_leads),
            "sub_questions_generated": len(sub_questions),
            "current_depth": current_depth,
            "depth_limit": depth_limit,
            "should_continue": (
                len(links_result["prioritized_links"]) > 0 or
                len(sub_questions) > 0
            )
        }
    }
    
    logger.info(
        f"Discovery completed: {len(result['prioritized_links'])} prioritized links, "
        f"{len(result['sub_questions'])} sub-questions, "
        f"{len(result['leads'])} conceptual leads"
    )
    
    return result