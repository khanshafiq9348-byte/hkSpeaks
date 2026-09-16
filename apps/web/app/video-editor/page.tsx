"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import Navbar from "@/components/Navbar";
import { useAuth } from "@/lib/auth-context";
import { 
  listVideoProjects, 
  createVideoProject, 
  deleteVideoProject, 
  VideoProjectSummary 
} from "@/lib/video-api";
import { 
  Film, 
  Plus, 
  Clock, 
  Layers, 
  Trash2, 
  Sparkles, 
  ArrowRight, 
  Play, 
  Video, 
  CheckCircle2, 
  AlertCircle,
  Loader2
} from "lucide-react";

export default function VideoProjectsPage() {
  const { user, isLoading: authLoading } = useAuth();
  const router = useRouter();

  const [projects, setProjects] = useState<VideoProjectSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // New project modal state
  const [showModal, setShowModal] = useState(false);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [aspectRatio, setAspectRatio] = useState("16:9");
  const [resolution, setResolution] = useState("1080p");
  const [fps, setFps] = useState(30);
  const [submitting, setSubmitting] = useState(false);
  const [modalError, setModalError] = useState<string | null>(null);

  useEffect(() => {
    if (!authLoading && !user) {
      router.push("/login");
      return;
    }
    if (user) {
      loadProjects();
    }
  }, [user, authLoading]);

  async function loadProjects() {
    try {
      setLoading(true);
      setError(null);
      const data = await listVideoProjects();
      setProjects(data);
    } catch (err: any) {
      setError(err?.message || "Failed to load documentary projects");
    } finally {
      setLoading(false);
    }
  }

  async function handleCreateProject(e: React.FormEvent) {
    e.preventDefault();
    const cleanTitle = title.trim();
    if (!cleanTitle) {
      setModalError("Please enter a project title.");
      return;
    }

    try {
      setSubmitting(true);
      setModalError(null);
      const created = await createVideoProject({
        title: cleanTitle,
        description: description.trim(),
        aspect_ratio: aspectRatio,
        resolution: resolution,
        fps: Number(fps) || 30,
      });
      setShowModal(false);
      setTitle("");
      setDescription("");
      router.push(`/video-editor/${created.id}`);
    } catch (err: any) {
      setModalError(err?.message || "Failed to create project");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDeleteProject(id: string, e: React.MouseEvent) {
    e.stopPropagation();
    if (!confirm("Are you sure you want to delete this documentary project?")) return;

    try {
      await deleteVideoProject(id);
      setProjects((prev) => prev.filter((p) => p.id !== id));
    } catch (err: any) {
      alert(err?.message || "Failed to delete project");
    }
  }

  function formatDuration(sec: number) {
    if (!sec || sec <= 0) return "0:00";
    const mins = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    return `${mins}:${s.toString().padStart(2, "0")}`;
  }

  return (
    <div className="min-h-screen bg-[#0A0B10] text-gray-100 flex flex-col">
      <Navbar />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-8">
        {/* Header Section */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-[#1E2235]">
          <div>
            <div className="flex items-center space-x-2">
              <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-purple-500/10 text-purple-400 border border-purple-500/20 uppercase tracking-wide">
                Product 2
              </span>
              <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white flex items-center space-x-2.5">
                <Film className="w-7 h-7 text-purple-400" />
                <span>AI Video Editor & Documentary Studio</span>
              </h1>
            </div>
            <p className="text-sm text-gray-400 mt-1">
              Upload image archives & voiceover audio. Auto-direct dynamic scenes with Ken Burns camera motion and export synchronized 1080p MP4.
            </p>
          </div>

          <button
            onClick={() => {
              setShowModal(true);
              setModalError(null);
            }}
            className="px-4 py-2.5 rounded-xl text-sm font-semibold bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white shadow-lg shadow-purple-600/25 flex items-center justify-center space-x-2 transition-all shrink-0"
          >
            <Plus className="w-4 h-4" />
            <span>New Documentary Project</span>
          </button>
        </div>

        {/* Content Section */}
        {loading ? (
          <div className="py-24 flex flex-col items-center justify-center space-y-3">
            <Loader2 className="w-8 h-8 text-purple-400 animate-spin" />
            <span className="text-sm text-gray-400">Loading your documentary projects...</span>
          </div>
        ) : error ? (
          <div className="py-16 text-center">
            <AlertCircle className="w-10 h-10 text-red-400 mx-auto mb-2" />
            <p className="text-sm text-red-300 mb-4">{error}</p>
            <button
              onClick={loadProjects}
              className="px-4 py-2 rounded-lg text-xs font-semibold bg-[#1C2035] hover:bg-[#252A47] text-gray-200"
            >
              Retry
            </button>
          </div>
        ) : projects.length === 0 ? (
          <div className="py-20 text-center max-w-md mx-auto">
            <div className="w-16 h-16 rounded-2xl bg-[#161828] border border-[#242942] flex items-center justify-center text-purple-400 mx-auto mb-4 shadow-xl">
              <Film className="w-8 h-8" />
            </div>
            <h3 className="text-lg font-bold text-white mb-2">No documentary projects yet</h3>
            <p className="text-xs text-gray-400 mb-6 leading-relaxed">
              Create your first project by uploading visual stills and a voiceover audio track. The Auto-Director engine will synchronize your documentary in seconds.
            </p>
            <button
              onClick={() => {
                setShowModal(true);
                setModalError(null);
              }}
              className="px-5 py-2.5 rounded-xl text-xs font-semibold bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white shadow-md shadow-purple-600/30 inline-flex items-center space-x-2"
            >
              <Plus className="w-4 h-4" />
              <span>Create First Documentary</span>
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5 mt-8">
            {projects.map((proj) => {
              const statusColors = {
                draft: "bg-gray-500/10 text-gray-400 border-gray-500/20",
                ready: "bg-indigo-500/10 text-indigo-400 border-indigo-500/20",
                rendering: "bg-amber-500/10 text-amber-400 border-amber-500/20 animate-pulse",
                completed: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
              }[proj.status] || "bg-gray-500/10 text-gray-400 border-gray-500/20";

              return (
                <div
                  key={proj.id}
                  onClick={() => router.push(`/video-editor/${proj.id}`)}
                  className="group cursor-pointer rounded-2xl bg-[#121422] border border-[#21263D] hover:border-purple-500/50 p-5 transition-all flex flex-col justify-between hover:shadow-xl hover:shadow-purple-950/20 relative"
                >
                  <div>
                    <div className="flex items-center justify-between mb-3">
                      <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full border ${statusColors}`}>
                        {proj.status}
                      </span>
                      <button
                        onClick={(e) => handleDeleteProject(proj.id, e)}
                        title="Delete project"
                        className="p-1.5 rounded-lg text-gray-500 hover:text-red-400 hover:bg-red-500/10 transition-colors"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>

                    <h3 className="font-bold text-base text-white group-hover:text-purple-300 transition-colors line-clamp-1 mb-1">
                      {proj.title}
                    </h3>
                    <p className="text-xs text-gray-400 line-clamp-2 mb-4">
                      {proj.description || "No description provided."}
                    </p>
                  </div>

                  <div className="pt-4 border-t border-[#1C2035] flex items-center justify-between text-xs text-gray-400">
                    <div className="flex items-center space-x-1.5">
                      <Clock className="w-3.5 h-3.5 text-gray-500" />
                      <span>{formatDuration(proj.total_duration)}</span>
                    </div>
                    <div className="flex items-center space-x-1.5 text-purple-400 font-semibold group-hover:translate-x-0.5 transition-transform">
                      <span>Open Studio</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </main>

      {/* New Project Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-md bg-[#121422] border border-[#262C47] rounded-2xl p-6 shadow-2xl relative">
            <h2 className="text-lg font-bold text-white mb-1 flex items-center space-x-2">
              <Film className="w-5 h-5 text-purple-400" />
              <span>New Documentary Project</span>
            </h2>
            {modalError && (
              <div className="mb-4 p-3 rounded-xl bg-red-500/15 border border-red-500/30 text-red-300 text-xs flex items-center space-x-2">
                <AlertCircle className="w-4 h-4 text-red-400 shrink-0" />
                <span>{modalError}</span>
              </div>
            )}

            <form onSubmit={handleCreateProject} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-300 mb-1.5">Project Title</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Rise of Ancient Rome Documentary"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-[#0B0C12] border border-[#242942] text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-purple-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-300 mb-1.5">Description (Optional)</label>
                <textarea
                  rows={2}
                  placeholder="Brief synopsis or documentary topic..."
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="w-full px-3.5 py-2 rounded-xl bg-[#0B0C12] border border-[#242942] text-xs text-gray-100 placeholder-gray-500 focus:outline-none focus:border-purple-500"
                />
              </div>

              <div className="grid grid-cols-3 gap-2.5">
                <div>
                  <label className="block text-xs font-semibold text-gray-300 mb-1.5">Aspect Ratio</label>
                  <select
                    value={aspectRatio}
                    onChange={(e) => setAspectRatio(e.target.value)}
                    className="w-full px-2.5 py-2 rounded-xl bg-[#0B0C12] border border-[#242942] text-xs text-gray-100 focus:outline-none focus:border-purple-500"
                  >
                    <option value="16:9">16:9 (Landscape)</option>
                    <option value="9:16">9:16 (Portrait)</option>
                    <option value="1:1">1:1 (Square)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-gray-300 mb-1.5">Resolution</label>
                  <select
                    value={resolution}
                    onChange={(e) => setResolution(e.target.value)}
                    className="w-full px-2.5 py-2 rounded-xl bg-[#0B0C12] border border-[#242942] text-xs text-gray-100 focus:outline-none focus:border-purple-500"
                  >
                    <option value="1080p">1080p (FHD)</option>
                    <option value="720p">720p (HD)</option>
                    <option value="4k">4K (UHD)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-gray-300 mb-1.5">Frame Rate</label>
                  <select
                    value={fps}
                    onChange={(e) => setFps(Number(e.target.value) || 30)}
                    className="w-full px-2.5 py-2 rounded-xl bg-[#0B0C12] border border-[#242942] text-xs text-gray-100 focus:outline-none focus:border-purple-500"
                  >
                    <option value={30}>30 fps</option>
                    <option value={24}>24 fps (Cinema)</option>
                    <option value={60}>60 fps (Smooth)</option>
                  </select>
                </div>
              </div>

              <div className="flex items-center justify-end space-x-3 pt-4 border-t border-[#1E2235]">
                <button
                  type="button"
                  onClick={() => {
                    setShowModal(false);
                    setModalError(null);
                  }}
                  className="px-4 py-2 rounded-xl text-xs font-semibold text-gray-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting || !title.trim()}
                  className="px-5 py-2 rounded-xl text-xs font-semibold bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white disabled:opacity-50 transition-all shadow-md shadow-purple-600/30 flex items-center space-x-1.5"
                >
                  {submitting && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  <span>Create Project</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
