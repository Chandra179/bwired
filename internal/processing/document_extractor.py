import logging
import tempfile
from pathlib import Path
from typing import Union, List

import requests
from docling.document_converter import DocumentConverter, PdfFormatOption, HTMLFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode
from docling.datamodel.base_models import InputFormat

logger = logging.getLogger(__name__)


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


def fetch_url_content(url: str, timeout: int = 30) -> str:
    """
    Fetch HTML content from a URL
    
    Args:
        url: URL to fetch
        timeout: Request timeout in seconds
        
    Returns:
        HTML content as string
        
    Raises:
        requests.RequestException: If the request fails
    """
    logger.info(f"Fetching URL: {url}")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    response = requests.get(url, headers=headers, timeout=timeout)
    response.raise_for_status()
    
    logger.info(f"Fetched {len(response.text)} chars from {url}")
    return response.text


def convert_urls_to_markdown(urls: List[str], timeout: int = 30) -> List[str]:
    """
    Convert a list of URLs to markdown using Docling
    
    Fetches HTML content from each URL and converts it to markdown.
    
    Args:
        urls: List of URLs to convert
        timeout: Request timeout in seconds for each URL
        
    Returns:
        List of markdown content strings (one per URL)
        
    Note:
        If a URL fails to fetch or convert, an empty string is returned
        for that URL and the error is logged.
    """
    logger.info(f"Converting {len(urls)} URLs to markdown")
    
    converter = DocumentConverter(
        format_options={
            InputFormat.HTML: HTMLFormatOption()
        }
    )
    
    results = []
    
    for i, url in enumerate(urls):
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
                results.append(markdown_content)
                logger.info(f"URL {i + 1} converted successfully ({len(markdown_content)} chars)")
            finally:
                # Clean up temporary file
                temp_html_path.unlink()
                
        except Exception as e:
            logger.error(f"Failed to convert URL {url}: {e}")
            results.append("")
    
    logger.info(f"Completed conversion of {len(urls)} URLs")
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