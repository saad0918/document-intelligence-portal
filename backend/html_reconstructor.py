
import os
import json
import html

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

OUTPUT_DIR = os.path.join(
    BASE_DIR,
    "reconstructed_documents"
)

DOCUMENTS = [
    "tata_tender",
    "company_document"
]


def safe(value):
    """Escape text before inserting it into HTML."""
    return html.escape(str(value or ""))


def make_page_content(page_data):
    width = float(page_data["width"])
    height = float(page_data["height"])
    page_number = int(page_data["page_number"])

    elements = []

    background_image = f"../pages/page_{page_number}.png"

    for block in page_data.get("blocks", []):

        bbox = block.get("bbox")

        if not bbox or len(bbox) != 4:
            continue

        x0, y0, x1, y1 = map(float, bbox)

        block_width = max(1, x1 - x0)
        block_height = max(1, y1 - y0)

        original_text = str(block.get("text", ""))

        if not original_text.strip():
            continue

        text = safe(original_text)

        font_sizes = block.get("font_sizes", [])

        if font_sizes:
            font_size = sum(font_sizes) / len(font_sizes)
        else:
            font_size = max(5, block_height * 0.75)

        font_size = max(5, min(font_size, 40))

        elements.append(
            f"""
            <div
                class="text-layer"
                data-text="{safe(original_text)}"
                style="
                    left: {x0}px;
                    top: {y0}px;
                    width: {block_width}px;
                    height: {block_height}px;
                    font-size: {font_size}px;
                "
            >{text.replace(chr(10), '<br>')}</div>
            """
        )

    return f"""
    <section
        class="document-page"
        id="page-{page_number}"
        data-page="{page_number}"
    >
        <div
            class="page"
            style="
                width: {width}px;
                height: {height}px;
            "
        >
            <img
                class="page-background"
                src="{background_image}"
                alt="Original PDF page {page_number}"
            >

            {''.join(elements)}
        </div>
    </section>
    """


def make_document_html(document_name, pages):

    page_sections = []

    for page_data in pages:
        page_sections.append(make_page_content(page_data))

    return f"""
    <!DOCTYPE html>
    <html lang="en">

    <head>
        <meta charset="UTF-8">

        <meta
            name="viewport"
            content="width=device-width, initial-scale=1.0"
        >

        <title>{safe(document_name)} - Complete Document</title>

        <style>

            * {{
                box-sizing: border-box;
            }}

            html {{
                scroll-behavior: smooth;
                scroll-padding-top: 20px;
            }}

            body {{
                margin: 0;
                padding: 24px;
                background: #e9edf3;
                font-family: Arial, sans-serif;
            }}

            .document-container {{
                width: 100%;
                display: flex;
                flex-direction: column;
                align-items: center;
                gap: 24px;
            }}

            .document-page {{
                width: 100%;
                display: flex;
                justify-content: center;
                scroll-margin-top: 20px;
            }}

            .page {{
                position: relative;
                flex-shrink: 0;
                background: white;
                overflow: hidden;
                box-shadow: 0 4px 18px rgba(0, 0, 0, 0.14);
            }}

            .page-background {{
                position: absolute;
                inset: 0;
                width: 100%;
                height: 100%;
                object-fit: fill;
                z-index: 1;
                pointer-events: none;
            }}

            .text-layer {{
                position: absolute;
                z-index: 2;
                color: transparent;
                background: transparent;
                font-family: Arial, sans-serif;
                font-weight: normal;
                line-height: 1.12;
                white-space: pre-wrap;
                overflow-wrap: break-word;
                cursor: text;
                user-select: text;
                -webkit-user-select: text;
            }}

            .text-layer::selection {{
                color: transparent;
                background: rgba(0, 120, 255, 0.35);
            }}

            @media (max-width: 700px) {{
                body {{
                    padding: 12px;
                }}

                .document-container {{
                    align-items: flex-start;
                }}

                .document-page {{
                    justify-content: flex-start;
                    overflow-x: auto;
                }}
            }}

            @media print {{
                body {{
                    padding: 0;
                    background: white;
                }}

                .document-container {{
                    gap: 0;
                }}

                .page {{
                    box-shadow: none;
                }}

                .document-page {{
                    page-break-after: always;
                }}
            }}

        </style>
    </head>

    <body>

        <main class="document-container">

            {''.join(page_sections)}

        </main>

    </body>

    </html>
    """


def main():

    for document_name in DOCUMENTS:

        document_dir = os.path.join(
            OUTPUT_DIR,
            document_name
        )

        json_path = os.path.join(
            document_dir,
            "document_data.json"
        )

        if not os.path.isfile(json_path):
            print(f"Missing JSON: {json_path}")
            continue

        with open(json_path, "r", encoding="utf-8") as file:
            pages = json.load(file)

        html_dir = os.path.join(
            document_dir,
            "html_pages"
        )

        os.makedirs(html_dir, exist_ok=True)

        print(f"\nRebuilding {document_name}...")

        # Generate individual HTML pages
        for page_data in pages:

            page_number = int(page_data["page_number"])

            page_html = make_document_html(
                document_name,
                [page_data]
            )

            output_path = os.path.join(
                html_dir,
                f"page_{page_number}.html"
            )

            with open(output_path, "w", encoding="utf-8") as file:
                file.write(page_html)

            print(
                f"Generated individual page {page_number}/{len(pages)}"
            )

        # Generate one continuous HTML document
        complete_html = make_document_html(
            document_name,
            pages
        )

        index_path = os.path.join(
            html_dir,
            "index.html"
        )

        with open(index_path, "w", encoding="utf-8") as file:
            file.write(complete_html)

        print(f"Generated continuous document: {index_path}")
        print(f"Completed: {document_name}")


if __name__ == "__main__":
    main()
