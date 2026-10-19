/**
 * TechSift AI - Status Badge Component.
 * Color-coded indicators for document and summary lifecycles.
 */

import React from 'react';
import { CheckCircle2, Clock, AlertCircle, AlertTriangle, Zap, Sparkles } from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';

export type BadgeVariant =
  | 'processed'
  | 'pending'
  | 'processing'
  | 'completed'
  | 'failed'
  | 'unsupported'
  | 'cached'
  | 'fresh';

interface StatusBadgeProps {
  status: string;
  variant?: BadgeVariant;
  className?: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, variant, className = '' }) => {
  const { t } = useLanguage();
  const key = (variant || status).toLowerCase();

  switch (key) {
    case 'processed':
    case 'completed':
      return (
        <span
          className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800/60 ${className}`}
        >
          <CheckCircle2 className="w-3.5 h-3.5" />
          {t.statusCompleted}
        </span>
      );

    case 'processing':
      return (
        <span
          className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-indigo-50 text-indigo-700 dark:bg-indigo-950/60 dark:text-indigo-400 border border-indigo-200 dark:border-indigo-800/60 animate-pulse ${className}`}
        >
          <Clock className="w-3.5 h-3.5 animate-spin" />
          {t.statusProcessing}
        </span>
      );

    case 'pending':
      return (
        <span
          className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-amber-50 text-amber-700 dark:bg-amber-950/60 dark:text-amber-400 border border-amber-200 dark:border-amber-800/60 ${className}`}
        >
          <Clock className="w-3.5 h-3.5" />
          {t.statusPending}
        </span>
      );

    case 'failed':
      return (
        <span
          className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-rose-50 text-rose-700 dark:bg-rose-950/60 dark:text-rose-400 border border-rose-200 dark:border-rose-800/60 ${className}`}
        >
          <AlertCircle className="w-3.5 h-3.5" />
          {t.statusFailed}
        </span>
      );

    case 'unsupported':
      return (
        <span
          className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300 border border-slate-300 dark:border-slate-700 ${className}`}
        >
          <AlertTriangle className="w-3.5 h-3.5" />
          {t.filterUnsupported}
        </span>
      );

    case 'cached':
      return (
        <span
          className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-cyan-50 text-cyan-800 dark:bg-cyan-950/70 dark:text-cyan-300 border border-cyan-200 dark:border-cyan-800 ${className}`}
        >
          <Zap className="w-3.5 h-3.5 text-cyan-600 dark:text-cyan-400" />
          {t.statusCached}
        </span>
      );

    case 'fresh':
      return (
        <span
          className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-purple-50 text-purple-800 dark:bg-purple-950/70 dark:text-purple-300 border border-purple-200 dark:border-purple-800 ${className}`}
        >
          <Sparkles className="w-3.5 h-3.5 text-purple-600 dark:text-purple-400" />
          {t.statusFresh}
        </span>
      );

    default:
      return (
        <span
          className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300 ${className}`}
        >
          {status}
        </span>
      );
  }
};
