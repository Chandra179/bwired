import sys
from pathlib import Path
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.datamodel.base_models import InputFormat

def get_overlap_ratio(bbox1, bbox2):
    """
    Calculates how much of bbox1 is inside bbox2.
    Robust to Top-Down vs Bottom-Up coordinate systems.
    """
    # 1. Normalize Coordinates (ensure l < r and min_y < max_y)
    b1_x_min, b1_x_max = sorted([bbox1.l, bbox1.r])
    b1_y_min, b1_y_max = sorted([bbox1.t, bbox1.b])
    
    b2_x_min, b2_x_max = sorted([bbox2.l, bbox2.r])
    b2_y_min, b2_y_max = sorted([bbox2.t, bbox2.b])

    # 2. Calculate Intersection Rectangle
    inter_x_min = max(b1_x_min, b2_x_min)
    inter_x_max = min(b1_x_max, b2_x_max)
    inter_y_min = max(b1_y_min, b2_y_min)
    inter_y_max = min(b1_y_max, b2_y_max)

    # 3. Check for valid intersection
    if inter_x_max <= inter_x_min or inter_y_max <= inter_y_min:
        return 0.0

    intersection_area = (inter_x_max - inter_x_min) * (inter_y_max - inter_y_min)
    b1_area = (b1_x_max - b1_x_min) * (b1_y_max - b1_y_min)

    if b1_area <= 0: return 0.0

    return intersection_area / b1_area

def convert_pdf_nuclear(pdf_path, output_dir=None):
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    if output_dir is None: output_dir = pdf_path.parent
    else: output_dir = Path(output_dir)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    images_dir = output_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    # --- Pipeline Setup ---
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = True 
    pipeline_options.do_table_structure = True
    pipeline_options.generate_picture_images = True
    pipeline_options.images_scale = 2.0 

    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        }
    )

    print(f"Processing {pdf_path.name} (Aggressive Filter Mode)...")
    result = converter.convert(pdf_path)
    doc = result.document

    markdown_lines = []

    for page_no, page in doc.pages.items():
        print(f"  Scanning Page {page_no}...")
        
        page_items = []
        image_bboxes_on_page = []

        # 1. Collect Images & Define "Kill Zones"
        for i, pic in enumerate(doc.pictures):
            if pic.prov and pic.prov[0].page_no == page_no:
                img_filename = f"image_p{page_no}_{i}.png"
                img_path = images_dir / img_filename
                
                if pic.image and pic.image.pil_image:
                    pic.image.pil_image.save(img_path)
                    
                    bbox = pic.prov[0].bbox
                    # We store the bbox to check against text later
                    image_bboxes_on_page.append(bbox)
                    
                    # Store for markdown generation
                    # Use 'min' of t/b to ensure we get the top-most point regardless of coord system
                    top_coord = min(bbox.t, bbox.b) 
                    
                    md_link = f"\n![Image]({images_dir.name}/{img_filename})\n"
                    page_items.append({
                        "top": top_coord,
                        "type": "image",
                        "content": md_link
                    })

        # 2. Collect Text with AGGRESSIVE Filtering
        for text_item in doc.texts:
            if text_item.prov and text_item.prov[0].page_no == page_no:
                bbox = text_item.prov[0].bbox
                text_content = text_item.text.strip()
                
                if not text_content: continue

                # --- The Nuclear Filter ---
                is_chart_junk = False
                for img_bbox in image_bboxes_on_page:
                    overlap = get_overlap_ratio(bbox, img_bbox)
                    
                    # If > 10% of the text touches the image box, KILL IT.
                    # This is aggressive but necessary for org charts where text 
                    # sits exactly on the box lines.
                    if overlap > 0.10: 
                        # EXCEPTION: If it looks like a caption
                        if text_content.lower().startswith(("fig", "tab", "image", "source")):
                            print(f"    - Keeping potential caption inside bbox: '{text_content[:20]}...'")
                        else:
                            is_chart_junk = True
                            # print(f"    - KILLED: '{text_content[:20]}...' (Overlap: {overlap:.2f})")
                            break
                
                if is_chart_junk:
                    continue
                # --------------------------

                top_coord = min(bbox.t, bbox.b)
                page_items.append({
                    "top": top_coord, 
                    "type": "text", 
                    "content": text_content
                })

        # 3. Collect Tables
        for table in doc.tables:
            if table.prov and table.prov[0].page_no == page_no:
                top_coord = min(table.prov[0].bbox.t, table.prov[0].bbox.b)
                html = table.export_to_html()
                page_items.append({
                    "top": top_coord,
                    "type": "table",
                    "content": f"\n{html}\n"
                })

        # 4. Sort strictly by Top Coordinate
        page_items.sort(key=lambda x: x["top"])

        # 5. Generate Markdown
        for item in page_items:
            if item["type"] == "text":
                markdown_lines.append(f"{item['content']}\n\n")
            else:
                markdown_lines.append(item["content"])

        markdown_lines.append("\n---\n")

    output_file = output_dir / f"{pdf_path.stem}_nuclear.md"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("".join(markdown_lines))

    print(f"\n✓ DONE: {output_file}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        convert_pdf_nuclear(sys.argv[1])
    else:
        print("Usage: python script.py <pdf_file>")