from flask import Flask, render_template, request, send_file, jsonify
from pypdf import PdfReader, PdfWriter, PageObject, Transformation

import os
import tempfile
import threading
import zipfile
import uuid

app = Flask(__name__)

UPLOAD_FOLDER = tempfile.gettempdir()
OUTPUT_FOLDER = tempfile.gettempdir()

progress = {
    "current": 0,
    "total": 0,
    "percent": 0,
    "completed": False,
    "zip_file": ""
}


@app.route("/")
def index():
    return render_template("index.html")


def process_single_pdf(
    input_file,
    output_file,
    top,
    bottom,
    left,
    right
):
    reader = PdfReader(input_file)
    writer = PdfWriter()

    for page in reader.pages:

        page.transfer_rotation_to_content()

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

    with open(output_file, "wb") as f:
        writer.write(f)


def process_multiple_files(
    files_data,
    top,
    bottom,
    left,
    right,
    zip_path
):
    global progress

    processed_pages = 0

    with zipfile.ZipFile(
        zip_path,
        "w",
        zipfile.ZIP_DEFLATED
    ) as zipf:

        for item in files_data:

            process_single_pdf(
                item["input"],
                item["output"],
                top,
                bottom,
                left,
                right
            )

            zipf.write(
                item["output"],
                arcname=os.path.basename(item["output"])
            )

            processed_pages += item["pages"]

            progress["current"] = processed_pages
            progress["percent"] = int(
                (processed_pages / progress["total"]) * 100
            )

    progress["completed"] = True
    progress["percent"] = 100


@app.route("/upload", methods=["POST"])
def upload():

    global progress

    pdf_files = request.files.getlist("pdfs")

    if not pdf_files:
        return jsonify({
            "error": "لم يتم اختيار ملفات"
        }), 400

    top = float(request.form.get("top", 0)) * 72
    bottom = float(request.form.get("bottom", 0)) * 72
    left = float(request.form.get("left", 0)) * 72
    right = float(request.form.get("right", 0)) * 72

    session_id = str(uuid.uuid4())

    zip_path = os.path.join(
        OUTPUT_FOLDER,
        f"{session_id}.zip"
    )

    files_data = []
    total_pages = 0

    for pdf_file in pdf_files:

        filename = pdf_file.filename

        input_file = os.path.join(
            UPLOAD_FOLDER,
            f"{session_id}_{filename}"
        )

        output_file = os.path.join(
            OUTPUT_FOLDER,
            f"margins_{filename}"
        )

        pdf_file.save(input_file)

        reader = PdfReader(input_file)
        pages_count = len(reader.pages)

        total_pages += pages_count

        files_data.append({
            "input": input_file,
            "output": output_file,
            "pages": pages_count
        })

    progress = {
        "current": 0,
        "total": total_pages,
        "percent": 0,
        "completed": False,
        "zip_file": zip_path
    }

    threading.Thread(
        target=process_multiple_files,
        args=(
            files_data,
            top,
            bottom,
            left,
            right,
            zip_path
        ),
        daemon=True
    ).start()

    return jsonify({
        "success": True
    })


@app.route("/progress")
def get_progress():
    return jsonify(progress)


@app.route("/download")
def download():

    if not progress["completed"]:
        return jsonify({
            "error": "الملف غير جاهز بعد"
        }), 400

    return send_file(
        progress["zip_file"],
        as_attachment=True,
        download_name="pdf_with_margins.zip"
    )


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )