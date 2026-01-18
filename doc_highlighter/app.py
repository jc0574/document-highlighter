import os
import re
import uuid
from flask import Flask, render_template, request, redirect, url_for, abort
import fitz
import docx

app = Flask(__name__)
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXT = {".pdf", ".docx", ".txt"}

def allowed_filename(filename):
    _, ext = os.path.splitext(filename.lower())
    return ext in ALLOWED_EXT

def extract_text_pdf(path):
    doc = fitz.open(path)
    pages = []
    for i in range(len(doc)):
        page_text = doc[i].get_text("text")
        pages.append(page_text)
    return pages

def extract_text_docx(path):
    d = docx.Document(path)
    lines = []
    for p in d.paragraphs:
        lines.append(p.text)
    return ["\n".join(lines)]

def extract_text_txt(path):
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return [f.read()]

def extract_pages(path, ext):
    if ext == ".pdf":
        return extract_text_pdf(path)
    if ext == ".docx":
        return extract_text_docx(path)
    if ext == ".txt":
        return extract_text_txt(path)
    return [""]

def highlight_html(text, query):
    if not query.strip():
        safe = (
            text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
        )
        return safe

    safe = (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
    )

    pattern = re.compile(re.escape(query), re.IGNORECASE)
    return pattern.sub(lambda m: f'<mark class="hit">{m.group(0)}</mark>', safe)

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        abort(400)

    f = request.files["file"]
    query = request.form.get("query", "").strip()

    if not f or not f.filename:
        return redirect(url_for("index"))

    if not allowed_filename(f.filename):
        return "Only PDF, DOCX, TXT are supported.", 400

    _, ext = os.path.splitext(f.filename.lower())
    file_id = str(uuid.uuid4())
    saved_path = os.path.join(UPLOAD_DIR, file_id + ext)
    f.save(saved_path)

    return redirect(url_for("view_doc", file_id=file_id, ext=ext[1:], q=query))

@app.route("/view/<file_id>.<ext>")
def view_doc(file_id, ext):
    query = request.args.get("q", "").strip()
    ext = "." + ext.lower()
    path = os.path.join(UPLOAD_DIR, file_id + ext)

    if not os.path.exists(path):
        return "File not found.", 404

    pages = extract_pages(path, ext)

    rendered_pages = []
    for i, p in enumerate(pages):
        rendered_pages.append({
            "page_num": i + 1,
            "html": highlight_html(p, query)
        })

    return render_template("view.html", pages=rendered_pages, query=query)

if __name__ == "__main__":
    app.run(debug=True)