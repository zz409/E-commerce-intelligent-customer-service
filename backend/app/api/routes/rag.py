from pathlib import Path

from fastapi import APIRouter,HTTPException,Response,UploadFile
from fastapi.responses import FileResponse

from app.modules.rag import service

router = APIRouter(
    prefix="/rag",
    tags=["知识库管理"],
)

PDF_DIR = Path(__file__).resolve().parents[3] / "data" / "pdfs"

@router.post("/documents", status_code=201)
def insert_document(file: UploadFile):
    service.insert_document(file.file,file.filename)

@router.get("/documents")
def list_document():
    return service.list_document()

@router.get("/documents/{document_id}/file")
def get_document(document_id):
    path=PDF_DIR/f"{document_id}.pdf"
    return FileResponse(
        path=path,
        media_type="application/pdf",
    )

@router.delete("/documents/{document_id}", status_code=204)
def delete_pdf(document_id):
    service.delete_document(document_id=document_id)