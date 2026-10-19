/**
 * TechSift AI - Document Workspace Page.
 * Deep architectural analysis, bilingual generation controls, structured concepts viewer,
 * and source citation inspection.
 */

import React, { useState, useEffect } from 'react';

import { useParams, Link, useSearchParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  FileText,
  Sparkles,
  BookOpen,
  Layers,
  CheckCircle2,
  AlertCircle,
  Clock,
  ArrowLeft,
  ArrowRight,
  Zap,
  Globe,
  Sliders,
  History,
  ShieldAlert,
  Hash,
  Bookmark,
  Headphones,
  GraduationCap,
} from 'lucide-react';
import { useLanguage } from '../context/LanguageContext';
import { api, ApiClientError } from '../services/api';
import type {
  LanguageCode,
  DetailLevel,
  SummaryItem,
  TechnicalSummaryContent,
  ConceptItem,
} from '../types/api';
import { StatusBadge } from '../components/common/StatusBadge';
import { KnowledgeJourney } from '../components/common/KnowledgeJourney';
import { AudioStudio } from '../components/audio/AudioStudio';
import { LearningStudio } from '../components/learning/LearningStudio';
import { ErrorBoundary } from '../components/common/ErrorBoundary';


function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
}

export const WorkspacePage: React.FC = () => {
  const { documentId } = useParams<{ documentId: string }>();
  const { t, direction } = useLanguage();
  const queryClient = useQueryClient();
  const BackArrow = direction === 'rtl' ? ArrowRight : ArrowLeft;

  // Local preferences or defaults
  const [searchParams] = useSearchParams();
  const paramTab = searchParams.get('tab') as 'summary' | 'audio' | 'learning' | 'source' | null;
  const savedDefaultLang = (localStorage.getItem('techsift_default_summary_lang') as LanguageCode) || 'ar';
  const savedDefaultDetail = (localStorage.getItem('techsift_default_detail_level') as DetailLevel) || 'standard';

  const [targetLang, setTargetLang] = useState<LanguageCode>(savedDefaultLang);
  const [detailLevel, setDetailLevel] = useState<DetailLevel>(savedDefaultDetail);
  const [userTab, setUserTab] = useState<'summary' | 'audio' | 'learning' | 'source' | null>(null);
  const activeTab = (paramTab && ['summary', 'audio', 'learning', 'source'].includes(paramTab)
    ? paramTab
    : userTab) || 'summary';
  const setActiveTab = (tab: 'summary' | 'audio' | 'learning' | 'source') => setUserTab(tab);
  const [selectedSummaryId, setSelectedSummaryId] = useState<string | null>(null);
  const [feedbackMessage, setFeedbackMessage] = useState<{
    type: 'success' | 'error' | 'info';
    text: string;
  } | null>(null);

  // Auto-clear feedback notification
  useEffect(() => {
    if (!feedbackMessage) return;
    const timer = setTimeout(() => setFeedbackMessage(null), 5000);
    return () => clearTimeout(timer);
  }, [feedbackMessage]);

  // 1. Fetch document details
  const {
    data: document,
    isLoading: isDocLoading,
    isError: isDocError,
    error: docError,
  } = useQuery({
    queryKey: ['document', documentId],
    queryFn: () => api.getDocument(documentId!),
    enabled: Boolean(documentId),
  });

  // 2. Fetch document summaries list with conditional polling for in-flight tasks
  const { data: summariesData } = useQuery({
    queryKey: ['document-summaries', documentId],
    queryFn: () => api.getDocumentSummaries(documentId!),
    enabled: Boolean(documentId),
    refetchInterval: (query) => {
      const items = query.state.data?.items || [];
      const hasInFlight = items.some(
        (s: SummaryItem) => s.status === 'pending' || s.status === 'processing'
      );
      return hasInFlight ? 2000 : false;
    },
  });

  const summaries: SummaryItem[] = summariesData?.items || [];

  // Determine current active summary
  const activeSummary: SummaryItem | null = selectedSummaryId
    ? summaries.find((s: SummaryItem) => s.id === selectedSummaryId) || null
    : summaries[0] || null;

  // Check if any summary is currently in progress
  const isSummaryProcessing = summaries.some(
    (s: SummaryItem) => s.status === 'pending' || s.status === 'processing'
  );

  const handleLanguageChange = (lang: LanguageCode) => {
    setTargetLang(lang);
    setFeedbackMessage(null);
    const matching = summaries.find(
      (s: SummaryItem) => s.language === lang && s.detail_level === detailLevel
    ) || summaries.find((s: SummaryItem) => s.language === lang);
    if (matching) {
      setSelectedSummaryId(matching.id);
    }
  };

  const handleDetailChange = (level: DetailLevel) => {
    setDetailLevel(level);
    setFeedbackMessage(null);
    const matching = summaries.find(
      (s: SummaryItem) => s.language === targetLang && s.detail_level === level
    );
    if (matching) {
      setSelectedSummaryId(matching.id);
    }
  };

  // 3. Generate Summary Mutation (Asynchronous: returns pending summary and auto-polls until completed)
  const generateMutation = useMutation({
    mutationFn: () =>
      api.createSummary(
        documentId!,
        {
          language: targetLang,
          detail_level: detailLevel,
        },
        false // Non-blocking: returns immediately and triggers background synthesis
      ),
    onSuccess: (newSummary: SummaryItem) => {
      queryClient.setQueryData(
        ['document-summaries', documentId],
        (old: { items: SummaryItem[]; total: number } | undefined) => {
          if (!old) return { items: [newSummary], total: 1 };
          const existingIdx = old.items.findIndex((s) => s.id === newSummary.id);
          if (existingIdx >= 0) {
            const updated = [...old.items];
            updated[existingIdx] = newSummary;
            return { ...old, items: updated };
          }
          return { ...old, items: [newSummary, ...old.items], total: old.total + 1 };
        }
      );
      queryClient.invalidateQueries({ queryKey: ['document-summaries', documentId] });
      queryClient.invalidateQueries({ queryKey: ['document-stats'] });
      setSelectedSummaryId(newSummary.id);
      setActiveTab('summary');

      if (newSummary.is_cached) {
        setFeedbackMessage({
          type: 'success',
          text: direction === 'rtl'
            ? 'تم استرجاع الملخص فوراً من الذاكرة المؤقتة (0 استهلاك ذكاء اصطناعي).'
            : 'Summary retrieved instantly from SQLite cache ($0 consumption).'
        });
      } else if (newSummary.status === 'completed') {
        setFeedbackMessage({
          type: 'success',
          text: direction === 'rtl'
            ? 'تم إنشاء الملخص الفني بنجاح!'
            : 'Technical summary generated successfully!'
        });
      } else if (newSummary.status === 'failed') {
        setFeedbackMessage({
          type: 'error',
          text: newSummary.error_message || (direction === 'rtl' ? 'فشل إنشاء الملخص.' : 'Summary generation failed.')
        });
      } else {
        setFeedbackMessage({
          type: 'info',
          text: direction === 'rtl'
            ? 'بدأ تحليل المستند وتوليد الملخص في الخلفية...'
            : 'Summary synthesis started in background...'
        });
      }
    },
    onError: (err: unknown) => {
      setFeedbackMessage({
        type: 'error',
        text: (err as ApiClientError)?.message || (direction === 'rtl' ? 'فشل طلب التوليد.' : 'Summary request failed. Please check connection.')
      });
    },
  });

  if (isDocLoading) {
    return (
      <div className="py-20 text-center text-sm text-slate-500">
        <Clock className="w-8 h-8 animate-spin mx-auto text-indigo-500 mb-2" />
        <span>{t.loading}</span>
      </div>
    );
  }

  if (isDocError || !document) {
    return (
      <div className="py-16 text-center max-w-md mx-auto">
        <AlertCircle className="w-10 h-10 text-rose-500 mx-auto mb-3" />
        <h2 className="text-lg font-bold text-slate-900 dark:text-white">
          {t.errorTitle}
        </h2>
        <p className="text-xs text-slate-500 mt-1 mb-4">
          {(docError as Error)?.message || 'Document could not be located.'}
        </p>
        <Link
          to="/documents"
          className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-100 dark:bg-slate-800 text-xs font-semibold"
        >
          <BackArrow className="w-4 h-4" />
          <span>{t.recentDocsViewAll}</span>
        </Link>
      </div>
    );
  }

  const summaryContent: TechnicalSummaryContent | null = activeSummary?.summary || null;

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Top Breadcrumb & Actions Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-200 dark:border-slate-800">
        <div className="flex items-center gap-3">
          <Link
            to="/documents"
            className="p-2 rounded-xl border border-slate-200 dark:border-slate-800 text-slate-500 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
            title={t.navLibrary}
          >
            <BackArrow className="w-4 h-4" />
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <span className="uppercase text-[10px] font-bold px-1.5 py-0.5 rounded-sm bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400">
                {document.file_type}
              </span>
              <h1 className="text-lg font-bold text-slate-900 dark:text-white truncate max-w-md sm:max-w-xl">
                {document.filename}
              </h1>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              {formatBytes(document.file_size)} • {document.word_count.toLocaleString()} words •{' '}
              {document.page_count ? `${document.page_count} pages` : 'Plain Text'}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <StatusBadge status={document.status} />
        </div>
      </div>

      {/* Compact Knowledge Journey Workflow Indicator */}
      <KnowledgeJourney compact />

      {/* Top Workspace Navigation Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-200 dark:border-slate-800 pb-3">
        <button
          type="button"
          onClick={() => setActiveTab('summary')}
          className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold transition-all ${
            activeTab === 'summary'
              ? 'bg-indigo-600 text-white shadow-xs'
              : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800'
          }`}
        >
          <Sparkles className="w-4 h-4" />
          <span>{t.tabSummary}</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('audio')}
          className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold transition-all ${
            activeTab === 'audio'
              ? 'bg-indigo-600 text-white shadow-xs'
              : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800'
          }`}
        >
          <Headphones className="w-4 h-4" />
          <span>{t.tabAudio}</span>
          <span className="text-[10px] font-bold px-1.5 py-0.5 rounded-full bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30">
            $0 Studio
          </span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('learning')}
          className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold transition-all ${
            activeTab === 'learning'
              ? 'bg-indigo-600 text-white shadow-xs'
              : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800'
          }`}
        >
          <GraduationCap className="w-4 h-4" />
          <span>{t.tabLearning}</span>
          <span className="text-[10px] font-bold px-1.5 py-0.5 rounded-full bg-indigo-500/20 text-indigo-600 dark:text-indigo-400 border border-indigo-500/30">
            $0 Studio
          </span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('source')}
          className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold transition-all ${
            activeTab === 'source'
              ? 'bg-indigo-600 text-white shadow-xs'
              : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800'
          }`}
        >
          <FileText className="w-4 h-4" />
          <span>{t.tabSourceText}</span>
        </button>
      </div>

      <ErrorBoundary fallbackTitle="Workspace Studio Error">
        {activeTab === 'audio' ? (
          <AudioStudio
            documentId={document.id}
            documentTitle={document.filename}
            summaries={summaries}
          />
        ) : activeTab === 'learning' ? (
          <LearningStudio
            documentId={document.id}
            documentTitle={document.filename}
          />
        ) : (
          /* Main Workspace Grid: Controls Panel (Left / Sticky) & Viewer (Right) */
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Controls Sidebar (4 Cols on LG) */}
        <div className="lg:col-span-4 space-y-6">
          {/* Generation Controls Card */}
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-xs space-y-5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-slate-900 dark:text-white font-bold text-sm">
                <Sliders className="w-4 h-4 text-indigo-500" />
                <span>{t.controlsTitle}</span>
              </div>
              <span className="text-[10px] font-semibold text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/60 px-2 py-0.5 rounded-full border border-emerald-200 dark:border-emerald-800/60">
                gemini-3.8-flash ($0)
              </span>
            </div>

            {/* Target Language Selection */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-2">
                {t.outputLanguageLabel}
              </label>
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => handleLanguageChange('ar')}
                  className={`px-3 py-2.5 rounded-xl border text-xs font-semibold flex items-center justify-center gap-1.5 transition-all ${
                    targetLang === 'ar'
                      ? 'border-indigo-600 bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 shadow-xs'
                      : 'border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800/60'
                  }`}
                >
                  <Globe className="w-3.5 h-3.5" />
                  <span>العربية (Modern Arabic)</span>
                </button>

                <button
                  type="button"
                  onClick={() => handleLanguageChange('en')}
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

            {/* Detail Level Selection */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-2">
                {t.detailLevelLabel}
              </label>
              <div className="space-y-2">
                {[
                  { id: 'short', title: t.detailShort, desc: t.detailShortDesc },
                  { id: 'standard', title: t.detailStandard, desc: t.detailStandardDesc },
                  { id: 'detailed', title: t.detailDetailed, desc: t.detailDetailedDesc },
                ].map((item) => (
                  <label
                    key={item.id}
                    onClick={() => handleDetailChange(item.id as DetailLevel)}
                    className={`block p-3 rounded-xl border cursor-pointer transition-all ${
                      detailLevel === item.id
                        ? 'border-indigo-600 bg-indigo-50/50 dark:bg-indigo-950/30 text-indigo-900 dark:text-indigo-200 ring-1 ring-indigo-500/20'
                        : 'border-slate-200 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/30 text-slate-700 dark:text-slate-300'
                    }`}
                  >
                    <div className="flex items-center justify-between text-xs font-semibold">
                      <span>{item.title}</span>
                      <input
                        type="radio"
                        name="detailLevel"
                        value={item.id}
                        checked={detailLevel === item.id}
                        onChange={() => handleDetailChange(item.id as DetailLevel)}
                        className="text-indigo-600 focus:ring-indigo-500 w-3.5 h-3.5"
                      />
                    </div>
                    <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">
                      {item.desc}
                    </p>
                  </label>
                ))}
              </div>
            </div>

            {/* Generate Action Button */}
            <button
              onClick={() => {
                setFeedbackMessage(null);
                generateMutation.mutate();
              }}
              disabled={generateMutation.isPending || isSummaryProcessing || document.status === 'failed'}
              className="w-full py-3 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-xs font-bold shadow-md shadow-indigo-500/20 transition-all flex items-center justify-center gap-2"
            >
              {generateMutation.isPending || isSummaryProcessing ? (
                <>
                  <Clock className="w-4 h-4 animate-spin" />
                  <span>{t.generatingSummary}</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  <span>{t.generateSummaryBtn}</span>
                </>
              )}
            </button>

            {/* Generation Feedback Status Banner */}
            {feedbackMessage && (
              <div
                className={`p-3 rounded-xl border text-xs flex items-center gap-2 animate-in fade-in duration-200 ${
                  feedbackMessage.type === 'success'
                    ? 'bg-emerald-50 dark:bg-emerald-950/60 border-emerald-200 dark:border-emerald-800 text-emerald-700 dark:text-emerald-300'
                    : feedbackMessage.type === 'info'
                    ? 'bg-indigo-50 dark:bg-indigo-950/60 border-indigo-200 dark:border-indigo-800 text-indigo-700 dark:text-indigo-300'
                    : 'bg-rose-50 dark:bg-rose-950/60 border-rose-200 dark:border-rose-800 text-rose-700 dark:text-rose-300'
                }`}
              >
                {feedbackMessage.type === 'success' ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" />
                ) : feedbackMessage.type === 'info' ? (
                  <Clock className="w-4 h-4 text-indigo-500 shrink-0 animate-spin" />
                ) : (
                  <AlertCircle className="w-4 h-4 text-rose-500 shrink-0" />
                )}
                <span>{feedbackMessage.text}</span>
              </div>
            )}

            {/* Error banner if generation fails */}
            {generateMutation.isError && !feedbackMessage && (
              <div className="p-3 bg-rose-50 dark:bg-rose-950/60 border border-rose-200 dark:border-rose-900/60 rounded-xl text-xs text-rose-700 dark:text-rose-300">
                <div className="flex items-center gap-1.5 font-bold mb-1">
                  <AlertCircle className="w-4 h-4 text-rose-500" />
                  <span>{t.statusFailed}</span>
                </div>
                <span>
                  {(generateMutation.error as ApiClientError)?.message ||
                    'Generation failed. Please retry.'}
                </span>
              </div>
            )}
          </div>

          {/* Previous Summaries History Card */}
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-xs space-y-3">
            <div className="flex items-center justify-between text-slate-900 dark:text-white font-bold text-xs">
              <div className="flex items-center gap-2">
                <History className="w-4 h-4 text-slate-500" />
                <span>{t.tabHistory}</span>
              </div>
              <span className="text-[11px] text-slate-400">
                {summaries.length} generated
              </span>
            </div>

            {summaries.length === 0 ? (
              <p className="text-xs text-slate-400 py-2">
                No past summaries for this document yet.
              </p>
            ) : (
              <div className="space-y-1.5 max-h-56 overflow-y-auto">
                {summaries.map((s: SummaryItem) => (
                  <button
                    key={s.id}
                    onClick={() => {
                      setSelectedSummaryId(s.id);
                      setTargetLang(s.language);
                      setDetailLevel(s.detail_level);
                      setActiveTab('summary');
                      setFeedbackMessage(null);
                    }}
                    className={`w-full text-left rtl:text-right p-2.5 rounded-xl border text-xs transition-colors flex items-center justify-between ${
                      activeSummary?.id === s.id
                        ? 'border-indigo-500 bg-indigo-50/70 dark:bg-indigo-950/40 font-semibold text-indigo-900 dark:text-indigo-200'
                        : 'border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800/40'
                    }`}
                  >
                    <div>
                      <div className="flex items-center gap-1.5">
                        <span className="uppercase text-[9px] font-bold px-1 py-0.5 rounded-xs bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
                          {s.language}
                        </span>
                        <span className="capitalize">{s.detail_level}</span>
                        {s.status === 'processing' || s.status === 'pending' ? (
                          <span className="inline-flex items-center gap-1 text-[9px] text-amber-600 dark:text-amber-400 font-bold bg-amber-50 dark:bg-amber-950/60 px-1.5 py-0.5 rounded-xs">
                            <Clock className="w-2.5 h-2.5 animate-spin" />
                            <span>{s.status}</span>
                          </span>
                        ) : s.status === 'failed' ? (
                          <span className="text-[9px] text-rose-500 font-bold bg-rose-50 dark:bg-rose-950/60 px-1.5 py-0.5 rounded-xs">
                            failed
                          </span>
                        ) : null}
                      </div>
                      <span className="text-[10px] text-slate-400 block mt-0.5">
                        {new Date(s.created_at).toLocaleTimeString([], {
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </span>
                    </div>

                    {s.is_cached && (
                      <span title={t.statusCached}>
                        <Zap className="w-3 h-3 text-cyan-500" />
                      </span>
                    )}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Viewer Content (8 Cols on LG) */}
        <div className="lg:col-span-8 space-y-6">
          {/* TAB 1: AI Technical Summary */}
          {activeTab === 'summary' && (
            <div className="space-y-6">
              {!activeSummary ? (
                <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-12 text-center">
                  <Sparkles className="w-10 h-10 text-indigo-400 mx-auto mb-3" />
                  <h3 className="text-base font-bold text-slate-800 dark:text-slate-200 mb-1">
                    {t.noSummaryYet}
                  </h3>
                  <p className="text-xs text-slate-400 max-w-sm mx-auto mb-6">
                    {t.noSummaryYetDesc}
                  </p>
                  <button
                    onClick={() => generateMutation.mutate()}
                    disabled={generateMutation.isPending || isSummaryProcessing}
                    className="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-xs font-bold shadow-md shadow-indigo-500/20 inline-flex items-center gap-2"
                  >
                    <Sparkles className="w-4 h-4" />
                    <span>{t.generateSummaryBtn}</span>
                  </button>
                </div>
              ) : activeSummary.status === 'pending' || activeSummary.status === 'processing' ? (
                <div className="bg-white dark:bg-slate-900 border border-indigo-200 dark:border-indigo-900/60 rounded-2xl p-12 text-center space-y-4">
                  <div className="relative inline-flex items-center justify-center">
                    <div className="w-16 h-16 rounded-full bg-indigo-100 dark:bg-indigo-950/80 flex items-center justify-center animate-pulse">
                      <Sparkles className="w-8 h-8 text-indigo-600 dark:text-indigo-400 animate-spin" style={{ animationDuration: '3s' }} />
                    </div>
                  </div>
                  <div>
                    <h3 className="text-base font-bold text-slate-900 dark:text-white mb-1">
                      {t.generatingSummary}
                    </h3>
                    <p className="text-xs text-slate-500 dark:text-slate-400 max-w-md mx-auto">
                      AI is analyzing document sections, extracting technical terminology, and synthesizing structured insights.
                    </p>
                  </div>
                  <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-indigo-50 dark:bg-indigo-950/60 border border-indigo-200 dark:border-indigo-800 text-xs font-semibold text-indigo-600 dark:text-indigo-400">
                    <span className="w-2 h-2 rounded-full bg-indigo-500 animate-ping" />
                    <span className="capitalize">{activeSummary.status}</span> • {activeSummary.detail_level} ({activeSummary.language.toUpperCase()})
                  </div>
                </div>
              ) : activeSummary.status === 'failed' ? (
                <div className="bg-white dark:bg-slate-900 border border-rose-200 dark:border-rose-900/60 rounded-2xl p-8 text-center space-y-4">
                  <div className="w-12 h-12 rounded-full bg-rose-100 dark:bg-rose-950/80 flex items-center justify-center mx-auto text-rose-500">
                    <AlertCircle className="w-6 h-6" />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-slate-900 dark:text-white mb-1">
                      {t.statusFailed}
                    </h3>
                    <p className="text-xs text-rose-600 dark:text-rose-400 max-w-md mx-auto font-mono bg-rose-50 dark:bg-rose-950/40 p-3 rounded-xl border border-rose-100 dark:border-rose-900/40">
                      {activeSummary.error_message || 'An error occurred during summary synthesis.'}
                    </p>
                  </div>
                  <button
                    onClick={() => generateMutation.mutate()}
                    disabled={generateMutation.isPending || isSummaryProcessing}
                    className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-xs font-bold shadow-md shadow-indigo-500/20 inline-flex items-center gap-2"
                  >
                    <Sparkles className="w-3.5 h-3.5" />
                    <span>{t.generateSummaryBtn}</span>
                  </button>
                </div>
              ) : summaryContent ? (
                <div className="space-y-6">
                  {/* Summary Status & Cache Origin Banner */}
                  <div className="flex flex-wrap items-center justify-between gap-3 p-3.5 bg-slate-100/70 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 rounded-2xl text-xs">
                    <div className="flex items-center gap-2">
                      {activeSummary.is_cached ? (
                        <span className="flex items-center gap-1.5 font-bold text-cyan-700 dark:text-cyan-400 bg-cyan-50 dark:bg-cyan-950/70 px-2.5 py-1 rounded-full border border-cyan-200 dark:border-cyan-800">
                          <Zap className="w-3.5 h-3.5" />
                          <span>{t.statusCached}</span>
                        </span>
                      ) : (
                        <span className="flex items-center gap-1.5 font-bold text-purple-700 dark:text-purple-400 bg-purple-50 dark:bg-purple-950/70 px-2.5 py-1 rounded-full border border-purple-200 dark:border-purple-800">
                          <Sparkles className="w-3.5 h-3.5" />
                          <span>{t.statusFresh}</span>
                        </span>
                      )}
                    </div>

                    <div className="text-slate-400 text-[11px] font-mono">
                      {t.modelBadgePrefix}: {activeSummary.model_used} • Lang:{' '}
                      <span className="uppercase font-bold">{activeSummary.language}</span>
                    </div>
                  </div>

                  {/* 1. Executive Summary Card */}
                  <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-xs">
                    <div className="flex items-center justify-between gap-3 mb-3">
                      <h3 className="text-sm font-bold uppercase tracking-wider text-indigo-600 dark:text-indigo-400 flex items-center gap-2">
                        <BookOpen className="w-4 h-4" />
                        <span>{t.sectionExecutive}</span>
                      </h3>
                      <button
                        type="button"
                        onClick={() => setActiveTab('audio')}
                        className="flex items-center gap-1.5 px-3 py-1 rounded-xl bg-indigo-50 dark:bg-indigo-950/60 hover:bg-indigo-100 dark:hover:bg-indigo-900/60 text-indigo-600 dark:text-indigo-400 border border-indigo-200 dark:border-indigo-800 text-xs font-semibold transition-colors"
                      >
                        <Headphones className="w-3.5 h-3.5" />
                        <span>{t.tabAudio}</span>
                      </button>
                    </div>
                    <p
                      className="text-sm text-slate-800 dark:text-slate-200 leading-relaxed font-normal whitespace-pre-line"
                      dir={activeSummary.language === 'ar' ? 'rtl' : 'ltr'}
                    >
                      {summaryContent.executive_summary}
                    </p>
                  </div>

                  {/* 2. Core Technical Concepts & Taxonomy */}
                  {summaryContent.main_concepts && summaryContent.main_concepts.length > 0 && (
                    <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-xs">
                      <h3 className="text-sm font-bold uppercase tracking-wider text-indigo-600 dark:text-indigo-400 mb-4 flex items-center gap-2">
                        <Layers className="w-4 h-4" />
                        <span>{t.sectionConcepts}</span>
                      </h3>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {summaryContent.main_concepts.map((concept: ConceptItem, idx: number) => (
                          <div
                            key={idx}
                            className="p-4 rounded-xl border border-slate-200 dark:border-slate-800/80 bg-slate-50/50 dark:bg-slate-800/20 hover:border-indigo-400 dark:hover:border-indigo-500 transition-colors"
                            dir={activeSummary.language === 'ar' ? 'rtl' : 'ltr'}
                          >
                            <h4 className="text-xs font-bold text-slate-900 dark:text-white mb-1.5 flex items-center justify-between gap-2">
                              <span className="flex items-center gap-2">
                                <span className="w-1.5 h-1.5 rounded-full bg-indigo-500" />
                                <span>{concept.term}</span>
                              </span>
                              {concept.category && (
                                <span className="text-[10px] font-medium px-2 py-0.5 rounded-md bg-indigo-50/80 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 border border-indigo-100 dark:border-indigo-900/60">
                                  {concept.category}
                                </span>
                              )}
                            </h4>
                            <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed mb-3">
                              {concept.definition}
                            </p>

                            {concept.relationships && concept.relationships.length > 0 && (
                              <div className="flex flex-wrap items-center gap-1.5 pt-2 border-t border-slate-200 dark:border-slate-800">
                                <span className="text-[10px] text-slate-400 font-semibold">
                                  {t.relatedConceptsLabel}:
                                </span>
                                {concept.relationships.map((rel: string, rIdx: number) => (
                                  <span
                                    key={rIdx}
                                    className="text-[10px] font-medium px-2 py-0.5 rounded-md bg-indigo-50 dark:bg-indigo-950 text-indigo-600 dark:text-indigo-400 border border-indigo-100 dark:border-indigo-900"
                                  >
                                    {rel}
                                  </span>
                                ))}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* 3. Key Findings & Takeaways (2 Columns) */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {/* Key Findings */}
                    {summaryContent.key_findings && summaryContent.key_findings.length > 0 && (
                      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-xs">
                        <h3 className="text-sm font-bold uppercase tracking-wider text-emerald-600 dark:text-emerald-400 mb-3 flex items-center gap-2">
                          <CheckCircle2 className="w-4 h-4" />
                          <span>{t.sectionFindings}</span>
                        </h3>
                        <ul
                          className="space-y-2.5 text-xs text-slate-700 dark:text-slate-300 leading-relaxed list-disc list-inside"
                          dir={activeSummary.language === 'ar' ? 'rtl' : 'ltr'}
                        >
                          {summaryContent.key_findings.map((finding: string, idx: number) => (
                            <li key={idx} className="pl-1">
                              {finding}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Key Takeaways */}
                    {summaryContent.key_takeaways && summaryContent.key_takeaways.length > 0 && (
                      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-xs">
                        <h3 className="text-sm font-bold uppercase tracking-wider text-purple-600 dark:text-purple-400 mb-3 flex items-center gap-2">
                          <Bookmark className="w-4 h-4" />
                          <span>{t.sectionTakeaways}</span>
                        </h3>
                        <ul
                          className="space-y-2.5 text-xs text-slate-700 dark:text-slate-300 leading-relaxed list-disc list-inside"
                          dir={activeSummary.language === 'ar' ? 'rtl' : 'ltr'}
                        >
                          {summaryContent.key_takeaways.map((takeaway: string, idx: number) => (
                            <li key={idx} className="pl-1">
                              {takeaway}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>

                  {/* 4. Architecture Overview (If Applicable) */}
                  {summaryContent.architecture_overview && (
                    <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-xs">
                      <h3 className="text-sm font-bold uppercase tracking-wider text-blue-600 dark:text-blue-400 mb-3 flex items-center gap-2">
                        <Layers className="w-4 h-4" />
                        <span>{t.sectionArchitecture}</span>
                      </h3>
                      <p
                        className="text-xs text-slate-800 dark:text-slate-200 leading-relaxed font-mono bg-slate-50 dark:bg-slate-950 p-4 rounded-xl border border-slate-200 dark:border-slate-800"
                        dir={activeSummary.language === 'ar' ? 'rtl' : 'ltr'}
                      >
                        {summaryContent.architecture_overview}
                      </p>
                    </div>
                  )}

                  {/* 5. Practical Applications & Limitations */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {/* Applications */}
                    {summaryContent.practical_applications &&
                      summaryContent.practical_applications.length > 0 && (
                        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-xs">
                          <h3 className="text-sm font-bold uppercase tracking-wider text-indigo-600 dark:text-indigo-400 mb-3 flex items-center gap-2">
                            <Sparkles className="w-4 h-4" />
                            <span>{t.sectionApplications}</span>
                          </h3>
                          <ul
                            className="space-y-2 text-xs text-slate-700 dark:text-slate-300 list-disc list-inside"
                            dir={activeSummary.language === 'ar' ? 'rtl' : 'ltr'}
                          >
                            {summaryContent.practical_applications.map((app: string, idx: number) => (
                              <li key={idx}>{app}</li>
                            ))}
                          </ul>
                        </div>
                      )}

                    {/* Limitations */}
                    {summaryContent.limitations && summaryContent.limitations.length > 0 && (
                      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-xs">
                        <h3 className="text-sm font-bold uppercase tracking-wider text-amber-600 dark:text-amber-400 mb-3 flex items-center gap-2">
                          <ShieldAlert className="w-4 h-4" />
                          <span>{t.sectionLimitations}</span>
                        </h3>
                        <ul
                          className="space-y-2 text-xs text-slate-700 dark:text-slate-300 list-disc list-inside"
                          dir={activeSummary.language === 'ar' ? 'rtl' : 'ltr'}
                        >
                          {summaryContent.limitations.map((lim: string, idx: number) => (
                            <li key={idx}>{lim}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>

                  {/* 6. Grounded Source Citations & References Panel */}
                  <div className="bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 text-xs space-y-3">
                    <div className="flex items-center gap-2 font-bold text-slate-900 dark:text-white">
                      <Hash className="w-4 h-4 text-indigo-500" />
                      <span>{t.sectionSources}</span>
                    </div>

                    <div className="flex flex-wrap items-center gap-3">
                      {/* Pages */}
                      <div className="flex items-center gap-1.5">
                        <span className="text-slate-500 font-semibold">
                          {t.sourcePagesLabel}:
                        </span>
                        {summaryContent.source_pages && summaryContent.source_pages.length > 0 ? (
                          <div className="flex items-center gap-1">
                            {summaryContent.source_pages.map((p: number) => (
                              <span
                                key={p}
                                className="px-2 py-0.5 rounded-md bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 font-mono font-bold text-slate-800 dark:text-slate-200"
                              >
                                p. {p}
                              </span>
                            ))}
                          </div>
                        ) : (
                          <span className="text-slate-400 italic">
                            {t.noSourcePagesAvailable}
                          </span>
                        )}
                      </div>

                      {/* Chunks */}
                      {summaryContent.source_chunks && summaryContent.source_chunks.length > 0 && (
                        <div className="flex items-center gap-1.5">
                          <span className="text-slate-500 font-semibold">
                            {t.sourceChunksLabel}:
                          </span>
                          <div className="flex items-center gap-1">
                            {summaryContent.source_chunks.map((c: number) => (
                              <span
                                key={c}
                                className="px-1.5 py-0.5 rounded-md bg-slate-200 dark:bg-slate-800 font-mono text-[10px] text-slate-600 dark:text-slate-300"
                              >
                                #{c}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>


                    <p className="text-[11px] text-slate-400 dark:text-slate-500 italic pt-1">
                      {summaryContent.disclaimer || t.sourceDisclaimer}
                    </p>
                  </div>
                </div>
              ) : (
                <div className="p-8 text-center bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl">
                  <AlertCircle className="w-8 h-8 text-amber-500 mx-auto mb-2" />
                  <p className="text-xs text-slate-400">
                    Summary status: {activeSummary.status}.{' '}
                    {activeSummary.error_message || 'Content pending completion.'}
                  </p>
                </div>
              )}
            </div>
          )}

          {/* TAB 2: Extracted Plain Text Inspection */}
          {activeTab === 'source' && (
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-xs space-y-3">
              <div className="flex items-center justify-between text-xs text-slate-400 pb-2 border-b border-slate-100 dark:border-slate-800">
                <span>{document.filename} (Extracted Content)</span>
                <span>{document.word_count.toLocaleString()} words</span>
              </div>
              <pre className="p-4 bg-slate-50 dark:bg-slate-950 rounded-xl border border-slate-200 dark:border-slate-800 text-xs font-mono text-slate-800 dark:text-slate-300 leading-relaxed overflow-x-auto whitespace-pre-wrap max-h-[600px] overflow-y-auto">
                {document.extracted_text || 'No text extracted for this document.'}
              </pre>
            </div>
          )}
        </div>
      </div>
      )}
      </ErrorBoundary>
    </div>
  );
};
