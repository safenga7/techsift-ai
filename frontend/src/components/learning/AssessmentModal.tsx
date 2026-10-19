/**
 * TechSift AI - Interactive Assessment & Quiz Modal Component (Phase 5B).
 * Supports Lesson Quizzes (5 questions), Module Assessments (10 questions),
 * and Final Comprehensive Exams (15 questions).
 * Features:
 * - Confidential test-taking: no answer leaks or explanations exposed before submission.
 * - Server-side deterministic grading (70% passing threshold, $0 cost).
 * - Full pedagogical review with user answers, correct answers, explanations, and citations.
 * - Bilingual RTL/LTR support (English & Modern Standard Arabic).
 */

import React, { useState, useEffect } from 'react';
import {
  X,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  ArrowRight,
  ArrowLeft,
  RotateCcw,
  Award,
  Check,
  Sparkles,
  BookOpen,
  Layers,
  GraduationCap,
} from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';
import { api, ApiClientError } from '../../services/api';
import type {
  AssessmentDetail,
  AssessmentType,
  AttemptResult,
  QuestionForTaker,
} from '../../types/api';

interface AssessmentModalProps {
  isOpen: boolean;
  onClose: () => void;
  learningPathId: string;
  assessmentType: AssessmentType;
  moduleId?: string;
  lessonId?: string;
  title: string;
  initialAttemptId?: string;
}

export const AssessmentModal: React.FC<AssessmentModalProps> = ({
  isOpen,
  onClose,
  learningPathId,
  assessmentType,
  moduleId,
  lessonId,
  title,
  initialAttemptId,
}) => {
  const { t, direction } = useLanguage();
  const isRtl = direction === 'rtl';

  // Lifecycle states
  const [loading, setLoading] = useState<boolean>(true);
  const [assessment, setAssessment] = useState<AssessmentDetail | null>(null);
  const [attemptId, setAttemptId] = useState<string | null>(null);
  const [currentIdx, setCurrentIdx] = useState<number>(0);
  const [selectedAnswers, setSelectedAnswers] = useState<Record<string, string>>({});
  const [submittingAnswer, setSubmittingAnswer] = useState<boolean>(false);
  const [submittingAttempt, setSubmittingAttempt] = useState<boolean>(false);
  const [attemptResult, setAttemptResult] = useState<AttemptResult | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Initialize assessment when modal opens
  useEffect(() => {
    let isCancelled = false;

    async function initAssessment() {
      setLoading(true);
      setErrorMessage(null);
      try {
        if (initialAttemptId) {
          const result = await api.getAttemptResults(initialAttemptId);
          if (isCancelled) return;
          setAttemptResult(result);
          setLoading(false);
          return;
        }

        // 1. Get or create assessment metadata
        const item = await api.createAssessment(learningPathId, {
          assessment_type: assessmentType,
          module_id: moduleId,
          lesson_id: lessonId,
          wait: true,
        });

        // 2. Fetch full taker assessment (confidential questions without answer leakage)
        const detail = await api.getAssessment(item.id);
        if (isCancelled) return;
        setAssessment(detail);

        // 3. Start a fresh attempt
        const attempt = await api.startAttempt(detail.id);
        if (isCancelled) return;
        setAttemptId(attempt.id);
        setCurrentIdx(0);
        setSelectedAnswers({});
      } catch (err: unknown) {
        if (!isCancelled) {
          const message =
            err instanceof ApiClientError
              ? err.message
              : 'Failed to initialize assessment. Please try again.';
          setErrorMessage(message);
        }
      } finally {
        if (!isCancelled) {
          setLoading(false);
        }
      }
    }

    initAssessment();

    return () => {
      isCancelled = true;
    };
  }, [isOpen, learningPathId, assessmentType, moduleId, lessonId, initialAttemptId]);

  if (!isOpen) return null;

  const questions: QuestionForTaker[] = assessment?.questions || [];
  const currentQuestion: QuestionForTaker | undefined = questions[currentIdx];

  // Helper to get type badge
  const getTypeBadge = () => {
    switch (assessmentType) {
      case 'lesson_quiz':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-indigo-100 dark:bg-indigo-950/80 text-indigo-700 dark:text-indigo-300">
            <BookOpen className="w-3 h-3" />
            <span>{t.takeLessonQuizBtn}</span>
          </span>
        );
      case 'module_assessment':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-purple-100 dark:bg-purple-950/80 text-purple-700 dark:text-purple-300">
            <Layers className="w-3 h-3" />
            <span>{t.takeModuleAssessmentBtn}</span>
          </span>
        );
      case 'final_assessment':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-100 dark:bg-emerald-950/80 text-emerald-700 dark:text-emerald-300">
            <GraduationCap className="w-3 h-3" />
            <span>{t.takeFinalAssessmentBtn}</span>
          </span>
        );
    }
  };

  // Option selection
  const handleSelectOption = (option: string) => {
    if (!currentQuestion) return;
    setSelectedAnswers((prev) => ({
      ...prev,
      [currentQuestion.id]: option,
    }));
  };

  // Submit current answer and navigate to next question
  const handleNextOrSave = async () => {
    if (!currentQuestion || !attemptId) return;
    const selected = selectedAnswers[currentQuestion.id];
    if (!selected) return;

    setSubmittingAnswer(true);
    try {
      await api.submitAnswer(attemptId, {
        question_id: currentQuestion.id,
        selected_answer: selected,
      });

      if (currentIdx < questions.length - 1) {
        setCurrentIdx((prev) => prev + 1);
      }
    } catch {
      // If error is duplicate answer, just advance
      if (currentIdx < questions.length - 1) {
        setCurrentIdx((prev) => prev + 1);
      }
    } finally {
      setSubmittingAnswer(false);
    }
  };

  // Finalize and grade entire attempt
  const handleFinalSubmit = async () => {
    if (!attemptId) return;
    setSubmittingAttempt(true);
    setErrorMessage(null);

    try {
      // 1. Submit any current selected answer if not already submitted
      if (currentQuestion && selectedAnswers[currentQuestion.id]) {
        try {
          await api.submitAnswer(attemptId, {
            question_id: currentQuestion.id,
            selected_answer: selectedAnswers[currentQuestion.id],
          });
        } catch {
          // Ignore if already submitted
        }
      }

      // 2. Finalize and evaluate locally on server
      const result = await api.submitAttempt(attemptId);
      setAttemptResult(result);
    } catch (err: unknown) {
      const msg =
        err instanceof ApiClientError
          ? err.message
          : 'Failed to complete assessment grading. Please try again.';
      setErrorMessage(msg);
    } finally {
      setSubmittingAttempt(false);
    }
  };

  // Retake assessment
  const handleRetake = async () => {
    if (!assessment) return;
    setLoading(true);
    setAttemptResult(null);
    setCurrentIdx(0);
    setSelectedAnswers({});
    setErrorMessage(null);

    try {
      const attempt = await api.startAttempt(assessment.id);
      setAttemptId(attempt.id);
    } catch {
      setErrorMessage('Failed to start a new attempt.');
    } finally {
      setLoading(false);
    }
  };

  const optionLetters = ['A', 'B', 'C', 'D'];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/70 backdrop-blur-xs">
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl w-full max-w-3xl max-h-[90vh] flex flex-col shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        {/* Header */}
        <div className="p-5 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between gap-4 bg-slate-50/50 dark:bg-slate-900/50">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-indigo-50 dark:bg-indigo-950/80 text-indigo-600 dark:text-indigo-400">
              <Award className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                  {title || t.assessmentModalTitle}
                </h3>
                {getTypeBadge()}
              </div>
              <p className="text-[11px] text-slate-500 dark:text-slate-400">
                {t.zeroCostTag} • Server-Side Deterministic Grading
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer"
            aria-label={t.close}
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* 1. Loading State */}
          {loading && (
            <div className="py-16 text-center space-y-4">
              <div className="w-12 h-12 rounded-full bg-indigo-100 dark:bg-indigo-950/80 flex items-center justify-center mx-auto text-indigo-600 dark:text-indigo-400 animate-pulse">
                <Sparkles className="w-6 h-6 animate-spin" />
              </div>
              <div>
                <h4 className="text-sm font-bold text-slate-900 dark:text-white mb-1">
                  {t.assessmentGeneratingTitle}
                </h4>
                <p className="text-xs text-slate-500 dark:text-slate-400 max-w-sm mx-auto">
                  {t.assessmentGeneratingDesc}
                </p>
              </div>
            </div>
          )}

          {/* 2. Error State */}
          {!loading && errorMessage && !attemptResult && (
            <div className="p-6 rounded-xl bg-rose-50 dark:bg-rose-950/30 border border-rose-200 dark:border-rose-900/60 text-center space-y-3">
              <AlertCircle className="w-8 h-8 text-rose-500 mx-auto" />
              <h4 className="text-sm font-bold text-rose-800 dark:text-rose-200">
                {t.errorTitle}
              </h4>
              <p className="text-xs text-rose-600 dark:text-rose-400 font-mono">
                {errorMessage}
              </p>
              <button
                onClick={handleRetake}
                className="px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-700 text-white text-xs font-bold inline-flex items-center gap-1.5 cursor-pointer"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span>{t.retry}</span>
              </button>
            </div>
          )}

          {/* 3. Active Test Taker View (Strict Confidentiality - No Answers Leaked) */}
          {!loading && !attemptResult && currentQuestion && (
            <div className="space-y-6">
              {/* Stepper & Progress */}
              <div className="space-y-2">
                <div className="flex items-center justify-between text-xs font-semibold text-slate-500 dark:text-slate-400">
                  <span>
                    {t.questionStepLabel} {currentIdx + 1} / {questions.length}
                  </span>
                  <span>
                    {Math.round(((currentIdx + 1) / questions.length) * 100)}%
                  </span>
                </div>
                <div className="w-full h-1.5 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
                  <div
                    className="h-full bg-indigo-600 dark:bg-indigo-500 rounded-full transition-all duration-300"
                    style={{
                      width: `${((currentIdx + 1) / questions.length) * 100}%`,
                    }}
                  />
                </div>
              </div>

              {/* Question Text */}
              <div className="p-5 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-800">
                <h4 className="text-sm font-bold text-slate-900 dark:text-white leading-relaxed">
                  {currentQuestion.question_text}
                </h4>
              </div>

              {/* Answer Options */}
              <div className="space-y-3">
                {currentQuestion.answer_options.map((option, optIdx) => {
                  const isSelected = selectedAnswers[currentQuestion.id] === option;
                  return (
                    <button
                      key={optIdx}
                      type="button"
                      onClick={() => handleSelectOption(option)}
                      className={`w-full p-4 rounded-xl border text-left rtl:text-right flex items-center gap-3.5 transition-all cursor-pointer ${
                        isSelected
                          ? 'border-indigo-600 dark:border-indigo-500 bg-indigo-50/70 dark:bg-indigo-950/40 ring-1 ring-indigo-500 text-indigo-900 dark:text-indigo-100 shadow-xs'
                          : 'border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700 bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-300'
                      }`}
                    >
                      <span
                        className={`w-7 h-7 rounded-lg text-xs font-bold flex items-center justify-center shrink-0 ${
                          isSelected
                            ? 'bg-indigo-600 text-white'
                            : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400'
                        }`}
                      >
                        {optionLetters[optIdx]}
                      </span>
                      <span className="text-xs font-medium leading-relaxed flex-1">
                        {option}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* 4. Graded Results & Pedagogical Review */}
          {!loading && attemptResult && (
            <div className="space-y-6">
              {/* Score Banner */}
              <div
                className={`p-6 rounded-2xl border text-center space-y-3 ${
                  attemptResult.passed
                    ? 'bg-emerald-50/60 dark:bg-emerald-950/30 border-emerald-200 dark:border-emerald-800/60'
                    : 'bg-amber-50/60 dark:bg-amber-950/30 border-amber-200 dark:border-amber-800/60'
                }`}
              >
                <div className="inline-flex items-center justify-center">
                  {attemptResult.passed ? (
                    <div className="w-14 h-14 rounded-full bg-emerald-100 dark:bg-emerald-900/60 flex items-center justify-center text-emerald-600 dark:text-emerald-400">
                      <CheckCircle2 className="w-8 h-8" />
                    </div>
                  ) : (
                    <div className="w-14 h-14 rounded-full bg-amber-100 dark:bg-amber-900/60 flex items-center justify-center text-amber-600 dark:text-amber-400">
                      <AlertCircle className="w-8 h-8" />
                    </div>
                  )}
                </div>

                <div>
                  <div className="text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight">
                    {attemptResult.percentage}%
                  </div>
                  <p className="text-xs font-semibold text-slate-600 dark:text-slate-400 mt-1">
                    {t.assessmentScoreLabel}: {attemptResult.score} / {attemptResult.max_score}{' '}
                    (Passing Threshold: {attemptResult.passing_threshold}%)
                  </p>
                </div>

                <div className="inline-flex items-center gap-2">
                  <span
                    className={`px-3 py-1 rounded-full text-xs font-bold ${
                      attemptResult.passed
                        ? 'bg-emerald-600 text-white shadow-xs'
                        : 'bg-amber-600 text-white shadow-xs'
                    }`}
                  >
                    {attemptResult.passed
                      ? t.assessmentPassedBadge
                      : t.assessmentFailedBadge}
                  </span>
                </div>
              </div>

              {/* Pedagogical Question-by-Question Review */}
              <div className="space-y-4">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 flex items-center gap-1.5">
                  <HelpCircle className="w-4 h-4 text-indigo-500" />
                  <span>{t.assessmentResultsTitle}</span>
                </h4>

                <div className="space-y-4">
                  {attemptResult.answers.map((ans, aIdx) => (
                    <div
                      key={ans.question_id || aIdx}
                      className={`p-5 rounded-xl border space-y-3.5 ${
                        ans.is_correct
                          ? 'border-emerald-200 dark:border-emerald-900/50 bg-emerald-50/20 dark:bg-emerald-950/10'
                          : 'border-rose-200 dark:border-rose-900/50 bg-rose-50/20 dark:bg-rose-950/10'
                      }`}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <span className="text-xs font-bold text-slate-900 dark:text-white flex items-center gap-2">
                          <span
                            className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] text-white shrink-0 ${
                              ans.is_correct ? 'bg-emerald-500' : 'bg-rose-500'
                            }`}
                          >
                            {aIdx + 1}
                          </span>
                          <span>{ans.question_text}</span>
                        </span>
                        <span
                          className={`text-[11px] font-bold px-2 py-0.5 rounded-full shrink-0 ${
                            ans.is_correct
                              ? 'bg-emerald-100 dark:bg-emerald-950/80 text-emerald-700 dark:text-emerald-300'
                              : 'bg-rose-100 dark:bg-rose-950/80 text-rose-700 dark:text-rose-300'
                          }`}
                        >
                          {ans.is_correct ? 'Correct' : 'Incorrect'}
                        </span>
                      </div>

                      {/* Your Answer */}
                      <div className="text-xs space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-slate-500 dark:text-slate-400">
                            {t.yourAnswerLabel}:
                          </span>
                          <span
                            className={`font-medium ${
                              ans.is_correct
                                ? 'text-emerald-700 dark:text-emerald-300 font-bold'
                                : 'text-rose-600 dark:text-rose-400'
                            }`}
                          >
                            {ans.selected_answer || '(Unanswered)'}
                          </span>
                        </div>

                        {!ans.is_correct && (
                          <div className="flex items-center gap-2">
                            <span className="font-semibold text-slate-500 dark:text-slate-400">
                              {t.correctAnswerLabel}:
                            </span>
                            <span className="font-bold text-emerald-600 dark:text-emerald-400">
                              {ans.correct_answer}
                            </span>
                          </div>
                        )}
                      </div>

                      {/* Explanation */}
                      {ans.explanation && (
                        <div className="p-3 rounded-lg bg-white/80 dark:bg-slate-900/80 border border-slate-200/80 dark:border-slate-800 text-xs text-slate-700 dark:text-slate-300 space-y-1">
                          <span className="text-[11px] font-bold text-indigo-600 dark:text-indigo-400 block">
                            {t.pedagogicalExplanationLabel}:
                          </span>
                          <p className="leading-relaxed">{ans.explanation}</p>
                        </div>
                      )}

                      {/* Citations */}
                      {ans.source_references && ans.source_references.length > 0 && (
                        <div className="flex flex-wrap gap-1.5 pt-1">
                          {ans.source_references.map((src: any, sIdx: number) => {
                            const page = src.page_number ?? src.page;
                            const chunk = src.chunk_index ?? src.chunk;
                            const section = src.section_title ?? src.section;
                            const citation = src.citation_text ?? src.citation;

                            const parts: string[] = [];
                            if (page !== undefined && page !== null) {
                              parts.push(`Page ${page}`);
                            }
                            if (section) {
                              parts.push(section);
                            }
                            if (chunk !== undefined && chunk !== null) {
                              parts.push(typeof chunk === 'number' ? `Chunk ${chunk}` : chunk);
                            }

                            const label = parts.length > 0 ? parts.join(' • ') : 'Source Reference';
                            const excerpt = citation ? ` • ${citation.length > 40 ? citation.slice(0, 40) + '...' : citation}` : '';

                            return (
                              <span
                                key={sIdx}
                                className="text-[10px] font-semibold px-2 py-0.5 rounded-md bg-indigo-50 dark:bg-indigo-950/60 text-indigo-700 dark:text-indigo-300 border border-indigo-100 dark:border-indigo-900/40 inline-flex items-center gap-1"
                                title={citation || section || undefined}
                              >
                                <span>{label}{excerpt}</span>
                              </span>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Modal Footer Controls */}
        <div className="p-4 border-t border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/50 flex items-center justify-between gap-3">
          {attemptResult ? (
            <div className="flex items-center justify-between w-full">
              <button
                onClick={handleRetake}
                className="px-4 py-2 rounded-xl bg-slate-200 hover:bg-slate-300 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-200 text-xs font-bold flex items-center gap-2 cursor-pointer"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span>{t.retakeAssessmentBtn}</span>
              </button>

              <button
                onClick={onClose}
                className="px-5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold shadow-md shadow-indigo-500/20 cursor-pointer"
              >
                {t.close}
              </button>
            </div>
          ) : (
            <>
              <button
                type="button"
                onClick={() => setCurrentIdx((prev) => Math.max(0, prev - 1))}
                disabled={currentIdx === 0 || loading || submittingAnswer || submittingAttempt}
                className="px-3.5 py-2 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 hover:bg-slate-50 dark:hover:bg-slate-800/80 disabled:opacity-40 text-slate-700 dark:text-slate-300 text-xs font-bold flex items-center gap-1.5 cursor-pointer"
              >
                {isRtl ? <ArrowRight className="w-3.5 h-3.5" /> : <ArrowLeft className="w-3.5 h-3.5" />}
                <span>{t.prevQuestionBtn}</span>
              </button>

              <div className="flex items-center gap-2">
                {currentIdx < questions.length - 1 ? (
                  <button
                    type="button"
                    onClick={handleNextOrSave}
                    disabled={
                      !currentQuestion ||
                      !selectedAnswers[currentQuestion.id] ||
                      submittingAnswer
                    }
                    className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-xs font-bold shadow-md shadow-indigo-500/20 flex items-center gap-1.5 cursor-pointer"
                  >
                    <span>{submittingAnswer ? t.submittingAnswer : t.nextQuestionBtn}</span>
                    {isRtl ? <ArrowLeft className="w-3.5 h-3.5" /> : <ArrowRight className="w-3.5 h-3.5" />}
                  </button>
                ) : (
                  <button
                    type="button"
                    onClick={handleFinalSubmit}
                    disabled={
                      questions.length === 0 ||
                      submittingAttempt ||
                      (currentQuestion ? !selectedAnswers[currentQuestion.id] : true)
                    }
                    className="px-5 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white text-xs font-bold shadow-md shadow-emerald-500/20 flex items-center gap-1.5 cursor-pointer"
                  >
                    <Check className="w-4 h-4" />
                    <span>
                      {submittingAttempt ? t.submittingAssessment : t.submitAssessmentBtn}
                    </span>
                  </button>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};
