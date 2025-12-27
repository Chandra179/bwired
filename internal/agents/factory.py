import logging
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.ollama import OllamaProvider

from internal.agents.search_agent import search_documents

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are an intelligent document assistant with access to a vector database system.

Your capabilities:
1. **Search Documents**: Search through document collections to answer questions

Guidelines:
- When users ask questions about documents, use the search_documents tool
- Always ask which collection to search if not specified
- Be concise and direct in your responses
- If a search returns no results, inform the user clearly
- Handle errors gracefully and suggest solutions

You have access to these tools:
- search_documents(query, collection_name, limit): Search and answer questions from documents

Remember: Users interact with you through chat"""


def create_document_agent(model_name: str = "llama3.2") -> Agent:
    """
    Create and configure the unified document assistant agent.
    
    Args:
        model_name: Name of the Ollama model to use (from config)
        
    Returns:
        Configured Agent instance with all tools registered
    """
    logger.info(f"Connecting to Ollama via OpenAI model: {model_name} at http://localhost:11434/v1")
    
    model = OpenAIChatModel(
        model_name=model_name,
        provider=OllamaProvider(base_url='http://localhost:11434/v1')
    )
    
    agent = Agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        retries=2
    )
    
    agent.tool(search_documents)
    
    logger.info("✓ Document agent created with 2 tools registered")
    return agent