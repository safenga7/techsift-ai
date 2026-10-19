/**
 * TechSift AI - Document Library Page.
 * Search, filter, pagination, upload dropzone, and safe deletion modal.
 */

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  FileText,
  Search,
  Filter,
  Trash2,
  ExternalLink,
  ChevronLeft,
  ChevronRight,
  Plus,
  X,
  AlertCircle,
  FileCode,
  FileCheck,
} from 'lucide-react';
import { useLanguage } from '../context/LanguageContext';
import { api } from '../services/api';
import type { DocumentItem, DocumentStatus } from '../types/api';
import { StatusBadge } from '../components/common/StatusBadge';
import { DropZone } from '../components/common/DropZone';
import { DeleteModal } from '../components/common/DeleteModal';


function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
}

function formatDate(isoString: string): string {
  try {
    const d = new Date(isoString);
    return d.toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  } catch {
    return isoString;
  }
}

export const LibraryPage: React.FC = () => {
  const { t, direction } = useLanguage();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [page, setPage] = useState(1);
  const pageSize = 10;
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedStatus, setSelectedStatus] = useState<DocumentStatus | ''>('');
  const [showUploadZone, setShowUploadZone] = useState(false);
  const [documentToDelete, setDocumentToDelete] = useState<DocumentItem | null>(null);

  // Fetch documents with TanStack Query
  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['documents', { page, pageSize, status: selectedStatus }],
    queryFn: () =>
      api.getDocuments(page, pageSize, (selectedStatus || undefined) as DocumentStatus),
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.deleteDocument(id),
    onSuccess: () => {
      setDocumentToDelete(null);
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      queryClient.invalidateQueries({ queryKey: ['document-stats'] });
    },
  });

  const allItems = data?.items || [];
  const pagination = data?.pagination;

  // Local filter for quick search by title
  const filteredDocuments = allItems.filter((doc) =>
    doc.filename.toLowerCase().includes(searchQuery.toLowerCase().trim())
  );

  const getFormatIcon = (type: string) => {
    switch (type.toLowerCase()) {
      case 'pdf':
        return <FileText className="w-4 h-4 text-rose-500" />;
      case 'md':
        return <FileCode className="w-4 h-4 text-cyan-500" />;
      default:
        return <FileCheck className="w-4 h-4 text-indigo-500" />;
    }
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
            {t.libraryTitle}
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            {t.librarySubtitle}
          </p>
        </div>

        <button
          onClick={() => setShowUploadZone(!showUploadZone)}
          className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold shadow-sm transition-all shadow-indigo-500/20 w-fit"
        >
          {showUploadZone ? <X className="w-4 h-4" /> : <Plus className="w-4 h-4" />}
          <span>{showUploadZone ? t.close : t.uploadButton}</span>
        </button>
      </div>

      {/* Expandable Upload Zone */}
      {showUploadZone && (
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm animate-in fade-in slide-in-from-top-4">
          <DropZone
            onUploadSuccess={(doc) => {
              setShowUploadZone(false);
              refetch();
              navigate(`/workspace/${doc.id}`);
            }}
          />
        </div>
      )}

      {/* Filters and Search Bar */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-4 shadow-xs flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3">
        {/* Search Input */}
        <div className="relative flex-1">
          <Search className="w-4 h-4 absolute top-1/2 -translate-y-1/2 left-3 rtl:left-auto rtl:right-3 text-slate-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder={t.searchPlaceholder}
            className="w-full pl-9 pr-4 rtl:pl-4 rtl:pr-9 py-2 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/60 text-sm text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-hidden focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
          />
        </div>

        {/* Status Filter */}
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-slate-400 shrink-0" />
          <select
            value={selectedStatus}
            onChange={(e) => {
              setSelectedStatus(e.target.value as DocumentStatus | '');
              setPage(1);
            }}
            className="px-3 py-2 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/60 text-sm text-slate-800 dark:text-slate-200 focus:outline-hidden focus:ring-2 focus:ring-indigo-500/20"
          >
            <option value="">{t.filterAll}</option>
            <option value="processed">{t.filterProcessed}</option>
            <option value="pending">{t.filterPending}</option>
            <option value="failed">{t.filterFailed}</option>
            <option value="unsupported">{t.filterUnsupported}</option>
          </select>
        </div>
      </div>

      {/* Table Container */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-xs overflow-hidden">
        {isLoading ? (
          <div className="p-12 text-center text-sm text-slate-500">
            {t.loading}
          </div>
        ) : isError ? (
          <div className="p-12 text-center">
            <AlertCircle className="w-8 h-8 text-rose-500 mx-auto mb-2" />
            <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-200">
              {t.errorTitle}
            </h3>
            <p className="text-xs text-slate-400 mt-1 max-w-md mx-auto">
              {(error as Error)?.message || t.networkErrorDesc}
            </p>
          </div>
        ) : filteredDocuments.length === 0 ? (
          <div className="p-12 text-center">
            <FileText className="w-10 h-10 text-slate-300 dark:text-slate-600 mx-auto mb-2" />
            <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300">
              {t.noDocsYet}
            </h3>
            <p className="text-xs text-slate-400 mt-1 max-w-sm mx-auto">
              {t.noDocsYetDesc}
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50/70 dark:bg-slate-800/40 border-b border-slate-200 dark:border-slate-800 text-slate-500 dark:text-slate-400 font-semibold uppercase tracking-wider">
                <tr>
                  <th className="px-5 py-3.5">{t.thFilename}</th>
                  <th className="px-4 py-3.5">{t.thType}</th>
                  <th className="px-4 py-3.5">{t.thSize}</th>
                  <th className="px-4 py-3.5">{t.thWords}</th>
                  <th className="px-4 py-3.5">{t.thPages}</th>
                  <th className="px-4 py-3.5">{t.thStatus}</th>
                  <th className="px-4 py-3.5">{t.thDate}</th>
                  <th className="px-5 py-3.5 text-right">{t.thActions}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60">
                {filteredDocuments.map((doc) => (
                  <tr
                    key={doc.id}
                    className="hover:bg-slate-50/70 dark:hover:bg-slate-800/30 transition-colors group"
                  >
                    {/* Filename */}
                    <td className="px-5 py-4 font-semibold text-slate-900 dark:text-white max-w-[280px]">
                      <div className="flex items-center gap-2.5 truncate">
                        {getFormatIcon(doc.file_type)}
                        <span className="truncate" title={doc.filename}>
                          {doc.filename}
                        </span>
                      </div>
                    </td>

                    {/* Format */}
                    <td className="px-4 py-4 uppercase font-bold text-[10px] text-slate-500">
                      {doc.file_type}
                    </td>

                    {/* Size */}
                    <td className="px-4 py-4 text-slate-600 dark:text-slate-400">
                      {formatBytes(doc.file_size)}
                    </td>

                    {/* Words */}
                    <td className="px-4 py-4 text-slate-600 dark:text-slate-400">
                      {doc.word_count.toLocaleString()}
                    </td>

                    {/* Pages */}
                    <td className="px-4 py-4 text-slate-600 dark:text-slate-400">
                      {doc.page_count ?? 'N/A'}
                    </td>

                    {/* Status */}
                    <td className="px-4 py-4">
                      <StatusBadge status={doc.status} />
                    </td>

                    {/* Ingestion Date */}
                    <td className="px-4 py-4 text-slate-500 dark:text-slate-400">
                      {formatDate(doc.created_at)}
                    </td>

                    {/* Action buttons */}
                    <td className="px-5 py-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => navigate(`/workspace/${doc.id}`)}
                          className="p-1.5 rounded-lg text-indigo-600 hover:bg-indigo-50 dark:text-indigo-400 dark:hover:bg-indigo-950/60 transition-colors"
                          title={t.actionOpenWorkspace}
                        >
                          <ExternalLink className="w-4 h-4" />
                        </button>

                        <button
                          onClick={() => setDocumentToDelete(doc)}
                          className="p-1.5 rounded-lg text-rose-500 hover:bg-rose-50 dark:text-rose-400 dark:hover:bg-rose-950/60 transition-colors"
                          title={t.actionDelete}
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination Bar */}
        {pagination && pagination.total_pages > 1 && (
          <div className="px-5 py-3.5 bg-slate-50/50 dark:bg-slate-800/30 border-t border-slate-200 dark:border-slate-800 flex items-center justify-between text-xs text-slate-500">
            <div>
              {t.paginationPage} <span className="font-semibold">{pagination.page}</span>{' '}
              {t.paginationOf}{' '}
              <span className="font-semibold">{pagination.total_pages}</span> (
              {pagination.total} documents)
            </div>

            <div className="flex items-center gap-1.5">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page <= 1}
                className="p-1.5 rounded-lg border border-slate-200 dark:border-slate-700 disabled:opacity-40 hover:bg-white dark:hover:bg-slate-800 transition-colors"
              >
                {direction === 'rtl' ? (
                  <ChevronRight className="w-4 h-4" />
                ) : (
                  <ChevronLeft className="w-4 h-4" />
                )}
              </button>

              <button
                onClick={() => setPage((p) => Math.min(pagination.total_pages, p + 1))}
                disabled={page >= pagination.total_pages}
                className="p-1.5 rounded-lg border border-slate-200 dark:border-slate-700 disabled:opacity-40 hover:bg-white dark:hover:bg-slate-800 transition-colors"
              >
                {direction === 'rtl' ? (
                  <ChevronLeft className="w-4 h-4" />
                ) : (
                  <ChevronRight className="w-4 h-4" />
                )}
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Delete Confirmation Modal */}
      <DeleteModal
        isOpen={Boolean(documentToDelete)}
        documentTitle={documentToDelete?.filename || ''}
        isDeleting={deleteMutation.isPending}
        onConfirm={() => {
          if (documentToDelete) {
            deleteMutation.mutate(documentToDelete.id);
          }
        }}
        onCancel={() => setDocumentToDelete(null)}
      />
    </div>
  );
};
