
import os
import json
import pymupdf
import pdfplumber
import pytesseract

pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

from PIL import Image
from io import BytesIO


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOCUMENTS_DIR = os.path.join(BASE_DIR, "documents")
OUTPUT_DIR = os.path.join(BASE_DIR, "reconstructed_documents")

os.makedirs(OUTPUT_DIR, exist_ok=True)


def extract_page_data(pdf_path):
    """Extract text, tables, images and layout information."""

    document_name = os.path.splitext(
        os.path.basename(pdf_path)
    )[0]

    document_output = os.path.join(
        OUTPUT_DIR,
        document_name
    )

    pages_output = os.path.join(
        document_output,
        "pages"
    )

    os.makedirs(pages_output, exist_ok=True)

    extracted_pages = []

    with pymupdf.open(pdf_path) as pdf:
        with pdfplumber.open(pdf_path) as plumber_pdf:

            total_pages = len(pdf)

            for index, page in enumerate(pdf):
                page_number = index + 1

                print(
                    f"Processing {document_name}: "
                    f"page {page_number}/{total_pages}"
                )

                page_data = {
                    "page_number": page_number,
                    "width": page.rect.width,
                    "height": page.rect.height,
                    "text": "",
                    "blocks": [],
                    "tables": [],
                    "images": []
                }

                # ---------------------------------
                # 1. Extract native PDF text blocks
                # ---------------------------------

                blocks = page.get_text("dict")["blocks"]

                for block in blocks:

                    if block.get("type") != 0:
                        continue

                    lines = []

                    font_sizes = []

                    for line in block.get("lines", []):

                        line_text = "".join(
                            span["text"]
                            for span in line.get("spans", [])
                        )

                        lines.append(line_text)

                        font_sizes.extend(
                            span["size"]
                            for span in line.get("spans", [])
                        )

                    block_text = "\n".join(lines)

                    if block_text.strip():

                        page_data["blocks"].append({
                            "text": block_text,
                            "bbox": block.get("bbox"),
                            "font_sizes": font_sizes,
                            "source": "native"
                        })

                # ---------------------------------
                # 2. Extract native page text
                # ---------------------------------

                page_data["text"] = page.get_text(
                    "text",
                    sort=True
                ).strip()

                # ---------------------------------
                # 3. OCR scanned pages
                # ---------------------------------

                if not page_data["text"]:

                    ocr_scale = 2

                    pixmap = page.get_pixmap(
                        matrix=pymupdf.Matrix(
                            ocr_scale,
                            ocr_scale
                        ),
                        alpha=False
                    )

                    image = Image.open(
                        BytesIO(pixmap.tobytes("png"))
                    )

                    ocr_data = pytesseract.image_to_data(
                        image,
                        lang="eng",
                        config="--psm 3",
                        output_type=pytesseract.Output.DICT
                    )

                    lines = {}

                    for i, word in enumerate(ocr_data["text"]):

                        word = word.strip()

                        try:
                            confidence = float(
                                ocr_data["conf"][i]
                            )
                        except (ValueError, TypeError):
                            continue

                        if not word or confidence < 30:
                            continue

                        key = (
                            ocr_data["block_num"][i],
                            ocr_data["par_num"][i],
                            ocr_data["line_num"][i]
                        )

                        x0 = (
                            ocr_data["left"][i] / ocr_scale
                        )

                        y0 = (
                            ocr_data["top"][i] / ocr_scale
                        )

                        x1 = (
                            ocr_data["left"][i]
                            + ocr_data["width"][i]
                        ) / ocr_scale

                        y1 = (
                            ocr_data["top"][i]
                            + ocr_data["height"][i]
                        ) / ocr_scale

                        if key not in lines:

                            lines[key] = {
                                "words": [],
                                "x0": x0,
                                "y0": y0,
                                "x1": x1,
                                "y1": y1,
                                "confidence": []
                            }

                        lines[key]["words"].append(word)

                        lines[key]["x0"] = min(
                            lines[key]["x0"],
                            x0
                        )

                        lines[key]["y0"] = min(
                            lines[key]["y0"],
                            y0
                        )

                        lines[key]["x1"] = max(
                            lines[key]["x1"],
                            x1
                        )

                        lines[key]["y1"] = max(
                            lines[key]["y1"],
                            y1
                        )

                        lines[key]["confidence"].append(
                            confidence
                        )

                    page_text_lines = []

                    for line in lines.values():

                        line_text = " ".join(
                            line["words"]
                        )

                        page_text_lines.append(line_text)

                        average_confidence = (
                            sum(line["confidence"])
                            / len(line["confidence"])
                        )

                        page_data["blocks"].append({
                            "text": line_text,
                            "bbox": [
                                line["x0"],
                                line["y0"],
                                line["x1"],
                                line["y1"]
                            ],
                            "confidence": round(
                                average_confidence,
                                2
                            ),
                            "source": "ocr"
                        })

                    page_data["text"] = "\n".join(
                        page_text_lines
                    ).strip()

                # ---------------------------------
                # 4. Extract tables
                # ---------------------------------

                plumber_page = plumber_pdf.pages[index]

                try:

                    tables = plumber_page.extract_tables()

                    for table in tables:
                        page_data["tables"].append(table)

                except Exception as error:

                    print(
                        f"Table extraction warning on page "
                        f"{page_number}: {error}"
                    )

                # ---------------------------------
                # 5. Extract embedded images
                # ---------------------------------

                for image_index, image_info in enumerate(
                    page.get_images(full=True),
                    start=1
                ):

                    xref = image_info[0]

                    try:

                        image_rects = page.get_image_rects(
                            xref
                        )

                        page_area = (
                            page.rect.width * page.rect.height
                        )

                        is_full_page_image = any(
                            (rect.width * rect.height)
                            >= page_area * 0.90
                            for rect in image_rects
                        )

                        if is_full_page_image:

                            print(
                                f"Skipping full-page image on "
                                f"page {page_number}"
                            )

                            continue

                        extracted_image = pdf.extract_image(
                            xref
                        )

                        image_bytes = extracted_image["image"]

                        extension = extracted_image["ext"]

                        image_filename = (
                            f"page_{page_number}_image_"
                            f"{image_index}.{extension}"
                        )

                        image_path = os.path.join(
                            pages_output,
                            image_filename
                        )

                        with open(
                            image_path,
                            "wb"
                        ) as image_file:

                            image_file.write(image_bytes)

                        page_data["images"].append({
                            "filename": image_filename,
                            "width": extracted_image["width"],
                            "height": extracted_image["height"],
                            "positions": [
                                list(rect)
                                for rect in image_rects
                            ]
                        })

                    except Exception as error:

                        print(
                            f"Image extraction warning: {error}"
                        )

                # ---------------------------------
                # 6. Save original page preview
                # ---------------------------------

                preview_path = os.path.join(
                    pages_output,
                    f"page_{page_number}.png"
                )

                page.get_pixmap(
                    matrix=pymupdf.Matrix(1.5, 1.5),
                    alpha=False
                ).save(preview_path)

                extracted_pages.append(page_data)

    # ---------------------------------
    # 7. Save extracted data as JSON
    # ---------------------------------

    json_path = os.path.join(
        document_output,
        "document_data.json"
    )

    with open(
        json_path,
        "w",
        encoding="utf-8"
    ) as json_file:

        json.dump(
            extracted_pages,
            json_file,
            ensure_ascii=False,
            indent=2
        )

    print(f"\nCompleted: {document_name}")

    print(
        f"Pages extracted: {len(extracted_pages)}"
    )

    print(
        f"Output: {document_output}"
    )

    return {
        "document": document_name,
        "pages": len(extracted_pages),
        "output": document_output
    }


def main():

    documents = [
        "tata_tender.pdf",
        "company_document.pdf"
    ]

    results = []

    for filename in documents:

        pdf_path = os.path.join(
            DOCUMENTS_DIR,
            filename
        )

        if not os.path.isfile(pdf_path):

            print(
                f"PDF not found: {filename}"
            )

            continue

        try:

            result = extract_page_data(pdf_path)

            results.append(result)

        except Exception as error:

            print(
                f"Failed to process {filename}: {error}"
            )

    print("\n========== FINAL SUMMARY ==========")

    for result in results:

        print(
            f"{result['document']}: "
            f"{result['pages']} pages processed"
        )


if __name__ == "__main__":
    main()
