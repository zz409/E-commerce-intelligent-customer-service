from uuid import UUID

from fastapi import APIRouter,HTTPException,Response,UploadFile
from fastapi.responses import FileResponse

from app.modules.rag import service

router = APIRouter(
    prefix="/knowledge",
    tags=["知识库管理"],
)


@router.post("/documents", status_code=201)
def upload_pdf(file: UploadFile):
    try:
        return service.upload_pdf(
            filename=file.filename or "document.pdf",
            source=file.file,
        )
    finally:
        file.file.close()


@router.get("/documents")
def list_pdfs():
    return service.list_pdfs()


@router.get("/documents/{document_id}/file")
def read_pdf(document_id: UUID):
    document, path = service.get_pdf(document_id.hex)

    if document is None or not path.is_file():
        raise HTTPException(404, "PDF 不存在")

    return FileResponse(
        path=path,
        media_type="application/pdf",
        filename=document["filename"],
        content_disposition_type="inline",
    )


@router.delete("/documents/{document_id}", status_code=204)
def delete_pdf(document_id: UUID):
    service.delete_pdf(document_id.hex)
    return Response(status_code=204)