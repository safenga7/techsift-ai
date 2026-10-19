/**
 * TechSift AI - Frontend API Type Definitions.
 * Aligned with FastAPI Pydantic V2 schemas (Phase 1 & Phase 2).
 */

export type DocumentStatus = 'pending' | 'processed' | 'failed' | 'unsupported';

export interface DocumentItem {
  id: string;
  filename: string;
  file_type: string;
  file_size: number;
  word_count: number;
  page_count: number | null;
  status: DocumentStatus;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentDetail extends DocumentItem {
  extracted_text: string | null;
}

export interface PaginationMetadata {
  total: number;
  skip: number;
  limit: number;
  page: number;
  total_pages: number;
}

export interface DocumentListResponse {
  items: DocumentItem[];
  pagination: PaginationMetadata;
}

export interface DocumentDeleteResponse {
  success: boolean;
  message: string;
  id: string;
}

export interface DocumentStatsResponse {
  total_documents: number;
  processed_documents: number;
  pending_documents: number;
  failed_documents: number;
  unsupported_documents: number;
  issues_documents: number;
  total_summaries: number;
}

export type LanguageCode = 'en' | 'ar';
export type DetailLevel = 'short' | 'standard' | 'detailed';
export type SummaryStatus = 'pending' | 'processing' | 'completed' | 'failed';

export interface ConceptItem {
  term: string;
  definition: string;
  relationships?: string[];
  category?: string;
}

export interface TechnicalSummaryContent {
  executive_summary: string;
  main_concepts: ConceptItem[];
  key_findings: string[];
  important_definitions: ConceptItem[];
  architecture_overview: string | null;
  practical_applications: string[];
  limitations: string[];
  key_takeaways: string[];
  source_pages: number[];
  source_chunks: number[];
  disclaimer: string;
}

export interface SummaryItem {
  id: string;
  document_id: string;
  language: LanguageCode;
  detail_level: DetailLevel;
  model_used: string;
  status: SummaryStatus;
  is_cached: boolean;
  summary: TechnicalSummaryContent | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface SummaryListResponse {
  items: SummaryItem[];
  total: number;
}

export interface CreateSummaryPayload {
  language?: LanguageCode;
  detail_level?: DetailLevel;
}

export interface HealthResponse {
  status: string;
  app: string;
  version: string;
  environment: string;
}

export interface ApiErrorDetail {
  code: string;
  message: string;
  details?: unknown;
}

export interface ApiErrorResponse {
  success: boolean;
  error: ApiErrorDetail;
}

export type AudioMode = 'narration' | 'podcast';
export type AudioVoiceGender = 'male' | 'female';
export type AudioStatus = 'pending' | 'processing' | 'completed' | 'failed';

export interface PodcastTurn {
  turn: number;
  speaker: string;
  voice: string;
  text: string;
}

export interface PodcastScript {
  title: string;
  language: LanguageCode;
  host_role: string;
  cohost_role: string;
  turns: PodcastTurn[];
  source_references?: string[];
}

export interface CreateAudioPayload {
  mode?: AudioMode;
  language?: LanguageCode;
  gender?: AudioVoiceGender;
  host_voice?: string;
  cohost_voice?: string;
  summary_id?: string;
  wait?: boolean;
}

export interface AudioTrack {
  id: string;
  document_id: string;
  summary_id: string | null;
  mode: AudioMode;
  language: LanguageCode;
  voice_config: Record<string, any>;
  script_content: any | null;
  file_size_bytes: number;
  duration_seconds: number;
  status: AudioStatus;
  error_message: string | null;
  is_cached: boolean;
  created_at: string;
  updated_at: string;
}

export interface AudioTrackListResponse {
  items: AudioTrack[];
  total: number;
}

export interface VoiceItem {
  id: string;
  name: string;
  language: string;
  gender: string;
  locale: string;
}

export interface VoiceCatalogResponse {
  voices: VoiceItem[];
}

// ---------------------------------------------------------------------------
// Phase 5A: Learning Path & Curriculum Types
// ---------------------------------------------------------------------------

export type LearningDifficulty = 'beginner' | 'intermediate' | 'advanced';
export type LearningPathStatus = 'pending' | 'processing' | 'completed' | 'failed';

export interface SourceReference {
  page_number?: number | null;
  chunk_index?: number | null;
  section_title?: string | null;
  citation_text?: string | null;
}

export interface KeyConcept {
  term: string;
  explanation: string;
}

export interface LearningLesson {
  id: string;
  module_id: string;
  title: string;
  explanation: string;
  key_concepts: KeyConcept[];
  examples: string[];
  source_references: SourceReference[];
  sequence_order: number;
  estimated_duration_minutes: number;
  created_at: string;
}

export interface LearningModule {
  id: string;
  learning_path_id: string;
  title: string;
  description: string | null;
  learning_objectives: string[];
  sequence_order: number;
  estimated_duration_minutes: number;
  lessons: LearningLesson[];
  created_at: string;
}

export interface LearningPath {
  id: string;
  document_id: string;
  language: LanguageCode;
  difficulty: LearningDifficulty;
  title: string;
  description: string | null;
  estimated_duration_minutes: number;
  status: LearningPathStatus;
  error_message: string | null;
  prerequisites: string[];
  learning_objectives: string[];
  modules: LearningModule[];
  is_cached: boolean;
  created_at: string;
  updated_at: string;
}

export interface LearningPathListResponse {
  items: LearningPath[];
  total: number;
}

export interface CreateLearningPathPayload {
  language?: LanguageCode;
  difficulty?: LearningDifficulty;
  wait?: boolean;
}

// ---------------------------------------------------------------------------
// Phase 5B: Interactive Quizzes & Assessments
// ---------------------------------------------------------------------------

export type AssessmentType = 'lesson_quiz' | 'module_assessment' | 'final_assessment';
export type QuestionType = 'multiple_choice';
export type AssessmentStatus = 'pending' | 'processing' | 'completed' | 'failed';
export type AttemptStatus = 'in_progress' | 'completed' | 'abandoned';

export interface QuestionForTaker {
  id: string;
  assessment_id: string;
  question_text: string;
  question_type: QuestionType;
  answer_options: string[];
  sequence_order: number;
}

export interface AssessmentItem {
  id: string;
  learning_path_id: string;
  module_id: string | null;
  lesson_id: string | null;
  assessment_type: AssessmentType;
  title: string;
  description: string | null;
  language: string;
  difficulty: string;
  status: AssessmentStatus;
  error_message: string | null;
  passing_threshold: number;
  questions_count: number;
  is_cached: boolean;
  created_at: string;
  updated_at: string;
}

export interface AssessmentDetail extends AssessmentItem {
  questions: QuestionForTaker[];
}

export interface AssessmentListResponse {
  items: AssessmentItem[];
  total: number;
}

export interface CreateAssessmentPayload {
  assessment_type: AssessmentType;
  module_id?: string;
  lesson_id?: string;
  question_count?: number;
  wait?: boolean;
}

export interface AssessmentAttempt {
  id: string;
  assessment_id: string;
  status: AttemptStatus;
  score: number;
  max_score: number;
  percentage: number;
  passed: boolean;
  started_at: string;
  completed_at: string | null;
  created_at: string;
}

export interface SubmitAnswerPayload {
  question_id: string;
  selected_answer: string;
}

export interface AnswerRecord {
  id: string;
  attempt_id: string;
  question_id: string;
  selected_answer: string;
  created_at: string;
}

export interface AnswerReviewItem {
  question_id: string;
  question_text: string;
  answer_options: string[];
  selected_answer: string | null;
  correct_answer: string;
  is_correct: boolean;
  explanation: string;
  source_references?: SourceReference[] | null;
}

export interface AttemptResult {
  attempt_id: string;
  assessment_id: string;
  assessment_title: string;
  status: AttemptStatus;
  score: number;
  max_score: number;
  percentage: number;
  passed: boolean;
  passing_threshold: number;
  started_at: string;
  completed_at: string | null;
  answers: AnswerReviewItem[];
}

// ---------------------------------------------------------------------------
// Phase 5C: Learning Progress & Dashboard Types
// ---------------------------------------------------------------------------

export type LessonProgressStatus = 'not_started' | 'in_progress' | 'completed';

export interface UpdateLessonProgressPayload {
  status: LessonProgressStatus;
}

export interface LessonProgress {
  id: string;
  learning_path_id: string;
  lesson_id: string;
  status: LessonProgressStatus;
  started_at: string | null;
  completed_at: string | null;
  last_accessed_at: string;
  created_at: string;
  updated_at: string;
}

export interface LessonProgressSummaryItem {
  lesson_id: string;
  module_id: string;
  sequence_order: number;
  title: string;
  status: LessonProgressStatus;
  completed: boolean;
  last_accessed_at: string | null;
  has_quiz: boolean;
  quiz_passed: boolean;
  quiz_score: number | null;
  quiz_attempts_count: number;
}

export interface ModuleProgressItem {
  module_id: string;
  sequence_order: number;
  title: string;
  total_lessons: number;
  completed_lessons: number;
  completion_percentage: number;
  is_completed: boolean;
  has_assessment: boolean;
  assessment_passed: boolean;
  assessment_score: number | null;
  assessment_attempts_count: number;
  lessons: LessonProgressSummaryItem[];
}

export interface PathProgressOverview {
  learning_path_id: string;
  total_lessons: number;
  completed_lessons: number;
  remaining_lessons: number;
  overall_completion_percentage: number;
  is_curriculum_completed: boolean;
  final_assessment_passed: boolean;
  final_assessment_score: number | null;
  last_visited_lesson_id: string | null;
  last_accessed_at: string | null;
  modules: ModuleProgressItem[];
}

export interface AssessmentStatItem {
  assessment_id: string;
  title: string;
  assessment_type: string;
  module_id: string | null;
  lesson_id: string | null;
  attempts_count: number;
  latest_score: number | null;
  latest_percentage: number | null;
  best_percentage: number | null;
  passed: boolean;
  passing_threshold: number;
  last_attempt_at: string | null;
}

export interface AssessmentOverviewStats {
  total_assessments: number;
  attempted_assessments: number;
  passed_assessments: number;
  failed_assessments: number;
  pass_rate: number;
  average_score: number;
  recent_assessments: AssessmentStatItem[];
}

export interface ConceptMasteryItem {
  term: string;
  explanation: string;
  lesson_id: string;
  lesson_title: string;
  module_id: string;
  status: 'mastered' | 'proficient' | 'needs_review' | 'not_assessed';
  accuracy_percentage: number | null;
  evidence: string;
}

export interface MissedQuestionItem {
  question_id: string;
  question_text: string;
  assessment_type: string;
  total_answers: number;
  incorrect_count: number;
  failure_rate: number;
  lesson_title: string | null;
}

export interface LessonMasteryPerformance {
  lesson_id: string;
  lesson_title: string;
  module_id: string;
  status: 'mastered' | 'proficient' | 'needs_review' | 'not_assessed';
  best_percentage: number | null;
  attempts_count: number;
  lesson_completed: boolean;
}

export interface KnowledgeMasteryReport {
  learning_path_id: string;
  strong_concepts: ConceptMasteryItem[];
  concepts_needing_review: ConceptMasteryItem[];
  frequently_missed_questions: MissedQuestionItem[];
  lessons_performance: LessonMasteryPerformance[];
}

export interface LearningRecommendation {
  id: string;
  type: string;
  title: string;
  description: string;
  target_id: string | null;
  priority: number;
}

export interface LearningRecommendationsResponse {
  learning_path_id: string;
  items: LearningRecommendation[];
}

export interface ResumeLearningTarget {
  learning_path_id: string;
  lesson_id: string;
  lesson_title: string;
  module_id: string;
  module_title: string;
  module_sequence: number;
  lesson_sequence: number;
  status: LessonProgressStatus;
  reason: string;
}

export interface LearningDashboardData {
  learning_path_id: string;
  path_title: string;
  difficulty: string;
  language: string;
  progress: PathProgressOverview;
  assessments_overview: AssessmentOverviewStats;
  knowledge_mastery: KnowledgeMasteryReport;
  recommendations: LearningRecommendation[];
  resume_target: ResumeLearningTarget | null;
}



