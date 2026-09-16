"use client";

import React, { useState, useEffect, useMemo } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  Sparkles,
  Download,
  RefreshCw,
  Clock,
  Layers,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Loader2,
  X,
  Maximize2
} from "lucide-react";

interface BatchItem {
  id: string;
  item_index: number;
  prompt: string;
  status: "pending" | "generating" | "completed" | "failed";
  image_url?: string;
  error_message?: string;
}

interface Batch {
  id: string;
  title: string;
  style_preset?: string;
  aspect_ratio: string;
  resolution: string;
  total_count: number;
  completed_count: number;
  failed_count: number;
  status: "pending" | "processing" | "completed" | "failed" | "queued";
  zip_url?: string;
  zip_size_bytes?: number;
  items: BatchItem[];
}

export default function BulkImagesPage() {
  // Input State
  const [promptsText, setPromptsText] = useState<string>("");
  const [aspectRatio, setAspectRatio] = useState<string>("16:9");
  const [resolution, setResolution] = useState<string>("1080p");
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Active Batch State
  const [currentBatch, setCurrentBatch] = useState<Batch | null>(null);
  const [previewItem, setPreviewItem] = useState<BatchItem | null>(null);

  // Auto-import prompts passed from AI Image Prompt Studio
  useEffect(() => {
    if (typeof window !== "undefined") {
      const stored = localStorage.getItem("hk_bulk_import_prompts");
      if (stored) {
        try {
          const parsed = JSON.parse(stored);
          if (Array.isArray(parsed) && parsed.length > 0) {
            setPromptsText(parsed.join("\n"));
            localStorage.removeItem("hk_bulk_import_prompts");
            localStorage.removeItem("hk_bulk_import_source");
          }
        } catch {
          // ignore
        }
      }
    }
  }, []);

  // Poll active batch while processing
  useEffect(() => {
    if (!currentBatch?.id) return;
    if (currentBatch.status === "processing" || currentBatch.status === "pending" || currentBatch.status === "queued") {
      const interval = setInterval(async () => {
        try {
          const res = await fetch(`http://127.0.0.1:8000/v1/bulk-images/batches/${currentBatch.id}`);
          if (res.ok) {
            const data = await res.json();
            setCurrentBatch(data);
          }
        } catch (err) {
          console.error("Polling error:", err);
        }
      }, 1500);
      return () => clearInterval(interval);
    }
  }, [currentBatch?.id, currentBatch?.status]);

  const parsedPrompts = useMemo(() => {
    return promptsText
      .split("\n")
      .map((p) => p.trim())
      .filter((p) => p.length > 0);
  }, [promptsText]);

  const handleGenerateImages = async () => {
    if (parsedPrompts.length === 0) {
      setErrorMessage("Please paste at least 1 prompt (one prompt per line).");
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      const res = await fetch("http://127.0.0.1:8000/v1/bulk-images/batches", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: `Batch of ${parsedPrompts.length} images`,
          prompts: parsedPrompts,
          aspect_ratio: aspectRatio,
          resolution: resolution,
        }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to start bulk image generation.");
      }

      const created = await res.json();
      // Fetch full batch with initial queued items
      const detailRes = await fetch(`http://127.0.0.1:8000/v1/bulk-images/batches/${created.id}`);
      if (detailRes.ok) {
        const detail = await detailRes.json();
        setCurrentBatch(detail);
      } else {
        setCurrentBatch(created);
      }
    } catch (err: any) {
      setErrorMessage(err.message || "Bulk generation error.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDownloadZip = () => {
    if (!currentBatch?.zip_url) return;
    const a = document.createElement("a");
    a.href = currentBatch.zip_url;
    a.download = `${currentBatch.title.replace(/\s+/g, "_")}.zip`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  const progressPct = useMemo(() => {
    if (!currentBatch || currentBatch.total_count === 0) return 0;
    const finished = (currentBatch.completed_count || 0) + (currentBatch.failed_count || 0);
    return Math.min(100, Math.round((finished / currentBatch.total_count) * 100));
  }, [currentBatch]);

  return (
    <div className="h-screen w-screen bg-[#08090E] text-gray-100 flex flex-col overflow-hidden selection:bg-purple-600 selection:text-white">
      {/* 1. TOP MINIMAL FOCUSED NAVBAR WITH SIMPLE BACK BUTTON */}
      {/* 1. TOP MINIMAL FOCUSED NAVBAR WITH SIMPLE BACK BUTTON */}
      <header className="h-16 px-6 border-b border-[#181C2B] bg-[#0C0E17]/90 backdrop-blur-md flex items-center justify-between flex-shrink-0 z-20">
        <div className="flex items-center space-x-4">
          <Link
            href="/"
            className="flex items-center space-x-2 px-3 py-1.5 rounded-xl bg-[#141724] hover:bg-[#1D2235] border border-[#21273C] text-xs font-semibold text-gray-300 hover:text-white transition-all shadow-sm group"
            title="Return to HK Speaks"
          >
            <ArrowLeft className="w-3.5 h-3.5 group-hover:-translate-x-0.5 transition-transform" />
            <span>Back to HK Speaks</span>
          </Link>

          <div className="h-4 w-px bg-[#202538]" />

          <div className="flex items-center space-x-2.5">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-tr from-purple-600 to-indigo-600 flex items-center justify-center shadow-md shadow-purple-600/20">
              <Layers className="w-4 h-4 text-white" />
            </div>
            <div>
              <h1 className="text-sm font-bold text-white tracking-tight">Bulk Image Generator</h1>
              <p className="text-[10px] text-gray-400">High-Throughput Parallel Synthesis &bull; 1,000+ Batch Scaling</p>
            </div>
          </div>
        </div>
      </header>

      {/* 2. TWO-PANEL WORKSPACE */}
      <div className="flex-1 flex overflow-hidden">
        {/* LEFT SIDEBAR CONTROLS */}
        <aside className="w-80 md:w-96 border-r border-[#181C2B] bg-[#0B0D15] p-5 flex flex-col space-y-4 overflow-y-auto flex-shrink-0">
          {errorMessage && (
            <div className="p-3 rounded-xl bg-rose-950/40 border border-rose-800/50 flex items-center space-x-2 text-xs text-rose-300">
              <AlertCircle className="w-4 h-4 text-rose-400 flex-shrink-0" />
              <span>{errorMessage}</span>
            </div>
          )}

          {/* Large Paste Prompts Input */}
          <div className="flex-1 flex flex-col space-y-1.5 min-h-[220px]">
            <div className="flex items-center justify-between">
              <label className="text-xs font-bold text-gray-200">Paste Prompts</label>
              <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-[#141726] text-purple-300 border border-[#21263D]">
                {parsedPrompts.length} {parsedPrompts.length === 1 ? "prompt" : "prompts"}
              </span>
            </div>
            <textarea
              value={promptsText}
              onChange={(e) => setPromptsText(e.target.value)}
              placeholder="Paste prompts here (one prompt per line)...&#10;&#10;Wide shot of astronaut walking on red dusty crater&#10;Neon cyber market street with hologram dragon&#10;Photorealistic emerald hummingbird in macro detail"
              rows={8}
              className="flex-1 w-full bg-[#08090E] border border-[#1C2030] rounded-xl p-3.5 text-xs text-gray-200 placeholder-gray-600 focus:outline-none focus:border-purple-500 font-mono leading-relaxed resize-none"
            />
            <span className="text-[10px] text-gray-500">One prompt per line &bull; Supports 1,000+ lines</span>
          </div>

          {/* Generate Images Button */}
          <button
            onClick={handleGenerateImages}
            disabled={isSubmitting || parsedPrompts.length === 0}
            className="w-full py-3 rounded-xl bg-gradient-to-r from-purple-600 via-indigo-600 to-cyan-600 hover:from-purple-500 hover:to-cyan-500 text-white font-extrabold text-xs shadow-lg shadow-purple-600/30 transition-all disabled:opacity-40 flex items-center justify-center space-x-2 active:scale-95"
          >
            {isSubmitting ? (
              <RefreshCw className="w-4 h-4 animate-spin" />
            ) : (
              <Sparkles className="w-4 h-4" />
            )}
            <span>{isSubmitting ? "Queueing Batch..." : `Generate ${parsedPrompts.length || ""} Images`}</span>
          </button>

          {/* Aspect Ratio Selector directly below Generate */}
          <div className="space-y-1">
            <label className="text-xs font-semibold text-gray-300">Aspect Ratio</label>
            <div className="grid grid-cols-3 gap-2">
              {[
                { id: "16:9", label: "16:9 (Landscape)" },
                { id: "1:1", label: "1:1 (Square)" },
                { id: "9:16", label: "9:16 (Vertical)" },
              ].map((ratio) => (
                <button
                  key={ratio.id}
                  type="button"
                  onClick={() => setAspectRatio(ratio.id)}
                  className={`py-2 px-2 text-xs font-semibold rounded-xl border transition-all text-center ${
                    aspectRatio === ratio.id
                      ? "bg-purple-600 text-white border-purple-500 shadow-sm"
                      : "bg-[#10131E] text-gray-400 border-[#1E2336] hover:text-white"
                  }`}
                >
                  {ratio.id}
                </button>
              ))}
            </div>
          </div>

          {/* Resolution Selector */}
          <div className="space-y-1">
            <label className="text-xs font-semibold text-gray-300">Resolution</label>
            <select
              value={resolution}
              onChange={(e) => setResolution(e.target.value)}
              className="w-full bg-[#10131E] border border-[#1E2336] text-xs text-gray-200 rounded-xl p-2.5 focus:outline-none focus:border-purple-500 font-medium"
            >
              <option value="1080p">1080p Full HD (Recommended)</option>
              <option value="720p">720p HD (Fast)</option>
              <option value="2K">2K QHD (Maximum Clarity)</option>
            </select>
          </div>

          {/* Generation Progress */}
          {currentBatch && (
            <div className="p-3.5 rounded-xl bg-[#121522] border border-[#1E2438] space-y-3">
              <div className="flex items-center justify-between text-xs font-mono">
                <span className="text-gray-200 font-bold flex items-center space-x-1.5">
                  {currentBatch.status === "processing" && (
                    <Loader2 className="w-3.5 h-3.5 text-purple-400 animate-spin inline" />
                  )}
                  <span>
                    Generating {Math.min(currentBatch.total_count, (currentBatch.completed_count || 0) + (currentBatch.failed_count || 0) + 1)}/{currentBatch.total_count}
                  </span>
                </span>
                <span className="text-purple-300 font-bold">{progressPct}%</span>
              </div>

              <div className="w-full h-2 bg-[#1C2030] rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-purple-500 via-indigo-500 to-cyan-400 transition-all duration-300"
                  style={{ width: `${progressPct}%` }}
                />
              </div>

              {/* Exact 3 metrics: Completed, Processing, Failed */}
              <div className="grid grid-cols-3 gap-1.5 pt-0.5 text-xs font-mono">
                <div className="bg-[#161928] py-2 px-1 rounded-lg text-center border border-[#21263E]">
                  <div className="text-emerald-400 font-bold text-sm">{currentBatch.completed_count || 0}</div>
                  <div className="text-[10px] text-gray-400 mt-0.5">Completed</div>
                </div>
                <div className="bg-[#161928] py-2 px-1 rounded-lg text-center border border-[#21263E]">
                  <div className="text-amber-400 font-bold text-sm">
                    {Math.max(0, currentBatch.total_count - (currentBatch.completed_count || 0) - (currentBatch.failed_count || 0))}
                  </div>
                  <div className="text-[10px] text-gray-400 mt-0.5">Processing</div>
                </div>
                <div className="bg-[#161928] py-2 px-1 rounded-lg text-center border border-[#21263E]">
                  <div className="text-rose-400 font-bold text-sm">{currentBatch.failed_count || 0}</div>
                  <div className="text-[10px] text-gray-400 mt-0.5">Failed</div>
                </div>
              </div>
            </div>
          )}

          {/* Export ZIP Button */}
          <button
            onClick={handleDownloadZip}
            disabled={!currentBatch?.zip_url}
            className={`w-full py-2.5 rounded-xl text-xs font-bold transition-all flex items-center justify-center space-x-2 border ${
              currentBatch?.zip_url
                ? "bg-emerald-600 hover:bg-emerald-500 text-white border-emerald-500 shadow-md shadow-emerald-600/20 active:scale-95"
                : "bg-[#11131E] text-gray-500 border-[#1B1F30] cursor-not-allowed"
            }`}
          >
            <Download className="w-4 h-4" />
            <span>
              {currentBatch?.zip_url
                ? "Export ZIP Archive"
                : currentBatch?.status === "processing"
                ? `Packaging ZIP (${progressPct}%)...`
                : "Export ZIP"}
            </span>
          </button>
        </aside>

        {/* RIGHT / MAIN AREA: LARGE IMAGE GALLERY */}
        <main className="flex-1 bg-[#08090E] p-6 overflow-y-auto flex flex-col">
          {!currentBatch || !currentBatch.items || currentBatch.items.length === 0 ? (
            <div className="flex-1 flex flex-col items-center justify-center text-center p-8">
              <div className="w-16 h-16 rounded-2xl bg-[#10131E] border border-[#1E2336] flex items-center justify-center text-purple-400 mb-4 shadow-xl">
                <Layers className="w-8 h-8" />
              </div>
              <h2 className="text-base font-bold text-gray-200 mb-1">Generated Gallery Ready</h2>
              <p className="text-xs text-gray-400 max-w-sm">
                Paste your prompts on the left and click <b>Generate Images</b>. Images will synthesize in parallel and display here with live status and 1-click ZIP export.
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="flex items-center justify-between pb-2 border-b border-[#161928]">
                <div className="flex items-center space-x-2">
                  <span className="text-xs font-bold text-gray-200">{currentBatch.title}</span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#141828] text-purple-300 border border-[#21263E]">
                    {currentBatch.aspect_ratio} &bull; {currentBatch.resolution}
                  </span>
                </div>
                <span className="text-xs text-gray-400">
                  Showing {currentBatch.items.length} images
                </span>
              </div>

              {/* Responsive Image Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
                {currentBatch.items.map((item) => {
                  const isDone = item.status === "completed" && !!item.image_url;
                  return (
                    <div
                      key={item.id}
                      onClick={() => isDone && setPreviewItem(item)}
                      className={`group relative rounded-xl overflow-hidden bg-[#0D0F18] border transition-all flex flex-col ${
                        isDone
                          ? "border-[#1A1D2D] hover:border-purple-500 cursor-pointer shadow-md hover:shadow-purple-600/20"
                          : "border-[#1A1D2D]"
                      }`}
                    >
                      {/* Visual Container */}
                      <div className={`relative ${
                        currentBatch.aspect_ratio === "1:1"
                          ? "aspect-square"
                          : currentBatch.aspect_ratio === "9:16"
                          ? "aspect-[9/16]"
                          : "aspect-video"
                      } bg-[#05060A] overflow-hidden flex items-center justify-center`}>
                        {isDone ? (
                          <>
                            <img
                              src={item.image_url}
                              alt={item.prompt}
                              className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                              loading="lazy"
                            />
                            {/* Hover overlay indicator for zoom */}
                            <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center pointer-events-none">
                              <div className="px-2.5 py-1 rounded-lg bg-black/70 backdrop-blur-md text-white text-[11px] font-semibold flex items-center space-x-1.5 border border-white/20">
                                <Maximize2 className="w-3.5 h-3.5" />
                                <span>Preview</span>
                              </div>
                            </div>
                          </>
                        ) : item.status === "generating" ? (
                          <div className="flex flex-col items-center space-y-1.5 text-purple-400">
                            <RefreshCw className="w-5 h-5 animate-spin" />
                            <span className="text-[10px] font-medium animate-pulse">Rendering...</span>
                          </div>
                        ) : item.status === "failed" ? (
                          <div className="flex flex-col items-center space-y-1 text-rose-400 p-2 text-center">
                            <XCircle className="w-5 h-5" />
                            <span className="text-[10px]">Failed</span>
                          </div>
                        ) : (
                          <div className="flex flex-col items-center space-y-1 text-gray-500">
                            <Clock className="w-4 h-4" />
                            <span className="text-[10px]">Queued</span>
                          </div>
                        )}

                        {/* Failed Error Message Tooltip/Indicator */}
                        {item.status === "failed" && item.error_message && (
                          <div className="absolute inset-x-0 bottom-0 p-1.5 bg-black/90 text-[10px] text-rose-300 line-clamp-2 text-center select-text">
                            {item.error_message}
                          </div>
                        )}
                      </div>

                      {/* Metadata & Prompt */}
                      <div className="p-2.5 flex-1 flex flex-col justify-between">
                        <p className="text-[11px] text-gray-300 line-clamp-2 leading-tight mb-2 select-text font-mono">
                          {item.prompt}
                        </p>

                        <div className="flex items-center justify-between text-[10px] text-gray-500 pt-1.5 border-t border-[#161928]">
                          <span className="font-mono">#{item.item_index}</span>
                          <span className={`capitalize font-mono ${
                            item.status === "completed"
                              ? "text-emerald-400"
                              : item.status === "generating"
                              ? "text-purple-400"
                              : item.status === "failed"
                              ? "text-rose-400"
                              : "text-gray-500"
                          }`}>
                            {item.status}
                          </span>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </main>
      </div>

      {/* 3. IN-PAGE LARGE FULL-RESOLUTION PREVIEW MODAL (SAME PAGE, NO NEW TAB) */}
      {previewItem && (
        <div
          className="fixed inset-0 z-50 bg-black/85 backdrop-blur-md flex items-center justify-center p-4 md:p-8 animate-in fade-in duration-200"
          onClick={() => setPreviewItem(null)}
        >
          <div
            className="relative max-w-5xl w-full bg-[#0D0F19] border border-[#21263D] rounded-2xl overflow-hidden shadow-2xl flex flex-col max-h-[92vh]"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="flex items-center justify-between px-5 py-3.5 border-b border-[#1A1E2E] bg-[#0A0C14]">
              <div className="flex items-center space-x-3">
                <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-purple-950/60 text-purple-300 border border-purple-800/50">
                  Image #{previewItem.item_index}
                </span>
                <span className="text-xs text-gray-400 font-mono">
                  {currentBatch?.aspect_ratio} &bull; {currentBatch?.resolution}
                </span>
              </div>
              <button
                onClick={() => setPreviewItem(null)}
                className="w-8 h-8 rounded-xl bg-[#141726] hover:bg-[#20253D] text-gray-400 hover:text-white flex items-center justify-center transition-colors"
                title="Close preview (Esc)"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Modal Image Area */}
            <div className="relative flex-1 bg-[#05060A] flex items-center justify-center p-2 min-h-[300px] max-h-[68vh] overflow-hidden">
              <img
                src={previewItem.image_url}
                alt={previewItem.prompt}
                className="max-h-[66vh] max-w-full w-auto object-contain rounded-lg shadow-xl"
              />
            </div>

            {/* Modal Prompt Footer */}
            <div className="p-4 bg-[#0A0C14] border-t border-[#1A1E2E]">
              <p className="text-xs text-gray-200 font-mono leading-relaxed select-text">
                {previewItem.prompt}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
