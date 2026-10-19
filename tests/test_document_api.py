"""
Automated Integration Tests for TechSift AI Document Management API (Phase 1).
Validates uploads, validations, extractions, deletions, storage cleanup, and pagination.
"""

from pathlib import Path
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.config import settings
from src.services.storage_service import storage_service


@pytest.mark.asyncio
async def test_api_v1_health(client: AsyncClient):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app"] == "TechSift AI"


@pytest.mark.asyncio
async def test_upload_valid_pdf(client: AsyncClient, sample_pdf_bytes: bytes):
    files = {"file": ("architecture_spec.pdf", sample_pdf_bytes, "application/pdf")}
    response = await client.post("/api/v1/documents", files=files)

    assert response.status_code == 201
    data = response.json()
    assert data["filename"] == "architecture_spec.pdf"
    assert data["file_type"] == "pdf"
    assert data["status"] == "processed"
    assert data["page_count"] == 1
    assert data["word_count"] > 5
    assert "id" in data
    assert "storage_path" not in data  # Never expose internal filesystem paths
    assert "storage_filename" not in data


@pytest.mark.asyncio
async def test_upload_valid_txt(client: AsyncClient):
    txt_content = b"TechSift AI is a zero-cost technical document analyzer. It runs locally."
    files = {"file": ("notes.txt", txt_content, "text/plain")}
    response = await client.post("/api/v1/documents", files=files)

    assert response.status_code == 201
    data = response.json()
    assert data["filename"] == "notes.txt"
    assert data["file_type"] == "txt"
    assert data["status"] == "processed"
    assert data["word_count"] == 11


@pytest.mark.asyncio
async def test_upload_valid_markdown(client: AsyncClient):
    md_content = b"# Distributed Consensus\n\n- Leader election\n- Log replication\n- Safety"
    files = {"file": ("consensus.md", md_content, "text/markdown")}
    response = await client.post("/api/v1/documents", files=files)

    assert response.status_code == 201
    data = response.json()
    assert data["filename"] == "consensus.md"
    assert data["file_type"] == "md"
    assert data["status"] == "processed"
    assert data["word_count"] > 3


@pytest.mark.asyncio
async def test_upload_scanned_image_pdf_handling(client: AsyncClient, scanned_pdf_bytes: bytes):
    files = {"file": ("scanned_manual.pdf", scanned_pdf_bytes, "application/pdf")}
    response = await client.post("/api/v1/documents", files=files)

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "unsupported"
    assert "Scanned or image-only PDF" in data["error_message"]
    assert "OCR is not supported" in data["error_message"]


@pytest.mark.asyncio
async def test_upload_invalid_extension(client: AsyncClient):
    files = {"file": ("malware.exe", b"binary_data_here", "application/octet-stream")}
    response = await client.post("/api/v1/documents", files=files)

    assert response.status_code == 400
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "INVALID_FILE_FORMAT"
    assert "Unsupported file extension" in data["error"]["message"]


@pytest.mark.asyncio
async def test_upload_fake_pdf_signature(client: AsyncClient):
    # Extension says .pdf but content is arbitrary text without %PDF- magic bytes
    files = {"file": ("fake.pdf", b"This is not a real PDF file", "application/pdf")}
    response = await client.post("/api/v1/documents", files=files)

    assert response.status_code == 400
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "INVALID_FILE_FORMAT"
    assert "%PDF-" in data["error"]["message"]


@pytest.mark.asyncio
async def test_upload_empty_file(client: AsyncClient):
    files = {"file": ("empty.txt", b"", "text/plain")}
    response = await client.post("/api/v1/documents", files=files)

    assert response.status_code == 400
    data = response.json()
    assert data["success"] is False
    assert "empty" in data["error"]["message"]


@pytest.mark.asyncio
async def test_upload_oversized_file(client: AsyncClient, monkeypatch):
    # Set limit to 50 bytes for test
    monkeypatch.setattr(settings, "MAX_UPLOAD_SIZE_BYTES", 50)
    large_content = b"A" * 100
    files = {"file": ("large.txt", large_content, "text/plain")}
    response = await client.post("/api/v1/documents", files=files)

    assert response.status_code == 413
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "FILE_TOO_LARGE"


@pytest.mark.asyncio
async def test_get_document_detail_and_not_found(client: AsyncClient):
    # 1. Upload
    content = b"Architecture analysis text for retrieval test."
    files = {"file": ("detail.txt", content, "text/plain")}
    upload_res = await client.post("/api/v1/documents", files=files)
    doc_id = upload_res.json()["id"]

    # 2. Get by ID
    get_res = await client.get(f"/api/v1/documents/{doc_id}")
    assert get_res.status_code == 200
    detail = get_res.json()
    assert detail["id"] == doc_id
    assert detail["extracted_text"] == content.decode()

    # 3. Not Found
    non_existent = "00000000-0000-0000-0000-000000000000"
    missing_res = await client.get(f"/api/v1/documents/{non_existent}")
    assert missing_res.status_code == 404
    assert missing_res.json()["error"]["code"] == "RESOURCE_NOT_FOUND"


@pytest.mark.asyncio
async def test_list_documents_pagination(client: AsyncClient):
    # Upload 3 items
    for i in range(3):
        files = {"file": (f"doc_{i}.txt", f"Content {i}".encode(), "text/plain")}
        await client.post("/api/v1/documents", files=files)

    # Page 1, size 2
    res_p1 = await client.get("/api/v1/documents?page=1&page_size=2")
    assert res_p1.status_code == 200
    data_p1 = res_p1.json()
    assert len(data_p1["items"]) == 2
    assert data_p1["pagination"]["total"] >= 3
    assert data_p1["pagination"]["page"] == 1
    assert data_p1["pagination"]["total_pages"] >= 2

    # Page 2, size 2
    res_p2 = await client.get("/api/v1/documents?page=2&page_size=2")
    assert res_p2.status_code == 200
    data_p2 = res_p2.json()
    assert len(data_p2["items"]) >= 1


@pytest.mark.asyncio
async def test_delete_document_and_local_storage_cleanup(client: AsyncClient):
    # 1. Upload
    content = b"Content to be deleted from both database and disk."
    files = {"file": ("to_delete.txt", content, "text/plain")}
    upload_res = await client.post("/api/v1/documents", files=files)
    doc_id = upload_res.json()["id"]

    # Verify physical file exists in storage
    files_in_storage_before = list(storage_service.base_dir.glob("*"))
    assert len(files_in_storage_before) >= 1

    # 2. Delete via API
    del_res = await client.delete(f"/api/v1/documents/{doc_id}")
    assert del_res.status_code == 200
    assert del_res.json()["success"] is True

    # 3. Assert document is gone from database
    get_res = await client.get(f"/api/v1/documents/{doc_id}")
    assert get_res.status_code == 404

    # 4. Assert physical file is deleted from local disk
    files_in_storage_after = list(storage_service.base_dir.glob("*"))
    assert len(files_in_storage_after) == len(files_in_storage_before) - 1


@pytest.mark.asyncio
async def test_path_traversal_sanitization(client: AsyncClient):
    malicious_filename = "../../../etc/passwd.txt"
    files = {"file": (malicious_filename, b"safe content", "text/plain")}
    upload_res = await client.post("/api/v1/documents", files=files)

    assert upload_res.status_code == 201
    doc_data = upload_res.json()
    assert ".." not in doc_data["filename"]
    assert doc_data["filename"] == "passwd.txt"


@pytest.mark.asyncio
async def test_read_upload_stream_aborts_during_streaming():
    """Verifies that streaming upload aborts immediately without loading remaining chunks."""
    from unittest.mock import AsyncMock
    from fastapi import UploadFile
    from src.core.exceptions import FileTooLargeError
    from src.services.document_service import read_upload_stream_with_size_limit

    # Mock an UploadFile with 10 chunks of 100 bytes each (total 1000 bytes)
    mock_file = AsyncMock(spec=UploadFile)
    chunk_data = b"X" * 100
    # Simulate an endless or long stream
    mock_file.read.side_effect = [chunk_data, chunk_data, chunk_data, chunk_data, b""]

    # Limit is 150 bytes, chunk is 100 bytes -> must abort on chunk 2 (200 bytes)
    with pytest.raises(FileTooLargeError) as exc_info:
        await read_upload_stream_with_size_limit(mock_file, max_size=150, chunk_size=100)

    assert exc_info.value.status_code == 413
    # Verify it stopped reading and did NOT call read() for remaining chunks
    assert mock_file.read.call_count == 2


@pytest.mark.asyncio
async def test_upload_partial_failure_storage_cleanup(client: AsyncClient, monkeypatch):
    """
    Verifies that if database insertion fails after writing to local storage,
    the storage file is cleaned up and no orphaned file is left on disk.
    """
    from unittest.mock import AsyncMock
    from src.repositories.document_repository import DocumentRepository

    # Mock doc_repo.create to raise an unexpected database exception
    async def failing_create(self, document):
        raise RuntimeError("Simulated SQLite disk write failure")

    monkeypatch.setattr(DocumentRepository, "create", failing_create)

    storage_before = list(storage_service.base_dir.glob("*"))

    files = {"file": ("rollback_test.txt", b"Rollback content", "text/plain")}
    response = await client.post("/api/v1/documents", files=files)

    assert response.status_code == 500
    # Storage should have zero orphaned files created
    storage_after = list(storage_service.base_dir.glob("*"))
    assert len(storage_after) == len(storage_before)


@pytest.mark.asyncio
async def test_delete_document_cleans_up_associated_audio_files(client: AsyncClient):
    """
    Regression Test (Phase 4C):
    Ensures that deleting a document purges both the source document and all
    associated generated audio files from storage/audio/.
    """
    import uuid
    from pathlib import Path
    from src.db.session import async_session_maker
    from src.models.audio_track import AudioTrack

    # 1. Upload document
    files = {"file": ("audio_cleanup_test.txt", b"Document with associated audio.", "text/plain")}
    upload_res = await client.post("/api/v1/documents", files=files)
    doc_id = upload_res.json()["id"]

    # 2. Create physical audio file in settings.AUDIO_DIR
    audio_dir = settings.AUDIO_DIR.resolve()
    audio_dir.mkdir(parents=True, exist_ok=True)
    audio_filename = f"test_cleanup_{uuid.uuid4()}.mp3"
    audio_file_path = audio_dir / audio_filename
    audio_file_path.write_bytes(b"dummy mp3 data for deletion test")
    assert audio_file_path.exists()

    # 3. Associate an AudioTrack with this document in the database
    async with async_session_maker() as session:
        track = AudioTrack(
            document_id=doc_id,
            mode="narration",
            language="en",
            voice_config={"voice": "en-US-GuyNeural"},
            file_path=f"audio/{audio_filename}",
            status="completed",
            config_hash=f"hash_{uuid.uuid4()}",
        )
        session.add(track)
        await session.commit()

    # 4. Delete document via API
    del_res = await client.delete(f"/api/v1/documents/{doc_id}")
    assert del_res.status_code == 200
    assert del_res.json()["success"] is True

    # 5. Verify the audio file was purged from disk
    assert not audio_file_path.exists()


@pytest.mark.asyncio
async def test_delete_document_handles_missing_audio_files_safely(client: AsyncClient):
    """
    Regression Test (Phase 4C):
    Verifies that if an audio file referenced in DB is missing from disk,
    document deletion succeeds safely without raising errors.
    """
    import uuid
    from src.db.session import async_session_maker
    from src.models.audio_track import AudioTrack

    # 1. Upload document
    files = {"file": ("missing_audio_test.txt", b"Doc with non-existent audio file.", "text/plain")}
    upload_res = await client.post("/api/v1/documents", files=files)
    doc_id = upload_res.json()["id"]

    # 2. Insert AudioTrack pointing to non-existent file
    async with async_session_maker() as session:
        track = AudioTrack(
            document_id=doc_id,
            mode="narration",
            language="en",
            voice_config={"voice": "en-US-GuyNeural"},
            file_path=f"audio/non_existent_file_{uuid.uuid4()}.mp3",
            status="completed",
            config_hash=f"hash_{uuid.uuid4()}",
        )
        session.add(track)
        await session.commit()

    # 3. Delete document via API - should succeed safely
    del_res = await client.delete(f"/api/v1/documents/{doc_id}")
    assert del_res.status_code == 200
    assert del_res.json()["success"] is True


@pytest.mark.asyncio
async def test_delete_document_rejects_audio_path_outside_storage_and_rolls_back(client: AsyncClient):
    """
    Regression Test (Phase 4C):
    Verifies that if an audio track points outside the permitted audio directory,
    deletion is aborted with StorageError, no files are deleted, and DB transaction is rolled back.
    """
    import uuid
    from src.db.session import async_session_maker
    from src.models.audio_track import AudioTrack

    # 1. Upload document
    files = {"file": ("traversal_delete_test.txt", b"Document content.", "text/plain")}
    upload_res = await client.post("/api/v1/documents", files=files)
    doc_id = upload_res.json()["id"]

    # 2. Insert AudioTrack with unsafe relative traversal path
    async with async_session_maker() as session:
        track = AudioTrack(
            document_id=doc_id,
            mode="narration",
            language="en",
            voice_config={"voice": "en-US-GuyNeural"},
            file_path="../../../etc/passwd",
            status="completed",
            config_hash=f"hash_{uuid.uuid4()}",
        )
        session.add(track)
        await session.commit()

    # 3. Attempt document deletion - must fail with 500 STORAGE_ERROR
    del_res = await client.delete(f"/api/v1/documents/{doc_id}")
    assert del_res.status_code == 500
    assert del_res.json()["error"]["code"] == "STORAGE_ERROR"

    # 4. Verify document still exists in DB (transaction rolled back)
    get_res = await client.get(f"/api/v1/documents/{doc_id}")
    assert get_res.status_code == 200

    # Cleanup test record
    async with async_session_maker() as session:
        from sqlalchemy import delete
        await session.execute(delete(AudioTrack).where(AudioTrack.document_id == doc_id))
        await session.commit()
    await client.delete(f"/api/v1/documents/{doc_id}")


@pytest.mark.asyncio
async def test_delete_document_aborts_and_rolls_back_if_filesystem_deletion_fails(client: AsyncClient, monkeypatch):
    """
    Regression Test (Phase 4C):
    Verifies that if unlinking a derived audio file fails with an OSError,
    deletion is aborted with StorageError and DB transaction is rolled back.
    """
    import uuid
    from pathlib import Path
    from src.db.session import async_session_maker
    from src.models.audio_track import AudioTrack

    # 1. Upload document
    files = {"file": ("fs_fail_test.txt", b"Test content.", "text/plain")}
    upload_res = await client.post("/api/v1/documents", files=files)
    doc_id = upload_res.json()["id"]

    audio_dir = settings.AUDIO_DIR.resolve()
    audio_dir.mkdir(parents=True, exist_ok=True)
    audio_filename = f"test_err_{uuid.uuid4()}.mp3"
    audio_file_path = audio_dir / audio_filename
    audio_file_path.write_bytes(b"dummy audio")

    async with async_session_maker() as session:
        track = AudioTrack(
            document_id=doc_id,
            mode="narration",
            language="en",
            voice_config={"voice": "en-US-GuyNeural"},
            file_path=f"audio/{audio_filename}",
            status="completed",
            config_hash=f"hash_{uuid.uuid4()}",
        )
        session.add(track)
        await session.commit()

    # Mock Path.rename to raise OSError on the audio file during staging
    orig_rename = Path.rename

    def mock_rename(self, *args, **kwargs):
        if self.name == audio_filename:
            raise OSError("Simulated permission denied")
        return orig_rename(self, *args, **kwargs)

    monkeypatch.setattr(Path, "rename", mock_rename)

    # Attempt deletion - must raise 500
    del_res = await client.delete(f"/api/v1/documents/{doc_id}")
    assert del_res.status_code == 500
    assert del_res.json()["error"]["code"] == "STORAGE_ERROR"

    # Reset monkeypatch and verify document still exists in DB
    monkeypatch.undo()
    get_res = await client.get(f"/api/v1/documents/{doc_id}")
    assert get_res.status_code == 200

    # Clean up test files and doc
    if audio_file_path.exists():
        audio_file_path.unlink()
    await client.delete(f"/api/v1/documents/{doc_id}")


@pytest.mark.asyncio
async def test_delete_document_reversible_staging_restores_files_on_partial_failure(client: AsyncClient, monkeypatch):
    """
    Regression Test (Phase 4C Final Review):
    Simulates a failure during staging of the second file (after the first file has already been staged).
    Verifies that reversible staging catches the error, restores the first file back to its original name,
    aborts the deletion, and leaves zero files missing or in dangling staged states.
    """
    import uuid
    from pathlib import Path
    from src.db.session import async_session_maker
    from src.models.audio_track import AudioTrack

    # 1. Upload document
    files = {"file": ("reversible_test.txt", b"Document content.", "text/plain")}
    upload_res = await client.post("/api/v1/documents", files=files)
    doc_id = upload_res.json()["id"]

    audio_dir = settings.AUDIO_DIR.resolve()
    audio_dir.mkdir(parents=True, exist_ok=True)

    audio1_name = f"test_rev1_{uuid.uuid4()}.mp3"
    audio2_name = f"test_rev2_{uuid.uuid4()}.mp3"

    audio1_path = audio_dir / audio1_name
    audio2_path = audio_dir / audio2_name

    audio1_path.write_bytes(b"audio track 1 data")
    audio2_path.write_bytes(b"audio track 2 data")

    async with async_session_maker() as session:
        t1 = AudioTrack(
            document_id=doc_id,
            mode="narration",
            language="en",
            voice_config={"voice": "en-US-GuyNeural"},
            file_path=f"audio/{audio1_name}",
            status="completed",
            config_hash=f"hash_r1_{uuid.uuid4()}",
        )
        t2 = AudioTrack(
            document_id=doc_id,
            mode="narration",
            language="ar",
            voice_config={"voice": "ar-EG-ShakirNeural"},
            file_path=f"audio/{audio2_name}",
            status="completed",
            config_hash=f"hash_r2_{uuid.uuid4()}",
        )
        session.add_all([t1, t2])
        await session.commit()

    # Monkeypatch Path.rename to fail ONLY when staging audio2
    orig_rename = Path.rename

    def mock_rename(self, target, *args, **kwargs):
        # If attempting to stage audio2 (rename to .del_*), simulate permission/filesystem error
        if self.name == audio2_name and ".del_" in str(target):
            raise OSError("Simulated filesystem I/O error on second file")
        return orig_rename(self, target, *args, **kwargs)

    monkeypatch.setattr(Path, "rename", mock_rename)

    # Attempt deletion - must abort with 500 STORAGE_ERROR
    del_res = await client.delete(f"/api/v1/documents/{doc_id}")
    assert del_res.status_code == 500
    assert del_res.json()["error"]["code"] == "STORAGE_ERROR"

    # Reset monkeypatch
    monkeypatch.undo()

    # Crucial Consistency Assertions:
    # 1. Document still exists in database
    get_res = await client.get(f"/api/v1/documents/{doc_id}")
    assert get_res.status_code == 200

    # 2. Both audio files STILL EXIST at their ORIGINAL paths (audio1 was restored from .del_*)
    assert audio1_path.exists(), "audio1 was not restored to its original path!"
    assert audio2_path.exists(), "audio2 was corrupted or missing!"
    assert audio1_path.read_bytes() == b"audio track 1 data"
    assert audio2_path.read_bytes() == b"audio track 2 data"

    # Clean up test artifacts
    if audio1_path.exists():
        audio1_path.unlink()
    if audio2_path.exists():
        audio2_path.unlink()
    await client.delete(f"/api/v1/documents/{doc_id}")


@pytest.mark.asyncio
async def test_delete_document_reversible_staging_restores_files_if_db_delete_fails(client: AsyncClient, monkeypatch):
    """
    Regression Test (Phase 4C Final Review):
    Simulates a failure during SQLite deletion after all files have already been staged.
    Verifies that reversible staging catches the DB exception, un-stages all files back
    to their original names, and preserves exact pre-deletion consistency.
    """
    import uuid
    from pathlib import Path
    from src.db.session import async_session_maker
    from src.models.audio_track import AudioTrack
    from src.repositories.document_repository import DocumentRepository

    files = {"file": ("db_fail_test.txt", b"Content.", "text/plain")}
    upload_res = await client.post("/api/v1/documents", files=files)
    doc_id = upload_res.json()["id"]

    audio_dir = settings.AUDIO_DIR.resolve()
    audio_dir.mkdir(parents=True, exist_ok=True)
    audio_name = f"test_db_fail_{uuid.uuid4()}.mp3"
    audio_path = audio_dir / audio_name
    audio_path.write_bytes(b"audio data for db fail test")

    async with async_session_maker() as session:
        t = AudioTrack(
            document_id=doc_id,
            mode="narration",
            language="en",
            voice_config={"voice": "en-US-GuyNeural"},
            file_path=f"audio/{audio_name}",
            status="completed",
            config_hash=f"hash_db_{uuid.uuid4()}",
        )
        session.add(t)
        await session.commit()

    # Mock doc_repo.delete to raise a database error
    async def mock_doc_delete(self, doc):
        raise RuntimeError("Simulated SQLite foreign key / lock failure during cascade delete")

    monkeypatch.setattr(DocumentRepository, "delete", mock_doc_delete)

    del_res = await client.delete(f"/api/v1/documents/{doc_id}")
    assert del_res.status_code == 500

    monkeypatch.undo()

    # Assert audio file was restored back to original path from staging
    assert audio_path.exists()
    assert audio_path.read_bytes() == b"audio data for db fail test"

    # Clean up
    if audio_path.exists():
        audio_path.unlink()
    await client.delete(f"/api/v1/documents/{doc_id}")


@pytest.mark.asyncio
async def test_document_stats_empty_library(client: AsyncClient):
    """
    Verifies that an empty database returns all zeros for document and summary metrics.
    """
    res = await client.get("/api/v1/documents/stats")
    assert res.status_code == 200
    data = res.json()
    assert data["total_documents"] == 0
    assert data["processed_documents"] == 0
    assert data["pending_documents"] == 0
    assert data["failed_documents"] == 0
    assert data["unsupported_documents"] == 0
    assert data["issues_documents"] == 0
    assert data["total_summaries"] == 0


@pytest.mark.asyncio
async def test_document_stats_with_documents_and_zero_summaries(client: AsyncClient):
    """
    Verifies that document counts increment properly when uploaded,
    while total_summaries correctly reflects 0 when no summaries exist.
    """
    for i in range(3):
        files = {"file": (f"stat_doc_{i}.txt", f"Plain text content {i}".encode(), "text/plain")}
        upload_res = await client.post("/api/v1/documents", files=files)
        assert upload_res.status_code == 201

    res = await client.get("/api/v1/documents/stats")
    assert res.status_code == 200
    data = res.json()
    assert data["total_documents"] == 3
    assert data["processed_documents"] == 3
    assert data["issues_documents"] == 0
    assert data["total_summaries"] == 0


@pytest.mark.asyncio
async def test_document_stats_large_collection_beyond_page_one_and_recent_limit(
    client: AsyncClient,
    test_db_session: AsyncSession,
):
    """
    Verifies that:
    1. Collections with > 50 documents compute status aggregates across the ENTIRE collection,
       independent of pagination.
    2. Failed and unsupported records beyond page 1 correctly contribute to issues_documents.
    3. Total completed summaries are accurately aggregated across all documents.
    4. Fetching page 1 with page_size=5 strictly returns only 5 recent documents.
    """
    import uuid
    from datetime import datetime, timezone
    from src.db.session import async_session_maker
    from src.models.document import Document
    from src.models.summary import Summary

    # We insert 55 documents into the test database:
    # - 40 processed
    # - 10 failed
    # - 5 unsupported
    # Total issues = 15
    async with async_session_maker() as session:
        created_docs = []
        for i in range(55):
            if i < 40:
                doc_status = "processed"
            elif i < 50:
                doc_status = "failed"
            else:
                doc_status = "unsupported"

            doc = Document(
                id=str(uuid.uuid4()),
                filename=f"bulk_doc_{i:03d}.txt",
                file_type="txt",
                file_size=1024 + i,
                storage_filename=f"storage/bulk_doc_{i:03d}.txt",
                content_hash=f"hash_{uuid.uuid4()}",
                word_count=150,
                status=doc_status,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            session.add(doc)
            created_docs.append(doc)

        # Add 4 completed summaries and 2 pending/failed summaries across the documents
        for j in range(4):
            s = Summary(
                id=str(uuid.uuid4()),
                document_id=created_docs[j].id,
                language="en",
                detail_level="standard",
                model_used="gemini-3.8-flash",
                status="completed",
                content_data={"overview": "Test summary overview"},
            )
            session.add(s)

        # Non-completed summaries should NOT be counted in total_summaries
        s_pending = Summary(
            id=str(uuid.uuid4()),
            document_id=created_docs[4].id,
            language="en",
            detail_level="standard",
            model_used="gemini-3.8-flash",
            status="pending",
        )
        s_failed = Summary(
            id=str(uuid.uuid4()),
            document_id=created_docs[5].id,
            language="en",
            detail_level="standard",
            model_used="gemini-3.8-flash",
            status="failed",
        )
        session.add(s_pending)
        session.add(s_failed)

        await session.commit()

    # 1. Test aggregate stats endpoint
    stats_res = await client.get("/api/v1/documents/stats")
    assert stats_res.status_code == 200
    stats = stats_res.json()

    assert stats["total_documents"] >= 55
    assert stats["processed_documents"] >= 40
    assert stats["failed_documents"] >= 10
    assert stats["unsupported_documents"] >= 5
    assert stats["issues_documents"] >= 15
    # Only completed summaries are counted
    assert stats["total_summaries"] >= 4

    # 2. Test Recent Documents table query (page_size=5)
    recent_res = await client.get("/api/v1/documents?page=1&page_size=5")
    assert recent_res.status_code == 200
    recent_data = recent_res.json()

    assert len(recent_data["items"]) == 5
    assert recent_data["pagination"]["page"] == 1
    assert recent_data["pagination"]["limit"] == 5
    assert recent_data["pagination"]["total"] >= 55
    assert recent_data["pagination"]["total_pages"] >= 11

