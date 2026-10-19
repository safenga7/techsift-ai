/**
 * TechSift AI - Centralized Typed API Client.
 * Production-ready with timeout safeguards, error sanitization, and upload progress.
 */

import type {
  DocumentDetail,
  DocumentItem,
  DocumentListResponse,
  DocumentStatsResponse,
  DocumentStatus,
  HealthResponse,
  SummaryItem,
  SummaryListResponse,
  CreateSummaryPayload,
  ApiErrorResponse,
  AudioTrack,
  AudioTrackListResponse,
  CreateAudioPayload,
  VoiceCatalogResponse,
  LearningPath,
  LearningPathListResponse,
  CreateLearningPathPayload,
  AssessmentItem,
  AssessmentDetail,
  AssessmentListResponse,
  CreateAssessmentPayload,
  AssessmentAttempt,
  SubmitAnswerPayload,
  AnswerRecord,
  AttemptResult,
  PathProgressOverview,
  LearningDashboardData,
  LearningRecommendationsResponse,
  ResumeLearningTarget,
  UpdateLessonProgressPayload,
  LessonProgress,
} from '../types/api';


const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? '';
const DEFAULT_TIMEOUT_MS = 30000;

class ApiClientError extends Error {
  code: string;
  statusCode: number;
  details?: unknown;

  constructor(message: string, code = 'API_ERROR', statusCode = 500, details?: unknown) {
    super(message);
    this.name = 'ApiClientError';
    this.code = code;
    this.statusCode = statusCode;
    this.details = details;
  }
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let errorData: ApiErrorResponse | null = null;
    try {
      errorData = await res.json();
    } catch {
      // Body not JSON
    }

    const message =
      errorData?.error?.message ||
      `HTTP ${res.status}: ${res.statusText || 'Server Error'}`;
    const code = errorData?.error?.code || 'HTTP_ERROR';
    const details = errorData?.error?.details;

    throw new ApiClientError(message, code, res.status, details);
  }

  return (await res.json()) as T;
}

export const api = {
  /**
   * Health Check
   */
  async getHealth(): Promise<HealthResponse> {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 5000);
    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/health`, {
        signal: controller.signal,
      });
      return await handleResponse<HealthResponse>(res);
    } catch (err: unknown) {
      if ((err as Error).name === 'AbortError') {
        throw new ApiClientError('Backend connection timed out (5s)', 'TIMEOUT', 504);
      }
      throw err;
    } finally {
      clearTimeout(timeout);
    }
  },

  /**
   * List Documents with pagination & status filtering
   */
  async getDocuments(
    page = 1,
    pageSize = 20,
    status?: DocumentStatus
  ): Promise<DocumentListResponse> {
    const params = new URLSearchParams({
      page: String(page),
      page_size: String(pageSize),
    });
    if (status) {
      params.append('status', status);
    }

    const res = await fetch(`${API_BASE_URL}/api/v1/documents?${params.toString()}`);
    return await handleResponse<DocumentListResponse>(res);
  },

  /**
   * Get document and summary aggregates across the entire collection
   */
  async getDocumentStats(): Promise<DocumentStatsResponse> {
    const res = await fetch(`${API_BASE_URL}/api/v1/documents/stats`);
    return await handleResponse<DocumentStatsResponse>(res);
  },

  /**
   * Get single document details with extracted text
   */
  async getDocument(documentId: string): Promise<DocumentDetail> {
    const res = await fetch(`${API_BASE_URL}/api/v1/documents/${encodeURIComponent(documentId)}`);
    return await handleResponse<DocumentDetail>(res);
  },

  /**
   * Upload Document with measurable progress
   */
  uploadDocument(
    file: File,
    onProgress?: (percent: number) => void
  ): Promise<DocumentItem> {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      const formData = new FormData();
      formData.append('file', file);

      if (onProgress && xhr.upload) {
        xhr.upload.onprogress = (event) => {
          if (event.lengthComputable) {
            const percent = Math.round((event.loaded / event.total) * 100);
            onProgress(percent);
          }
        };
      }

      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          try {
            const data = JSON.parse(xhr.responseText) as DocumentItem;
            resolve(data);
          } catch (e) {
            reject(new ApiClientError('Failed to parse upload response', 'PARSE_ERROR', xhr.status, e));
          }
        } else {
          try {
            const errorObj = JSON.parse(xhr.responseText) as ApiErrorResponse;
            reject(
              new ApiClientError(
                errorObj.error?.message || `Upload failed (${xhr.status})`,
                errorObj.error?.code || 'UPLOAD_FAILED',
                xhr.status,
                errorObj.error?.details
              )
            );
          } catch {
            reject(new ApiClientError(`Upload failed with status ${xhr.status}`, 'UPLOAD_FAILED', xhr.status));
          }
        }
      };

      xhr.onerror = () => {
        reject(new ApiClientError('Network error during upload', 'NETWORK_ERROR', 0));
      };

      xhr.ontimeout = () => {
        reject(new ApiClientError('Upload request timed out', 'TIMEOUT', 504));
      };

      xhr.timeout = DEFAULT_TIMEOUT_MS * 2; // 60s for uploads
      xhr.open('POST', `${API_BASE_URL}/api/v1/documents`);
      xhr.send(formData);
    });
  },

  /**
   * Delete Document
   */
  async deleteDocument(documentId: string): Promise<{ success: boolean; id: string }> {
    const res = await fetch(`${API_BASE_URL}/api/v1/documents/${encodeURIComponent(documentId)}`, {
      method: 'DELETE',
    });
    return await handleResponse<{ success: boolean; message: string; id: string }>(res);
  },

  /**
   * Generate Summary for Document
   */
  async createSummary(
    documentId: string,
    payload: CreateSummaryPayload = {},
    wait = true
  ): Promise<SummaryItem> {
    const params = new URLSearchParams({ wait: String(wait) });
    if (payload.language) params.append('language', payload.language);
    if (payload.detail_level) params.append('detail_level', payload.detail_level);

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), DEFAULT_TIMEOUT_MS * 2); // 60s for LLM wait

    try {
      const res = await fetch(
        `${API_BASE_URL}/api/v1/documents/${encodeURIComponent(documentId)}/summaries?${params.toString()}`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(payload),
          signal: controller.signal,
        }
      );
      return await handleResponse<SummaryItem>(res);
    } catch (err: unknown) {
      if ((err as Error).name === 'AbortError') {
        throw new ApiClientError(
          'Summarization request timed out. Please try requesting asynchronously or check status later.',
          'TIMEOUT',
          504
        );
      }
      throw err;
    } finally {
      clearTimeout(timeout);
    }
  },

  /**
   * List all summaries for a specific document
   */
  async getDocumentSummaries(documentId: string): Promise<SummaryListResponse> {
    const res = await fetch(
      `${API_BASE_URL}/api/v1/documents/${encodeURIComponent(documentId)}/summaries`
    );
    return await handleResponse<SummaryListResponse>(res);
  },

  /**
   * Get single summary by UUID
   */
  async getSummary(summaryId: string): Promise<SummaryItem> {
    const res = await fetch(`${API_BASE_URL}/api/v1/summaries/${encodeURIComponent(summaryId)}`);
    return await handleResponse<SummaryItem>(res);
  },

  /**
   * Request Audio Generation (Narration or Podcast)
   */
  async createAudio(
    documentId: string,
    payload: CreateAudioPayload = {},
    wait = false
  ): Promise<AudioTrack> {
    const params = new URLSearchParams();
    if (wait) {
      params.append('wait', 'true');
    }
    const controller = new AbortController();
    // 30s timeout for async job dispatch; 180s if caller explicitly waits for synthesis
    const timeout = setTimeout(
      () => controller.abort(),
      wait ? DEFAULT_TIMEOUT_MS * 6 : DEFAULT_TIMEOUT_MS
    );

    try {
      const queryString = params.toString() ? `?${params.toString()}` : '';
      const res = await fetch(
        `${API_BASE_URL}/api/v1/documents/${encodeURIComponent(documentId)}/audio${queryString}`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ ...payload, wait }),
          signal: controller.signal,
        }
      );
      return await handleResponse<AudioTrack>(res);
    } catch (err: unknown) {
      if ((err as Error).name === 'AbortError') {
        throw new ApiClientError(
          'Audio synthesis request timed out. Please poll or refresh later.',
          'TIMEOUT',
          504
        );
      }
      throw err;
    } finally {
      clearTimeout(timeout);
    }
  },

  /**
   * List all audio tracks for a specific document
   */
  async getDocumentAudio(documentId: string): Promise<AudioTrackListResponse> {
    const res = await fetch(
      `${API_BASE_URL}/api/v1/documents/${encodeURIComponent(documentId)}/audio`
    );
    return await handleResponse<AudioTrackListResponse>(res);
  },

  /**
   * Get single audio track metadata
   */
  async getAudioTrack(audioId: string): Promise<AudioTrack> {
    const res = await fetch(`${API_BASE_URL}/api/v1/audio/${encodeURIComponent(audioId)}`);
    return await handleResponse<AudioTrack>(res);
  },

  /**
   * Get direct streaming URL for audio track (supports HTTP Range headers)
   */
  getAudioStreamUrl(audioId: string): string {
    return `${API_BASE_URL}/api/v1/audio/${encodeURIComponent(audioId)}/stream`;
  },

  /**
   * Get attachment download URL for MP3
   */
  getAudioDownloadUrl(audioId: string): string {
    return `${API_BASE_URL}/api/v1/audio/${encodeURIComponent(audioId)}/download`;
  },

  /**
   * Fetch available voices catalog
   */
  async getAudioVoices(): Promise<VoiceCatalogResponse> {
    const res = await fetch(`${API_BASE_URL}/api/v1/audio/voices`);
    return await handleResponse<VoiceCatalogResponse>(res);
  },

  /**
   * Request Learning Path Generation (Synchronous or Asynchronous)
   */
  async createLearningPath(
    documentId: string,
    payload: CreateLearningPathPayload = {},
    wait = false
  ): Promise<LearningPath> {
    const params = new URLSearchParams();
    if (!wait) {
      params.append('wait', 'false');
    }
    const controller = new AbortController();
    const timeout = setTimeout(
      () => controller.abort(),
      wait ? DEFAULT_TIMEOUT_MS * 6 : DEFAULT_TIMEOUT_MS
    );

    try {
      const queryString = params.toString() ? `?${params.toString()}` : '';
      const res = await fetch(
        `${API_BASE_URL}/api/v1/documents/${encodeURIComponent(documentId)}/learning-paths${queryString}`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(payload),
          signal: controller.signal,
        }
      );
      return await handleResponse<LearningPath>(res);
    } catch (err: unknown) {
      if ((err as Error).name === 'AbortError') {
        throw new ApiClientError(
          'Learning path generation timed out. Please poll or refresh later.',
          'TIMEOUT',
          504
        );
      }
      throw err;
    } finally {
      clearTimeout(timeout);
    }
  },

  /**
   * List all learning paths for a specific document
   */
  async getDocumentLearningPaths(documentId: string): Promise<LearningPathListResponse> {
    const res = await fetch(
      `${API_BASE_URL}/api/v1/documents/${encodeURIComponent(documentId)}/learning-paths`
    );
    return await handleResponse<LearningPathListResponse>(res);
  },

  /**
   * Get single learning path with modules and lessons
   */
  async getLearningPath(pathId: string): Promise<LearningPath> {
    const res = await fetch(
      `${API_BASE_URL}/api/v1/learning-paths/${encodeURIComponent(pathId)}`
    );
    return await handleResponse<LearningPath>(res);
  },

  /**
   * Request or Retrieve Assessment (Lesson Quiz, Module Assessment, or Final Exam)
   */
  async createAssessment(
    learningPathId: string,
    payload: CreateAssessmentPayload
  ): Promise<AssessmentItem> {
    const controller = new AbortController();
    const timeout = setTimeout(
      () => controller.abort(),
      payload.wait !== false ? DEFAULT_TIMEOUT_MS * 4 : DEFAULT_TIMEOUT_MS
    );

    try {
      const res = await fetch(
        `${API_BASE_URL}/api/v1/learning-paths/${encodeURIComponent(learningPathId)}/assessments`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(payload),
          signal: controller.signal,
        }
      );
      return await handleResponse<AssessmentItem>(res);
    } catch (err: unknown) {
      if ((err as Error).name === 'AbortError') {
        throw new ApiClientError(
          'Assessment generation request timed out. Please poll or refresh later.',
          'TIMEOUT',
          504
        );
      }
      throw err;
    } finally {
      clearTimeout(timeout);
    }
  },

  /**
   * List assessments for a learning path, optionally filtered by type, module, or lesson
   */
  async getLearningPathAssessments(
    learningPathId: string,
    params?: { assessment_type?: string; module_id?: string; lesson_id?: string }
  ): Promise<AssessmentListResponse> {
    const query = new URLSearchParams();
    if (params?.assessment_type) query.append('assessment_type', params.assessment_type);
    if (params?.module_id) query.append('module_id', params.module_id);
    if (params?.lesson_id) query.append('lesson_id', params.lesson_id);
    const queryString = query.toString() ? `?${query.toString()}` : '';

    const res = await fetch(
      `${API_BASE_URL}/api/v1/learning-paths/${encodeURIComponent(learningPathId)}/assessments${queryString}`
    );
    return await handleResponse<AssessmentListResponse>(res);
  },

  /**
   * Get single assessment with taker questions (without answer leak)
   */
  async getAssessment(assessmentId: string): Promise<AssessmentDetail> {
    const res = await fetch(
      `${API_BASE_URL}/api/v1/assessments/${encodeURIComponent(assessmentId)}`
    );
    return await handleResponse<AssessmentDetail>(res);
  },

  /**
   * Start a new test-taking attempt for an assessment
   */
  async startAttempt(assessmentId: string): Promise<AssessmentAttempt> {
    const res = await fetch(
      `${API_BASE_URL}/api/v1/assessments/${encodeURIComponent(assessmentId)}/attempts`,
      {
        method: 'POST',
      }
    );
    return await handleResponse<AssessmentAttempt>(res);
  },

  /**
   * Submit an answer to a single question within an active attempt
   */
  async submitAnswer(
    attemptId: string,
    payload: SubmitAnswerPayload
  ): Promise<AnswerRecord> {
    const res = await fetch(
      `${API_BASE_URL}/api/v1/attempts/${encodeURIComponent(attemptId)}/answers`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      }
    );
    return await handleResponse<AnswerRecord>(res);
  },

  /**
   * Finalize and grade an assessment attempt (idempotent)
   */
  async submitAttempt(attemptId: string): Promise<AttemptResult> {
    const res = await fetch(
      `${API_BASE_URL}/api/v1/attempts/${encodeURIComponent(attemptId)}/submit`,
      {
        method: 'POST',
      }
    );
    return await handleResponse<AttemptResult>(res);
  },

  /**
   * Get graded results for a completed assessment attempt
   */
  async getAttemptResults(attemptId: string): Promise<AttemptResult> {
    const res = await fetch(
      `${API_BASE_URL}/api/v1/attempts/${encodeURIComponent(attemptId)}/results`
    );
    return await handleResponse<AttemptResult>(res);
  },

  /**
   * Get learning path progress overview
   */
  async getPathProgress(pathId: string): Promise<PathProgressOverview> {
    const res = await fetch(
      `${API_BASE_URL}/api/v1/learning-paths/${encodeURIComponent(pathId)}/progress`
    );
    return await handleResponse<PathProgressOverview>(res);
  },

  /**
   * Get consolidated learning dashboard
   */
  async getLearningDashboard(pathId: string): Promise<LearningDashboardData> {
    const res = await fetch(
      `${API_BASE_URL}/api/v1/learning-paths/${encodeURIComponent(pathId)}/dashboard`
    );
    return await handleResponse<LearningDashboardData>(res);
  },

  /**
   * Get rule-based pedagogical recommendations
   */
  async getRecommendations(pathId: string): Promise<LearningRecommendationsResponse> {
    const res = await fetch(
      `${API_BASE_URL}/api/v1/learning-paths/${encodeURIComponent(pathId)}/recommendations`
    );
    return await handleResponse<LearningRecommendationsResponse>(res);
  },

  /**
   * Resolve Resume Learning target
   */
  async getResumeTarget(pathId: string): Promise<ResumeLearningTarget> {
    const res = await fetch(
      `${API_BASE_URL}/api/v1/learning-paths/${encodeURIComponent(pathId)}/resume`
    );
    return await handleResponse<ResumeLearningTarget>(res);
  },

  /**
   * Update reading / completion progress for a lesson
   */
  async updateLessonProgress(
    lessonId: string,
    payload: UpdateLessonProgressPayload
  ): Promise<LessonProgress> {
    const res = await fetch(
      `${API_BASE_URL}/api/v1/lessons/${encodeURIComponent(lessonId)}/progress`,
      {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      }
    );
    return await handleResponse<LessonProgress>(res);
  },
};

export { ApiClientError };
