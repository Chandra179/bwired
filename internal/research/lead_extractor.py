import logging
import re
import json
from typing import List, Dict, Any, Optional
import numpy as np
from ollama import AsyncClient
from pydantic import BaseModel
from internal.config import load_config

logger = logging.getLogger(__name__)

__all__ = [
    "extract_citations",
    "extract_conceptual_leads",
    "identify_conceptual_leads_llm",
    "generate_sub_questions",
    "extract_leads",
    "extract_links_with_anchor_text",
    "calculate_link_priority",
    "prioritize_and_prune_links",
    "extract_and_prioritize_links"
]


class ConceptualLeads(BaseModel):
    """Conceptual leads that need further research"""
    leads: List[str]


class SubQuestions(BaseModel):
    """Generated sub-questions for a concept"""
    questions: List[str]


def extract_citations(extracted_facts: Dict[str, Any], markdown: str) -> List[Dict[str, str]]:
    """
    Extract citations and references from extracted facts and markdown.

    Args:
        extracted_facts: Structured facts extracted from document
        markdown: Original markdown content

    Returns:
        List of extracted citations with metadata
    """
    citations = []

    url_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
    matches = re.findall(url_pattern, markdown)

    seen_urls = set()
    for anchor_text, url in matches:
        if url in seen_urls:
            continue
        seen_urls.add(url)

        citations.append({
            "anchor_text": anchor_text,
            "url": url,
            "type": "external_link"
        })

    reference_pattern = r'\[(\d+)\]'
    ref_matches = re.findall(reference_pattern, markdown)
    for ref_num in ref_matches:
        citations.append({
            "reference": f"[{ref_num}]",
            "type": "citation"
        })

    logger.info(f"Extracted {len(citations)} citations from markdown")
    return citations


def extract_conceptual_leads(extracted_facts: Dict[str, Any], markdown: str) -> List[str]:
    """
    Identify mentions without details (conceptual leads).

    Args:
        extracted_facts: Structured facts extracted from document
        markdown: Original markdown content

    Returns:
        List of concepts that need further research
    """
    import json

    leads = []

    def extract_from_value(value: Any) -> List[str]:
        if isinstance(value, str):
            capitalized_words = re.findall(r'\b[A-Z][a-zA-Z]+\b', value)
            return [word for word in capitalized_words if len(word) > 2]
        elif isinstance(value, list):
            result = []
            for item in value:
                result.extend(extract_from_value(item))
            return result
        elif isinstance(value, dict):
            result = []
            for v in value.values():
                result.extend(extract_from_value(v))
            return result
        return []

    for key, value in extracted_facts.items():
        if isinstance(value, str) and len(value) < 50:
            leads.append(value)
        else:
            leads.extend(extract_from_value(value))

    deduplicated_leads = list(set(leads))
    logger.info(f"Identified {len(deduplicated_leads)} potential conceptual leads")
    return deduplicated_leads


async def identify_conceptual_leads_llm(extracted_facts: Dict[str, Any], markdown: str) -> List[str]:
    """
    Use LLM to identify concepts that need more research.

    Args:
        extracted_facts: Structured facts extracted from document
        markdown: Original markdown content

    Returns:
        List of concepts that need further research
    """
    config = load_config()
    client = AsyncClient()

    model_name = "llama3.2"
    if config and config.llm:
        model_name = config.llm.model

    facts_summary = json.dumps(extracted_facts, indent=2)

    prompt = f"""Analyze the extracted facts and identify concepts, entities, or topics
that are mentioned but lack detailed information and would benefit from further research.

Extracted Facts:
{facts_summary}

Instructions:
1. Identify concepts that are mentioned but not fully explained
2. Look for technical terms, names of organizations/people, or specific phenomena
3. Focus on concepts that are crucial to understanding the topic
4. Ignore common words and well-known facts
5. Return 3-5 key concepts that would benefit from further research
6. Return each concept as a short phrase (2-5 words)

Return only the concepts as a JSON list of strings."""

    try:
        response = await client.chat(
            model=model_name,
            messages=[
                {"role": "system", "content": "You are a research analyst that identifies key concepts needing further investigation. Always respond with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            format=ConceptualLeads.model_json_schema()
        )

        content = response.get("message", {}).get("content", "")
        parsed = json.loads(content)
        
        leads = parsed.get("leads", [])
        logger.info(f"LLM identified {len(leads)} conceptual leads")
        return leads

    except Exception as e:
        logger.error(f"Failed to identify conceptual leads with LLM: {e}")
        return []


async def generate_sub_questions(concept: str, original_goal: str, count: int = 3) -> List[str]:
    """
    Generate research questions for unknown concepts.

    Args:
        concept: The concept that needs more research
        original_goal: The original research goal
        count: Number of questions to generate

    Returns:
        List of research questions
    """
    config = load_config()
    client = AsyncClient()

    model_name = "llama3.2"
    if config and config.llm:
        model_name = config.llm.model

    prompt = f"""Generate {count} specific research questions about the following concept
in the context of the original research goal.

Concept to research: {concept}

Original research goal: {original_goal}

Each question should:
1. Be directly related to the concept
2. Help achieve the original research goal
3. Be specific and answerable through web research
4. Be phrased as a clear question (not a statement)
5. Focus on uncovering details about the concept

Return exactly {count} questions as a JSON list of strings."""

    try:
        response = await client.chat(
            model=model_name,
            messages=[
                {"role": "system", "content": "You are a research assistant that generates focused questions for investigating specific concepts. Always respond with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            format=SubQuestions.model_json_schema()
        )

        content = response.get("message", {}).get("content", "")
        parsed = json.loads(content)
        
        questions = parsed.get("questions", [])
        logger.info(f"Generated {len(questions)} sub-questions for concept: {concept}")
        return questions

    except Exception as e:
        logger.error(f"Failed to generate sub-questions for concept '{concept}': {e}")
        raise


async def extract_leads(extracted_facts: Dict[str, Any], markdown: str) -> Dict[str, Any]:
    """
    Extract all leads from facts and markdown including citations and conceptual leads.

    Args:
        extracted_facts: Structured facts extracted from document
        markdown: Original markdown content

    Returns:
        Dictionary containing citations and conceptual leads
    """
    citations = extract_citations(extracted_facts, markdown)
    conceptual_leads = await identify_conceptual_leads_llm(extracted_facts, markdown)
    
    logger.info(f"Extracted {len(citations)} citations and {len(conceptual_leads)} conceptual leads")
    
    return {
        "citations": citations,
        "conceptual_leads": conceptual_leads
    }


def extract_links_with_anchor_text(markdown: str) -> List[Dict[str, str]]:
    """
    Extract links from Markdown with their anchor text.

    Args:
        markdown: Original markdown content

    Returns:
        List of dictionaries with 'anchor_text' and 'url' keys, deduplicated by URL
    """
    url_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
    matches = re.findall(url_pattern, markdown)
    
    seen_urls = set()
    links = []
    
    for anchor_text, url in matches:
        url = url.strip()
        
        if not url or url in seen_urls:
            continue
        
        seen_urls.add(url)
        
        links.append({
            "anchor_text": anchor_text.strip(),
            "url": url
        })
    
    logger.info(f"Extracted {len(links)} unique links from markdown")
    return links


def calculate_link_priority(anchor_text: str, question_vector: np.ndarray, embedder) -> float:
    """
    Calculate priority score for a link based on cosine similarity between anchor text and question.

    Args:
        anchor_text: The anchor text of the link
        question_vector: The embedding vector of the original question
        embedder: DenseEmbedder instance for creating embeddings

    Returns:
        Priority score between 0.0 and 1.0
    """
    if not anchor_text or question_vector is None or embedder is None:
        return 0.0
    
    try:
        anchor_embeddings = embedder.encode([anchor_text])
        
        if not anchor_embeddings:
            return 0.0
        
        anchor_vector = anchor_embeddings[0]
        
        cosine_similarity = np.dot(question_vector, anchor_vector) / (
            np.linalg.norm(question_vector) * np.linalg.norm(anchor_vector) + 1e-8
        )
        
        priority_score = float(max(0.0, min(1.0, cosine_similarity)))
        
        return priority_score
    
    except Exception as e:
        logger.warning(f"Failed to calculate priority for anchor '{anchor_text}': {e}")
        return 0.0


def prioritize_and_prune_links(
    links: List[Dict[str, str]],
    question_vector: np.ndarray,
    embedder,
    depth_limit: int,
    current_depth: int,
    priority_threshold: Optional[float] = None
) -> List[Dict[str, Any]]:
    """
    Prioritize and prune links based on priority score and depth limit.

    Args:
        links: List of link dictionaries with 'anchor_text' and 'url'
        question_vector: The embedding vector of the original question
        embedder: DenseEmbedder instance for creating embeddings
        depth_limit: Maximum allowed depth level
        current_depth: Current depth level
        priority_threshold: Minimum priority score (default from config)

    Returns:
        List of prioritized and pruned links with scores
    """
    config = load_config()
    threshold = priority_threshold
    if threshold is None and config and config.research:
        threshold = config.research.priority_threshold
    elif threshold is None:
        threshold = 0.5
    
    if current_depth >= depth_limit:
        logger.info(f"Depth limit ({depth_limit}) reached, pruning all links")
        return []
    
    prioritized_links = []
    
    for link in links:
        anchor_text = link.get("anchor_text", "")
        url = link.get("url", "")
        
        if not anchor_text or not url:
            continue
        
        priority_score = calculate_link_priority(anchor_text, question_vector, embedder)
        
        if priority_score >= threshold:
            prioritized_links.append({
                "anchor_text": anchor_text,
                "url": url,
                "priority_score": priority_score
            })
    
    prioritized_links.sort(key=lambda x: x["priority_score"], reverse=True)
    
    logger.info(f"Prioritized {len(prioritized_links)} links (pruned {len(links) - len(prioritized_links)} below threshold {threshold})")
    
    return prioritized_links


async def extract_and_prioritize_links(
    markdown: str,
    question_text: str,
    question_vector: Optional[np.ndarray],
    embedder,
    depth_limit: int,
    current_depth: int,
    priority_threshold: Optional[float] = None
) -> Dict[str, Any]:
    """
    Extract links from markdown and prioritize them based on relevance to the question.

    Args:
        markdown: Original markdown content
        question_text: The original research question text
        question_vector: The embedding vector of the question (optional, will generate if None)
        embedder: DenseEmbedder instance for creating embeddings
        depth_limit: Maximum allowed depth level
        current_depth: Current depth level
        priority_threshold: Minimum priority score (default from config)

    Returns:
        Dictionary with 'extracted_links', 'prioritized_links', and 'statistics'
    """
    links = extract_links_with_anchor_text(markdown)
    
    if question_vector is None and embedder is not None:
        try:
            question_embeddings = embedder.encode([question_text])
            question_vector = question_embeddings[0] if question_embeddings else None
        except Exception as e:
            logger.warning(f"Failed to generate question vector: {e}")
    
    if question_vector is None:
        logger.warning("No question vector available, cannot prioritize links")
        return {
            "extracted_links": links,
            "prioritized_links": [],
            "statistics": {
                "total_links": len(links),
                "prioritized_links": 0,
                "pruned_links": len(links)
            }
        }
    
    prioritized_links = prioritize_and_prune_links(
        links=links,
        question_vector=question_vector,
        embedder=embedder,
        depth_limit=depth_limit,
        current_depth=current_depth,
        priority_threshold=priority_threshold
    )
    
    return {
        "extracted_links": links,
        "prioritized_links": prioritized_links,
        "statistics": {
            "total_links": len(links),
            "prioritized_links": len(prioritized_links),
            "pruned_links": len(links) - len(prioritized_links),
            "current_depth": current_depth,
            "depth_limit": depth_limit
        }
    }