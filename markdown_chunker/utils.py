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


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted size string
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"


def print_summary(
    document_id: str,
    num_elements: int,
    num_chunks: int,
    total_tokens: int,
    file_size: int
):
    """
    Print processing summary
    
    Args:
        document_id: Document identifier
        num_elements: Number of parsed elements
        num_chunks: Number of generated chunks
        total_tokens: Total token count
        file_size: File size in bytes
    """
    print("\n" + "="*60)
    print("PROCESSING SUMMARY")
    print("="*60)
    print(f"Document ID:        {document_id}")
    print(f"File Size:          {format_file_size(file_size)}")
    print(f"Markdown Elements:  {num_elements}")
    print(f"Generated Chunks:   {num_chunks}")
    print(f"Total Tokens:       {total_tokens:,}")
    print(f"Avg Tokens/Chunk:   {total_tokens // num_chunks if num_chunks > 0 else 0}")
    print("="*60 + "\n")