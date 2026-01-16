import logging
from pathlib import Path

from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode
from docling.datamodel.base_models import InputFormat

logger = logging.getLogger(__name__)


# This function will be used later if we got PDF file
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