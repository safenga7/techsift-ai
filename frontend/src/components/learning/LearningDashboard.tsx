/**
 * TechSift AI - Consolidated Learning Progress & Mastery Dashboard (Phase 5C).
 * Renders real-time curriculum completion, assessment statistics, deterministic
 * knowledge mastery, explainable recommendations, and session continuity.
 */

import React from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  TrendingUp,
  Award,
  CheckCircle2,
  Clock,
  Sparkles,
  HelpCircle,
  RotateCcw,
  ArrowRight,
  ArrowLeft,
  AlertTriangle,
  Lightbulb,
  Layers,
  GraduationCap,
} from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';
import { api } from '../../services/api';
import type {
  AssessmentType,
  LearningDashboardData,
  ModuleProgressItem,
  LessonProgressSummaryItem,
  ConceptMasteryItem,
  LearningRecommendation,
} from '../../types/api';

interface LearningDashboardProps {
  learningPathId: string;
  onOpenLesson?: (lessonId: string, moduleId: string) => void;
  onLaunchAssessment?: (
    assessmentType: AssessmentType,
    moduleId?: string,
    lessonId?: string,
    title?: string
  ) => void;
}

export const LearningDashboard: React.FC<LearningDashboardProps> = ({
  learningPathId,
  onOpenLesson,
  onLaunchAssessment,
}) => {
  const { t, direction } = useLanguage();
  const isRtl = direction === 'rtl';
  const ArrowIcon = isRtl ? ArrowLeft : ArrowRight;

  const { data: dashboard, isLoading, error } = useQuery<LearningDashboardData>({
    queryKey: ['learning-dashboard', learningPathId],
    queryFn: () => api.getLearningDashboard(learningPathId),
    enabled: Boolean(learningPathId),
    refetchInterval: 5000, // keep dashboard live as user completes lessons
  });

  if (isLoading) {
    return (
      <div className="py-20 text-center space-y-4 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl">
        <div className="w-12 h-12 rounded-full bg-indigo-50 dark:bg-indigo-950/80 flex items-center justify-center mx-auto text-indigo-600 dark:text-indigo-400 animate-spin">
          <Sparkles className="w-6 h-6" />
        </div>
        <p className="text-xs text-slate-500 dark:text-slate-400">{t.loading}</p>
      </div>
    );
  }

  if (error || !dashboard) {
    return (
      <div className="p-8 text-center space-y-3 bg-white dark:bg-slate-900 border border-rose-200 dark:border-rose-900/60 rounded-2xl">
        <AlertTriangle className="w-8 h-8 text-rose-500 mx-auto" />
        <h4 className="text-sm font-bold text-slate-900 dark:text-white">{t.errorTitle}</h4>
        <p className="text-xs text-rose-600 dark:text-rose-400 font-mono">
          {error instanceof Error ? error.message : 'Failed to load dashboard data.'}
        </p>
      </div>
    );
  }

  const { progress, assessments_overview: stats, knowledge_mastery: mastery, recommendations, resume_target } = dashboard;

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* 1. Resume Learning Banner */}
      {resume_target && (
        <div className="bg-linear-to-r from-indigo-600 to-indigo-800 dark:from-indigo-900 dark:to-slate-900 text-white rounded-2xl p-6 shadow-md flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-white/20 text-[11px] font-semibold text-indigo-100 backdrop-blur-xs">
              <Sparkles className="w-3 h-3 text-amber-300" />
              <span>{resume_target.reason}</span>
            </div>
            <h3 className="text-base font-bold text-white">
              Module {resume_target.module_sequence}.{resume_target.lesson_sequence} — {resume_target.lesson_title}
            </h3>
            <p className="text-xs text-indigo-100/80">
              {resume_target.module_title}
            </p>
          </div>

          <button
            type="button"
            onClick={() => onOpenLesson?.(resume_target.lesson_id, resume_target.module_id)}
            className="px-5 py-2.5 rounded-xl bg-white text-indigo-700 hover:bg-indigo-50 font-bold text-xs shadow-md transition-all flex items-center gap-2 cursor-pointer shrink-0"
          >
            <span>{t.resumeLearningBtn}</span>
            <ArrowIcon className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* 2. Overview KPI Metrics (4 Cards) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Card 1: Completion Rate */}
        <div className="p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs space-y-3">
          <div className="flex items-center justify-between text-slate-500 dark:text-slate-400">
            <span className="text-xs font-semibold">{t.completionRateLabel}</span>
            <div className="p-2 rounded-lg bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400">
              <TrendingUp className="w-4 h-4" />
            </div>
          </div>
          <div>
            <div className="text-2xl font-extrabold text-slate-900 dark:text-white">
              {progress.overall_completion_percentage}%
            </div>
            <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">
              {progress.completed_lessons} / {progress.total_lessons} {t.completedLessonsLabel.toLowerCase()}
            </p>
          </div>
          <div className="w-full h-1.5 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
            <div
              className="h-full bg-indigo-600 dark:bg-indigo-500 rounded-full transition-all duration-300"
              style={{ width: `${progress.overall_completion_percentage}%` }}
            />
          </div>
        </div>

        {/* Card 2: Lessons Completed */}
        <div className="p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs space-y-3">
          <div className="flex items-center justify-between text-slate-500 dark:text-slate-400">
            <span className="text-xs font-semibold">{t.completedLessonsLabel}</span>
            <div className="p-2 rounded-lg bg-emerald-50 dark:bg-emerald-950/60 text-emerald-600 dark:text-emerald-400">
              <CheckCircle2 className="w-4 h-4" />
            </div>
          </div>
          <div>
            <div className="text-2xl font-extrabold text-slate-900 dark:text-white">
              {progress.completed_lessons}
            </div>
            <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">
              {progress.remaining_lessons} {t.remainingLessonsLabel.toLowerCase()}
            </p>
          </div>
          <div className="text-[11px] font-semibold text-emerald-600 dark:text-emerald-400 flex items-center gap-1">
            <span>{progress.is_curriculum_completed ? 'Curriculum Fully Complete!' : 'In Progress'}</span>
          </div>
        </div>

        {/* Card 3: Assessment Pass Rate */}
        <div className="p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs space-y-3">
          <div className="flex items-center justify-between text-slate-500 dark:text-slate-400">
            <span className="text-xs font-semibold">{t.assessmentPassRateLabel}</span>
            <div className="p-2 rounded-lg bg-purple-50 dark:bg-purple-950/60 text-purple-600 dark:text-purple-400">
              <Award className="w-4 h-4" />
            </div>
          </div>
          <div>
            <div className="text-2xl font-extrabold text-slate-900 dark:text-white">
              {stats.pass_rate}%
            </div>
            <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">
              {stats.passed_assessments} passed of {stats.attempted_assessments} attempted
            </p>
          </div>
          <div className="w-full h-1.5 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
            <div
              className="h-full bg-purple-600 dark:bg-purple-500 rounded-full transition-all duration-300"
              style={{ width: `${stats.pass_rate}%` }}
            />
          </div>
        </div>

        {/* Card 4: Average Score */}
        <div className="p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs space-y-3">
          <div className="flex items-center justify-between text-slate-500 dark:text-slate-400">
            <span className="text-xs font-semibold">{t.averageQuizScoreLabel}</span>
            <div className="p-2 rounded-lg bg-amber-50 dark:bg-amber-950/60 text-amber-600 dark:text-amber-400">
              <Lightbulb className="w-4 h-4" />
            </div>
          </div>
          <div>
            <div className="text-2xl font-extrabold text-slate-900 dark:text-white">
              {stats.average_score}%
            </div>
            <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">
              Threshold: 70% passing
            </p>
          </div>
          <div className="text-[11px] font-semibold text-slate-500 dark:text-slate-400">
            {stats.attempted_assessments > 0 ? `${stats.attempted_assessments} total tests evaluated` : 'No tests taken yet'}
          </div>
        </div>
      </div>

      {/* 3. Pedagogical Recommendations */}
      {recommendations && recommendations.length > 0 && (
        <div className="p-6 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs space-y-4">
          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 flex items-center gap-1.5">
            <Sparkles className="w-4 h-4 text-indigo-500" />
            <span>{t.smartRecommendationsTitle}</span>
          </h4>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {recommendations.map((rec: LearningRecommendation) => (
              <div
                key={rec.id}
                className="p-4 rounded-xl border border-indigo-100 dark:border-indigo-950/60 bg-indigo-50/30 dark:bg-indigo-950/20 flex flex-col justify-between gap-3"
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-indigo-500" />
                    <h5 className="text-xs font-bold text-slate-900 dark:text-white">
                      {rec.title}
                    </h5>
                  </div>
                  <p className="text-[11px] text-slate-600 dark:text-slate-400 leading-relaxed">
                    {rec.description}
                  </p>
                </div>

                <div className="pt-2 border-t border-indigo-100/60 dark:border-indigo-950/40 flex items-center justify-end">
                  {rec.type === 'review_lesson' || rec.type === 'continue_lesson' ? (
                    <button
                      type="button"
                      onClick={() => rec.target_id && onOpenLesson?.(rec.target_id, '')}
                      className="text-xs font-bold text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 flex items-center gap-1 cursor-pointer"
                    >
                      <span>Open Lesson</span>
                      <ArrowIcon className="w-3 h-3" />
                    </button>
                  ) : rec.type === 'retake_assessment' || rec.type === 'take_module_assessment' || rec.type === 'take_final_assessment' ? (
                    <button
                      type="button"
                      onClick={() => {
                        const aType: AssessmentType =
                          rec.type === 'take_final_assessment'
                            ? 'final_assessment'
                            : rec.type === 'take_module_assessment'
                            ? 'module_assessment'
                            : 'lesson_quiz';
                        onLaunchAssessment?.(aType, rec.target_id || undefined, undefined, rec.title);
                      }}
                      className="text-xs font-bold text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 flex items-center gap-1 cursor-pointer"
                    >
                      <span>Take Assessment</span>
                      <ArrowIcon className="w-3 h-3" />
                    </button>
                  ) : null}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 4. Curriculum Module Progress Breakdown */}
      <div className="p-6 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs space-y-5">
        <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 flex items-center gap-1.5">
          <Layers className="w-4 h-4 text-indigo-500" />
          <span>{t.progressOverviewTitle}</span>
        </h4>

        <div className="space-y-4">
          {progress.modules.map((mod: ModuleProgressItem) => (
            <div
              key={mod.module_id}
              className="p-4 rounded-xl border border-slate-100 dark:border-slate-800 bg-slate-50/40 dark:bg-slate-950/30 space-y-3"
            >
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-2.5">
                  <span className="w-6 h-6 rounded-lg bg-indigo-600 text-white flex items-center justify-center text-xs font-bold">
                    {mod.sequence_order}
                  </span>
                  <div>
                    <h5 className="text-xs font-bold text-slate-900 dark:text-white">
                      {mod.title}
                    </h5>
                    <span className="text-[11px] text-slate-400">
                      {mod.completed_lessons} of {mod.total_lessons} lessons completed ({mod.completion_percentage}%)
                    </span>
                  </div>
                </div>

                {mod.has_assessment && (
                  <span
                    className={`text-[11px] font-bold px-2 py-0.5 rounded-full ${
                      mod.assessment_passed
                        ? 'bg-emerald-100 dark:bg-emerald-950/80 text-emerald-700 dark:text-emerald-300'
                        : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400'
                    }`}
                  >
                    {mod.assessment_passed ? `Assessment: ${mod.assessment_score}%` : 'Assessment Pending'}
                  </span>
                )}
              </div>

              {/* Progress bar */}
              <div className="w-full h-1.5 rounded-full bg-slate-200 dark:bg-slate-800 overflow-hidden">
                <div
                  className="h-full bg-indigo-600 rounded-full transition-all duration-300"
                  style={{ width: `${mod.completion_percentage}%` }}
                />
              </div>

              {/* Lesson Pills */}
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2 pt-1">
                {mod.lessons.map((les: LessonProgressSummaryItem) => (
                  <div
                    key={les.lesson_id}
                    onClick={() => onOpenLesson?.(les.lesson_id, mod.module_id)}
                    className={`p-2 rounded-lg border text-xs flex items-center justify-between gap-2 transition-all cursor-pointer ${
                      les.completed
                        ? 'border-emerald-200 dark:border-emerald-900/60 bg-emerald-50/40 dark:bg-emerald-950/20 text-emerald-900 dark:text-emerald-200'
                        : les.status === 'in_progress'
                        ? 'border-indigo-200 dark:border-indigo-900/60 bg-indigo-50/40 dark:bg-indigo-950/20 text-indigo-900 dark:text-indigo-200'
                        : 'border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-400'
                    }`}
                  >
                    <span className="truncate font-medium">
                      {mod.sequence_order}.{les.sequence_order} {les.title}
                    </span>
                    <span className="shrink-0">
                      {les.completed ? (
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                      ) : les.status === 'in_progress' ? (
                        <Clock className="w-3.5 h-3.5 text-indigo-500 animate-pulse" />
                      ) : (
                        <span className="w-2 h-2 rounded-full bg-slate-300 dark:bg-slate-700" />
                      )}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 5. Knowledge Mastery & Technical Concept Performance */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Strong Concepts */}
        <div className="p-6 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs space-y-4">
          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 flex items-center gap-1.5">
            <CheckCircle2 className="w-4 h-4 text-emerald-500" />
            <span>{t.strongConceptsTitle}</span>
          </h4>

          {mastery.strong_concepts && mastery.strong_concepts.length > 0 ? (
            <div className="space-y-3">
              {mastery.strong_concepts.map((concept: ConceptMasteryItem, idx: number) => (
                <div
                  key={idx}
                  className="p-3.5 rounded-xl border border-emerald-100 dark:border-emerald-950/60 bg-emerald-50/20 dark:bg-emerald-950/10 space-y-1.5"
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-xs font-bold text-emerald-700 dark:text-emerald-300">
                      {concept.term}
                    </span>
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-100 dark:bg-emerald-950/80 text-emerald-700 dark:text-emerald-300">
                      {concept.status.toUpperCase()}
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-600 dark:text-slate-400">
                    {concept.explanation}
                  </p>
                  <p className="text-[10px] text-emerald-600 dark:text-emerald-400 font-semibold pt-1">
                    {t.evidenceLabel}: {concept.evidence}
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-slate-400 italic">
              {t.noStrongConceptsYet}
            </p>
          )}
        </div>

        {/* Concepts Needing Review */}
        <div className="p-6 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs space-y-4">
          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 flex items-center gap-1.5">
            <RotateCcw className="w-4 h-4 text-amber-500" />
            <span>{t.conceptsNeedingReviewTitle}</span>
          </h4>

          {mastery.concepts_needing_review && mastery.concepts_needing_review.length > 0 ? (
            <div className="space-y-3">
              {mastery.concepts_needing_review.map((concept: ConceptMasteryItem, idx: number) => (
                <div
                  key={idx}
                  className="p-3.5 rounded-xl border border-amber-100 dark:border-amber-950/60 bg-amber-50/20 dark:bg-amber-950/10 space-y-1.5"
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-xs font-bold text-amber-700 dark:text-amber-300">
                      {concept.term}
                    </span>
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-100 dark:bg-amber-950/80 text-amber-700 dark:text-amber-300">
                      Needs Review
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-600 dark:text-slate-400">
                    {concept.explanation}
                  </p>
                  <p className="text-[10px] text-amber-600 dark:text-amber-400 font-semibold pt-1">
                    {t.evidenceLabel}: {concept.evidence}
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-slate-400 italic">
              {t.noConceptsNeedingReviewYet}
            </p>
          )}
        </div>
      </div>

      {/* 6. Frequently Missed Questions */}
      {mastery.frequently_missed_questions && mastery.frequently_missed_questions.length > 0 && (
        <div className="p-6 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs space-y-4">
          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 flex items-center gap-1.5">
            <HelpCircle className="w-4 h-4 text-rose-500" />
            <span>{t.frequentlyMissedQuestionsTitle}</span>
          </h4>

          <div className="space-y-3">
            {mastery.frequently_missed_questions.map((q) => (
              <div
                key={q.question_id}
                className="p-4 rounded-xl border border-rose-100 dark:border-rose-950/60 bg-rose-50/20 dark:bg-rose-950/10 flex items-start justify-between gap-3"
              >
                <div className="space-y-1 flex-1">
                  <span className="text-xs font-bold text-slate-900 dark:text-white">
                    {q.question_text}
                  </span>
                  <p className="text-[11px] text-slate-500 dark:text-slate-400">
                    {q.assessment_type.replace('_', ' ').toUpperCase()} • {q.incorrect_count} incorrect answers of {q.total_answers} attempts
                  </p>
                </div>
                <span className="text-xs font-extrabold px-2.5 py-1 rounded-full bg-rose-100 dark:bg-rose-950/80 text-rose-700 dark:text-rose-300 shrink-0">
                  {q.failure_rate}% {t.failureRateLabel.toLowerCase()}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 7. Recent Assessment History */}
      {stats.recent_assessments && stats.recent_assessments.length > 0 && (
        <div className="p-6 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs space-y-4">
          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 flex items-center gap-1.5">
            <GraduationCap className="w-4 h-4 text-indigo-500" />
            <span>{t.recentAssessmentsHistoryTitle}</span>
          </h4>

          <div className="space-y-2.5">
            {stats.recent_assessments.map((item) => (
              <div
                key={item.assessment_id}
                className="p-3.5 rounded-xl border border-slate-100 dark:border-slate-800 flex items-center justify-between gap-3 text-xs"
              >
                <div>
                  <h5 className="font-bold text-slate-900 dark:text-white">
                    {item.title}
                  </h5>
                  <span className="text-[11px] text-slate-400">
                    {item.attempts_count} attempt(s) • Best: {item.best_percentage}% • Latest: {item.latest_percentage}%
                  </span>
                </div>

                <div className="flex items-center gap-2">
                  <span
                    className={`font-bold px-2 py-0.5 rounded-full text-[11px] ${
                      item.passed
                        ? 'bg-emerald-100 dark:bg-emerald-950/80 text-emerald-700 dark:text-emerald-300'
                        : 'bg-amber-100 dark:bg-amber-950/80 text-amber-700 dark:text-amber-300'
                    }`}
                  >
                    {item.passed ? 'Passed' : 'Needs Review'}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
