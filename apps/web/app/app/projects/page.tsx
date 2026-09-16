"use client";

import React, { useState, useEffect } from "react";
import { apiClient } from "@/lib/api";
import { FolderKanban, Plus, FileText, Trash2, Edit3, ArrowRight, Save, Loader2 } from "lucide-react";
import { useRouter } from "next/navigation";

interface Document {
  id: string;
  title: string;
  content: string;
  language: string;
  version: number;
}

interface Project {
  id: string;
  name: string;
  description: string;
  documents: Document[];
  updated_at: string;
}

export default function ProjectsPage() {
  const router = useRouter();
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  const [activeDoc, setActiveDoc] = useState<Document | null>(null);
  const [docContent, setDocContent] = useState("");
  const [docTitle, setDocTitle] = useState("");
  const [isSaving, setIsSaving] = useState(false);

  // New project modal state
  const [isCreating, setIsCreating] = useState(false);
  const [newProjName, setNewProjName] = useState("");
  const [newProjDesc, setNewProjDesc] = useState("");

  useEffect(() => {
    loadProjects();
  }, []);

  const loadProjects = async () => {
    try {
      const data = await apiClient<Project[]>("/projects");
      setProjects(data);
      if (data.length > 0 && !selectedProject) {
        setSelectedProject(data[0]);
        if (data[0].documents?.length > 0) {
          selectDocument(data[0].documents[0]);
        }
      }
    } catch {
      // ignore
    }
  };

  const selectDocument = (doc: Document) => {
    setActiveDoc(doc);
    setDocContent(doc.content);
    setDocTitle(doc.title);
  };

  const handleSaveDoc = async () => {
    if (!selectedProject || !activeDoc) return;
    setIsSaving(true);
    try {
      await apiClient(`/projects/${selectedProject.id}/documents/${activeDoc.id}`, {
        method: "PUT",
        body: JSON.stringify({
          title: docTitle,
          content: docContent,
        }),
      });
      await loadProjects();
    } catch {
      // ignore
    } finally {
      setIsSaving(false);
    }
  };

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newProjName) return;
    try {
      const p = await apiClient<Project>("/projects", {
        method: "POST",
        body: JSON.stringify({ name: newProjName, description: newProjDesc }),
      });
      setIsCreating(false);
      setNewProjName("");
      setNewProjDesc("");
      await loadProjects();
      setSelectedProject(p);
      if (p.documents?.length > 0) {
        selectDocument(p.documents[0]);
      }
    } catch {
      // ignore
    }
  };

  const handleDeleteProject = async (id: string) => {
    if (!confirm("Are you sure you want to delete this project?")) return;
    try {
      await apiClient(`/projects/${id}`, { method: "DELETE" });
      setSelectedProject(null);
      setActiveDoc(null);
      await loadProjects();
    } catch {
      // ignore
    }
  };

  return (
    <div className="flex-1 flex flex-col min-w-0 h-full overflow-y-auto bg-[#090A0F] text-gray-100">
      <main className="max-w-7xl w-full mx-auto p-6 grid grid-cols-1 md:grid-cols-12 gap-6 flex-1">
        {/* Projects & Documents Sidebar (4 cols) */}
        <div className="md:col-span-4 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold text-white flex items-center space-x-2">
              <FolderKanban className="w-5 h-5 text-indigo-400" />
              <span>Projects</span>
            </h2>
            <button
              onClick={() => setIsCreating(true)}
              className="p-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white transition-colors"
              title="New Project"
            >
              <Plus className="w-4 h-4" />
            </button>
          </div>

          {/* Project List */}
          <div className="space-y-2">
            {projects.map((p) => {
              const isSelected = selectedProject?.id === p.id;
              return (
                <div
                  key={p.id}
                  onClick={() => {
                    setSelectedProject(p);
                    if (p.documents?.length > 0) {
                      selectDocument(p.documents[0]);
                    } else {
                      setActiveDoc(null);
                    }
                  }}
                  className={`p-3.5 rounded-xl cursor-pointer transition-all border ${
                    isSelected
                      ? "bg-[#161928] border-indigo-500/40 shadow-sm"
                      : "bg-[#12141F] border-[#202436] hover:bg-[#151726]"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-semibold text-gray-100">{p.name}</h3>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDeleteProject(p.id);
                      }}
                      className="text-gray-500 hover:text-red-400 p-1"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                  {p.description && (
                    <p className="text-xs text-gray-400 mt-1 line-clamp-1">{p.description}</p>
                  )}
                  <span className="text-[11px] text-gray-500 mt-2 block">
                    {p.documents?.length || 0} scripts • Updated recently
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Script Editor Pane (8 cols) */}
        <div className="md:col-span-8 flex flex-col">
          {selectedProject && activeDoc ? (
            <div className="p-6 rounded-2xl bg-[#12141F] border border-[#202436] flex-1 flex flex-col shadow-xl space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-[#1E2235]">
                <input
                  type="text"
                  value={docTitle}
                  onChange={(e) => setDocTitle(e.target.value)}
                  className="bg-transparent font-bold text-lg text-white focus:outline-none"
                />

                <div className="flex items-center space-x-2">
                  <button
                    onClick={handleSaveDoc}
                    disabled={isSaving}
                    className="flex items-center space-x-1.5 px-3.5 py-1.5 rounded-lg bg-[#1A1D2E] hover:bg-[#22273D] text-gray-200 text-xs font-semibold border border-[#2B314C] transition-colors"
                  >
                    {isSaving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />}
                    <span>Save</span>
                  </button>

                  <button
                    onClick={() => {
                      if (activeDoc) {
                        router.push(`/app/studio?text=${encodeURIComponent(docContent)}&docId=${activeDoc.id}`);
                      } else {
                        router.push("/app/studio");
                      }
                    }}
                    className="flex items-center space-x-1.5 px-3.5 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-md shadow-indigo-600/30 transition-all"
                  >
                    <span>Synthesize in Studio</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>

              <textarea
                value={docContent}
                onChange={(e) => setDocContent(e.target.value)}
                placeholder="Write your chapter or scene script here..."
                className="w-full flex-1 bg-transparent text-gray-100 placeholder-gray-600 resize-none focus:outline-none text-base leading-relaxed"
                rows={16}
              />

              <div className="pt-3 border-t border-[#1E2235] flex items-center justify-between text-xs text-gray-400 font-mono">
                <span>{docContent.trim().length} characters</span>
                <span>Version {activeDoc.version}</span>
              </div>
            </div>
          ) : (
            <div className="p-12 rounded-2xl bg-[#12141F] border border-[#202436] flex-1 flex flex-col items-center justify-center text-center space-y-3 text-gray-500">
              <FileText className="w-10 h-10 opacity-30 text-gray-400" />
              <p className="text-sm">Select a project and script to view or edit.</p>
            </div>
          )}
        </div>
      </main>

      {/* New Project Modal */}
      {isCreating && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm">
          <div className="w-full max-w-md bg-[#0F111C] border border-[#23273D] rounded-2xl p-5 shadow-2xl">
            <h3 className="font-bold text-base text-white mb-3">Create New Project</h3>
            <form onSubmit={handleCreateProject} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-300 mb-1">Project Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Science Fiction Audiobook"
                  value={newProjName}
                  onChange={(e) => setNewProjName(e.target.value)}
                  className="w-full px-3.5 py-2 bg-[#141624] border border-[#23273D] rounded-xl text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-indigo-500"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-300 mb-1">Description (Optional)</label>
                <input
                  type="text"
                  placeholder="Brief synopsis or project notes"
                  value={newProjDesc}
                  onChange={(e) => setNewProjDesc(e.target.value)}
                  className="w-full px-3.5 py-2 bg-[#141624] border border-[#23273D] rounded-xl text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-indigo-500"
                />
              </div>
              <div className="flex items-center justify-end space-x-2 pt-2">
                <button
                  type="button"
                  onClick={() => setIsCreating(false)}
                  className="px-4 py-2 text-xs font-semibold text-gray-400 hover:text-gray-200 rounded-xl bg-[#141624]"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-500 rounded-xl shadow-md shadow-indigo-600/30"
                >
                  Create Project
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
