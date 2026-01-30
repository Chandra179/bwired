import logging
import re
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Union, List, Tuple, Optional
from urllib.parse import urlparse

from docling.document_converter import DocumentConverter, PdfFormatOption, HTMLFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode
from docling.datamodel.base_models import InputFormat

from internal.fetcher import fetch_url_content

logger = logging.getLogger(__name__)

# Default exports directory
DEFAULT_EXPORTS_DIR = Path("exports")


def convert_pdf_to_markdown(pdf_path: Path) -> str:
    """
    Convert PDF to markdown using Docling
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        Markdown content as string
    """
    logger.info(f"Converting PDF to markdown: {pdf_path.name}")
    
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = True
    pipeline_options.do_table_structure = True
    pipeline_options.table_structure_options.do_cell_matching = True
    pipeline_options.table_structure_options.mode = TableFormerMode.ACCURATE
    pipeline_options.generate_picture_images = False
    pipeline_options.generate_page_images = False
    
    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        }
    )
    
    result = converter.convert(pdf_path)
    markdown_content = result.document.export_to_markdown()
    
    logger.info(f"PDF converted successfully ({len(markdown_content)} chars)")
    return markdown_content


def convert_html_to_markdown(html_path: Path) -> str:
    """
    Convert HTML to markdown using Docling
    
    Args:
        html_path: Path to HTML file
        
    Returns:
        Markdown content as string
    """
    logger.info(f"Converting HTML to markdown: {html_path.name}")
    
    converter = DocumentConverter(
        format_options={
            InputFormat.HTML: HTMLFormatOption()
        }
    )
    
    result = converter.convert(html_path)
    markdown_content = result.document.export_to_markdown()
    
    logger.info(f"HTML converted successfully ({len(markdown_content)} chars)")
    return markdown_content


# Note: fetch_url_content is now imported from internal.processing.url_fetcher
# It provides enhanced headers, User-Agent rotation, and retry logic


def _sanitize_filename(url: str, max_length: int = 100) -> str:
    """
    Create a safe filename from a URL.
    
    Args:
        url: The URL to convert to a filename
        max_length: Maximum length for the filename
        
    Returns:
        A sanitized filename string
    """
    # Parse URL to get domain and path
    parsed = urlparse(url)
    
    # Start with domain
    domain = parsed.netloc or "unknown"
    
    # Add path if present (remove leading/trailing slashes)
    path = parsed.path.strip("/")
    if path:
        # Take last part of path or full path if short
        path_parts = path.split("/")
        path = path_parts[-1] if path_parts else path
    
    # Combine domain and path
    if path and len(domain + "_" + path) <= max_length:
        filename = f"{domain}_{path}"
    else:
        filename = domain
    
    # Replace invalid characters with underscores
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Limit length
    if len(filename) > max_length:
        filename = filename[:max_length]
    
    # Remove trailing dots/spaces
    filename = filename.rstrip('. ')
    
    # Ensure we have something valid
    if not filename or filename == "_":
        filename = "exported_content"
    
    return filename


def _generate_unique_filename(url: str, exports_dir: Path, timestamp: Optional[str] = None) -> Path:
    """
    Generate a unique filename for a markdown export.
    
    Args:
        url: The URL being converted
        exports_dir: Directory to save the file
        timestamp: Optional timestamp string to include in filename
        
    Returns:
        Path object for the unique filename
    """
    base_name = _sanitize_filename(url)
    
    if timestamp:
        base_name = f"{timestamp}_{base_name}"
    
    # Ensure unique filename
    counter = 0
    filename = f"{base_name}.md"
    file_path = exports_dir / filename
    
    while file_path.exists():
        counter += 1
        filename = f"{base_name}_{counter}.md"
        file_path = exports_dir / filename
    
    return file_path


def convert_urls_to_markdown(
    urls: List[str], 
    timeout: int = 30,
    save_to_disk: bool = False,
    exports_dir: Optional[Path] = None,
    include_timestamp: bool = True
) -> List[Tuple[str, Optional[Path]]]:
    """
    Convert a list of URLs to markdown using Docling
    
    Fetches HTML content from each URL and converts it to markdown.
    Optionally saves the markdown content to disk.
    
    Args:
        urls: List of URLs to convert
        timeout: Request timeout in seconds for each URL
        save_to_disk: Whether to save markdown files to disk
        exports_dir: Directory to save files (defaults to ./exports/)
        include_timestamp: Whether to include timestamp in filenames
        
    Returns:
        List of tuples containing (markdown_content, file_path) for each URL.
        file_path is None if save_to_disk is False or if conversion failed.
        
    Note:
        If a URL fails to fetch or convert, an empty string is returned
        for that URL and the error is logged.
    """
    logger.info(f"Converting {len(urls)} URLs to markdown (save_to_disk={save_to_disk})")
    
    # Setup exports directory
    if save_to_disk:
        if exports_dir is None:
            exports_dir = DEFAULT_EXPORTS_DIR
        exports_dir = Path(exports_dir)
        exports_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Exports directory: {exports_dir.absolute()}")
    
    # Generate timestamp for filenames
    timestamp = None
    if save_to_disk and include_timestamp:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    converter = DocumentConverter(
        format_options={
            InputFormat.HTML: HTMLFormatOption()
        }
    )
    
    results = []
    
    for i, url in enumerate(urls):
        file_path: Optional[Path] = None
        markdown_content = ""
        
        try:
            logger.info(f"Processing URL {i + 1}/{len(urls)}: {url}")
            
            # Fetch HTML content
            html_content = fetch_url_content(url, timeout=timeout)
            
            # Create temporary file with HTML content
            with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as temp_file:
                temp_file.write(html_content)
                temp_html_path = Path(temp_file.name)
            
            try:
                # Convert HTML to markdown
                result = converter.convert(temp_html_path)
                markdown_content = result.document.export_to_markdown()
                
                # Save to disk if requested
                if save_to_disk and markdown_content:
                    file_path = _generate_unique_filename(url, exports_dir, timestamp)
                    file_path.write_text(markdown_content, encoding="utf-8")
                    logger.info(f"URL {i + 1} converted and saved to {file_path.name} ({len(markdown_content)} chars)")
                else:
                    logger.info(f"URL {i + 1} converted successfully ({len(markdown_content)} chars)")
                    
            finally:
                # Clean up temporary file
                temp_html_path.unlink()
                
        except Exception as e:
            logger.error(f"Failed to convert URL {url}: {e}")
            markdown_content = ""
            file_path = None
        
        results.append((markdown_content, file_path))
    
    saved_count = sum(1 for _, fp in results if fp is not None)
    logger.info(f"Completed conversion of {len(urls)} URLs ({saved_count} saved to disk)")
    return results


if __name__ == "__main__":
    """Test the convert_html_to_markdown function with dummy HTML data"""
    import os

    # Configure logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # Create dummy HTML content for testing
    dummy_html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Test Document</title>
</head>
<body>
    <h1>Welcome to the Test Document</h1>
    <p>This is a <strong>dummy HTML file</strong> created for testing the <em>convert_html_to_markdown</em> function.</p>
    
    <h2>Features</h2>
    <ul>
        <li>Simple HTML structure</li>
        <li>Basic formatting elements</li>
        <li>Lists and headings</li>
    </ul>
    
    <h2>Code Example</h2>
    <pre><code>def hello_world():
    print("Hello, World!")</code></pre>
    
    <p>For more information, visit <a href="https://example.com">Example Website</a>.</p>
    
    <table>
        <tr>
            <th>Feature</th>
            <th>Status</th>
        </tr>
        <tr>
            <td>HTML Parsing</td>
            <td>Active</td>
        </tr>
        <tr>
            <td>Markdown Export</td>
            <td>Active</td>
        </tr>
    </table>
</body>
</html>"""

    # Create a temporary HTML file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as temp_file:
        temp_file.write(dummy_html_content)
        temp_html_path = Path(temp_file.name)

    try:
        logger.info("=" * 50)
        logger.info("Testing convert_html_to_markdown function")
        logger.info("=" * 50)

        # Convert HTML to markdown
        markdown_result = convert_html_to_markdown(temp_html_path)

        # Save the result to a file
        output_path = Path("example_html.md")
        output_path.write_text(markdown_result, encoding="utf-8")

        # Display the result
        logger.info("-" * 50)
        logger.info("CONVERTED MARKDOWN OUTPUT:")
        logger.info("-" * 50)
        print(markdown_result)
        logger.info("-" * 50)
        logger.info(f"Total characters in output: {len(markdown_result)}")
        logger.info(f"Output saved to: {output_path}")
        logger.info("Test completed successfully!")

    except Exception as e:
        logger.error(f"Error during conversion: {e}")
        raise

    finally:
        # Clean up the temporary file
        os.unlink(temp_html_path)
        logger.info(f"Cleaned up temporary file: {temp_html_path}")