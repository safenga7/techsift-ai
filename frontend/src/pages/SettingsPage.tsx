/**
 * TechSift AI - Settings & System Diagnostics Page.
 * Manages preferences (Language, Theme, Summary defaults) and live backend connectivity checks.
 */

import React, { useState } from 'react';
import {
  Settings as SettingsIcon,
  Globe,
  Sun,
  Moon,
  Activity,
  ShieldCheck,
  CheckCircle2,
  AlertCircle,
  Database,
  Cpu,
  Layers,
} from 'lucide-react';
import { useLanguage } from '../context/LanguageContext';
import { useTheme } from '../context/ThemeContext';
import { api } from '../services/api';
import type { LanguageCode, DetailLevel, HealthResponse } from '../types/api';


export const SettingsPage: React.FC = () => {
  const { t, language, setLanguage } = useLanguage();
  const { theme, setTheme } = useTheme();

  // Local preferences
  const [defaultSummaryLang, setDefaultSummaryLang] = useState<LanguageCode>(() => {
    return (localStorage.getItem('techsift_default_summary_lang') as LanguageCode) || 'ar';
  });

  const [defaultDetailLevel, setDefaultDetailLevel] = useState<DetailLevel>(() => {
    return (localStorage.getItem('techsift_default_detail_level') as DetailLevel) || 'standard';
  });

  // Diagnostics State
  const [isTestingApi, setIsTestingApi] = useState(false);
  const [healthData, setHealthData] = useState<HealthResponse | null>(null);
  const [healthLatency, setHealthLatency] = useState<number | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);
  const [savedNotice, setSavedNotice] = useState(false);

  const handleSaveDefaults = (lang: LanguageCode, detail: DetailLevel) => {
    setDefaultSummaryLang(lang);
    setDefaultDetailLevel(detail);
    localStorage.setItem('techsift_default_summary_lang', lang);
    localStorage.setItem('techsift_default_detail_level', detail);
    setSavedNotice(true);
    setTimeout(() => setSavedNotice(false), 3000);
  };

  const handleTestBackend = async () => {
    setIsTestingApi(true);
    setHealthError(null);
    const start = performance.now();

    try {
      const data = await api.getHealth();
      const end = performance.now();
      setHealthData(data);
      setHealthLatency(Math.round(end - start));
    } catch (err: unknown) {
      setHealthError((err as Error).message || 'Connection failed.');
      setHealthData(null);
      setHealthLatency(null);
    } finally {
      setIsTestingApi(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8 animate-in fade-in duration-200">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white flex items-center gap-2.5">
          <SettingsIcon className="w-6 h-6 text-indigo-500" />
          <span>{t.settingsTitle}</span>
        </h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
          {t.settingsSubtitle}
        </p>
      </div>

      {savedNotice && (
        <div className="p-3 bg-emerald-50 dark:bg-emerald-950/60 border border-emerald-200 dark:border-emerald-900/60 rounded-xl text-xs text-emerald-700 dark:text-emerald-300 flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-500" />
          <span>{t.savePreferencesSuccess}</span>
        </div>
      )}

      {/* User Preferences Card */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-xs space-y-6">
        <h2 className="text-sm font-bold uppercase tracking-wider text-indigo-600 dark:text-indigo-400 pb-2 border-b border-slate-100 dark:border-slate-800">
          {t.sectionPreferences}
        </h2>

        {/* 1. Interface Language */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <label className="text-sm font-semibold text-slate-900 dark:text-white flex items-center gap-2">
              <Globe className="w-4 h-4 text-slate-400" />
              <span>{t.uiLanguageLabel}</span>
            </label>
            <p className="text-xs text-slate-400 mt-0.5">
              Supports English (LTR) and Modern Standard Arabic (RTL)
            </p>
          </div>

          <div className="inline-flex rounded-xl p-1 bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
            <button
              onClick={() => setLanguage('en')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                language === 'en'
                  ? 'bg-white dark:bg-slate-900 text-indigo-600 dark:text-indigo-400 shadow-xs'
                  : 'text-slate-500 hover:text-slate-900 dark:hover:text-white'
              }`}
            >
              English
            </button>
            <button
              onClick={() => setLanguage('ar')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                language === 'ar'
                  ? 'bg-white dark:bg-slate-900 text-indigo-600 dark:text-indigo-400 shadow-xs'
                  : 'text-slate-500 hover:text-slate-900 dark:hover:text-white'
              }`}
            >
              العربية (Arabic)
            </button>
          </div>
        </div>

        {/* 2. Color Theme */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-4 border-t border-slate-100 dark:border-slate-800">
          <div>
            <label className="text-sm font-semibold text-slate-900 dark:text-white flex items-center gap-2">
              {theme === 'dark' ? (
                <Moon className="w-4 h-4 text-purple-400" />
              ) : (
                <Sun className="w-4 h-4 text-amber-500" />
              )}
              <span>{t.themeLabel}</span>
            </label>
            <p className="text-xs text-slate-400 mt-0.5">
              Choose between dark technical aesthetic or crisp light mode
            </p>
          </div>

          <div className="inline-flex rounded-xl p-1 bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
            <button
              onClick={() => setTheme('light')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                theme === 'light'
                  ? 'bg-white dark:bg-slate-900 text-indigo-600 dark:text-indigo-400 shadow-xs'
                  : 'text-slate-500 hover:text-slate-900 dark:hover:text-white'
              }`}
            >
              <Sun className="w-3.5 h-3.5" />
              <span>{t.themeLight}</span>
            </button>
            <button
              onClick={() => setTheme('dark')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                theme === 'dark'
                  ? 'bg-white dark:bg-slate-900 text-indigo-600 dark:text-indigo-400 shadow-xs'
                  : 'text-slate-500 hover:text-slate-900 dark:hover:text-white'
              }`}
            >
              <Moon className="w-3.5 h-3.5" />
              <span>{t.themeDark}</span>
            </button>
          </div>
        </div>

        {/* 3. Default Summary Language */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-4 border-t border-slate-100 dark:border-slate-800">
          <div>
            <label className="text-sm font-semibold text-slate-900 dark:text-white">
              {t.defaultSummaryLangLabel}
            </label>
            <p className="text-xs text-slate-400 mt-0.5">
              Default output language for AI technical summarization
            </p>
          </div>

          <select
            value={defaultSummaryLang}
            onChange={(e) =>
              handleSaveDefaults(e.target.value as LanguageCode, defaultDetailLevel)
            }
            className="px-3 py-1.5 rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-xs font-semibold text-slate-800 dark:text-slate-200"
          >
            <option value="ar">{t.langArabic}</option>
            <option value="en">{t.langEnglish}</option>
          </select>
        </div>

        {/* 4. Default Detail Level */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-4 border-t border-slate-100 dark:border-slate-800">
          <div>
            <label className="text-sm font-semibold text-slate-900 dark:text-white">
              {t.defaultDetailLevelLabel}
            </label>
            <p className="text-xs text-slate-400 mt-0.5">
              Default depth and granularity of generated summaries
            </p>
          </div>

          <select
            value={defaultDetailLevel}
            onChange={(e) =>
              handleSaveDefaults(defaultSummaryLang, e.target.value as DetailLevel)
            }
            className="px-3 py-1.5 rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-xs font-semibold text-slate-800 dark:text-slate-200"
          >
            <option value="short">{t.detailShort}</option>
            <option value="standard">{t.detailStandard}</option>
            <option value="detailed">{t.detailDetailed}</option>
          </select>
        </div>
      </div>

      {/* Backend Health Diagnostics Card */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-xs space-y-5">
        <div className="flex items-center justify-between pb-2 border-b border-slate-100 dark:border-slate-800">
          <h2 className="text-sm font-bold uppercase tracking-wider text-indigo-600 dark:text-indigo-400 flex items-center gap-2">
            <Activity className="w-4 h-4" />
            <span>{t.sectionSystemHealth}</span>
          </h2>

          <button
            onClick={handleTestBackend}
            disabled={isTestingApi}
            className="px-3 py-1.5 rounded-xl bg-indigo-50 hover:bg-indigo-100 dark:bg-indigo-950 dark:hover:bg-indigo-900 text-indigo-600 dark:text-indigo-400 text-xs font-semibold transition-colors disabled:opacity-50"
          >
            {isTestingApi ? t.testingConnection : t.testConnectionBtn}
          </button>
        </div>

        {healthData && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-slate-50/70 dark:bg-slate-800/40 p-4 rounded-xl border border-slate-200 dark:border-slate-800 text-xs font-mono">
            <div>
              <span className="text-[10px] text-slate-400 uppercase font-semibold block">
                {t.backendStatusLabel}
              </span>
              <span className="font-bold text-emerald-600 dark:text-emerald-400">
                {healthData.status.toUpperCase()}
              </span>
            </div>
            <div>
              <span className="text-[10px] text-slate-400 uppercase font-semibold block">
                {t.backendVersionLabel}
              </span>
              <span className="font-bold text-slate-800 dark:text-slate-200">
                {healthData.version}
              </span>
            </div>
            <div>
              <span className="text-[10px] text-slate-400 uppercase font-semibold block">
                {t.backendEnvLabel}
              </span>
              <span className="font-bold text-slate-800 dark:text-slate-200">
                {healthData.environment}
              </span>
            </div>
            <div>
              <span className="text-[10px] text-slate-400 uppercase font-semibold block">
                Latency
              </span>
              <span className="font-bold text-indigo-600 dark:text-indigo-400">
                {healthLatency} ms
              </span>
            </div>
          </div>
        )}

        {healthError && (
          <div className="p-3 bg-rose-50 dark:bg-rose-950/60 border border-rose-200 dark:border-rose-900/60 rounded-xl text-xs text-rose-700 dark:text-rose-300 flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-rose-500" />
            <span>{healthError}</span>
          </div>
        )}
      </div>

      {/* Zero-Cost Architecture Guarantee Card */}
      <div className="bg-gradient-to-tr from-slate-900 to-indigo-950 text-white rounded-2xl p-6 shadow-md border border-indigo-900/50 space-y-3">
        <div className="flex items-center gap-2.5">
          <div className="p-2 bg-emerald-500/20 text-emerald-400 rounded-xl">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <h3 className="font-bold text-sm tracking-wide">
            {t.zeroCostGuaranteeTitle}
          </h3>
        </div>

        <p className="text-xs text-slate-300 leading-relaxed max-w-2xl">
          {t.zeroCostGuaranteeDesc}
        </p>

        <div className="flex flex-wrap items-center gap-4 pt-2 text-[11px] text-slate-400 font-mono">
          <div className="flex items-center gap-1.5">
            <Database className="w-3.5 h-3.5 text-indigo-400" />
            <span>Local SQLite (aiosqlite)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <Cpu className="w-3.5 h-3.5 text-purple-400" />
            <span>Google Gemini 3.8 Flash ($0.00 Free Tier)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <Layers className="w-3.5 h-3.5 text-emerald-400" />
            <span>Rate-Limit Safeguards (10 RPM)</span>
          </div>
        </div>
      </div>
    </div>
  );
};
