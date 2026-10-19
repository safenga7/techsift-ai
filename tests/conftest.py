"""
Pytest configuration and fixtures for Phase 1 tests.
Uses temporary isolated SQLite databases and storage directories.
"""

from pathlib import Path
from typing import AsyncGenerator
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from src.api.main import app
from src.core.config import settings
from src.db.base import Base
from src.db.session import get_db
from src.services.storage_service import storage_service


@pytest_asyncio.fixture
async def test_db_session(tmp_path: Path) -> AsyncGenerator[AsyncSession, None]:
    """Provides an isolated async SQLite database session for each test."""
    db_file = tmp_path / "test_techsift.db"
    db_url = f"sqlite+aiosqlite:///{db_file}"

    engine = create_async_engine(
        db_url,
        echo=False,
        connect_args={"check_same_thread": False},
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_maker() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def client(tmp_path: Path) -> AsyncGenerator[AsyncClient, None]:
    """Provides an AsyncClient with temporary storage and database overrides."""
    # 1. Setup isolated test database
    db_file = tmp_path / "test_client.db"
    db_url = f"sqlite+aiosqlite:///{db_file}"
    engine = create_async_engine(
        db_url,
        echo=False,
        connect_args={"check_same_thread": False},
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    # 2. Setup isolated storage directory
    temp_storage = tmp_path / "storage"
    temp_storage.mkdir(parents=True, exist_ok=True)
    temp_audio = temp_storage / "audio"
    temp_audio.mkdir(parents=True, exist_ok=True)
    temp_docs = temp_storage / "documents"
    temp_docs.mkdir(parents=True, exist_ok=True)

    orig_storage_dir = settings.STORAGE_DIR
    orig_audio_dir = settings.AUDIO_DIR
    orig_service_base = storage_service.base_dir

    settings.STORAGE_DIR = temp_storage
    settings.AUDIO_DIR = temp_audio
    storage_service.base_dir = temp_docs.resolve()

    # 3. Apply FastAPI dependency override and patch async_session_maker for background tasks
    app.dependency_overrides[get_db] = override_get_db
    import src.db.session
    import src.services.assessment_service
    import src.services.audio_service
    import src.services.learning_path_service
    import src.services.summary_service
    orig_session_maker = src.db.session.async_session_maker
    src.db.session.async_session_maker = session_maker
    src.services.assessment_service.async_session_maker = session_maker
    src.services.audio_service.async_session_maker = session_maker
    src.services.learning_path_service.async_session_maker = session_maker
    src.services.summary_service.async_session_maker = session_maker

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac

    # 4. Teardown
    src.db.session.async_session_maker = orig_session_maker
    src.services.assessment_service.async_session_maker = orig_session_maker
    src.services.audio_service.async_session_maker = orig_session_maker
    src.services.learning_path_service.async_session_maker = orig_session_maker
    src.services.summary_service.async_session_maker = orig_session_maker
    app.dependency_overrides.clear()
    settings.STORAGE_DIR = orig_storage_dir
    settings.AUDIO_DIR = orig_audio_dir
    storage_service.base_dir = orig_service_base
    await engine.dispose()


@pytest.fixture
def sample_pdf_bytes() -> bytes:
    """Generates valid PDF bytes containing extractable technical text."""
    import io
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    c.drawString(72, 700, "FastAPI Architecture and Asynchronous I/O Specifications")
    c.drawString(72, 680, "Consensus protocols like Raft ensure fault-tolerant state machine replication.")
    c.save()
    return buf.getvalue()


@pytest.fixture
def scanned_pdf_bytes() -> bytes:
    """Generates a PDF with zero extractable text (simulating a scanned image PDF)."""
    import io
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    # Drawing only geometric lines, no text strings
    c.line(0, 0, 100, 100)
    c.line(100, 100, 200, 200)
    c.save()
    return buf.getvalue()
