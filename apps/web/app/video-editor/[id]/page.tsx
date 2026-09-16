"use client";

import React, { useState, useEffect, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  VideoProjectDetail,
  VideoAsset,
  Scene,
  TimelineClip,
  RenderJob,
  getVideoProject,
  uploadVideoAssets,
  deleteVideoAsset,
  generateDocumentaryTimeline,
  updateVideoTimeline,
  submitVideoRender,
  getRenderJobStatus,
} from "@/lib/video-api";
import { useAuth } from "@/lib/auth-context";
import Navbar from "@/components/Navbar";
import {
  ArrowLeft,
  Sparkles,
  Upload,
  Play,
  Pause,
  Clock,
  Download,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Trash2,
  ChevronRight,
  ChevronDown,
  Layers,
  Film,
  Music,
  Maximize2,
  Image as ImageIcon,
  Check,
  Video,
} from "lucide-react";

export default function DocumentaryStudioPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params?.id as string;
  const { user, isLoading: authLoading } = useAuth();

  const [project, setProject] = useState<VideoProjectDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Asset upload states
  const [uploading, setUploading] = useState(false);
  const imageInputRef = useRef<HTMLInputElement>(null);
  const voiceoverInputRef = useRef<HTMLInputElement>(null);

  // Generation & Render/Export states
  const [generating, setGenerating] = useState(false);
  const [rendering, setRendering] = useState(false);
  const [activeJob, setActiveJob] = useState<RenderJob | null>(null);
  const [showExportDropdown, setShowExportDropdown] = useState(false);
  const [exportResolution, setExportResolution] = useState("1080p");
  const [downloadTriggered, setDownloadTriggered] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);

  // Active scene / playback state
  const [selectedSceneIndex, setSelectedSceneIndex] = useState(0);
  const [isPlayingAudio, setIsPlayingAudio] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [viewMode, setViewMode] = useState<"preview" | "rendered">("preview");

  const audioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    if (!authLoading && !user) {
      router.push("/login");
      return;
    }
    if (user && projectId) {
      loadProject();
    }
  }, [user, authLoading, projectId]);

  // Polling for active render job with automatic browser download upon completion
  useEffect(() => {
    let interval: NodeJS.Timeout | null = null;
    if (activeJob && (activeJob.status === "queued" || activeJob.status === "processing" || activeJob.status === "rendering")) {
      interval = setInterval(async () => {
        try {
          const updated = await getRenderJobStatus(activeJob.id);
          setActiveJob(updated);
          if (updated.status === "completed") {
            setRendering(false);
            const fresh = await getVideoProject(projectId);
            setProject(fresh);

            // Automatic browser download trigger
            if (fresh.render_outputs && fresh.render_outputs.length > 0 && !downloadTriggered) {
              setDownloadTriggered(true);
              const latest = fresh.render_outputs[0];
              const dlUrl = latest.download_url || latest.url;
              if (dlUrl) {
                triggerDirectFileDownload(dlUrl, latest.filename);
              }
            }
          } else if (updated.status === "failed") {
            setRendering(false);
            setExportError(updated.error_message || "Video export failed. Please verify media files.");
          }
        } catch (e) {
          console.error("Failed to poll render job", e);
        }
      }, 1200);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [activeJob, projectId, downloadTriggered]);

  async function loadProject() {
    try {
      setLoading(true);
      setError(null);
      const data = await getVideoProject(projectId);
      setProject(data);
      if (data.latest_render && (data.latest_render.status === "queued" || data.latest_render.status === "processing" || data.latest_render.status === "rendering")) {
        setActiveJob(data.latest_render);
        setRendering(true);
      } else if (data.latest_render && data.latest_render.status === "failed") {
        setActiveJob(data.latest_render);
        setRendering(false);
        setExportError(data.latest_render.error_message || "Video export failed");
      } else if (data.latest_render && data.latest_render.status === "completed") {
        setActiveJob(data.latest_render);
        setRendering(false);
      }
    } catch (err: any) {
      setError(err?.message || "Failed to load project details");
    } finally {
      setLoading(false);
    }
  }

  async function handleVoiceoverUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    try {
      setUploading(true);
      const uploaded = await uploadVideoAssets(projectId, Array.from(files), "voiceover");
      await loadProject();
    } catch (err: any) {
      alert(err?.message || "Failed to upload voiceover");
    } finally {
      setUploading(false);
      if (voiceoverInputRef.current) voiceoverInputRef.current.value = "";
    }
  }

  async function handleImageUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    try {
      setUploading(true);
      await uploadVideoAssets(projectId, Array.from(files), "image");
      await loadProject();
    } catch (err: any) {
      alert(err?.message || "Failed to upload images");
    } finally {
      setUploading(false);
      if (imageInputRef.current) imageInputRef.current.value = "";
    }
  }

  async function handleDeleteAsset(assetId: string) {
    if (!confirm("Are you sure you want to remove this asset?")) return;
    try {
      await deleteVideoAsset(projectId, assetId);
      await loadProject();
    } catch (err: any) {
      alert(err?.message || "Failed to delete asset");
    }
  }

  async function handleGenerateDocumentary() {
    try {
      setGenerating(true);
      const updated = await generateDocumentaryTimeline(projectId);
      setProject(updated);
      setSelectedSceneIndex(0);
    } catch (err: any) {
      alert(err?.message || "Failed to generate documentary timeline");
    } finally {
      setGenerating(false);
    }
  }

  async function handleMotionChange(sceneIndex: number, newMotion: string) {
    if (!project || !project.timeline_clips) return;
    const updatedClips = project.timeline_clips.map((c, idx) => {
      if (idx === sceneIndex) {
        return {
          id: c.id,
          asset_id: c.asset_id,
          start_time: c.start_time,
          end_time: c.end_time,
          duration: c.duration,
          motion_type: newMotion as any,
          scale_factor: c.scale_factor,
          framing: c.framing,
        };
      }
      return {
        id: c.id,
        asset_id: c.asset_id,
        start_time: c.start_time,
        end_time: c.end_time,
        duration: c.duration,
        motion_type: c.motion_type,
        scale_factor: c.scale_factor,
        framing: c.framing,
      };
    });

    try {
      const updated = await updateVideoTimeline(projectId, updatedClips);
      setProject(updated);
    } catch (e: any) {
      alert(e?.message || "Failed to update motion");
    }
  }

  async function handleSwapAsset(sceneIndex: number, newAssetId: string) {
    if (!project || !project.timeline_clips) return;
    const clip = project.timeline_clips[sceneIndex];
    if (!clip) return;

    const updatedClips = project.timeline_clips.map((c, idx) => {
      if (idx === sceneIndex) {
        return {
          id: c.id,
          asset_id: newAssetId,
          start_time: c.start_time,
          end_time: c.end_time,
          duration: c.duration,
          motion_type: c.motion_type,
          scale_factor: c.scale_factor,
          framing: c.framing,
        };
      }
      return {
        id: c.id,
        asset_id: c.asset_id,
        start_time: c.start_time,
        end_time: c.end_time,
        duration: c.duration,
        motion_type: c.motion_type,
        scale_factor: c.scale_factor,
        framing: c.framing,
      };
    });

    try {
      const updated = await updateVideoTimeline(projectId, updatedClips);
      setProject(updated);
    } catch (e: any) {
      alert(e?.message || "Failed to swap image");
    }
  }

  async function handleStartExport(chosenRes: string) {
    if (!project?.timeline_clips || project.timeline_clips.length === 0) {
      alert("Please generate the documentary timeline before exporting.");
      return;
    }
    setShowExportDropdown(false);
    setExportResolution(chosenRes);
    try {
      setRendering(true);
      setDownloadTriggered(false);
      setExportError(null);
      const job = await submitVideoRender(projectId, {
        aspect_ratio: project.aspect_ratio || "16:9",
        resolution: chosenRes,
        format: "mp4",
        fps: project.fps || 30,
      });
      setActiveJob(job);
    } catch (err: any) {
      setRendering(false);
      setExportError(err?.message || "Failed to start export job");
    }
  }

  async function triggerDirectFileDownload(url: string, filename: string) {
    try {
      // Direct blob download strictly forces direct file download to disk and NEVER opens in a browser tab
      const res = await fetch(url);
      if (!res.ok) throw new Error("Download fetch failed");
      const blob = await res.blob();
      const blobUrl = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.style.display = "none";
      a.href = blobUrl;
      a.download = filename || "documentary.mp4";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      setTimeout(() => window.URL.revokeObjectURL(blobUrl), 15000);
    } catch (e) {
      // Fallback with attachment query
      const fallbackUrl = `${url}${url.includes("?") ? "&" : "?"}download=1`;
      const a = document.createElement("a");
      a.style.display = "none";
      a.href = fallbackUrl;
      a.setAttribute("download", filename || "documentary.mp4");
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    }
  }

  function handleDownloadExportedMp4() {
    if (!project?.render_outputs || project.render_outputs.length === 0) return;
    const latest = project.render_outputs[0];
    const dlUrl = latest.download_url || latest.url;
    if (!dlUrl) return;
    triggerDirectFileDownload(dlUrl, latest.filename);
  }

  function toggleAudioPlayback() {
    if (!audioRef.current) return;
    if (isPlayingAudio) {
      audioRef.current.pause();
      setIsPlayingAudio(false);
    } else {
      audioRef.current.play();
      setIsPlayingAudio(true);
    }
  }

  function handleAudioTimeUpdate() {
    if (!audioRef.current || !project) return;
    const t = audioRef.current.currentTime;
    setCurrentTime(t);

    // Sync selected scene based on current audio playback position
    const foundIdx = project.timeline_clips.findIndex(
      (c) => t >= c.start_time && t < c.end_time
    );
    if (foundIdx !== -1 && foundIdx !== selectedSceneIndex) {
      setSelectedSceneIndex(foundIdx);
    }
  }

  function seekToScene(sceneIdx: number) {
    setSelectedSceneIndex(sceneIdx);
    if (!project || !audioRef.current) return;
    const clip = project.timeline_clips[sceneIdx];
    if (clip) {
      audioRef.current.currentTime = clip.start_time;
      setCurrentTime(clip.start_time);
    }
  }

  function formatDuration(sec: number) {
    if (!sec || sec <= 0) return "0:00";
    const mins = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    return `${mins}:${s.toString().padStart(2, "0")}`;
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0A0B10] text-gray-100 flex flex-col">
        <Navbar />
        <div className="flex-1 flex flex-col items-center justify-center space-y-3">
          <Loader2 className="w-8 h-8 text-purple-400 animate-spin" />
          <span className="text-sm text-gray-400">Loading Documentary Studio...</span>
        </div>
      </div>
    );
  }

  if (error || !project) {
    return (
      <div className="min-h-screen bg-[#0A0B10] text-gray-100 flex flex-col">
        <Navbar />
        <div className="flex-1 flex flex-col items-center justify-center p-6 text-center">
          <div className="w-12 h-12 rounded-2xl bg-red-500/10 border border-red-500/30 flex items-center justify-center text-red-400 mb-3">
            <AlertCircle className="w-6 h-6" />
          </div>
          <h2 className="text-lg font-bold text-white mb-1">Documentary Project Error</h2>
          <p className="text-xs text-gray-400 mb-4 max-w-sm">{error || "Could not load project details"}</p>
          <Link
            href="/video-editor"
            className="px-4 py-2 rounded-xl text-xs font-semibold bg-[#1C1F32] hover:bg-[#262B42] text-white transition-colors"
          >
            Return to Video Editor
          </Link>
        </div>
      </div>
    );
  }

  const imageAssets = project.assets.filter((a) => a.asset_type === "image");
  const selectedClip = project.timeline_clips[selectedSceneIndex];
  const selectedScene = project.scenes[selectedSceneIndex];
  const selectedAsset = selectedClip?.asset || imageAssets[0];
  const latestRenderOutput = project.render_outputs && project.render_outputs.length > 0 ? project.render_outputs[0] : null;

  // Export control lifecycle states
  const isExporting = Boolean(
    rendering ||
    (activeJob && (activeJob.status === "queued" || activeJob.status === "processing" || activeJob.status === "rendering"))
  );
  const isCompleted = !isExporting && (
    activeJob?.status === "completed" ||
    Boolean(project.render_outputs && project.render_outputs.length > 0)
  );
  const isFailed = !isExporting && activeJob?.status === "failed";

  // Determine Ken Burns CSS class
  const motionCss = {
    zoom_in: "scale-110 transition-transform duration-[4000ms] ease-out",
    zoom_out: "scale-95 transition-transform duration-[4000ms] ease-out",
    pan_left: "translate-x-[-3%] transition-transform duration-[4000ms] ease-out",
    pan_right: "translate-x-[3%] transition-transform duration-[4000ms] ease-out",
    ken_burns: "scale-110 translate-x-[2%] transition-transform duration-[4000ms] ease-out",
    static: "",
  }[selectedClip?.motion_type || "static"];

  return (
    <div className="min-h-screen bg-[#090A10] text-gray-100 flex flex-col selection:bg-purple-500 selection:text-white">
      <Navbar />

      {/* Top Action Bar */}
      <div className="border-b border-[#1E2235] bg-[#0E101A] px-4 sm:px-6 py-3 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center space-x-3">
          <Link
            href="/video-editor"
            className="p-1.5 rounded-lg bg-[#151726] hover:bg-[#1E2238] text-gray-400 hover:text-white border border-[#262B40] transition-colors"
            title="Back to All Projects"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="font-bold text-base text-white">{project.title}</h1>
              <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-purple-500/15 text-purple-300 border border-purple-500/30">
                {project.aspect_ratio} • {project.resolution}
              </span>
            </div>
            <div className="flex items-center space-x-2 text-xs text-gray-400 mt-0.5">
              <span>{project.scenes.length} Scenes</span>
              <span>•</span>
              <span className="flex items-center space-x-1">
                <Clock className="w-3 h-3 text-gray-500" />
                <span>{formatDuration(project.total_duration)}</span>
              </span>
            </div>
          </div>
        </div>

        <div className="flex items-center space-x-2.5">
          {latestRenderOutput && (
            <div className="flex items-center space-x-1 bg-[#151828] p-1 rounded-xl border border-[#22273E]">
              <button
                onClick={() => setViewMode("preview")}
                className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
                  viewMode === "preview"
                    ? "bg-purple-600 text-white shadow-sm"
                    : "text-gray-400 hover:text-gray-200"
                }`}
              >
                Timeline Preview
              </button>
              <button
                onClick={() => setViewMode("rendered")}
                className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
                  viewMode === "rendered"
                    ? "bg-emerald-600 text-white shadow-sm"
                    : "text-gray-400 hover:text-gray-200"
                }`}
              >
                Rendered MP4
              </button>
            </div>
          )}

          <button
            onClick={handleGenerateDocumentary}
            disabled={generating || !project.voiceover || imageAssets.length === 0}
            className="px-4 py-2 rounded-xl text-xs font-semibold bg-[#181B2B] hover:bg-[#22273D] text-purple-300 border border-purple-500/30 disabled:opacity-50 transition-all flex items-center space-x-1.5"
            title="Analyze voiceover cadence & auto-direct scenes"
          >
            {generating ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin text-purple-400" />
            ) : (
              <Sparkles className="w-3.5 h-3.5 text-purple-400" />
            )}
            <span>{project.scenes.length > 0 ? "Regenerate Timeline" : "Generate Documentary"}</span>
          </button>

          {/* REBUILT NON-BLOCKING EXPORT CONTROL */}
          <div className="relative">
            {isExporting ? (
              /* LIVE IN-BUTTON PROGRESS STATE */
              <div 
                className="flex items-center space-x-2.5 px-4 py-2 rounded-xl text-xs font-semibold bg-[#16182B] border border-purple-500/40 text-purple-200 shadow-md shadow-purple-950/40 relative overflow-hidden select-none"
                title={activeJob?.current_step || "FFmpeg export in progress..."}
              >
                {/* Embedded progress bar visual */}
                <div
                  className="absolute inset-y-0 left-0 bg-gradient-to-r from-purple-600/40 via-indigo-600/40 to-purple-500/40 transition-all duration-300 pointer-events-none"
                  style={{ width: `${Math.max(4, Math.min(100, Math.round(activeJob?.progress || 0)))}%` }}
                />
                <Loader2 className="w-3.5 h-3.5 animate-spin text-purple-400 relative z-10" />
                <span className="relative z-10 font-mono tracking-tight">
                  Exporting {exportResolution.toUpperCase()}... {Math.round(activeJob?.progress || 0)}%
                </span>
              </div>
            ) : isCompleted ? (
              /* EXPORT COMPLETE -> DOWNLOAD MP4 STATE */
              <div className="flex items-center space-x-1">
                <button
                  onClick={handleDownloadExportedMp4}
                  className="px-4 py-2 rounded-xl text-xs font-semibold bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white shadow-md shadow-emerald-700/20 transition-all flex items-center space-x-2"
                  title="Download rendered MP4 video"
                >
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-200" />
                  <span>Download MP4</span>
                </button>
                <button
                  onClick={() => setShowExportDropdown(!showExportDropdown)}
                  className="p-2 rounded-xl bg-[#181B2B] hover:bg-[#22273D] text-gray-300 border border-[#2B3150] transition-colors"
                  title="Export in another quality"
                >
                  <ChevronDown className="w-3.5 h-3.5" />
                </button>
              </div>
            ) : isFailed ? (
              /* FAILURE RETRY STATE */
              <div className="flex items-center space-x-1">
                <button
                  onClick={() => setShowExportDropdown(!showExportDropdown)}
                  className="px-4 py-2 rounded-xl text-xs font-semibold bg-red-500/20 border border-red-500/40 text-red-300 hover:bg-red-500/30 transition-all flex items-center space-x-2"
                  title={activeJob?.error_message || "Export failed. Click to retry."}
                >
                  <AlertCircle className="w-3.5 h-3.5 text-red-400" />
                  <span>Export Failed — Retry</span>
                  <ChevronDown className="w-3.5 h-3.5 ml-0.5 opacity-70" />
                </button>
              </div>
            ) : (
              /* DEFAULT READY TO EXPORT STATE */
              <button
                onClick={() => {
                  if (!project.timeline_clips || project.timeline_clips.length === 0) {
                    alert("Please click 'Generate Documentary' to build your timeline before exporting.");
                    return;
                  }
                  setShowExportDropdown(!showExportDropdown);
                }}
                className="px-4 py-2 rounded-xl text-xs font-semibold bg-gradient-to-r from-purple-600 via-indigo-600 to-purple-500 hover:from-purple-500 hover:to-indigo-500 text-white shadow-md shadow-purple-600/30 transition-all flex items-center space-x-2"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Export Video</span>
                <ChevronDown className="w-3.5 h-3.5 ml-0.5 opacity-80" />
              </button>
            )}

            {/* NON-BLOCKING QUALITY PICKER DROPDOWN */}
            {showExportDropdown && (
              <div className="absolute right-0 top-full mt-2 w-72 bg-[#121422] border border-[#2B3150] rounded-2xl shadow-2xl p-3.5 z-50 text-left animate-in fade-in slide-in-from-top-1 duration-150">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-xs font-bold text-white uppercase tracking-wider">Select Export Quality</h3>
                  <button
                    onClick={() => setShowExportDropdown(false)}
                    className="text-gray-400 hover:text-white text-xs px-1"
                  >
                    ✕
                  </button>
                </div>
                <p className="text-[11px] text-gray-400 mb-3">
                  Format: MP4 • {project.aspect_ratio || "16:9"} (YouTube Long)
                </p>

                {isFailed && activeJob?.error_message && (
                  <div className="mb-3 p-2.5 rounded-xl bg-red-500/15 border border-red-500/30 text-[11px] text-red-300">
                    <span className="font-semibold block mb-0.5">Error detail:</span>
                    {activeJob.error_message}
                  </div>
                )}

                <div className="space-y-2">
                  {[
                    { key: "1080p", title: "1080p (Full HD)", res: "1920×1080", desc: "Fast render • Standard YouTube" },
                    { key: "1440p", title: "1440p (2K QHD)", res: "2560×1440", desc: "High clarity • 2K QHD detail" },
                    { key: "4k", title: "4K (Ultra HD)", res: "3840×2160", desc: "Maximum fidelity • 2160p UHD" },
                  ].map((opt) => (
                    <button
                      key={opt.key}
                      onClick={() => handleStartExport(opt.key)}
                      className="w-full p-2.5 rounded-xl bg-[#17192A] hover:bg-purple-600/20 border border-[#232840] hover:border-purple-500/50 transition-all text-left group flex items-center justify-between"
                    >
                      <div>
                        <div className="text-xs font-bold text-gray-200 group-hover:text-white">
                          {opt.title}
                        </div>
                        <p className="text-[10px] text-gray-400 mt-0.5">{opt.desc}</p>
                      </div>
                      <span className="text-[10px] font-mono text-purple-400 font-semibold shrink-0 ml-2">
                        {opt.res}
                      </span>
                    </button>
                  ))}
                </div>

                <div className="mt-3 pt-2.5 border-t border-[#1E2338] text-[10px] text-gray-400 text-center">
                  Runs asynchronously in background. You can keep editing while FFmpeg exports.
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Main Studio Split Layout */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-0 overflow-hidden">
        {/* PANEL A: ASSETS (3 cols) */}
        <div className="lg:col-span-3 border-r border-[#1E2235] bg-[#0C0D16] p-4 flex flex-col space-y-4 overflow-y-auto max-h-[calc(100vh-16rem)]">
          <div>
            <div className="flex items-center justify-between mb-2">
              <h2 className="text-xs font-bold uppercase tracking-wider text-gray-300 flex items-center space-x-1.5">
                <Music className="w-3.5 h-3.5 text-purple-400" />
                <span>Voiceover Audio</span>
              </h2>
              <button
                onClick={() => voiceoverInputRef.current?.click()}
                disabled={uploading}
                className="text-[11px] font-semibold text-purple-400 hover:text-purple-300 flex items-center space-x-1"
              >
                <Upload className="w-3 h-3" />
                <span>{project.voiceover ? "Replace" : "Upload"}</span>
              </button>
              <input
                type="file"
                ref={voiceoverInputRef}
                onChange={handleVoiceoverUpload}
                accept="audio/*"
                className="hidden"
              />
            </div>

            {project.voiceover ? (
              <div className="p-3 rounded-xl bg-[#141624] border border-[#22273D] space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-white truncate max-w-[180px]">
                    {project.voiceover.filename}
                  </span>
                  <span className="text-[10px] font-mono text-purple-300 bg-purple-500/10 px-1.5 py-0.5 rounded">
                    {formatDuration(project.voiceover.duration)}
                  </span>
                </div>
                {project.voiceover.url && (
                  <audio
                    ref={audioRef}
                    src={project.voiceover.url}
                    onTimeUpdate={handleAudioTimeUpdate}
                    onEnded={() => setIsPlayingAudio(false)}
                    className="w-full h-7 mt-1"
                    controls
                  />
                )}
              </div>
            ) : (
              <div
                onClick={() => voiceoverInputRef.current?.click()}
                className="border-2 border-dashed border-[#22273D] hover:border-purple-500/50 rounded-2xl p-4 text-center cursor-pointer transition-colors"
              >
                <Music className="w-6 h-6 text-gray-500 mx-auto mb-1.5" />
                <p className="text-xs font-semibold text-gray-300">Upload Voiceover Audio</p>
                <p className="text-[10px] text-gray-500 mt-0.5">MP3, WAV, M4A from Voice Studio or files</p>
              </div>
            )}
          </div>

          <div className="pt-2 border-t border-[#1E2235]">
            <div className="flex items-center justify-between mb-2">
              <h2 className="text-xs font-bold uppercase tracking-wider text-gray-300 flex items-center space-x-1.5">
                <ImageIcon className="w-3.5 h-3.5 text-indigo-400" />
                <span>Image Assets ({imageAssets.length})</span>
              </h2>
              <button
                onClick={() => imageInputRef.current?.click()}
                disabled={uploading}
                className="text-[11px] font-semibold text-indigo-400 hover:text-indigo-300 flex items-center space-x-1"
              >
                <Upload className="w-3 h-3" />
                <span>Add Images</span>
              </button>
              <input
                type="file"
                ref={imageInputRef}
                onChange={handleImageUpload}
                accept="image/*"
                multiple
                className="hidden"
              />
            </div>

            {imageAssets.length === 0 ? (
              <div
                onClick={() => imageInputRef.current?.click()}
                className="border-2 border-dashed border-[#22273D] hover:border-indigo-500/50 rounded-2xl p-6 text-center cursor-pointer transition-colors"
              >
                <ImageIcon className="w-7 h-7 text-gray-500 mx-auto mb-1.5" />
                <p className="text-xs font-semibold text-gray-300">Upload Documentary Images</p>
                <p className="text-[10px] text-gray-500 mt-0.5">High-res stills, photos, archival graphics</p>
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-2">
                {imageAssets.map((asset) => (
                  <div
                    key={asset.id}
                    className="group relative rounded-xl overflow-hidden border border-[#22273D] bg-[#141624] aspect-video"
                  >
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={asset.url}
                      alt={asset.filename}
                      className="w-full h-full object-cover group-hover:scale-105 transition-transform"
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent opacity-0 group-hover:opacity-100 transition-opacity flex items-end justify-between p-1.5">
                      <span className="text-[9px] text-white truncate max-w-[80px]">{asset.filename}</span>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDeleteAsset(asset.id);
                        }}
                        className="p-1 rounded bg-red-600/80 hover:bg-red-600 text-white"
                        title="Delete asset"
                      >
                        <Trash2 className="w-2.5 h-2.5" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* PANEL B: CANVAS PREVIEW (6 cols) */}
        <div className="lg:col-span-6 bg-[#07080D] p-4 flex flex-col items-center justify-center relative overflow-hidden">
          {viewMode === "rendered" && latestRenderOutput ? (
            <div className="w-full max-w-2xl flex flex-col items-center">
              <div className="w-full rounded-2xl overflow-hidden border border-purple-500/30 bg-black shadow-2xl aspect-video relative">
                <video
                  src={latestRenderOutput.download_url || latestRenderOutput.url}
                  controls
                  autoPlay
                  className="w-full h-full object-contain"
                />
              </div>
              <div className="w-full mt-3 flex items-center justify-between text-xs text-gray-400">
                <span className="font-semibold text-emerald-400 flex items-center space-x-1">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>Rendered Output: {latestRenderOutput.filename}</span>
                </span>
                <span>
                  {latestRenderOutput.resolution} • {latestRenderOutput.file_size ? `${(latestRenderOutput.file_size / 1024 / 1024).toFixed(1)} MB` : ""}
                </span>
              </div>
            </div>
          ) : (
            <div className="w-full max-w-2xl flex flex-col items-center">
              {/* Aspect Ratio Bounded Screen */}
              <div className="w-full rounded-2xl overflow-hidden border border-[#22273D] bg-black shadow-2xl aspect-video relative flex items-center justify-center">
                {selectedAsset ? (
                  <div className="w-full h-full relative overflow-hidden">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={selectedAsset.url}
                      alt={selectedAsset.filename}
                      className={`w-full h-full object-cover ${isPlayingAudio ? motionCss : ""}`}
                    />
                    <div className="absolute top-3 left-3 bg-black/60 backdrop-blur-sm px-2.5 py-1 rounded-lg border border-white/10 text-[10px] font-semibold text-purple-300">
                      {selectedClip?.motion_type?.toUpperCase().replace("_", " ") || "KEN BURNS"}
                    </div>
                    {selectedScene && (
                      <div className="absolute bottom-0 inset-x-0 bg-gradient-to-t from-black/90 via-black/40 to-transparent p-4">
                        <span className="text-[10px] font-bold text-purple-400 uppercase tracking-widest">
                          Scene {selectedSceneIndex + 1}
                        </span>
                        <h3 className="text-sm font-bold text-white mt-0.5">{selectedScene.title}</h3>
                        {selectedScene.narrative_text && (
                          <p className="text-xs text-gray-300 line-clamp-2 mt-1 italic font-serif">
                            "{selectedScene.narrative_text}"
                          </p>
                        )}
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="text-center p-8 text-gray-500">
                    <Film className="w-10 h-10 mx-auto mb-2 opacity-30" />
                    <p className="text-xs font-semibold">No Timeline Generated Yet</p>
                    <p className="text-[10px] text-gray-600 mt-1">
                      Upload audio and images, then click "Generate Documentary"
                    </p>
                  </div>
                )}
              </div>

              {/* Playback Transport Bar */}
              <div className="w-full mt-3 flex items-center justify-between px-2">
                <div className="flex items-center space-x-3">
                  <button
                    onClick={toggleAudioPlayback}
                    disabled={!project.voiceover}
                    className="w-8 h-8 rounded-full bg-purple-600 hover:bg-purple-500 text-white flex items-center justify-center shadow-lg shadow-purple-600/30 disabled:opacity-40 transition-all"
                  >
                    {isPlayingAudio ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4 ml-0.5" />}
                  </button>
                  <span className="font-mono text-xs text-gray-300">
                    {formatDuration(currentTime)} / {formatDuration(project.total_duration)}
                  </span>
                </div>

                <div className="flex items-center space-x-2 text-xs text-gray-400">
                  <span className="text-[11px] px-2 py-0.5 rounded bg-[#161828] border border-[#23273D]">
                    {selectedClip ? `${selectedClip.duration}s Scene` : "Ready"}
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* PANEL C: SCENE INSPECTOR (3 cols) */}
        <div className="lg:col-span-3 border-l border-[#1E2235] bg-[#0C0D16] p-4 flex flex-col space-y-4 overflow-y-auto max-h-[calc(100vh-16rem)]">
          <div className="flex items-center justify-between pb-2 border-b border-[#1E2235]">
            <h2 className="text-xs font-bold uppercase tracking-wider text-gray-300 flex items-center space-x-1.5">
              <Layers className="w-3.5 h-3.5 text-purple-400" />
              <span>Scene Inspector</span>
            </h2>
            <span className="text-[10px] font-semibold text-purple-400 bg-purple-500/10 px-2 py-0.5 rounded-full">
              {project.scenes.length > 0 ? `${selectedSceneIndex + 1} of ${project.scenes.length}` : "0 Scenes"}
            </span>
          </div>

          {selectedScene && selectedClip ? (
            <div className="space-y-4">
              <div>
                <label className="block text-[11px] font-semibold text-gray-400 mb-1">Scene Title</label>
                <div className="p-2.5 rounded-xl bg-[#141624] border border-[#22273D] text-xs font-semibold text-white">
                  {selectedScene.title}
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-gray-400 mb-1">Narration Segment</label>
                <div className="p-2.5 rounded-xl bg-[#141624] border border-[#22273D] text-xs text-gray-300 italic font-serif leading-relaxed">
                  {selectedScene.narrative_text || "No narrative text analyzed."}
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-gray-400 mb-1">Cinematic Motion (Ken Burns)</label>
                <select
                  value={selectedClip.motion_type}
                  onChange={(e) => handleMotionChange(selectedSceneIndex, e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-[#141624] border border-[#22273D] text-xs text-white focus:outline-none focus:border-purple-500"
                >
                  <option value="zoom_in">Slow Zoom In (Intimacy)</option>
                  <option value="zoom_out">Slow Zoom Out (Reveal)</option>
                  <option value="pan_left">Pan Left (Exploration)</option>
                  <option value="pan_right">Pan Right (Progress)</option>
                  <option value="ken_burns">Classic Ken Burns (Pan + Zoom)</option>
                  <option value="static">Static (Still)</option>
                </select>
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-gray-400 mb-1">Swap Image for Scene</label>
                <div className="grid grid-cols-3 gap-1.5">
                  {imageAssets.map((asset) => (
                    <div
                      key={asset.id}
                      onClick={() => handleSwapAsset(selectedSceneIndex, asset.id)}
                      className={`relative rounded-lg overflow-hidden cursor-pointer aspect-video border transition-all ${
                        selectedClip.asset_id === asset.id
                          ? "border-purple-500 ring-2 ring-purple-500/50"
                          : "border-[#22273D] opacity-60 hover:opacity-100"
                      }`}
                    >
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img src={asset.url} alt={asset.filename} className="w-full h-full object-cover" />
                      {selectedClip.asset_id === asset.id && (
                        <div className="absolute inset-0 bg-purple-600/30 flex items-center justify-center">
                          <Check className="w-3.5 h-3.5 text-white" />
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              <div className="pt-2 border-t border-[#1E2235] text-[10px] text-gray-500 space-y-1">
                <div className="flex justify-between">
                  <span>Start Time:</span>
                  <span className="font-mono text-gray-400">{selectedClip.start_time}s</span>
                </div>
                <div className="flex justify-between">
                  <span>End Time:</span>
                  <span className="font-mono text-gray-400">{selectedClip.end_time}s</span>
                </div>
                <div className="flex justify-between">
                  <span>Duration:</span>
                  <span className="font-mono text-gray-400">{selectedClip.duration}s</span>
                </div>
              </div>
            </div>
          ) : (
            <div className="text-center py-10 text-gray-500 text-xs">
              <Film className="w-8 h-8 mx-auto mb-2 opacity-30" />
              <span>Select a scene from the timeline below to inspect and customize.</span>
            </div>
          )}
        </div>
      </div>

      {/* TIMELINE BOTTOM TRAY */}
      <div className="border-t border-[#1E2235] bg-[#0A0B13] p-4 flex flex-col space-y-2">
        <div className="flex items-center justify-between text-xs text-gray-400">
          <div className="flex items-center space-x-2">
            <Film className="w-3.5 h-3.5 text-purple-400" />
            <span className="font-bold text-gray-200">Synchronized Timeline Track</span>
            <span className="text-[10px] text-gray-500">
              ({project.timeline_clips.length} Clips, {formatDuration(project.total_duration)})
            </span>
          </div>
          <div className="text-[11px] text-gray-400">
            Click any block to jump to that scene
          </div>
        </div>

        {/* Horizontal Timeline Track */}
        <div className="overflow-x-auto pb-2 scrollbar-thin scrollbar-thumb-purple-600">
          <div className="flex items-center space-x-2 min-w-max py-1">
            {project.timeline_clips.length === 0 ? (
              <div className="h-20 w-full min-w-[600px] border border-dashed border-[#22273D] rounded-xl flex items-center justify-center text-xs text-gray-500">
                Timeline is empty. Upload voiceover and images, then click "Generate Documentary".
              </div>
            ) : (
              project.timeline_clips.map((clip, idx) => {
                const isCurrent = idx === selectedSceneIndex;
                const widthPx = Math.max(120, Math.min(260, clip.duration * 28));

                return (
                  <div
                    key={clip.id}
                    onClick={() => seekToScene(idx)}
                    style={{ width: `${widthPx}px` }}
                    className={`h-20 rounded-xl overflow-hidden cursor-pointer relative border transition-all flex flex-col justify-between p-2 shrink-0 ${
                      isCurrent
                        ? "border-purple-500 ring-2 ring-purple-500/50 bg-[#1E1933]"
                        : "border-[#22273D] bg-[#121422] hover:border-gray-500"
                    }`}
                  >
                    {/* Background image preview thumbnail */}
                    {clip.asset && (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img
                        src={clip.asset.url}
                        alt=""
                        className="absolute inset-0 w-full h-full object-cover opacity-20 pointer-events-none"
                      />
                    )}
                    <div className="relative z-10 flex items-center justify-between">
                      <span className="text-[10px] font-bold text-purple-300">
                        #{idx + 1} {clip.motion_type?.replace("_", " ")}
                      </span>
                      <span className="text-[9px] font-mono text-gray-400 bg-black/40 px-1 rounded">
                        {clip.duration}s
                      </span>
                    </div>

                    <div className="relative z-10">
                      <p className="text-[10px] font-medium text-gray-200 truncate">
                        {project.scenes[idx]?.title || `Scene ${idx + 1}`}
                      </p>
                      <span className="text-[8px] font-mono text-gray-500">
                        {clip.start_time}s → {clip.end_time}s
                      </span>
                    </div>
                  </div>
                );
              })
            )}
          </div>

          {/* Audio Master Track */}
          <div className="h-8 w-full min-w-[600px] bg-[#111320] px-3 rounded-lg border border-[#1E2338] flex items-center justify-between text-[10px] text-gray-400">
            <div className="flex items-center space-x-2">
              <Music className="w-3 3 text-indigo-400" />
              <span className="font-semibold text-indigo-300">
                {project.voiceover ? project.voiceover.filename : "No Audio Track"}
              </span>
            </div>
            <div className="flex items-center space-x-1">
              {Array.from({ length: 24 }).map((_, i) => (
                <div
                  key={i}
                  className="w-1 bg-indigo-500/40 rounded-full"
                  style={{ height: `${(Math.sin(i * 0.8) + 1.2) * 8}px` }}
                />
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
