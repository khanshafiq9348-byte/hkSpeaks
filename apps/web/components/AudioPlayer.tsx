"use client";

import React, { useRef, useState, useEffect } from "react";
import { Play, Pause, Download, Volume2, VolumeX, RotateCcw, Loader2 } from "lucide-react";

interface AudioPlayerProps {
  src: string | null;
  title?: string;
  voiceName?: string;
  duration?: number;
  format?: string;
  autoPlay?: boolean;
}

export default function AudioPlayer({
  src,
  title = "Generated Audio",
  voiceName,
  duration = 0,
  format = "mp3",
  autoPlay = false,
}: AudioPlayerProps) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [totalDuration, setTotalDuration] = useState(duration);
  const [playbackRate, setPlaybackRate] = useState(1.0);
  const [isDownloading, setIsDownloading] = useState(false);
  const [isMuted, setIsMuted] = useState(false);

  useEffect(() => {
    if (duration && duration > 0) {
      setTotalDuration(duration);
    }
  }, [duration]);

  useEffect(() => {
    setIsPlaying(false);
    setCurrentTime(0);
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
      audioRef.current.load();
      if (autoPlay && src) {
        audioRef.current.play().then(() => setIsPlaying(true)).catch(() => {});
      }
    }
  }, [src]);

  const togglePlay = async () => {
    if (!audioRef.current || !src) return;
    if (isPlaying) {
      audioRef.current.pause();
      setIsPlaying(false);
    } else {
      try {
        await audioRef.current.play();
        setIsPlaying(true);
      } catch (err) {
        console.error("Audio playback error:", err);
        setIsPlaying(false);
      }
    }
  };

  const handleTimeUpdate = () => {
    if (audioRef.current) {
      setCurrentTime(audioRef.current.currentTime);
      if (audioRef.current.duration && !isNaN(audioRef.current.duration) && audioRef.current.duration > 0) {
        setTotalDuration(audioRef.current.duration);
      }
    }
  };

  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const target = parseFloat(e.target.value);
    if (audioRef.current) {
      audioRef.current.currentTime = target;
      setCurrentTime(target);
    }
  };

  const cyclePlaybackRate = () => {
    const speeds = [1.0, 1.25, 1.5, 0.8];
    const nextIdx = (speeds.indexOf(playbackRate) + 1) % speeds.length;
    const nextRate = speeds[nextIdx];
    setPlaybackRate(nextRate);
    if (audioRef.current) {
      audioRef.current.playbackRate = nextRate;
    }
  };

  const toggleMute = () => {
    if (audioRef.current) {
      audioRef.current.muted = !isMuted;
      setIsMuted(!isMuted);
    }
  };

  const handleDownload = async () => {
    if (!src) return;
    setIsDownloading(true);
    try {
      const res = await fetch(src);
      const blob = await res.blob();
      const blobUrl = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = blobUrl;
      a.download = `audio_${Date.now()}.${format.toLowerCase()}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(blobUrl);
    } catch (err) {
      // Fallback
      window.open(src, "_blank");
    } finally {
      setIsDownloading(false);
    }
  };

  const formatTime = (secs: number) => {
    if (!secs || isNaN(secs) || secs < 0) return "0:00";
    const m = Math.floor(secs / 60);
    const s = Math.floor(secs % 60);
    return `${m}:${s < 10 ? "0" : ""}${s}`;
  };

  if (!src) {
    return (
      <div className="p-6 rounded-2xl bg-[#12141F] border border-[#202436] flex flex-col items-center justify-center text-center space-y-2 text-gray-500">
        <Volume2 className="w-8 h-8 opacity-40 text-gray-400" />
        <p className="text-sm">No audio generated yet. Enter script and click Generate.</p>
      </div>
    );
  }

  return (
    <div className="p-6 rounded-2xl bg-[#12141F] border border-indigo-500/30 shadow-xl shadow-indigo-950/20 space-y-4">
      <audio
        ref={audioRef}
        src={src}
        preload="auto"
        onTimeUpdate={handleTimeUpdate}
        onEnded={() => setIsPlaying(false)}
        onError={(e) => console.warn("Audio tag error:", e)}
      />

      <div className="flex items-center justify-between">
        <div>
          <h4 className="text-sm font-semibold text-gray-100">{title}</h4>
          {voiceName && (
            <p className="text-xs text-indigo-400 flex items-center space-x-1 mt-0.5">
              <span>Voice: {voiceName}</span>
            </p>
          )}
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={toggleMute}
            className="p-1.5 rounded-lg bg-[#1C2033] hover:bg-[#252A42] text-gray-400 hover:text-white transition-colors"
            title={isMuted ? "Unmute" : "Mute"}
          >
            {isMuted ? <VolumeX className="w-3.5 h-3.5 text-red-400" /> : <Volume2 className="w-3.5 h-3.5" />}
          </button>
          <button
            onClick={cyclePlaybackRate}
            className="px-2.5 py-1 text-xs font-medium rounded-lg bg-[#1C2033] hover:bg-[#252A42] text-gray-300 border border-[#2A304C] transition-colors"
          >
            {playbackRate}x
          </button>
          <button
            onClick={handleDownload}
            disabled={isDownloading}
            className="flex items-center space-x-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white shadow-md shadow-indigo-600/30 transition-colors"
          >
            {isDownloading ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Download className="w-3.5 h-3.5" />
            )}
            <span>Download .{format.toUpperCase()}</span>
          </button>
        </div>
      </div>

      {/* Decorative Waveform Bars */}
      <div className="flex items-center justify-between space-x-1 h-12 px-2 py-1 bg-[#0B0C14] rounded-xl border border-[#1A1D2D] overflow-hidden">
        {Array.from({ length: 42 }).map((_, i) => {
          const progress = currentTime / (totalDuration || 1);
          const isPassed = i / 42 <= progress;
          const baseHeight = 15 + Math.sin(i * 0.5) * 12 + ((i * 7) % 15);
          const animHeight = isPlaying ? Math.max(10, (baseHeight * (0.6 + Math.sin(Date.now() / 200 + i) * 0.4))) : baseHeight;
          return (
            <div
              key={i}
              className={`flex-1 rounded-full transition-all duration-150 ${
                isPassed ? "bg-indigo-500 shadow-sm shadow-indigo-500/50" : "bg-[#23273D]"
              }`}
              style={{ height: `${animHeight}%` }}
            />
          );
        })}
      </div>

      {/* Controls & Scrubber */}
      <div className="space-y-1.5">
        <input
          type="range"
          min="0"
          max={totalDuration || 1}
          step="0.01"
          value={currentTime}
          onChange={handleSeek}
          className="w-full h-1.5 bg-[#202438] rounded-lg appearance-none cursor-pointer accent-indigo-500"
        />
        <div className="flex items-center justify-between text-xs text-gray-400 font-mono">
          <span>{formatTime(currentTime)}</span>
          <div className="flex items-center space-x-3">
            <button
              onClick={() => {
                if (audioRef.current) {
                  audioRef.current.currentTime = 0;
                  setCurrentTime(0);
                }
              }}
              className="p-1 hover:text-white transition-colors"
            >
              <RotateCcw className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={togglePlay}
              className="p-2 rounded-full bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-600/30 transition-transform active:scale-95"
            >
              {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4 ml-0.5 fill-current" />}
            </button>
          </div>
          <span>{formatTime(totalDuration)}</span>
        </div>
      </div>
    </div>
  );
}
