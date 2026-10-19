/**
 * TechSift AI - Dashboard Page.
 * Real metrics, pipeline activity, Knowledge Journey, and quick ingestion action.
 */

import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  FileText,
  Sparkles,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  ArrowLeft,
  Layers,
  UploadCloud,
} from 'lucide-react';
import { useLanguage } from '../context/LanguageContext';
import { api } from '../services/api';
import { StatusBadge } from '../components/common/StatusBadge';
import { KnowledgeJourney } from '../components/common/KnowledgeJourney';
import { DropZone } from '../components/common/DropZone';
import type { DocumentItem } from '../types/api';


function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
}

export const DashboardPage: React.FC = () => {
  const { t, direction } = useLanguage();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const ArrowIcon = direction === 'rtl' ? ArrowLeft : ArrowRight;

  // 1. Dedicated query for aggregate statistics across the entire collection
  const {
    data: statsData,
    isLoading: isLoadingStats,
  } = useQuery({
    queryKey: ['document-stats'],
    queryFn: () => api.getDocumentStats(),
  });

  // 2. Fetch strictly the top 5 documents for the Recent Documents table
  const {
    data: documentsData,
    isLoading: isLoadingDocs,
  } = useQuery({
    queryKey: ['documents', { page: 1, pageSize: 5 }],
    queryFn: () => api.getDocuments(1, 5),
  });

  const recentDocs = documentsData?.items || [];
  const totalDocs = statsData?.total_documents ?? 0;
  const processedDocs = statsData?.processed_documents ?? 0;
  const failedDocs = statsData?.issues_documents ?? 0;
  const totalSummaries = statsData?.total_summaries ?? 0;
  const isLoading = isLoadingStats || isLoadingDocs;

  const handleUploadSuccess = (doc: DocumentItem) => {
    queryClient.invalidateQueries({ queryKey: ['documents'] });
    queryClient.invalidateQueries({ queryKey: ['document-stats'] });
    navigate(`/workspace/${doc.id}`);
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-200">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
            {t.dashboardTitle}
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            {t.dashboardSubtitle}
          </p>
        </div>

        <Link
          to="/documents"
          className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold shadow-sm transition-all shadow-indigo-500/20 w-fit"
        >
          <UploadCloud className="w-4 h-4" />
          <span>{t.uploadButton}</span>
        </Link>
      </div>

      {/* Knowledge Journey Workflow Banner */}
      <KnowledgeJourney />

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Documents */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
              {t.statTotalDocs}
            </span>
            <div className="p-2 bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 rounded-xl">
              <FileText className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-slate-900 dark:text-white">
              {isLoading ? '...' : totalDocs}
            </span>
            <span className="text-xs text-slate-500 dark:text-slate-400">files</span>
          </div>
        </div>

        {/* Ready for Analysis */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
              {t.statProcessedDocs}
            </span>
            <div className="p-2 bg-emerald-50 dark:bg-emerald-950/60 text-emerald-600 dark:text-emerald-400 rounded-xl">
              <CheckCircle2 className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-slate-900 dark:text-white">
              {isLoading ? '...' : processedDocs}
            </span>
            <span className="text-xs text-emerald-600 dark:text-emerald-400 font-medium">ready</span>
          </div>
        </div>

        {/* Summaries Status */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
              {t.statTotalSummaries}
            </span>
            <div className="p-2 bg-purple-50 dark:bg-purple-950/60 text-purple-600 dark:text-purple-400 rounded-xl">
              <Sparkles className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-slate-900 dark:text-white">
              {isLoadingStats ? '...' : totalSummaries}
            </span>
            <span className="text-xs text-purple-600 dark:text-purple-400 font-medium">completed</span>
          </div>
        </div>

        {/* Attention / Failed */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
              {t.statFailedDocs}
            </span>
            <div className="p-2 bg-rose-50 dark:bg-rose-950/60 text-rose-600 dark:text-rose-400 rounded-xl">
              <AlertTriangle className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-slate-900 dark:text-white">
              {isLoading ? '...' : failedDocs}
            </span>
            <span className="text-xs text-slate-500 dark:text-slate-400">issues</span>
          </div>
        </div>
      </div>

      {/* Main Grid: Quick Upload & Recent Documents */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Quick Ingest Card (1 Col) */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <div className="p-2 bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 rounded-xl">
                <UploadCloud className="w-5 h-5" />
              </div>
              <h2 className="text-base font-bold text-slate-900 dark:text-white">
                {t.quickUploadTitle}
              </h2>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400 mb-4 leading-relaxed">
              {t.quickUploadDesc}
            </p>
          </div>

          <DropZone compact onUploadSuccess={handleUploadSuccess} />
        </div>

        {/* Recently Uploaded Documents (2 Cols) */}
        <div className="lg:col-span-2 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-xs">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <div className="p-2 bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 rounded-xl">
                <Layers className="w-5 h-5" />
              </div>
              <h2 className="text-base font-bold text-slate-900 dark:text-white">
                {t.recentDocsTitle}
              </h2>
            </div>

            <Link
              to="/documents"
              className="text-xs font-semibold text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 flex items-center gap-1"
            >
              <span>{t.recentDocsViewAll}</span>
              <ArrowIcon className="w-3.5 h-3.5" />
            </Link>
          </div>

          {recentDocs.length === 0 ? (
            <div className="text-center py-12 border border-dashed border-slate-200 dark:border-slate-800 rounded-xl">
              <FileText className="w-10 h-10 mx-auto text-slate-300 dark:text-slate-600 mb-2" />
              <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300">
                {t.noDocsYet}
              </h3>
              <p className="text-xs text-slate-400 max-w-sm mx-auto mt-1">
                {t.noDocsYetDesc}
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-200 dark:border-slate-800 text-slate-400 dark:text-slate-500">
                    <th className="py-2.5 font-medium">{t.thFilename}</th>
                    <th className="py-2.5 font-medium">{t.thSize}</th>
                    <th className="py-2.5 font-medium">{t.thStatus}</th>
                    <th className="py-2.5 font-medium text-right">{t.thActions}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60">
                  {recentDocs.map((doc) => (
                    <tr
                      key={doc.id}
                      className="hover:bg-slate-50/50 dark:hover:bg-slate-800/30 transition-colors"
                    >
                      <td className="py-3 font-medium text-slate-800 dark:text-slate-200 max-w-[220px] truncate">
                        <div className="flex items-center gap-2">
                          <span className="uppercase text-[10px] font-bold px-1.5 py-0.5 rounded-sm bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400">
                            {doc.file_type}
                          </span>
                          <span className="truncate">{doc.filename}</span>
                        </div>
                      </td>
                      <td className="py-3 text-slate-500 dark:text-slate-400">
                        {formatBytes(doc.file_size)}
                      </td>
                      <td className="py-3">
                        <StatusBadge status={doc.status} />
                      </td>
                      <td className="py-3 text-right">
                        <button
                          onClick={() => navigate(`/workspace/${doc.id}`)}
                          className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-indigo-50 hover:bg-indigo-100 dark:bg-indigo-950/60 dark:hover:bg-indigo-900/60 text-indigo-600 dark:text-indigo-400 font-semibold text-xs transition-colors"
                        >
                          <span>{t.actionOpenWorkspace}</span>
                          <ArrowIcon className="w-3 h-3" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
