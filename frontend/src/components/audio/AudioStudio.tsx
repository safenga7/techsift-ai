/**
 * TechSift AI - Audio & Podcast Studio Component.
 * Bilingual technical audio studio providing single-speaker narration
 * and dual-speaker educational podcasts with 450ms pauses, grounded in document context.
 */

import React, { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Headphones,
  Mic,
  Sparkles,
  Clock,
  AlertCircle,
  Play,
  User,
  Zap,
  Globe,
  Sliders,
  Bookmark,
  Volume2,
} from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';
import { api, ApiClientError } from '../../services/api';
import type {
  AudioMode,
  AudioTrack,
  LanguageCode,
  AudioVoiceGender,
  PodcastTurn,
  SummaryItem,
} from '../../types/api';
import { AudioPlayer } from './AudioPlayer';

interface AudioStudioProps {
  documentId: string;
  documentTitle: string;
  summaries: SummaryItem[];
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
}

function formatDuration(seconds: number): string {
  if (isNaN(seconds) || seconds < 0) return '0s';
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  if (mins === 0) return `${secs}s`;
  return `${mins}m ${secs}s`;
}

export const AudioStudio: React.FC<AudioStudioProps> = ({
  documentId,
  documentTitle,
  summaries,
}) => {
  const { t } = useLanguage();
  const queryClient = useQueryClient();

  // Studio Creation State
  const [searchParams] = useSearchParams();
  const paramTrack = searchParams.get('trackId') || searchParams.get('mode');
  const [mode, setMode] = useState<AudioMode>('podcast');
  const [language, setLanguage] = useState<LanguageCode>('ar');
  const [gender, setGender] = useState<AudioVoiceGender>('male');
  const [selectedTrackId, setSelectedTrackId] = useState<string | null>(null);

  // Fetch audio tracks for this document with auto-polling for in-flight tasks
  const { data: audioData } = useQuery({
    queryKey: ['document-audio', documentId],
    queryFn: () => api.getDocumentAudio(documentId),
    enabled: Boolean(documentId),
    refetchInterval: (query) => {
      const items = query.state.data?.items || [];
      const hasInFlight = items.some(
        (t: AudioTrack) => t.status === 'pending' || t.status === 'processing'
      );
      return hasInFlight ? 2000 : false;
    },
  });

  const tracks: AudioTrack[] = audioData?.items || [];

  // Determine active track for viewer
  const activeTrack: AudioTrack | null = selectedTrackId
    ? tracks.find((tr) => tr.id === selectedTrackId) || null
    : paramTrack
    ? tracks.find((tr) => tr.id === paramTrack || tr.mode === paramTrack) || tracks[0] || null
    : tracks[0] || null;

  // Determine if any track is currently being synthesized in the background
  const isAudioProcessing = tracks.some(
    (t: AudioTrack) => t.status === 'pending' || t.status === 'processing'
  );

  // Find summary matching chosen target language
  const matchingSummary = summaries.find(
    (s) => s.status === 'completed' && s.language === language
  ) || (summaries.length > 0 && summaries[0].language === language ? summaries[0] : undefined);

  // Generate Audio Mutation (Asynchronous: returns HTTP 202 immediately, then auto-polls)
  const generateMutation = useMutation({
    mutationFn: () =>
      api.createAudio(
        documentId,
        {
          mode,
          language,
          gender: mode === 'narration' ? gender : undefined,
          summary_id: matchingSummary?.id,
          wait: false,
        },
        false
      ),
    onSuccess: (newTrack: AudioTrack) => {
      // Optimistically insert or update the track in query cache so the UI
      // immediately displays the in-progress synthesis card and begins auto-polling
      queryClient.setQueryData(
        ['document-audio', documentId],
        (old: { items: AudioTrack[]; total: number } | undefined) => {
          if (!old) return { items: [newTrack], total: 1 };
          const exists = old.items.some((t) => t.id === newTrack.id);
          if (exists) {
            return {
              ...old,
              items: old.items.map((t) => (t.id === newTrack.id ? newTrack : t)),
            };
          }
          return {
            items: [newTrack, ...old.items],
            total: old.total + 1,
          };
        }
      );
      queryClient.invalidateQueries({ queryKey: ['document-audio', documentId] });
      setSelectedTrackId(newTrack.id);
    },
  });

  return (
    <div className="space-y-8 animate-in fade-in duration-200">
      {/* Studio Banner & Mode Overview */}
      <div className="bg-gradient-to-r from-indigo-900/40 via-purple-900/30 to-slate-900/40 border border-indigo-500/20 rounded-2xl p-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="p-2 rounded-xl bg-indigo-600/30 text-indigo-400 border border-indigo-500/30">
                <Volume2 className="w-5 h-5 text-indigo-300" />
              </span>
              <h2 className="text-lg font-bold text-slate-900 dark:text-white">
                {t.tabAudio} • <span className="font-normal text-slate-300">{documentTitle}</span>
              </h2>
              <span className="text-[10px] font-bold text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/60 px-2 py-0.5 rounded-full border border-emerald-200 dark:border-emerald-800">
                100% Free ($0)
              </span>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400 max-w-xl">
              {mode === 'podcast' ? t.audioModePodcastDesc : t.audioModeNarrationDesc}
              {summaries.length > 0 && (
                <span className="block mt-1 text-[11px] text-indigo-300">
                  Grounded on {summaries.length} available technical analysis summaries
                </span>
              )}
            </p>
          </div>

          <div className="text-[11px] font-mono text-slate-400 bg-black/20 px-3 py-1.5 rounded-xl border border-white/5">
            Engine: Edge-TTS + Piper (Zero-Cost Offline)
          </div>
        </div>
      </div>

      {/* Main Studio Grid: Generation Configuration (Left) & Active Player / Transcript (Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Configuration Controls (4 Cols) */}
        <div className="lg:col-span-4 space-y-6">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-xs space-y-5">
            <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3">
              <div className="flex items-center gap-2 text-slate-900 dark:text-white font-bold text-sm">
                <Sliders className="w-4 h-4 text-indigo-500" />
                <span>{t.controlsTitle}</span>
              </div>
            </div>

            {/* 1. Audio Mode Selection */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-2">
                {t.audioModeLabel}
              </label>
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => setMode('podcast')}
                  className={`p-3 rounded-xl border text-xs font-semibold flex flex-col items-center justify-center gap-1.5 text-center transition-all ${
                    mode === 'podcast'
                      ? 'border-indigo-600 bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 shadow-xs ring-1 ring-indigo-500/20'
                      : 'border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800/60'
                  }`}
                >
                  <Headphones className="w-4 h-4" />
                  <span>{t.audioModePodcast}</span>
                  <span className="text-[10px] text-slate-400 font-normal">
                    2 Speakers • 450ms Pauses
                  </span>
                </button>

                <button
                  type="button"
                  onClick={() => setMode('narration')}
                  className={`p-3 rounded-xl border text-xs font-semibold flex flex-col items-center justify-center gap-1.5 text-center transition-all ${
                    mode === 'narration'
                      ? 'border-indigo-600 bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 shadow-xs ring-1 ring-indigo-500/20'
                      : 'border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800/60'
                  }`}
                >
                  <Mic className="w-4 h-4" />
                  <span>{t.audioModeNarration}</span>
                  <span className="text-[10px] text-slate-400 font-normal">
                    Single Speaker Summary
                  </span>
                </button>
              </div>
            </div>

            {/* 2. Target Audio Language */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-2">
                {t.outputLanguageLabel}
              </label>
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => setLanguage('ar')}
                  className={`px-3 py-2.5 rounded-xl border text-xs font-semibold flex items-center justify-center gap-1.5 transition-all ${
                    language === 'ar'
                      ? 'border-indigo-600 bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 shadow-xs'
                      : 'border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800/60'
                  }`}
                >
                  <Globe className="w-3.5 h-3.5" />
                  <span>العربية (Arabic)</span>
                </button>

                <button
                  type="button"
                  onClick={() => setLanguage('en')}
                  className={`px-3 py-2.5 rounded-xl border text-xs font-semibold flex items-center justify-center gap-1.5 transition-all ${
                    language === 'en'
                      ? 'border-indigo-600 bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 shadow-xs'
                      : 'border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800/60'
                  }`}
                >
                  <Globe className="w-3.5 h-3.5" />
                  <span>English</span>
                </button>
              </div>
            </div>

            {/* 3. Speaker Configuration */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-2">
                {t.audioVoiceLabel}
              </label>

              {mode === 'narration' ? (
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => setGender('male')}
                    className={`px-3 py-2.5 rounded-xl border text-xs font-semibold flex items-center justify-center gap-1.5 transition-all ${
                      gender === 'male'
                        ? 'border-indigo-600 bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 shadow-xs'
                        : 'border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800/60'
                    }`}
                  >
                    <User className="w-3.5 h-3.5" />
                    <span>{t.voiceMale} ({language === 'ar' ? 'شاكر' : 'Guy'})</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setGender('female')}
                    className={`px-3 py-2.5 rounded-xl border text-xs font-semibold flex items-center justify-center gap-1.5 transition-all ${
                      gender === 'female'
                        ? 'border-indigo-600 bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 shadow-xs'
                        : 'border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800/60'
                    }`}
                  >
                    <User className="w-3.5 h-3.5" />
                    <span>{t.voiceFemale} ({language === 'ar' ? 'سلمى' : 'Jenny'})</span>
                  </button>
                </div>
              ) : (
                <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700 space-y-2 text-xs">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-slate-700 dark:text-slate-300 flex items-center gap-1.5">
                      <span className="w-2 h-2 rounded-full bg-blue-500"></span>
                      {t.voiceHost}
                    </span>
                    <span className="font-mono text-[11px] text-slate-500">
                      {language === 'ar' ? 'شاكر (ar-EG-ShakirNeural)' : 'Guy (en-US-GuyNeural)'}
                    </span>
                  </div>

                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-slate-700 dark:text-slate-300 flex items-center gap-1.5">
                      <span className="w-2 h-2 rounded-full bg-purple-500"></span>
                      {t.voiceCohost}
                    </span>
                    <span className="font-mono text-[11px] text-slate-500">
                      {language === 'ar' ? 'سلمى (ar-EG-SalmaNeural)' : 'Jenny (en-US-JennyNeural)'}
                    </span>
                  </div>

                  <div className="text-[10px] text-slate-400 pt-1 border-t border-slate-200 dark:border-slate-700">
                    {t.conversationalPauseNotice}
                  </div>
                </div>
              )}
            </div>

            {/* 4. Action Button */}
            <button
              type="button"
              onClick={() => generateMutation.mutate()}
              disabled={generateMutation.isPending || isAudioProcessing}
              className="w-full py-3.5 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-xs font-bold shadow-md shadow-indigo-500/20 transition-all flex items-center justify-center gap-2"
            >
              {generateMutation.isPending || isAudioProcessing ? (
                <>
                  <Clock className="w-4 h-4 animate-spin" />
                  <span>{t.generatingAudio}</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  <span>{t.generateAudioBtn}</span>
                </>
              )}
            </button>

            {/* Error Message */}
            {generateMutation.isError && (
              <div className="p-3 bg-rose-50 dark:bg-rose-950/60 border border-rose-200 dark:border-rose-900/60 rounded-xl text-xs text-rose-700 dark:text-rose-300">
                <div className="flex items-center gap-1.5 font-bold mb-1">
                  <AlertCircle className="w-4 h-4 text-rose-500" />
                  <span>{t.statusFailed}</span>
                </div>
                <span>
                  {(generateMutation.error as ApiClientError)?.message ||
                    'Audio generation failed. Please try again.'}
                </span>
              </div>
            )}
          </div>

          {/* Previous Audio Episodes Card */}
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-xs space-y-3">
            <div className="flex items-center justify-between text-slate-900 dark:text-white font-bold text-xs">
              <div className="flex items-center gap-2">
                <Headphones className="w-4 h-4 text-slate-500" />
                <span>{t.audioHistoryTitle}</span>
              </div>
              <span className="text-[11px] text-slate-400">{tracks.length}</span>
            </div>

            {tracks.length === 0 ? (
              <p className="text-xs text-slate-400 py-2">
                {t.noAudioYet}
              </p>
            ) : (
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {tracks.map((tr) => {
                  const isCompleted = tr.status === 'completed';
                  const isProcessing = tr.status === 'processing' || tr.status === 'pending';
                  const isFailed = tr.status === 'failed';

                  return (
                    <button
                      key={tr.id}
                      type="button"
                      onClick={() => setSelectedTrackId(tr.id)}
                      className={`w-full text-left rtl:text-right p-3 rounded-xl border text-xs transition-colors flex items-center justify-between ${
                        activeTrack?.id === tr.id
                          ? isFailed
                            ? 'border-rose-500 bg-rose-50/70 dark:bg-rose-950/40 text-rose-900 dark:text-rose-200 ring-1 ring-rose-500/20'
                            : isProcessing
                            ? 'border-amber-500 bg-amber-50/70 dark:bg-amber-950/40 text-amber-900 dark:text-amber-200 ring-1 ring-amber-500/20'
                            : 'border-indigo-500 bg-indigo-50/70 dark:bg-indigo-950/40 font-semibold text-indigo-900 dark:text-indigo-200 ring-1 ring-indigo-500/20'
                          : 'border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800/40'
                      }`}
                    >
                      <div className="space-y-1">
                        <div className="flex items-center gap-1.5">
                          <span className="uppercase text-[9px] font-bold px-1.5 py-0.5 rounded-sm bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
                            {tr.mode}
                          </span>
                          <span className="uppercase text-[9px] font-bold px-1.5 py-0.5 rounded-sm bg-indigo-100 dark:bg-indigo-950 text-indigo-700 dark:text-indigo-300">
                            {tr.language}
                          </span>
                          {isCompleted ? (
                            <span className="text-[11px] font-mono text-slate-400">
                              {formatDuration(tr.duration_seconds)}
                            </span>
                          ) : isProcessing ? (
                            <span className="text-[10px] font-semibold text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/60 px-1.5 py-0.5 rounded-sm">
                              {t.statusProcessing}
                            </span>
                          ) : (
                            <span className="text-[10px] font-semibold text-rose-600 dark:text-rose-400 bg-rose-50 dark:bg-rose-950/60 px-1.5 py-0.5 rounded-sm">
                              {t.statusFailed}
                            </span>
                          )}
                        </div>

                        <span className="text-[10px] text-slate-400 block">
                          {new Date(tr.created_at).toLocaleTimeString([], {
                            hour: '2-digit',
                            minute: '2-digit',
                          })}
                          {isCompleted && ` • ${formatBytes(tr.file_size_bytes)}`}
                        </span>
                      </div>

                      <div className="flex items-center gap-2">
                        {tr.is_cached && (
                          <span title={t.statusCached}>
                            <Zap className="w-3.5 h-3.5 text-cyan-500" />
                          </span>
                        )}
                        {isCompleted && <Play className="w-3.5 h-3.5 text-indigo-500 fill-indigo-500/20" />}
                        {isProcessing && <Clock className="w-3.5 h-3.5 text-amber-500 animate-spin" />}
                        {isFailed && <AlertCircle className="w-3.5 h-3.5 text-rose-500" />}
                      </div>
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* Player & Dialogue Transcript Viewer (8 Cols) */}
        <div className="lg:col-span-8 space-y-6">
          {!activeTrack ? (
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-12 text-center space-y-4">
              <Headphones className="w-12 h-12 text-indigo-400 mx-auto" />
              <div>
                <h3 className="text-base font-bold text-slate-800 dark:text-slate-200">
                  {t.noAudioYet}
                </h3>
                <p className="text-xs text-slate-400 max-w-sm mx-auto mt-1">
                  {t.noAudioYetDesc}
                </p>
              </div>
              <button
                type="button"
                onClick={() => generateMutation.mutate()}
                disabled={generateMutation.isPending}
                className="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold shadow-md shadow-indigo-500/20 inline-flex items-center gap-2"
              >
                <Sparkles className="w-4 h-4" />
                <span>{t.generateAudioBtn}</span>
              </button>
            </div>
          ) : activeTrack.status === 'failed' ? (
            /* FAILED STATUS CARD - NEVER RENDER AUDIO PLAYER FOR FAILED TRACKS */
            <div className="bg-white dark:bg-slate-900 border border-rose-200 dark:border-rose-900/60 rounded-2xl p-8 shadow-xs space-y-4">
              <div className="flex items-start gap-4">
                <div className="p-3 rounded-2xl bg-rose-50 dark:bg-rose-950/60 border border-rose-200 dark:border-rose-800 text-rose-600 dark:text-rose-400 shrink-0">
                  <AlertCircle className="w-8 h-8" />
                </div>
                <div className="space-y-1 flex-1">
                  <div className="flex items-center justify-between">
                    <h3 className="text-base font-bold text-slate-900 dark:text-white">
                      {t.audioFailedCardTitle}
                    </h3>
                    <span className="uppercase text-[10px] font-bold px-2 py-0.5 rounded-full bg-rose-100 dark:bg-rose-950 text-rose-700 dark:text-rose-300 border border-rose-300 dark:border-rose-800">
                      {t.statusFailed}
                    </span>
                  </div>
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    {t.audioFailedCardDesc}
                  </p>
                </div>
              </div>

              {activeTrack.error_message && (
                <div className="p-4 bg-slate-50 dark:bg-slate-950 rounded-xl border border-slate-200 dark:border-slate-800 text-xs font-mono text-rose-600 dark:text-rose-400 leading-relaxed overflow-x-auto whitespace-pre-wrap">
                  {activeTrack.error_message}
                </div>
              )}

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => generateMutation.mutate()}
                  disabled={generateMutation.isPending || isAudioProcessing}
                  className="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-xs font-bold shadow-md shadow-indigo-500/20 inline-flex items-center gap-2 transition-all"
                >
                  {generateMutation.isPending || isAudioProcessing ? (
                    <>
                      <Clock className="w-4 h-4 animate-spin" />
                      <span>{t.generatingAudio}</span>
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-4 h-4" />
                      <span>{t.generateAudioBtn}</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          ) : activeTrack.status === 'processing' || activeTrack.status === 'pending' ? (
            /* IN-PROGRESS SYNTHESIS CARD */
            <div className="bg-white dark:bg-slate-900 border border-indigo-200 dark:border-indigo-900/60 rounded-2xl p-8 shadow-xs text-center space-y-4">
              <div className="p-4 rounded-full bg-indigo-50 dark:bg-indigo-950/60 border border-indigo-200 dark:border-indigo-800 w-16 h-16 mx-auto flex items-center justify-center text-indigo-600 dark:text-indigo-400">
                <Clock className="w-8 h-8 animate-spin" />
              </div>
              <div className="space-y-1">
                <h3 className="text-base font-bold text-slate-900 dark:text-white">
                  {t.audioGeneratingCardTitle}
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 max-w-md mx-auto">
                  {t.audioGeneratingCardDesc}
                </p>
              </div>
              <div className="w-48 h-1.5 bg-indigo-100 dark:bg-indigo-950 rounded-full mx-auto overflow-hidden">
                <div className="h-full bg-indigo-600 rounded-full animate-pulse"></div>
              </div>
            </div>
          ) : (
            <div className="space-y-6">
              {/* Custom HTML5 Audio Player */}
              <AudioPlayer key={activeTrack.id} track={activeTrack} />

              {/* Dialogue Transcript & Script Card */}
              <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-xs space-y-5">
                <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 dark:border-slate-800 pb-3">
                  <div className="flex items-center gap-2">
                    <Bookmark className="w-4 h-4 text-indigo-500" />
                    <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                      {t.audioTranscriptTitle}
                    </h3>
                  </div>

                  {activeTrack.script_content?.title && (
                    <span className="text-xs font-semibold text-indigo-600 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-950/60 px-3 py-1 rounded-full border border-indigo-200 dark:border-indigo-800">
                      {activeTrack.script_content.title}
                    </span>
                  )}
                </div>

                {/* Podcast Turns */}
                {activeTrack.mode === 'podcast' && (activeTrack.script_content?.turns || activeTrack.script_content?.dialogue) ? (
                  <div className="space-y-3">
                    {(activeTrack.script_content.turns || activeTrack.script_content.dialogue).map((turn: PodcastTurn) => {
                      const isHost =
                        turn.speaker.toLowerCase().includes('host') ||
                        turn.speaker.includes('المقدم');

                      return (
                        <div
                          key={turn.turn}
                          className={`p-4 rounded-2xl border transition-all ${
                            isHost
                              ? 'bg-blue-50/40 dark:bg-blue-950/20 border-blue-200/60 dark:border-blue-900/40'
                              : 'bg-purple-50/40 dark:bg-purple-950/20 border-purple-200/60 dark:border-purple-900/40'
                          }`}
                        >
                          <div className="flex items-center justify-between gap-2 mb-2">
                            <div className="flex items-center gap-2">
                              <span
                                className={`text-[11px] font-bold px-2 py-0.5 rounded-full ${
                                  isHost
                                    ? 'bg-blue-100 dark:bg-blue-900/60 text-blue-800 dark:text-blue-300'
                                    : 'bg-purple-100 dark:bg-purple-900/60 text-purple-800 dark:text-purple-300'
                                }`}
                              >
                                {turn.speaker}
                              </span>
                              <span className="text-[10px] font-mono text-slate-400">
                                Turn #{turn.turn}
                              </span>
                            </div>

                            <span className="text-[10px] font-mono text-slate-400">
                              {turn.voice}
                            </span>
                          </div>

                          <p
                            className="text-xs sm:text-sm text-slate-800 dark:text-slate-200 leading-relaxed"
                            dir={activeTrack.language === 'ar' ? 'rtl' : 'ltr'}
                          >
                            {turn.text}
                          </p>
                        </div>
                      );
                    })}

                    {/* Source References Pill List */}
                    {activeTrack.script_content.source_references &&
                      activeTrack.script_content.source_references.length > 0 && (
                        <div className="pt-3 border-t border-slate-100 dark:border-slate-800">
                          <span className="text-[11px] font-semibold text-slate-500 block mb-1.5">
                            {t.sectionSources}:
                          </span>
                          <div className="flex flex-wrap gap-1.5">
                            {activeTrack.script_content.source_references.map(
                              (ref: string, idx: number) => (
                                <span
                                  key={idx}
                                  className="text-[10px] font-semibold bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 px-2 py-0.5 rounded-md border border-slate-200 dark:border-slate-700"
                                >
                                  {ref}
                                </span>
                              )
                            )}
                          </div>
                        </div>
                      )}
                  </div>
                ) : activeTrack.script_content?.text ? (
                  /* Single Speaker Narration Script */
                  <div className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-800">
                    <p
                      className="text-xs sm:text-sm text-slate-800 dark:text-slate-200 leading-relaxed whitespace-pre-line"
                      dir={activeTrack.language === 'ar' ? 'rtl' : 'ltr'}
                    >
                      {activeTrack.script_content.text}
                    </p>
                  </div>
                ) : (
                  <p className="text-xs text-slate-400">
                    Transcript content unavailable for this track.
                  </p>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
