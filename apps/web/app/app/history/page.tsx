"use client";

import React, { useState, useEffect } from "react";
import AudioPlayer from "@/components/AudioPlayer";
import { apiClient } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { 
  History, 
  Play, 
  Pause, 
  Download, 
  CheckCircle2, 
  Clock, 
  XCircle, 
  RotateCcw, 
  Trash2, 
  Sparkles,
  Loader2,
  FileAudio
} from "lucide-react";
import Link from "next/link";

interface Generation {
  id: string;
  voice_name?: string;
  input_characters: number;
  actual_audio_seconds: number;
  format: string;
  status: "queued" | "processing" | "completed" | "failed" | "cancelled" | string;
  audio_url?: string;
  created_at: string;
}

export default function HistoryPage() {
  const { user, loginAsDemo } = useAuth();
  const [generations, setGenerations] = useState<Generation[]>([]);
  const [activeGen, setActiveGen] = useState<Generation | null>(null);
  const [isPlayingId, setIsPlayingId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isLoggingIn, setIsLoggingIn] = useState(false);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);
  const [isClearing, setIsClearing] = useState(false);

  useEffect(() => {
    loadHistory();
  }, [user]);

  const loadHistory = async () => {
    setIsLoading(true);
    try {
      const data = await apiClient<{ items: Generation[] }>("/generations?page_size=50");
      const items = data.items || [];
      setGenerations(items);
      if (items.length > 0 && !activeGen) {
        const firstCompleted = items.find((g) => g.status === "completed" && g.audio_url);
        if (firstCompleted) {
          setActiveGen(firstCompleted);
        }
      }
    } catch {
      // ignore if unauthenticated
    } finally {
      setIsLoading(false);
    }
  };

  const handlePlayGeneration = (gen: Generation) => {
    if (!gen.audio_url) return;
    setActiveGen(gen);
    if (isPlayingId === gen.id) {
      setIsPlayingId(null);
    } else {
      setIsPlayingId(gen.id);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Are you sure you want to delete this generation record and its audio?")) return;
    try {
      await apiClient(`/generations/${id}`, { method: "DELETE" });
      if (activeGen?.id === id) {
        setActiveGen(null);
        setIsPlayingId(null);
      }
      setGenerations((prev) => prev.filter((g) => g.id !== id));
    } catch (err: any) {
      alert(err.message || "Failed to delete generation.");
    }
  };

  const handleClearAll = async () => {
    if (!confirm("Are you sure you want to delete ALL generation records and audio files?")) return;
    setIsClearing(true);
    try {
      await apiClient("/generations", { method: "DELETE" });
      setActiveGen(null);
      setIsPlayingId(null);
      setGenerations([]);
    } catch (err: any) {
      alert(err.message || "Failed to clear history.");
    } finally {
      setIsClearing(false);
    }
  };

  const handleDirectDownload = async (g: Generation) => {
    if (!g.audio_url) return;
    setDownloadingId(g.id);
    try {
      const res = await fetch(g.audio_url);
      const blob = await res.blob();
      const blobUrl = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = blobUrl;
      a.download = `speech_${g.id.slice(0, 8)}.${g.format.toLowerCase()}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(blobUrl);
    } catch {
      window.open(g.audio_url, "_blank");
    } finally {
      setDownloadingId(null);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "completed":
        return (
          <span className="flex items-center space-x-1 text-[11px] font-semibold text-emerald-400 bg-emerald-500/10 px-2.5 py-0.5 rounded-full border border-emerald-500/20">
            <CheckCircle2 className="w-3 h-3" />
            <span>Completed</span>
          </span>
        );
      case "processing":
      case "queued":
        return (
          <span className="flex items-center space-x-1 text-[11px] font-semibold text-indigo-400 bg-indigo-500/10 px-2.5 py-0.5 rounded-full border border-indigo-500/20">
            <Clock className="w-3 h-3" />
            <span className="capitalize">{status}</span>
          </span>
        );
      default:
        return (
          <span className="flex items-center space-x-1 text-[11px] font-semibold text-red-400 bg-red-500/10 px-2.5 py-0.5 rounded-full border border-red-500/20">
            <XCircle className="w-3 h-3" />
            <span className="capitalize">{status}</span>
          </span>
        );
    }
  };

  return (
    <div className="flex-1 flex flex-col min-w-0 h-full overflow-y-auto bg-[#090A0F] text-gray-100">
      <main className="max-w-7xl w-full mx-auto p-6 space-y-6 flex-1 flex flex-col">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-white tracking-tight flex items-center space-x-2.5">
              <History className="w-6 h-6 text-indigo-400" />
              <span>Generation History</span>
            </h1>
            <p className="text-xs text-gray-400 mt-1">
              Review, play, and download your past audio speech outputs
            </p>
          </div>

          <div className="flex items-center space-x-2">
            {!user && (
              <button
                onClick={async () => {
                  setIsLoggingIn(true);
                  try {
                    await loginAsDemo("creator");
                  } finally {
                    setIsLoggingIn(false);
                  }
                }}
                disabled={isLoggingIn}
                className="px-3.5 py-1.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold flex items-center space-x-1.5 shadow-md shadow-indigo-600/30 transition-all"
              >
                {isLoggingIn ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />}
                <span>1-Click Demo Sign-In</span>
              </button>
            )}

            <button
              onClick={loadHistory}
              disabled={isLoading}
              className="flex items-center space-x-1.5 px-3.5 py-1.5 rounded-xl bg-[#141624] hover:bg-[#1A1D2E] text-xs font-semibold text-gray-300 border border-[#23273D] transition-colors"
            >
              <RotateCcw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin" : ""}`} />
              <span>Refresh</span>
            </button>

            {generations.length > 0 && (
              <button
                onClick={handleClearAll}
                disabled={isClearing}
                className="flex items-center space-x-1.5 px-3.5 py-1.5 rounded-xl bg-red-500/10 hover:bg-red-500/20 text-xs font-semibold text-red-400 border border-red-500/20 hover:border-red-500/30 transition-all"
                title="Delete all generations"
              >
                {isClearing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Trash2 className="w-3.5 h-3.5" />}
                <span>Clear History</span>
              </button>
            )}
          </div>
        </div>

        {/* Active Audio Player Preview */}
        {activeGen && activeGen.audio_url && (
          <div className="animate-in fade-in duration-200 bg-[#12141F] p-4 rounded-2xl border border-[#202436] space-y-3 shadow-lg">
            <AudioPlayer
              src={activeGen.audio_url}
              title={`Playing: ${activeGen.voice_name || "Neural Audio"}`}
              voiceName={activeGen.voice_name}
              duration={activeGen.actual_audio_seconds}
              format={activeGen.format}
              autoPlay={true}
            />
            <div className="flex items-center justify-between pt-2 border-t border-[#202436]/60 text-xs">
              <span className="text-gray-400">
                Active Selection: <strong className="text-white">{activeGen.voice_name || "Neural Voice"}</strong> ({activeGen.actual_audio_seconds}s)
              </span>
              <button
                onClick={() => handleDelete(activeGen.id)}
                className="flex items-center space-x-1.5 text-xs font-medium text-red-400 hover:text-red-300 bg-red-500/10 hover:bg-red-500/20 px-3 py-1 rounded-lg border border-red-500/20 transition-all"
              >
                <Trash2 className="w-3.5 h-3.5" />
                <span>Delete Track</span>
              </button>
            </div>
          </div>
        )}

        {/* Generations Table */}
        <div className="bg-[#12141F] border border-[#202436] rounded-2xl overflow-hidden shadow-xl flex-1">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-gray-300">
              <thead className="bg-[#0B0C14] text-gray-400 font-semibold border-b border-[#202436]">
                <tr>
                  <th className="px-5 py-3.5">Voice</th>
                  <th className="px-5 py-3.5">Characters</th>
                  <th className="px-5 py-3.5">Duration</th>
                  <th className="px-5 py-3.5">Format</th>
                  <th className="px-5 py-3.5">Status</th>
                  <th className="px-5 py-3.5">Created At</th>
                  <th className="px-5 py-3.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1A1D2E]">
                {generations.map((g) => {
                  const isActive = activeGen?.id === g.id;
                  return (
                    <tr
                      key={g.id}
                      className={`transition-colors ${
                        isActive ? "bg-indigo-600/10 border-l-2 border-indigo-500" : "hover:bg-[#151726]"
                      }`}
                    >
                      <td className="px-5 py-4 font-semibold text-white flex items-center space-x-2">
                        <FileAudio className={`w-4 h-4 ${isActive ? "text-indigo-400" : "text-gray-500"}`} />
                        <span>{g.voice_name || "Neural Voice"}</span>
                      </td>
                      <td className="px-5 py-4 font-mono">{g.input_characters.toLocaleString()}</td>
                      <td className="px-5 py-4 font-mono">
                        {g.actual_audio_seconds ? `${g.actual_audio_seconds}s` : "—"}
                      </td>
                      <td className="px-5 py-4 uppercase font-mono">{g.format}</td>
                      <td className="px-5 py-4">{getStatusBadge(g.status)}</td>
                      <td className="px-5 py-4 text-gray-400 font-mono">
                        {new Date(g.created_at).toLocaleString()}
                      </td>
                      <td className="px-5 py-4 text-right">
                        <div className="inline-flex items-center space-x-1.5">
                          {g.status === "completed" && g.audio_url ? (
                            <>
                              <button
                                onClick={() => handlePlayGeneration(g)}
                                className={`p-2 rounded-lg transition-colors ${
                                  isActive
                                    ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/30"
                                    : "bg-[#1D2133] hover:bg-indigo-600 hover:text-white text-gray-200"
                                }`}
                                title={isActive ? "Loaded in Player" : "Play Audio"}
                              >
                                {isActive ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5 fill-current" />}
                              </button>
                              <button
                                onClick={() => handleDirectDownload(g)}
                                disabled={downloadingId === g.id}
                                className="p-2 rounded-lg bg-[#1D2133] hover:bg-indigo-600 hover:text-white text-gray-200 transition-colors"
                                title="Download Audio File"
                              >
                                {downloadingId === g.id ? (
                                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                ) : (
                                  <Download className="w-3.5 h-3.5" />
                                )}
                              </button>
                            </>
                          ) : null}

                          <button
                            onClick={() => handleDelete(g.id)}
                            className="px-2.5 py-1.5 rounded-lg bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/20 hover:border-red-500/30 transition-all flex items-center space-x-1 text-xs font-semibold"
                            title="Delete Generation Record"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                            <span>Delete</span>
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}

                {generations.length === 0 && !isLoading && (
                  <tr>
                    <td colSpan={7} className="px-6 py-12 text-center text-gray-500 space-y-2">
                      <p>No generations found.</p>
                      <Link
                        href="/app/studio"
                        className="inline-block text-xs font-semibold text-indigo-400 hover:text-indigo-300"
                      >
                        Visit Studio to generate speech →
                      </Link>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </main>
    </div>
  );
}
