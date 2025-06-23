import io
import os
import re
import tempfile
from datetime import datetime

import markdown  # Import the markdown library
from fpdf import FPDF
from fpdf.enums import XPos, YPos  # Add this import if not present
from PIL import Image
from pydantic import BaseModel

from src.general import FONT_PATH, LOGO_PATH, navy_hex, peach_hex


def markdown_to_simple_html(md: str) -> str:
    # Replace all asterisks (*) with nothing
    md = md.replace("*", "")
    html = markdown.markdown(md, extensions=["fenced_code", "tables"])
    # Remove all styles/scripts
    html = re.sub(r"<style.*?>.*?</style>", "", html, flags=re.DOTALL)
    html = re.sub(r"<script.*?>.*?</script>", "", html, flags=re.DOTALL)
    # Remove all attributes
    html = re.sub(r"<(\w+)[^>]*>", r"<\1>", html)
    return html


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Converts a hex color string to an (R, G, B) tuple."""
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))


def get_html_style() -> str:
    """Defines a basic CSS style for the HTML content."""
    text_color = "#323232"  # Dark Gray
    return f"""
    <style>
        p {{ 
            margin: 0 0 5px 0; 
            line-height: 1.5;
            color: {text_color};
        }}
        ul, ol {{ 
            margin: 0 0 10px 0; 
            padding-left: 20px; 
            color: {text_color};
        }}
        li {{ 
            margin-bottom: 3px; 
        }}
        h1, h2, h3, h4, h5, h6 {{
            margin-bottom: 5px;
            font-weight: bold;
        }}
    </style>
    """


class ReportSection(BaseModel):
    heading: str
    main_body_text: str
    png_img: bytes | None


# The PDF class now also inherits from HTMLMixin
class PDF(FPDF):  # new
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.brand_navy_rgb = hex_to_rgb(navy_hex)
        self.brand_peach_rgb = hex_to_rgb(peach_hex)
        self.text_color_rgb = (50, 50, 50)

    def header(self):
        if self.page_no() == 1:
            return
        w_logo = 20
        try:
            self.image(LOGO_PATH, x=10, y=8, w=w_logo)
        except FileNotFoundError:
            self.set_font("DejaVu", "B", 12)
            self.cell(30, 10, "[Logo]", 0, 0, "L")
        self.set_font("DejaVu", "B", 15)
        self.set_text_color(*self.brand_navy_rgb)
        self.cell(
            0, 10, "Turri.Cr Report", 0, new_x=XPos.RIGHT, new_y=YPos.TOP, align="C"
        )
        self.ln(20)
        self.set_draw_color(*self.brand_peach_rgb)
        self.line(10, 30, 200, 30)

    def footer(self):
        self.set_y(-15)
        self.set_font("DejaVu", "I", 8)
        self.set_text_color(128)
        self.cell(
            0,
            10,
            f"Page {self.page_no()}/{{nb}}",
            0,
            new_x=XPos.RIGHT,
            new_y=YPos.TOP,
            align="C",
        )

    def add_title_page(self):
        self.add_page()
        self.ln(20)  # Padding before logo/title
        try:
            logo_w = 40
            logo_x = (self.w - logo_w) / 2
            self.image(LOGO_PATH, x=logo_x, y=self.get_y(), w=logo_w)
            self.ln(logo_w + 10)  # Padding after logo
        except FileNotFoundError:
            self.set_font("DejaVu", "B", 20)
            self.cell(0, 10, "[Turri.Cr Logo]", 0, 1, "C")
            self.ln(20)  # Padding after placeholder

        self.set_font("DejaVu", "B", 28)
        self.set_text_color(*self.brand_navy_rgb)
        self.cell(
            0, 20, "Turri.Cr Report", 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C"
        )
        self.ln(15)  # More padding after title

        self.set_font("DejaVu", "", 12)
        self.set_text_color(*self.text_color_rgb)
        self.cell(
            0,
            10,
            f"Generated on: {datetime.now().strftime('%B %d, %Y')}",
            0,
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
            align="C",
        )

    def add_report_section(
        self,
        section: ReportSection,
    ):
        self.add_page()

        # Section Heading
        self.set_font("DejaVu", "B", 16)
        self.set_text_color(*self.brand_navy_rgb)
        self.multi_cell(0, 10, section.heading, 0, "L")
        self.ln(5)

        # --- NEW: Convert Markdown to HTML and write it ---
        # Set default font for the HTML content
        self.set_font("DejaVu", "", 10)

        # Convert markdown to HTML
        # Combine with our CSS styles
        self.write_html(markdown_to_simple_html(section.main_body_text))
        # --- End of new section ---

        self.ln(5)

        # Image (no changes here)
        if section.png_img:
            try:
                img = Image.open(io.BytesIO(section.png_img))
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                    img.save(tmp.name, format="PNG")
                    path = tmp.name
                img_w = 170
                img_x = (self.w - img_w) / 2
                self.image(path, x=img_x, w=img_w)
                os.remove(path)
            except Exception as e:
                self.set_font("DejaVu", "I", 9)
                self.set_text_color(255, 0, 0)
                self.cell(0, 10, f"[Error rendering image: {e}]")


def generate_report_pdf_bytes(sections: list[ReportSection]) -> bytes:
    """
    Generates a styled PDF report, rendering Markdown content to HTML.
    """
    pdf = PDF()
    pdf.alias_nb_pages()

    pdf.add_font("DejaVu", "", FONT_PATH)
    pdf.add_font("DejaVu", "B", FONT_PATH)
    pdf.add_font("DejaVu", "I", FONT_PATH)

    pdf.add_title_page()

    for section in sections:
        pdf.add_report_section(section)

    # Fix PDF output to bytes using BytesIO
    from io import BytesIO

    buf = BytesIO()
    pdf.output(buf)
    pdf_bytes = buf.getvalue()
    return pdf_bytes


# --- EXAMPLE USAGE ---
if __name__ == "__main__":
    # Sample markdown content from an LLM
    sample_markdown = """
This is a paragraph describing the sales performance. The results have been **very encouraging** this quarter.

Key takeaways include:
*   *Increased sales* in the northern region.
*   A 15% growth in the *Kombucha Limón Jengibre* product line.
*   Consistent performance from our best-seller.

### Next Steps
1.  Focus marketing efforts on the southern region.
2.  Consider a new flavor launch for Q4.
3.  Re-evaluate supply chain for cost savings.
"""
    sample_image_bytes = None  # For this example

    # Create the sections list
    report_sections = [
        ReportSection(
            heading="Sales Performance Analysis",
            main_body_text=sample_markdown,
            png_img=sample_image_bytes,
        ),
        ReportSection(
            heading="Another Section",
            main_body_text="This section has no image and just plain text.",
            png_img=None,
        ),
    ]

    # Generate the PDF
    pdf_data = generate_report_pdf_bytes(report_sections)

    # Save it to a file
    with open("styled_markdown_report.pdf", "wb") as f:
        f.write(pdf_data)

    print("Successfully generated 'styled_markdown_report.pdf'")
