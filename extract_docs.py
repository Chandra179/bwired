import sys
from pathlib import Path
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode
from docling_core.types.doc.base import ImageRefMode
from docling.datamodel.base_models import InputFormat

def convert_pdf_nuclear(pdf_path, output_dir=None):
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    
    if output_dir is None:
        output_dir = Path.cwd()
    else:
        output_dir = Path(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = True 
    pipeline_options.do_table_structure = True
    pipeline_options.generate_picture_images = True
    pipeline_options.generate_page_images = True
    pipeline_options.do_layout_analysis = True
    pipeline_options.table_structure_options.do_cell_matching = True
    pipeline_options.table_structure_options.mode = TableFormerMode.ACCURATE  # vs FAST
    
    pipeline_options.images_scale = 2.0 

    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        }
    )

    result = converter.convert(pdf_path)
    doc = result.document

    images_dir = Path("images")
    final_filename = output_dir / f"{pdf_path.stem}_nuclear.md"
    
    doc.save_as_markdown(
        filename=final_filename,
        image_mode=ImageRefMode.REFERENCED, 
        artifacts_dir=images_dir)

    print(f"\n✓ DONE: {final_filename}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        convert_pdf_nuclear(sys.argv[1])
    else:
        print("Usage: python script.py <pdf_file>")