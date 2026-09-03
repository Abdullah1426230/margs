from flask import Flask, render_template, request, send_file
from pypdf import PdfReader, PdfWriter, PageObject, Transformation

import os
import sys

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "output"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


@app.route("/")
def index():
    return render_template("index.html")


def process_pdf(
    input_file,
    output_file,
    top,
    bottom,
    left,
    right
):
    reader = PdfReader(input_file)
    writer = PdfWriter()

    total_pages = len(reader.pages)

    for i, page in enumerate(reader.pages, start=1):

        old_width = float(page.mediabox.width)
        old_height = float(page.mediabox.height)

        new_width = old_width + left + right
        new_height = old_height + top + bottom

        new_page = PageObject.create_blank_page(
            width=new_width,
            height=new_height
        )

        new_page.merge_transformed_page(
            page,
            Transformation().translate(
                tx=left,
                ty=bottom
            )
        )

        writer.add_page(new_page)

        print(f"Processing {i}/{total_pages}")

    with open(output_file, "wb") as f:
        writer.write(f)


@app.route("/upload", methods=["POST"])
def upload():

    if "pdf" not in request.files:
        return {"error": "No file selected"}, 400

    pdf_file = request.files["pdf"]

    input_file = os.path.join(
        UPLOAD_FOLDER,
        "input.pdf"
    )

    output_file = os.path.join(
        OUTPUT_FOLDER,
        "pdf_with_margins.pdf"
    )

    pdf_file.save(input_file)

    top = float(request.form.get("top", 0)) * 72
    bottom = float(request.form.get("bottom", 0)) * 72
    left = float(request.form.get("left", 0)) * 72
    right = float(request.form.get("right", 0)) * 72

    process_pdf(
        input_file,
        output_file,
        top,
        bottom,
        left,
        right
    )

    return send_file(
        output_file,
        as_attachment=True,
        download_name="pdf_with_margins.pdf"
    )


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )