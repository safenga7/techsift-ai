"""
TechSift AI - API v1 Router Aggregator.
"""

from fastapi import APIRouter
from src.api.v1.endpoints import assessments, audio, documents, health, learning_paths, learning_progress, summaries

api_v1_router = APIRouter(prefix="/api/v1")

# Mount endpoints
api_v1_router.include_router(health.router)
api_v1_router.include_router(documents.router)
api_v1_router.include_router(summaries.router)
api_v1_router.include_router(audio.router)
api_v1_router.include_router(learning_paths.router)
api_v1_router.include_router(assessments.router)
api_v1_router.include_router(learning_progress.router)
