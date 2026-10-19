/**
 * TechSift AI - Interactive Learning Studio Component (Phase 5A).
 * Transforms technical documents into structured, source-grounded learning paths
 * with beginner, intermediate, and advanced curricula, bilingual support (EN/AR),
 * step-by-step lessons, and verified page/chunk citations.
 */

import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  GraduationCap,
  BookOpen,
  Sparkles,
  Clock,
  AlertCircle,
  Zap,
  Globe,
  Sliders,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  FileText,
  Code2,
  Lightbulb,
  Layers,
  History,
  Award,
  LayoutDashboard,
} from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';
import { api, ApiClientError } from '../../services/api';
import type {
  LearningDifficulty,
  LearningPath,
  LearningModule,
  LearningLesson,
  LanguageCode,
  AssessmentType,
  PathProgressOverview,
  ModuleProgressItem,
} from '../../types/api';
import { AssessmentModal } from './AssessmentModal';
import { LearningDashboard } from './LearningDashboard';

interface LearningStudioProps {
  documentId: string;
  documentTitle?: string;
}

export const LearningStudio: React.FC<LearningStudioProps> = ({
  documentId,
}) => {
  const { t, language: uiLang } = useLanguage();
  const queryClient = useQueryClient();

  const [searchParams] = useSearchParams();
  const [selectedDifficulty, setSelectedDifficulty] = useState<LearningDifficulty>('intermediate');
  const [targetLang, setTargetLang] = useState<LanguageCode>(uiLang === 'ar' ? 'ar' : 'en');
  const [selectedPathId, setSelectedPathId] = useState<string | null>(null);
  const [expandedModules, setExpandedModules] = useState<Record<string, boolean>>({});
  const [activeAssessmentConfig, setActiveAssessmentConfig] = useState<{
    isOpen: boolean;
    learningPathId: string;
    assessmentType: AssessmentType;
    moduleId?: string;
    lessonId?: string;
    title: string;
    initialAttemptId?: string;
  } | null>(null);

  const [userStudioTab, setUserStudioTab] = useState<'curriculum' | 'dashboard' | null>(null);
  const studioTabParam = searchParams.get('studioTab');
  const activeStudioTab = (studioTabParam === 'dashboard' || studioTabParam === 'curriculum')
    ? studioTabParam
    : (userStudioTab || 'curriculum');
  const setActiveStudioTab = (tab: 'curriculum' | 'dashboard') => setUserStudioTab(tab);



  // Mark lesson progress mutation
  const markLessonMutation = useMutation({
    mutationFn: ({ lessonId, status }: { lessonId: string; status: 'completed' | 'in_progress' }) =>
      api.updateLessonProgress(lessonId, { status }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['learning-path-progress'] });
      queryClient.invalidateQueries({ queryKey: ['learning-dashboard'] });
    },
  });

  const handleOpenLesson = (lessonId: string, moduleId: string) => {
    setActiveStudioTab('curriculum');
    if (moduleId) {
      setExpandedModules((prev) => ({ ...prev, [moduleId]: true }));
    }
    markLessonMutation.mutate({ lessonId, status: 'in_progress' });
  };

  // 1. Fetch learning paths for this document with auto-polling for in-flight tasks
  const {
    data: pathsData,
    isLoading: isPathsLoading,
    isError: isPathsError,
    error: pathsError,
    refetch: refetchPaths,
  } = useQuery({
    queryKey: ['document-learning-paths', documentId],
    queryFn: () => api.getDocumentLearningPaths(documentId),
    enabled: Boolean(documentId),
    refetchInterval: (query) => {
      const items = query.state.data?.items || [];
      const hasInFlight = items.some(
        (p: LearningPath) => p.status === 'pending' || p.status === 'processing'
      );
      return hasInFlight ? 2000 : false;
    },
  });

  const paths: LearningPath[] = pathsData?.items || [];

  // Determine active path for viewer
  const activePath: LearningPath | null = selectedPathId
    ? paths.find((p) => p.id === selectedPathId) || null
    : paths[0] || null;

  // Determine if any path is currently being generated
  const isGenerating = paths.some(
    (p: LearningPath) => p.status === 'pending' || p.status === 'processing'
  );

  // 2. Fetch full active path details with eager modules & lessons
  const { data: fullPathData } = useQuery({
    queryKey: ['learning-path', activePath?.id],
    queryFn: () => api.getLearningPath(activePath!.id),
    enabled: Boolean(activePath?.id && activePath.status === 'completed'),
  });

  const currentPath: LearningPath | null = fullPathData || activePath;

  useEffect(() => {
    const assessmentParam = searchParams.get('assessment') as AssessmentType | null;
    const attemptParam = searchParams.get('attempt');
    if (assessmentParam && currentPath) {
      setActiveAssessmentConfig({
        isOpen: true,
        learningPathId: currentPath.id,
        assessmentType: assessmentParam,
        title: assessmentParam === 'final_assessment' ? currentPath.title : 'Lesson Quiz',
        initialAttemptId: attemptParam || undefined,
      });
    }
  }, [searchParams, currentPath]);

  // Path progress overview query
  const { data: progressData } = useQuery<PathProgressOverview>({
    queryKey: ['learning-path-progress', currentPath?.id],
    queryFn: () => api.getPathProgress(currentPath!.id),
    enabled: Boolean(currentPath?.id && currentPath.status === 'completed'),
    refetchInterval: 5000,
  });

  const completedLessonMap = React.useMemo(() => {
    const set = new Set<string>();
    if (progressData?.modules) {
      for (const mod of progressData.modules) {
        if (mod.lessons) {
          for (const l of mod.lessons) {
            if (l.completed || l.status === 'completed') {
              set.add(l.lesson_id);
            }
          }
        }
      }
    }
    return set;
  }, [progressData]);

  // 3. Generate Learning Path Mutation (Non-blocking: returns immediately and triggers background synthesis)
  const generateMutation = useMutation({
    mutationFn: () =>
      api.createLearningPath(
        documentId,
        {
          difficulty: selectedDifficulty,
          language: targetLang,
        },
        false // wait=false for asynchronous background processing
      ),
    onSuccess: (newPath: LearningPath) => {
      setSelectedPathId(newPath.id);
      queryClient.setQueryData(
        ['document-learning-paths', documentId],
        (old: { items: LearningPath[]; total: number } | undefined) => {
          if (!old) return { items: [newPath], total: 1 };
          const existingIdx = old.items.findIndex((p) => p.id === newPath.id);
          if (existingIdx >= 0) {
            const updated = [...old.items];
            updated[existingIdx] = newPath;
            return { ...old, items: updated };
          }
          return { ...old, items: [newPath, ...old.items], total: old.total + 1 };
        }
      );
      queryClient.invalidateQueries({ queryKey: ['document-learning-paths', documentId] });
    },
  });

  // Toggle module expansion in accordion
  const toggleModule = (moduleId: string) => {
    setExpandedModules((prev) => ({
      ...prev,
      [moduleId]: prev[moduleId] !== undefined ? !prev[moduleId] : false, // default is open if undefined
    }));
  };

  const isModuleOpen = (moduleId: string, defaultOpen = true) => {
    return expandedModules[moduleId] !== undefined ? expandedModules[moduleId] : defaultOpen;
  };

  const difficultyOptions: Array<{
    id: LearningDifficulty;
    title: string;
    desc: string;
    badgeColor: string;
  }> = [
    {
      id: 'beginner',
      title: t.difficultyBeginner,
      desc: t.difficultyBeginnerDesc,
      badgeColor: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300 border-emerald-200 dark:border-emerald-800',
    },
    {
      id: 'intermediate',
      title: t.difficultyIntermediate,
      desc: t.difficultyIntermediateDesc,
      badgeColor: 'bg-indigo-50 text-indigo-700 dark:bg-indigo-950/60 dark:text-indigo-300 border-indigo-200 dark:border-indigo-800',
    },
    {
      id: 'advanced',
      title: t.difficultyAdvanced,
      desc: t.difficultyAdvancedDesc,
      badgeColor: 'bg-purple-50 text-purple-700 dark:bg-purple-950/60 dark:text-purple-300 border-purple-200 dark:border-purple-800',
    },
  ];

  return (
    <div className="space-y-8">
      {/* Studio Banner */}
      <div className="bg-gradient-to-r from-indigo-900/40 via-purple-900/30 to-slate-900/50 border border-indigo-500/20 rounded-2xl p-6 relative overflow-hidden">
        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1.5">
            <div className="flex items-center gap-2">
              <span className="p-2 rounded-xl bg-indigo-500/20 text-indigo-400 border border-indigo-500/30">
                <GraduationCap className="w-5 h-5" />
              </span>
              <h2 className="text-lg font-bold text-slate-900 dark:text-white">
                {t.learningStudioTitle}
              </h2>
            </div>
            <p className="text-xs text-slate-600 dark:text-slate-300 max-w-2xl leading-relaxed">
              {t.learningStudioDesc}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <span className="inline-flex items-center gap-1.5 text-[11px] font-bold px-3 py-1 rounded-full bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30">
              <Sparkles className="w-3.5 h-3.5" />
              <span>Zero-Cost ($0)</span>
            </span>
            <span className="inline-flex items-center gap-1.5 text-[11px] font-semibold px-3 py-1 rounded-full bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border border-indigo-500/30">
              <Layers className="w-3.5 h-3.5" />
              <span>Grounded Citations</span>
            </span>
          </div>
        </div>
      </div>

      {/* Main Studio Grid: Controls & History (Left 4 cols) & Curriculum Viewer (Right 8 cols) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Controls Sidebar */}
        <div className="lg:col-span-4 space-y-6">
          {/* Generation Form Card */}
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-xs space-y-5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-slate-900 dark:text-white font-bold text-sm">
                <Sliders className="w-4 h-4 text-indigo-500" />
                <span>{t.learningDifficultyLabel}</span>
              </div>
              <span className="text-[10px] font-semibold text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/60 px-2 py-0.5 rounded-full border border-emerald-200 dark:border-emerald-800/60">
                gemini-3.8-flash ($0)
              </span>
            </div>

            {/* Language Selection */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-2">
                {t.learningLanguageLabel}
              </label>
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => setTargetLang('ar')}
                  className={`px-3 py-2.5 rounded-xl border text-xs font-semibold flex items-center justify-center gap-1.5 transition-all ${
                    targetLang === 'ar'
                      ? 'border-indigo-600 bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 shadow-xs'
                      : 'border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800/60'
                  }`}
                >
                  <Globe className="w-3.5 h-3.5" />
                  <span>العربية (Modern)</span>
                </button>

                <button
                  type="button"
                  onClick={() => setTargetLang('en')}
                  className={`px-3 py-2.5 rounded-xl border text-xs font-semibold flex items-center justify-center gap-1.5 transition-all ${
                    targetLang === 'en'
                      ? 'border-indigo-600 bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 shadow-xs'
                      : 'border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800/60'
                  }`}
                >
                  <Globe className="w-3.5 h-3.5" />
                  <span>English (Technical)</span>
                </button>
              </div>
            </div>

            {/* Difficulty Cards */}
            <div className="space-y-2.5">
              {difficultyOptions.map((opt) => (
                <div
                  key={opt.id}
                  onClick={() => setSelectedDifficulty(opt.id)}
                  className={`p-3 rounded-xl border cursor-pointer transition-all ${
                    selectedDifficulty === opt.id
                      ? 'border-indigo-600 bg-indigo-50/70 dark:bg-indigo-950/40 shadow-xs'
                      : 'border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-bold text-slate-900 dark:text-white capitalize">
                      {opt.title}
                    </span>
                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${opt.badgeColor}`}>
                      {opt.id}
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-500 dark:text-slate-400 leading-relaxed">
                    {opt.desc}
                  </p>
                </div>
              ))}
            </div>

            {/* Generate Action Button */}
            <button
              type="button"
              onClick={() => generateMutation.mutate()}
              disabled={generateMutation.isPending || isGenerating}
              className="w-full py-3 px-4 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 disabled:opacity-50 text-white text-xs font-bold shadow-md shadow-indigo-500/20 flex items-center justify-center gap-2 transition-all cursor-pointer disabled:cursor-not-allowed"
            >
              {generateMutation.isPending || isGenerating ? (
                <>
                  <Clock className="w-4 h-4 animate-spin" />
                  <span>{t.generatingLearningPath}</span>
                </>
              ) : (
                <>
                  <GraduationCap className="w-4 h-4" />
                  <span>{t.generateLearningPathBtn}</span>
                </>
              )}
            </button>

            {/* Error Feedback */}
            {generateMutation.isError && (
              <div className="p-3 bg-rose-50 dark:bg-rose-950/50 border border-rose-200 dark:border-rose-900 rounded-xl text-xs text-rose-600 dark:text-rose-400 flex items-start gap-2">
                <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                <span>
                  {(generateMutation.error as ApiClientError)?.message ||
                    'Curriculum generation failed. Please retry.'}
                </span>
              </div>
            )}
          </div>

          {/* Past Curricula History Card */}
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-xs space-y-3">
            <div className="flex items-center justify-between text-slate-900 dark:text-white font-bold text-xs">
              <div className="flex items-center gap-2">
                <History className="w-4 h-4 text-slate-500" />
                <span>{t.learningPathHistoryTitle}</span>
              </div>
              <span className="text-[11px] text-slate-400">
                {paths.length} generated
              </span>
            </div>

            {isPathsLoading ? (
              <div className="py-4 text-center text-xs text-slate-400 space-y-1">
                <Clock className="w-4 h-4 animate-spin mx-auto text-indigo-500" />
                <span>{t.loading}</span>
              </div>
            ) : paths.length === 0 ? (
              <p className="text-xs text-slate-400 py-2">
                {t.noLearningPathsYetDesc}
              </p>
            ) : (
              <div className="space-y-1.5 max-h-56 overflow-y-auto">
                {paths.map((p: LearningPath) => (
                  <button
                    key={p.id}
                    onClick={() => setSelectedPathId(p.id)}
                    className={`w-full text-left rtl:text-right p-2.5 rounded-xl border text-xs transition-colors flex items-center justify-between ${
                      activePath?.id === p.id
                        ? 'border-indigo-500 bg-indigo-50/70 dark:bg-indigo-950/40 font-semibold text-indigo-900 dark:text-indigo-200'
                        : 'border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800/40'
                    }`}
                  >
                    <div>
                      <div className="flex items-center gap-1.5">
                        <span className="uppercase text-[9px] font-bold px-1.5 py-0.5 rounded-xs bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
                          {p.language}
                        </span>
                        <span className="capitalize">{p.difficulty}</span>
                        {p.status === 'processing' || p.status === 'pending' ? (
                          <span className="inline-flex items-center gap-1 text-[9px] text-amber-600 dark:text-amber-400 font-bold bg-amber-50 dark:bg-amber-950/60 px-1.5 py-0.5 rounded-xs">
                            <Clock className="w-2.5 h-2.5 animate-spin" />
                            <span>{p.status}</span>
                          </span>
                        ) : p.status === 'failed' ? (
                          <span className="text-[9px] text-rose-500 font-bold bg-rose-50 dark:bg-rose-950/60 px-1.5 py-0.5 rounded-xs">
                            failed
                          </span>
                        ) : null}
                      </div>
                      <span className="text-[10px] text-slate-400 block mt-0.5">
                        {p.estimated_duration_minutes} {t.estimatedMinutesLabel} • {p.modules?.length || 0} {t.modulesLabel}
                      </span>
                    </div>

                    {p.is_cached && (
                      <span title="Cached Result ($0)">
                        <Zap className="w-3 h-3 text-cyan-500" />
                      </span>
                    )}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Curriculum Viewer (Right 8 cols) */}
        <div className="lg:col-span-8 space-y-6">
          {isPathsLoading ? (
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-12 text-center space-y-3">
              <Clock className="w-8 h-8 text-indigo-500 animate-spin mx-auto" />
              <h3 className="text-sm font-bold text-slate-800 dark:text-slate-200">
                {t.loading}
              </h3>
              <p className="text-xs text-slate-400">Loading curriculum details...</p>
            </div>
          ) : isPathsError ? (
            <div className="bg-white dark:bg-slate-900 border border-rose-200 dark:border-rose-900/60 rounded-2xl p-8 text-center space-y-4">
              <div className="w-12 h-12 rounded-full bg-rose-100 dark:bg-rose-950/80 flex items-center justify-center mx-auto text-rose-500">
                <AlertCircle className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-slate-900 dark:text-white mb-1">
                  {t.errorTitle}
                </h3>
                <p className="text-xs text-rose-600 dark:text-rose-400 max-w-md mx-auto font-mono bg-rose-50 dark:bg-rose-950/40 p-3 rounded-xl border border-rose-100 dark:border-rose-900/40">
                  {(pathsError as ApiClientError)?.message || 'Failed to retrieve learning paths.'}
                </p>
              </div>
              <button
                type="button"
                onClick={() => refetchPaths()}
                className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold shadow-md shadow-indigo-500/20 inline-flex items-center gap-2 cursor-pointer transition-colors"
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>{t.retryGeneration}</span>
              </button>
            </div>
          ) : !activePath ? (
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-12 text-center">
              <GraduationCap className="w-10 h-10 text-indigo-400 mx-auto mb-3" />
              <h3 className="text-base font-bold text-slate-800 dark:text-slate-200 mb-1">
                {t.noLearningPathsYet}
              </h3>
              <p className="text-xs text-slate-400 max-w-sm mx-auto mb-6">
                {t.noLearningPathsYetDesc}
              </p>
              <button
                type="button"
                onClick={() => generateMutation.mutate()}
                disabled={generateMutation.isPending || isGenerating}
                className="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-xs font-bold shadow-md shadow-indigo-500/20 inline-flex items-center gap-2 cursor-pointer"
              >
                <GraduationCap className="w-4 h-4" />
                <span>{t.generateLearningPathBtn}</span>
              </button>
            </div>
          ) : activePath.status === 'pending' || activePath.status === 'processing' ? (
            <div className="bg-white dark:bg-slate-900 border border-indigo-200 dark:border-indigo-900/60 rounded-2xl p-12 text-center space-y-4">
              <div className="relative inline-flex items-center justify-center">
                <div className="w-16 h-16 rounded-full bg-indigo-100 dark:bg-indigo-950/80 flex items-center justify-center animate-pulse">
                  <GraduationCap className="w-8 h-8 text-indigo-600 dark:text-indigo-400 animate-bounce" />
                </div>
              </div>
              <div>
                <h3 className="text-base font-bold text-slate-900 dark:text-white mb-1">
                  {t.learningGeneratingCardTitle}
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 max-w-md mx-auto">
                  {t.learningGeneratingCardDesc}
                </p>
              </div>
              <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-indigo-50 dark:bg-indigo-950/60 border border-indigo-200 dark:border-indigo-800 text-xs font-semibold text-indigo-600 dark:text-indigo-400">
                <span className="w-2 h-2 rounded-full bg-indigo-500 animate-ping" />
                <span className="capitalize">{activePath.status}</span> • {activePath.difficulty} ({activePath.language.toUpperCase()})
              </div>
            </div>
          ) : activePath.status === 'failed' ? (
            <div className="bg-white dark:bg-slate-900 border border-rose-200 dark:border-rose-900/60 rounded-2xl p-8 text-center space-y-4">
              <div className="w-12 h-12 rounded-full bg-rose-100 dark:bg-rose-950/80 flex items-center justify-center mx-auto text-rose-500">
                <AlertCircle className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-slate-900 dark:text-white mb-1">
                  {t.learningFailedCardTitle}
                </h3>
                <p className="text-xs text-rose-600 dark:text-rose-400 max-w-md mx-auto font-mono bg-rose-50 dark:bg-rose-950/40 p-3 rounded-xl border border-rose-100 dark:border-rose-900/40">
                  {activePath.error_message || t.learningFailedCardDesc}
                </p>
              </div>
              <button
                onClick={() => generateMutation.mutate()}
                disabled={generateMutation.isPending || isGenerating}
                className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-xs font-bold shadow-md shadow-indigo-500/20 inline-flex items-center gap-2 cursor-pointer"
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>{t.retryGeneration}</span>
              </button>
            </div>
          ) : currentPath ? (
            <div className="space-y-6">
              {/* Studio View Mode Switcher: Curriculum vs Learning Dashboard */}
              <div className="flex items-center gap-2 border-b border-slate-200 dark:border-slate-800 pb-3">
                <button
                  type="button"
                  onClick={() => setActiveStudioTab('curriculum')}
                  className={`px-4 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-2 cursor-pointer ${
                    activeStudioTab === 'curriculum'
                      ? 'bg-indigo-600 text-white shadow-xs'
                      : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800/60'
                  }`}
                >
                  <BookOpen className="w-4 h-4" />
                  <span>{t.tabCurriculum}</span>
                </button>
                <button
                  type="button"
                  onClick={() => setActiveStudioTab('dashboard')}
                  className={`px-4 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-2 cursor-pointer ${
                    activeStudioTab === 'dashboard'
                      ? 'bg-indigo-600 text-white shadow-xs'
                      : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800/60'
                  }`}
                >
                  <LayoutDashboard className="w-4 h-4" />
                  <span>{t.tabProgressDashboard}</span>
                  {progressData && (
                    <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-indigo-500/20 text-indigo-200 font-mono">
                      {Math.round(progressData.overall_completion_percentage)}%
                    </span>
                  )}
                </button>
              </div>

              {activeStudioTab === 'dashboard' ? (
                <LearningDashboard
                  learningPathId={currentPath.id}
                  onOpenLesson={handleOpenLesson}
                  onLaunchAssessment={(assessmentType, moduleId, lessonId, title) =>
                    setActiveAssessmentConfig({
                      isOpen: true,
                      learningPathId: currentPath.id,
                      assessmentType,
                      moduleId,
                      lessonId,
                      title: title || currentPath.title,
                    })
                  }
                />
              ) : (
                <>
                  {/* Path Metadata Banner */}
                  <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-xs space-y-4">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="uppercase text-xs font-bold px-2.5 py-1 rounded-full bg-indigo-100 dark:bg-indigo-950/80 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800">
                          {currentPath.difficulty}
                        </span>
                        <span className="uppercase text-xs font-bold px-2.5 py-1 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
                          {currentPath.language}
                        </span>
                        <span className="inline-flex items-center gap-1 text-xs font-semibold px-2.5 py-1 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400">
                          <Clock className="w-3.5 h-3.5" />
                          <span>{currentPath.estimated_duration_minutes} {t.estimatedMinutesLabel}</span>
                        </span>
                      </div>

                      <div className="flex items-center gap-2">
                        {currentPath.is_cached && (
                          <span className="flex items-center gap-1.5 font-bold text-xs text-cyan-700 dark:text-cyan-400 bg-cyan-50 dark:bg-cyan-950/70 px-2.5 py-1 rounded-full border border-cyan-200 dark:border-cyan-800">
                            <Zap className="w-3.5 h-3.5" />
                            <span>Cached ($0)</span>
                          </span>
                        )}

                        <button
                          type="button"
                          onClick={() =>
                            setActiveAssessmentConfig({
                              isOpen: true,
                              learningPathId: currentPath.id,
                              assessmentType: 'final_assessment',
                              title: currentPath.title,
                            })
                          }
                          className="px-3 py-1.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold shadow-xs inline-flex items-center gap-1.5 cursor-pointer transition-colors"
                        >
                          <Award className="w-3.5 h-3.5" />
                          <span>{t.takeFinalAssessmentBtn}</span>
                        </button>
                      </div>
                    </div>

                    <div>
                      <h3 className="text-xl font-bold text-slate-900 dark:text-white mb-2">
                        {currentPath.title}
                      </h3>
                      <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
                        {currentPath.description}
                      </p>
                    </div>

                    {/* Path Progress Bar */}
                    {progressData && (
                      <div className="pt-2 border-t border-slate-100 dark:border-slate-800 space-y-1.5">
                        <div className="flex items-center justify-between text-xs">
                          <span className="font-semibold text-slate-700 dark:text-slate-300">
                            {t.completionRateLabel}: <span className="font-bold text-indigo-600 dark:text-indigo-400">{Math.round(progressData.overall_completion_percentage)}%</span>
                          </span>
                          <span className="text-[11px] text-slate-500 dark:text-slate-400">
                            {progressData.completed_lessons} / {progressData.total_lessons} {t.completedLessonsLabel}
                          </span>
                        </div>
                        <div className="h-2 w-full bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-gradient-to-r from-indigo-500 to-emerald-500 rounded-full transition-all duration-500"
                            style={{ width: `${progressData.overall_completion_percentage}%` }}
                          />
                        </div>
                      </div>
                    )}

                {/* Prerequisites */}
                {currentPath.prerequisites && currentPath.prerequisites.length > 0 && (
                  <div className="pt-2 border-t border-slate-100 dark:border-slate-800">
                    <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500 block mb-2">
                      {t.prerequisitesLabel}
                    </span>
                    <div className="flex flex-wrap gap-2">
                      {currentPath.prerequisites.map((prereq, idx) => (
                        <span
                          key={idx}
                          className="text-xs px-2.5 py-1 rounded-lg bg-slate-100 dark:bg-slate-800/80 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700/60"
                        >
                          {typeof prereq === 'string' ? prereq : JSON.stringify(prereq)}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Overall Objectives */}
                {currentPath.learning_objectives && currentPath.learning_objectives.length > 0 && (
                  <div className="pt-2 border-t border-slate-100 dark:border-slate-800">
                    <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500 block mb-2">
                      {t.learningObjectivesLabel}
                    </span>
                    <ul className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs text-slate-700 dark:text-slate-300">
                      {currentPath.learning_objectives.map((obj, idx) => (
                        <li key={idx} className="flex items-start gap-2">
                          <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0 mt-0.5" />
                          <span>{typeof obj === 'string' ? obj : JSON.stringify(obj)}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>

              {/* Modules & Lessons Section */}
              <div className="space-y-4">
                <h4 className="text-sm font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 px-1">
                  {t.viewPathDetails} ({currentPath.modules?.length || 0} {t.modulesLabel})
                </h4>

                {(!currentPath.modules || currentPath.modules.length === 0) ? (
                  <div className="p-6 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl text-center text-xs text-slate-400">
                    No modules loaded for this curriculum yet.
                  </div>
                ) : (
                  currentPath.modules.map((mod: LearningModule, modIndex: number) => {
                    const isOpen = isModuleOpen(mod.id, modIndex === 0);
                    const modProgress = progressData?.modules?.find((m: ModuleProgressItem) => m.module_id === mod.id);
                    return (
                      <div
                        key={mod.id}
                        className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl overflow-hidden shadow-xs transition-all"
                      >
                        {/* Module Header Bar */}
                        <button
                          type="button"
                          onClick={() => toggleModule(mod.id)}
                          className="w-full p-5 text-left rtl:text-right flex items-center justify-between bg-slate-50/60 dark:bg-slate-800/40 hover:bg-slate-100/60 dark:hover:bg-slate-800/70 transition-colors cursor-pointer"
                        >
                          <div className="flex items-start gap-3">
                            <span className="w-7 h-7 rounded-lg bg-indigo-600 text-white flex items-center justify-center text-xs font-bold shrink-0">
                              {mod.sequence_order}
                            </span>
                            <div>
                              <h5 className="text-sm font-bold text-slate-900 dark:text-white">
                                {mod.title}
                              </h5>
                              <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5 line-clamp-1">
                                {mod.description}
                              </p>
                            </div>
                          </div>

                          <div className="flex items-center gap-2.5 shrink-0">
                            {modProgress && (
                              <span className="text-[10px] font-bold px-2 py-1 rounded-lg bg-indigo-50 dark:bg-indigo-950/60 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800">
                                {modProgress.completed_lessons}/{modProgress.total_lessons} ({Math.round(modProgress.completion_percentage)}%)
                              </span>
                            )}

                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                setActiveAssessmentConfig({
                                  isOpen: true,
                                  learningPathId: currentPath.id,
                                  assessmentType: 'module_assessment',
                                  moduleId: mod.id,
                                  title: mod.title,
                                });
                              }}
                              className="px-2.5 py-1 rounded-lg bg-purple-50 dark:bg-purple-950/60 hover:bg-purple-100 dark:hover:bg-purple-900/60 text-purple-700 dark:text-purple-300 border border-purple-200 dark:border-purple-800 text-[11px] font-bold inline-flex items-center gap-1.5 transition-colors cursor-pointer"
                            >
                              <Award className="w-3 h-3" />
                              <span>{t.takeModuleAssessmentBtn}</span>
                            </button>

                            <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 flex items-center gap-1">
                              <Clock className="w-3.5 h-3.5" />
                              <span>{mod.estimated_duration_minutes} {t.estimatedMinutesLabel}</span>
                            </span>
                            <span className="p-1 rounded-md text-slate-400 hover:text-slate-600 dark:hover:text-slate-200">
                              {isOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                            </span>
                          </div>
                        </button>

                        {/* Module Content & Lessons (Collapsible) */}
                        {isOpen && (
                          <div className="p-5 border-t border-slate-100 dark:border-slate-800 space-y-6">
                            {/* Module Objectives */}
                            {mod.learning_objectives && mod.learning_objectives.length > 0 && (
                              <div className="p-3.5 bg-indigo-50/40 dark:bg-indigo-950/20 rounded-xl border border-indigo-100 dark:border-indigo-900/40 space-y-1.5">
                                <span className="text-[11px] font-bold text-indigo-700 dark:text-indigo-300">
                                  {t.learningObjectivesLabel}:
                                </span>
                                <ul className="space-y-1 text-xs text-slate-700 dark:text-slate-300">
                                  {mod.learning_objectives.map((obj, i) => (
                                    <li key={i} className="flex items-center gap-2">
                                      <span className="w-1.5 h-1.5 rounded-full bg-indigo-500" />
                                      <span>{typeof obj === 'string' ? obj : JSON.stringify(obj)}</span>
                                    </li>
                                  ))}
                                </ul>
                              </div>
                            )}

                            {/* Lessons List */}
                            <div className="space-y-5">
                              {(!mod.lessons || mod.lessons.length === 0) ? (
                                <p className="text-xs text-slate-400 italic">No lessons in this module.</p>
                              ) : (
                                mod.lessons.map((lesson: LearningLesson) => {
                                  const isCompleted = completedLessonMap.has(lesson.id);
                                  return (
                                  <div
                                    key={lesson.id}
                                    className="p-5 rounded-xl border border-slate-200 dark:border-slate-800/80 bg-slate-50/30 dark:bg-slate-950/40 space-y-4"
                                  >
                                    {/* Lesson Title & Duration */}
                                    <div className="flex items-center justify-between gap-2 pb-2 border-b border-slate-100 dark:border-slate-800/60">
                                      <div className="flex items-center gap-2">
                                        <BookOpen className="w-4 h-4 text-indigo-500" />
                                        <h6 className="text-xs font-bold text-slate-900 dark:text-white">
                                          {mod.sequence_order}.{lesson.sequence_order} — {lesson.title}
                                        </h6>
                                      </div>
                                      <div className="flex items-center gap-2.5">
                                        {isCompleted ? (
                                          <span className="inline-flex items-center gap-1 text-[11px] font-bold text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/60 px-2.5 py-1 rounded-lg border border-emerald-200 dark:border-emerald-800">
                                            <CheckCircle2 className="w-3.5 h-3.5" />
                                            <span>{t.lessonCompletedBadge}</span>
                                          </span>
                                        ) : (
                                          <button
                                            type="button"
                                            onClick={() =>
                                              markLessonMutation.mutate({
                                                lessonId: lesson.id,
                                                status: 'completed',
                                              })
                                            }
                                            disabled={markLessonMutation.isPending}
                                            className="px-2 py-0.5 rounded-lg bg-slate-100 hover:bg-emerald-50 dark:bg-slate-800 dark:hover:bg-emerald-950/60 text-slate-600 hover:text-emerald-700 dark:text-slate-300 dark:hover:text-emerald-300 border border-slate-200 dark:border-slate-700 text-[11px] font-semibold inline-flex items-center gap-1 transition-colors cursor-pointer"
                                            title={t.markLessonCompletedBtn}
                                          >
                                            <CheckCircle2 className="w-3 h-3 text-slate-400" />
                                            <span>{t.markLessonCompletedBtn}</span>
                                          </button>
                                        )}

                                        <button
                                          type="button"
                                          onClick={() =>
                                            setActiveAssessmentConfig({
                                              isOpen: true,
                                              learningPathId: currentPath.id,
                                              assessmentType: 'lesson_quiz',
                                              lessonId: lesson.id,
                                              title: lesson.title,
                                            })
                                          }
                                          className="px-2 py-0.5 rounded-lg bg-indigo-50 dark:bg-indigo-950/60 hover:bg-indigo-100 dark:hover:bg-indigo-900/60 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800 text-[11px] font-bold inline-flex items-center gap-1 transition-colors cursor-pointer"
                                        >
                                          <Award className="w-3 h-3" />
                                          <span>{t.takeLessonQuizBtn}</span>
                                        </button>
                                        <span className="text-[11px] font-semibold text-slate-400">
                                          {lesson.estimated_duration_minutes} {t.estimatedMinutesLabel}
                                        </span>
                                      </div>
                                    </div>

                                    {/* Lesson Explanation Content */}
                                    <div className="text-xs text-slate-700 dark:text-slate-300 leading-relaxed whitespace-pre-wrap">
                                      {lesson.explanation}
                                    </div>

                                    {/* Key Technical Concepts */}
                                    {lesson.key_concepts && lesson.key_concepts.length > 0 && (
                                      <div className="space-y-2 pt-2">
                                        <span className="text-[11px] font-bold text-slate-500 dark:text-slate-400 flex items-center gap-1.5">
                                          <Lightbulb className="w-3.5 h-3.5 text-amber-500" />
                                          <span>{t.keyConceptsLabel}</span>
                                        </span>
                                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                                          {lesson.key_concepts.map((kc: any, kIdx: number) => {
                                            const isObj = typeof kc === 'object' && kc !== null;
                                            const term = isObj ? (kc.term || kc.name || '') : String(kc);
                                            const explanation = isObj ? (kc.explanation || kc.desc || '') : '';

                                            return (
                                              <div
                                                key={kIdx}
                                                className="p-2.5 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-xs"
                                              >
                                                <span className="font-bold text-indigo-600 dark:text-indigo-400 block mb-0.5">
                                                  {term}
                                                </span>
                                                {explanation && (
                                                  <span className="text-[11px] text-slate-600 dark:text-slate-400 leading-snug">
                                                    {explanation}
                                                  </span>
                                                )}
                                              </div>
                                            );
                                          })}
                                        </div>
                                      </div>
                                    )}

                                    {/* Practical Examples */}
                                    {lesson.examples && lesson.examples.length > 0 && (
                                      <div className="space-y-1.5 pt-2">
                                        <span className="text-[11px] font-bold text-slate-500 dark:text-slate-400 flex items-center gap-1.5">
                                          <Code2 className="w-3.5 h-3.5 text-indigo-400" />
                                          <span>{t.exampleSnippetLabel}</span>
                                        </span>
                                        <div className="space-y-2">
                                          {lesson.examples.map((ex: any, exIdx: number) => {
                                            const isObj = typeof ex === 'object' && ex !== null;
                                            const codeContent = isObj
                                              ? (ex.code || ex.snippet || JSON.stringify(ex, null, 2))
                                              : String(ex);
                                            const lang = isObj ? (ex.language || ex.lang) : null;

                                            return (
                                              <div key={exIdx} className="space-y-1">
                                                {lang && (
                                                  <span className="text-[10px] font-mono uppercase tracking-wider text-indigo-400 bg-indigo-950/60 px-2 py-0.5 rounded border border-indigo-800/40 inline-block">
                                                    {lang}
                                                  </span>
                                                )}
                                                <pre className="p-3.5 rounded-xl bg-slate-900 text-slate-100 font-mono text-[11px] overflow-x-auto border border-slate-800 leading-relaxed">
                                                  <code>{codeContent}</code>
                                                </pre>
                                              </div>
                                            );
                                          })}
                                        </div>
                                      </div>
                                    )}

                                    {/* Source Grounding & Citations */}
                                    {lesson.source_references && lesson.source_references.length > 0 && (
                                      <div className="space-y-2 pt-2 border-t border-slate-100 dark:border-slate-800/60">
                                        <span className="text-[11px] font-bold text-slate-500 dark:text-slate-400 flex items-center gap-1.5">
                                          <FileText className="w-3.5 h-3.5 text-emerald-500" />
                                          <span>{t.sourceReferencesLabel}</span>
                                        </span>
                                        <div className="flex flex-wrap gap-2">
                                          {lesson.source_references.map((src: any, sIdx: number) => {
                                            const page = src.page_number ?? src.page;
                                            const chunk = src.chunk_index ?? src.chunk;
                                            const section = src.section_title ?? src.section;
                                            const citation = src.citation_text ?? src.citation ?? section;

                                            return (
                                              <div
                                                key={sIdx}
                                                className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-emerald-50/70 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800/60 text-[11px]"
                                                title={citation || undefined}
                                              >
                                                <FileText className="w-3 h-3" />
                                                <span>
                                                  {page !== undefined && page !== null ? `Page ${page}` : ''}
                                                  {page !== undefined && page !== null && chunk !== undefined ? ' • ' : ''}
                                                  {chunk !== undefined ? (typeof chunk === 'number' ? `Chunk ${chunk}` : chunk) : ''}
                                                  {section ? ` (${section})` : ''}
                                                </span>
                                              </div>
                                            );
                                          })}
                                        </div>
                                      </div>
                                    )}
                                  </div>
                                );
                              })
                              )}
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })
                )}
              </div>
            </>
          )}
        </div>
      ) : null}
        </div>
      </div>
      {/* Interactive Assessment Modal (Phase 5B) */}
      {activeAssessmentConfig && (
        <AssessmentModal
          isOpen={activeAssessmentConfig.isOpen}
          onClose={() => setActiveAssessmentConfig(null)}
          learningPathId={activeAssessmentConfig.learningPathId}
          assessmentType={activeAssessmentConfig.assessmentType}
          moduleId={activeAssessmentConfig.moduleId}
          lessonId={activeAssessmentConfig.lessonId}
          title={activeAssessmentConfig.title}
          initialAttemptId={activeAssessmentConfig.initialAttemptId}
        />
      )}
    </div>
  );
};
