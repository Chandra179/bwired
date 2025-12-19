"""
Utility functions
"""
import logging
import sys
from pathlib import Path
from typing import Optional
import yaml


def setup_logging(level: str = "INFO"):
    """
    Setup logging configuration
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    
    handlers = [console_handler]
    
    logging.basicConfig(
        level=numeric_level,
        handlers=handlers
    )


def read_markdown_file(file_path: str) -> str:
    """
    Read markdown file content
    
    Args:
        file_path: Path to markdown file
        
    Returns:
        File content as string
    """
    path = Path(file_path)
    
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    if not path.suffix.lower() in ['.md', '.markdown']:
        raise ValueError(f"Not a markdown file: {file_path}")
    
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    return content


def load_config_file(config_path: str) -> dict:
    """
    Load configuration from YAML file
    
    Args:
        config_path: Path to config file
        
    Returns:
        Configuration dictionary
    """
    path = Path(config_path)
    
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    with open(path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    return config or {}


def get_document_id_from_path(file_path: str) -> str:
    """
    Generate document ID from file path
    
    Args:
        file_path: Path to file
        
    Returns:
        Document ID (filename without extension)
    """
    return Path(file_path).stem