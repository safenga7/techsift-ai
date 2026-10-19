/**
 * TechSift AI - Custom HTML5 Audio Player Component.
 * Supports streaming (HTTP 206 Range), scrubbing, playback speed, volume/mute,
 * and MP3 download. Works seamlessly in Dark/Light themes and RTL/LTR.
 */

import React, { useState, useRef } from 'react';
import {
  Play,
  Pause,
  Volume2,
  VolumeX,
  Download,
  RotateCcw,
  Headphones,
  Mic,
  Zap,
} from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';
import { api } from '../../services/api';
import type { AudioTrack } from '../../types/api';

interface AudioPlayerProps {
  track: AudioTrack;
  onEnded?: () => void;
}

function formatTime(seconds: number): string {
  if (isNaN(seconds) || seconds < 0) return '0:00';
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
}

export const AudioPlayer: React.FC<AudioPlayerProps> = ({ track, onEnded }) => {
  const { t } = useLanguage();
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(track.duration_seconds || 0);
  const [playbackRate, setPlaybackRate] = useState(1);
  const [volume, setVolume] = useState(1);
  const [isMuted, setIsMuted] = useState(false);
  const [isSeeking, setIsSeeking] = useState(false);

  const streamUrl = api.getAudioStreamUrl(track.id);
  const downloadUrl = api.getAudioDownloadUrl(track.id);

  const togglePlay = () => {
    if (!audioRef.current) return;
    if (isPlaying) {
      audioRef.current.pause();
      setIsPlaying(false);
    } else {
      audioRef.current
        .play()
        .then(() => setIsPlaying(true))
        .catch((err) => console.error('Audio playback failed:', err));
    }
  };

  const handleTimeUpdate = () => {
    if (!audioRef.current || isSeeking) return;
    setCurrentTime(audioRef.current.currentTime);
  };

  const handleLoadedMetadata = () => {
    if (!audioRef.current) return;
    if (audioRef.current.duration && !isNaN(audioRef.current.duration)) {
      setDuration(audioRef.current.duration);
    }
  };

  const handleSeekChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = parseFloat(e.target.value);
    setCurrentTime(val);
  };

  const handleSeekEnd = () => {
    if (!audioRef.current) return;
    audioRef.current.currentTime = currentTime;
    setIsSeeking(false);
  };

  const handleSpeedChange = (rate: number) => {
    setPlaybackRate(rate);
    if (audioRef.current) {
      audioRef.current.playbackRate = rate;
    }
  };

  const toggleMute = () => {
    if (!audioRef.current) return;
    const newMuted = !isMuted;
    setIsMuted(newMuted);
    audioRef.current.muted = newMuted;
  };

  const handleVolumeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = parseFloat(e.target.value);
    setVolume(val);
    if (audioRef.current) {
      audioRef.current.volume = val;
      if (val === 0) {
        setIsMuted(true);
        audioRef.current.muted = true;
      } else if (isMuted) {
        setIsMuted(false);
        audioRef.current.muted = false;
      }
    }
  };

  const restartAudio = () => {
    if (!audioRef.current) return;
    audioRef.current.currentTime = 0;
    setCurrentTime(0);
  };

  const progressPercent = duration > 0 ? (currentTime / duration) * 100 : 0;

  return (
    <div className="bg-gradient-to-br from-slate-900 to-indigo-950 text-white rounded-2xl p-5 shadow-lg border border-indigo-900/40 space-y-4">
      {/* Hidden Native Audio Element */}
      <audio
        ref={audioRef}
        src={streamUrl}
        preload="metadata"
        onTimeUpdate={handleTimeUpdate}
        onLoadedMetadata={handleLoadedMetadata}
        onEnded={() => {
          setIsPlaying(false);
          if (onEnded) onEnded();
        }}
      />

      {/* Header Info: Mode, Language & Badges */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-white/10 pb-3">
        <div className="flex items-center gap-2">
          <div className="p-2 rounded-xl bg-indigo-600/30 text-indigo-400 border border-indigo-500/30">
            {track.mode === 'podcast' ? (
              <Headphones className="w-5 h-5 text-indigo-300" />
            ) : (
              <Mic className="w-5 h-5 text-indigo-300" />
            )}
          </div>
          <div>
            <h4 className="text-sm font-bold text-white flex items-center gap-2">
              <span>
                {track.mode === 'podcast'
                  ? t.audioModePodcast
                  : t.audioModeNarration}
              </span>
              <span className="uppercase text-[10px] font-bold px-1.5 py-0.5 rounded-sm bg-white/10 text-indigo-200">
                {track.language}
              </span>
            </h4>
            <p className="text-[11px] text-slate-300">
              {track.mode === 'podcast'
                ? `${t.voiceHost}: ${track.voice_config.host_voice || 'Default'} • ${t.voiceCohost}: ${track.voice_config.cohost_voice || 'Default'}`
                : `${track.voice_config.voice || 'Default'}`}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {track.is_cached && (
            <span
              className="flex items-center gap-1 text-[11px] font-semibold text-cyan-300 bg-cyan-950/80 px-2.5 py-0.5 rounded-full border border-cyan-800"
              title={t.statusCached}
            >
              <Zap className="w-3 h-3 text-cyan-400" />
              <span>Cached ($0)</span>
            </span>
          )}

          <a
            href={downloadUrl}
            download
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white/10 hover:bg-white/20 text-xs font-semibold text-white transition-colors border border-white/10"
            title={t.audioDownloadMp3}
          >
            <Download className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">{t.audioDownloadMp3}</span>
          </a>
        </div>
      </div>

      {/* Scrubber Bar */}
      <div className="space-y-1.5">
        <div className="relative w-full flex items-center">
          <input
            type="range"
            min={0}
            max={duration || 100}
            step={0.1}
            value={currentTime}
            onMouseDown={() => setIsSeeking(true)}
            onTouchStart={() => setIsSeeking(true)}
            onChange={handleSeekChange}
            onMouseUp={handleSeekEnd}
            onTouchEnd={handleSeekEnd}
            className="w-full h-2 bg-white/20 rounded-lg appearance-none cursor-pointer accent-indigo-400 focus:outline-none"
            style={{
              background: `linear-gradient(to right, #818cf8 0%, #818cf8 ${progressPercent}%, rgba(255,255,255,0.2) ${progressPercent}%, rgba(255,255,255,0.2) 100%)`,
            }}
          />
        </div>

        <div className="flex justify-between text-[11px] font-mono text-slate-400">
          <span>{formatTime(currentTime)}</span>
          <span>{formatTime(duration)}</span>
        </div>
      </div>

      {/* Controls Bar: Play/Pause, Rewind, Speed, Volume */}
      <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
        {/* Play / Rewind */}
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={restartAudio}
            className="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-white/10 transition-colors"
            title="Restart"
          >
            <RotateCcw className="w-4 h-4" />
          </button>

          <button
            type="button"
            onClick={togglePlay}
            className="p-3.5 rounded-2xl bg-indigo-600 hover:bg-indigo-500 text-white shadow-md shadow-indigo-600/30 transition-all flex items-center justify-center"
            title={isPlaying ? 'Pause' : 'Play'}
          >
            {isPlaying ? (
              <Pause className="w-5 h-5 fill-current" />
            ) : (
              <Play className="w-5 h-5 fill-current ms-0.5" />
            )}
          </button>
        </div>

        {/* Speed Controls */}
        <div className="flex items-center gap-1 bg-white/10 p-1 rounded-xl">
          {[0.75, 1, 1.25, 1.5, 2].map((rate) => (
            <button
              key={rate}
              type="button"
              onClick={() => handleSpeedChange(rate)}
              className={`px-2 py-0.5 rounded-lg text-xs font-semibold transition-colors ${
                playbackRate === rate
                  ? 'bg-indigo-600 text-white shadow-xs'
                  : 'text-slate-300 hover:text-white hover:bg-white/10'
              }`}
            >
              {rate}x
            </button>
          ))}
        </div>

        {/* Volume & Mute */}
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={toggleMute}
            className="p-2 rounded-xl text-slate-300 hover:text-white hover:bg-white/10 transition-colors"
            title={isMuted ? 'Unmute' : 'Mute'}
          >
            {isMuted || volume === 0 ? (
              <VolumeX className="w-4 h-4 text-rose-400" />
            ) : (
              <Volume2 className="w-4 h-4" />
            )}
          </button>
          <input
            type="range"
            min={0}
            max={1}
            step={0.05}
            value={isMuted ? 0 : volume}
            onChange={handleVolumeChange}
            className="w-16 h-1.5 bg-white/20 rounded-lg appearance-none cursor-pointer accent-indigo-400"
          />
        </div>
      </div>
    </div>
  );
};
