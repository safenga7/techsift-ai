"""
TechSift AI - SQLAlchemy Models Package.
Exports all models to ensure complete mapper registry initialization.
"""

from src.models.assessment import (
    Assessment,
    AssessmentAnswer,
    AssessmentAttempt,
    AssessmentQuestion,
)
from src.models.audio_track import AudioTrack
from src.models.document import Document
from src.models.document_chunk import DocumentChunk
from src.models.learning_path import LearningLesson, LearningModule, LearningPath
from src.models.learning_progress import LessonProgress, PathProgress
from src.models.processing_job import ProcessingJob
from src.models.summary import Summary

__all__ = [
    "Assessment",
    "AssessmentAnswer",
    "AssessmentAttempt",
    "AssessmentQuestion",
    "AudioTrack",
    "Document",
    "DocumentChunk",
    "LearningLesson",
    "LearningModule",
    "LearningPath",
    "LessonProgress",
    "PathProgress",
    "ProcessingJob",
    "Summary",
]
