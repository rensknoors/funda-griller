"""Documents per Listing: upload, re-upload, re-analyse, remove, and the file for the app's own UI."""

from typing import Annotated

from fastapi import APIRouter, File, Response, UploadFile
from fastapi.responses import FileResponse

from app import documents, store
from app.wiring import NotFound, Wiring

# The kind of a Document the user added themselves (the other kind is the funda brochure).
USER_KIND = "user"


def routes(w: Wiring) -> APIRouter:
    router = APIRouter(prefix="/api/listings/{funda_id}/documents")
    settings = w.settings

    def public(funda_id: str, document_id: int) -> dict:
        hidden = {"stored_name", "sha256", "funda_id"}
        return {key: value for key, value in w.document(funda_id, document_id).items() if key not in hidden}

    @router.get("", response_model=None)
    def list_documents(funda_id: str) -> list[dict]:
        w.listing(funda_id)
        return [public(funda_id, d["id"]) for d in store.documents(settings.database_path, funda_id)]

    @router.post("", status_code=201, response_model=None)
    def add_document(funda_id: str, file: Annotated[UploadFile, File()]) -> dict:
        """Add a Document (Vragenlijst, Lijst van zaken, ...) and extract its Findings once."""
        w.listing(funda_id)
        now = w.clock().isoformat()
        name = (file.filename or "Document").strip() or "Document"
        document_id = store.add_document(settings.database_path, funda_id, USER_KIND, name, now)
        documents.store_content(
            settings.database_path, settings.media_dir, funda_id, w.document(funda_id, document_id),
            file.file.read(), w.ports.llm_client, settings.vision_model, now,
        )
        return public(funda_id, document_id)

    @router.put("/{document_id}", response_model=None)
    def replace_document(funda_id: str, document_id: int, file: Annotated[UploadFile, File()]) -> dict:
        """Re-upload: the new file replaces the old one and its Findings."""
        document = w.document(funda_id, document_id)
        if file.filename and document["kind"] == USER_KIND:
            store.update_document(settings.database_path, document_id, name=file.filename.strip() or document["name"])
        documents.store_content(
            settings.database_path, settings.media_dir, funda_id, document, file.file.read(),
            w.ports.llm_client, settings.vision_model, w.clock().isoformat(),
        )
        return public(funda_id, document_id)

    @router.post("/{document_id}/analyse", response_model=None)
    def reanalyse_document(funda_id: str, document_id: int) -> dict:
        """Retry a Document that was not analysed, or whose brochure download failed."""
        document = w.document(funda_id, document_id)
        now = w.clock().isoformat()
        if document["status"] == "download_failed" and w.ports.document_downloader is not None:
            documents.download_and_analyse(
                settings.database_path, settings.media_dir, funda_id, document,
                w.ports.document_downloader, w.ports.llm_client, settings.vision_model, now,
            )
        elif document["status"] != "download_failed":
            documents.analyse(
                settings.database_path, settings.media_dir, funda_id, document_id,
                w.ports.llm_client, settings.vision_model, now,
            )
        return public(funda_id, document_id)

    @router.delete("/{document_id}", status_code=204)
    def remove_document(funda_id: str, document_id: int) -> Response:
        w.discard_document(funda_id, w.document(funda_id, document_id))
        return Response(status_code=204)

    @router.get("/{document_id}/file", response_model=None)
    def read_document_file(funda_id: str, document_id: int) -> FileResponse:
        """The Document itself, for the app's own UI only: shown inline, never offered elsewhere."""
        document = w.document(funda_id, document_id)
        path = store.document_file_path(settings.media_dir, funda_id, document["stored_name"])
        if path is None:
            raise NotFound()
        return FileResponse(
            path,
            media_type="application/pdf",
            content_disposition_type="inline",
            filename=document["name"],
            headers={"Cache-Control": "private, no-store", "X-Robots-Tag": "noindex"},
        )

    return router
