from fastapi import FastAPI, UploadFile, File
from docling.document_converter import DocumentConverter
import shutil
import tempfile

app = FastAPI()
converter = DocumentConverter()


@app.post("/extract-text")
async def extract_text(file: UploadFile = File(...)):
    with tempfile.NamedTemporaryFile(delete=False, suffix=file.filename) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    result = converter.convert(tmp_path)
    extracted_text = result.document.export_to_markdown()

    return {"text": extracted_text}