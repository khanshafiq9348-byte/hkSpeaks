"use client";

import React, { useState, useEffect, useRef } from "react";
import { 
  X, 
  Search, 
  Upload, 
  Volume2, 
  Play, 
  Pause, 
  Trash2, 
  Check, 
  AlertCircle, 
  Loader2
} from "lucide-react";
import { apiClient } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { Voice } from "./VoiceSelectorModal";

export interface UploadedVoiceModalProps {
  isOpen: boolean;
  onClose: () => void;
  selectedVoiceId?: string;
  onSelectVoice: (voice: Voice) => void;
  onSuccess?: (voice?: Voice) => void;
}

export interface UserCloneStatus {
  has_clone?: boolean;
  voice: Voice | null;
  can_clone: boolean;
  max_clones: number;
  saved_count: number;
}

export default function UploadedVoiceModal({
  isOpen,
  onClose,
  selectedVoiceId,
  onSelectVoice,
  onSuccess,
}: UploadedVoiceModalProps) {
  const { user } = useAuth();
  const [search, setSearch] = useState("");
  const [voiceName, setVoiceName] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [consentConfirmed, setConsentConfirmed] = useState(false);
  const [cloneStatus, setCloneStatus] = useState<UserCloneStatus>({
    voice: null,
    can_clone: true,
    max_clones: 1,
    saved_count: 0,
  });
  const [isLoading, setIsLoading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [playingAudio, setPlayingAudio] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    if (isOpen) {
      loadUserCloneStatus();
    } else {
      if (audioRef.current) {
        audioRef.current.pause();
      }
      setPlayingAudio(null);
      setError(null);
    }
  }, [isOpen, user]);

  const loadUserCloneStatus = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await apiClient<UserCloneStatus>("/voices/user-clone");
      setCloneStatus({
        voice: data.voice || null,
        can_clone: true,
        max_clones: 1,
        saved_count: data.voice ? 1 : 0,
      });
    } catch {
      setCloneStatus((prev) => ({
        ...prev,
        can_clone: true,
        max_clones: 1,
      }));
    } finally {
      setIsLoading(false);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selected = e.target.files[0];
      if (selected.size > 10 * 1024 * 1024) {
        setError("File size exceeds 10 MB limit.");
        return;
      }
      setFile(selected);
      setError(null);
      if (!voiceName) {
        const baseName = selected.name.replace(/\.[^/.]+$/, "").replace(/[-_]/g, " ");
        setVoiceName(baseName.charAt(0).toUpperCase() + baseName.slice(1));
      }
    }
  };

  const handleSaveVoice = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      setError("Please select an audio recording (.mp3 or .wav) to upload.");
      return;
    }
    if (!consentConfirmed) {
      setError("Please confirm voice authorization and acceptable use terms.");
      return;
    }

    setIsUploading(true);
    setError(null);

    const formData = new FormData();
    formData.append("name", voiceName.trim() || "My Uploaded Voice");
    formData.append("description", "");
    formData.append("gender", "neutral");
    formData.append("language", "en");
    formData.append("consent_confirmed", "true");
    formData.append("rights_confirmed", "true");
    formData.append("audio_file", file);

    try {
      const createdVoice = await apiClient<Voice>("/voices/clone", {
        method: "POST",
        body: formData,
      });

      setFile(null);
      setVoiceName("");
      setConsentConfirmed(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }

      const clonedVoiceObj: Voice = {
        ...createdVoice,
        type: "cloned",
        voice_type: "clone",
        tier: "custom"
      };

      // Immediately reflect clone in this same selection screen
      setCloneStatus({
        voice: clonedVoiceObj,
        can_clone: true,
        max_clones: 1,
        saved_count: 1,
      });

      // Select that exact cloned voice and persist
      if (typeof window !== "undefined") {
        localStorage.setItem("hk_selected_voice_id", createdVoice.id);
        localStorage.setItem("hk_selected_voice_type", "cloned");
        localStorage.setItem("hk_selected_voice_name", createdVoice.name);
        localStorage.setItem("hk_selected_voice_obj", JSON.stringify(clonedVoiceObj));
      }

      onSelectVoice(clonedVoiceObj);
      if (onSuccess) {
        onSuccess(clonedVoiceObj);
      }
      onClose();
    } catch (err: any) {
      setError(err.message || "Failed to upload and clone voice.");
    } finally {
      setIsUploading(false);
    }
  };

  const handleDeleteVoice = async (voiceId: string) => {
    if (!confirm("Are you sure you want to delete your uploaded voice clone?")) return;
    setIsDeleting(true);
    try {
      await apiClient(`/voices/${voiceId}`, { method: "DELETE" });
      setCloneStatus({
        voice: null,
        can_clone: true,
        max_clones: 1,
        saved_count: 0,
      });
      if (typeof window !== "undefined") {
        const storedId = localStorage.getItem("hk_selected_voice_id");
        if (storedId === voiceId) {
          localStorage.removeItem("hk_selected_voice_id");
          localStorage.removeItem("hk_selected_voice_type");
          localStorage.removeItem("hk_selected_voice_name");
          localStorage.removeItem("hk_selected_voice_obj");
        }
      }
      await loadUserCloneStatus();
    } catch (err: any) {
      setError(err.message || "Failed to delete custom voice.");
    } finally {
      setIsDeleting(false);
    }
  };

  const togglePlayPreview = (url?: string, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    if (!url) return;
    if (playingAudio === url) {
      if (audioRef.current) audioRef.current.pause();
      setPlayingAudio(null);
    } else {
      if (audioRef.current) audioRef.current.pause();
      const a = new Audio(url);
      audioRef.current = a;
      a.play().catch(() => {});
      setPlayingAudio(url);
      a.onended = () => setPlayingAudio(null);
    }
  };

  const handleSelectClonedVoice = (voice: Voice) => {
    const clonedVoiceObj: Voice = {
      ...voice,
      type: "cloned",
      voice_type: "clone",
      tier: "custom"
    };
    if (typeof window !== "undefined") {
      localStorage.setItem("hk_selected_voice_id", voice.id);
      localStorage.setItem("hk_selected_voice_type", "cloned");
      localStorage.setItem("hk_selected_voice_name", voice.name);
      localStorage.setItem("hk_selected_voice_obj", JSON.stringify(clonedVoiceObj));
    }
    onSelectVoice(clonedVoiceObj);
    if (onSuccess) {
      onSuccess(clonedVoiceObj);
    }
    onClose();
  };

  if (!isOpen) return null;

  const currentVoice = cloneStatus.voice;
  const isSelected = currentVoice && selectedVoiceId === currentVoice.id;
  const matchesSearch =
    !search ||
    (currentVoice && currentVoice.name.toLowerCase().includes(search.toLowerCase()));

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-150">
      <div className="w-full max-w-3xl bg-white border border-gray-200 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Modal Header */}
        <div className="px-6 py-5 border-b border-gray-100 flex items-start justify-between">
          <div>
            <h3 className="text-xl font-bold text-gray-900 tracking-tight">Select uploaded voice</h3>
            <p className="text-xs text-gray-500 mt-1">
              Upload a recording, then choose which of your private voices speaks this script.
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg bg-gray-50 hover:bg-gray-100 text-gray-400 hover:text-gray-700 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Search Bar */}
        <div className="p-4 bg-white border-b border-gray-100">
          <div className="relative">
            <Search className="w-4 h-4 text-gray-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search your voices..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-10 pr-4 py-2 bg-white border border-gray-200 rounded-xl text-sm text-gray-800 placeholder-gray-400 focus:outline-none focus:border-indigo-500 transition-colors"
            />
          </div>
        </div>

        {/* ADD A VOICE Section */}
        <div className="p-5 border-b border-gray-100 bg-gray-50/60 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-gray-500 tracking-wider uppercase">
              ADD A VOICE
            </span>
            <span className="text-xs font-semibold text-gray-600">
              {cloneStatus.saved_count} of {cloneStatus.max_clones} saved
            </span>
          </div>

          <div className="p-2.5 rounded-xl bg-teal-50 border border-teal-200/60 text-xs text-teal-800 flex items-center justify-between">
            <span>Each account includes 1 active cloned voice. Uploading a new recording will replace your previous clone.</span>
          </div>

          {/* Input Form Row */}
          <form onSubmit={handleSaveVoice} className="space-y-3">
            <div className="grid grid-cols-1 sm:grid-cols-12 gap-2.5">
              {/* Voice Name Input */}
              <div className="sm:col-span-5">
                <input
                  type="text"
                  placeholder="Voice name (optional)"
                  value={voiceName}
                  onChange={(e) => setVoiceName(e.target.value)}
                  disabled={isUploading}
                  className="w-full px-3.5 py-2.5 bg-white border border-gray-200 rounded-xl text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:border-indigo-500 disabled:opacity-50"
                />
              </div>

              {/* Upload File Button */}
              <div className="sm:col-span-4">
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="audio/mp3,audio/wav,audio/mpeg,audio/m4a"
                  onChange={handleFileChange}
                  disabled={isUploading}
                  className="hidden"
                  id="voice-upload-file-input"
                />
                <label
                  htmlFor="voice-upload-file-input"
                  className={`w-full px-3.5 py-2.5 rounded-xl border border-gray-200 bg-white hover:bg-gray-50 text-sm text-gray-700 cursor-pointer flex items-center justify-center space-x-2 transition-colors overflow-hidden ${
                    isUploading ? "opacity-50 cursor-not-allowed" : ""
                  }`}
                >
                  <Upload className="w-4 h-4 text-gray-400 shrink-0" />
                  <span className="truncate">
                    {file ? file.name : "Upload .mp3 or .wav (max 10 MB)"}
                  </span>
                </label>
              </div>

              {/* Save Voice Button */}
              <div className="sm:col-span-3">
                <button
                  type="submit"
                  disabled={!file || !consentConfirmed || isUploading}
                  className="w-full px-4 py-2.5 rounded-xl bg-white hover:bg-gray-100 border border-gray-300 disabled:opacity-50 disabled:cursor-not-allowed text-gray-900 font-semibold text-sm transition-all shadow-sm flex items-center justify-center space-x-1.5"
                >
                  {isUploading ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin text-teal-600" />
                      <span>Saving...</span>
                    </>
                  ) : (
                    <span>Save voice</span>
                  )}
                </button>
              </div>
            </div>

            {/* Required Consent / Rights Confirmation Checkbox */}
            <div className="pt-1 flex items-start space-x-2">
              <input
                id="consent-checkbox-modal"
                type="checkbox"
                checked={consentConfirmed}
                onChange={(e) => setConsentConfirmed(e.target.checked)}
                className="mt-0.5 h-4 w-4 rounded border-gray-300 text-teal-600 focus:ring-teal-500 cursor-pointer"
              />
              <label htmlFor="consent-checkbox-modal" className="text-xs text-gray-600 cursor-pointer select-none">
                I declare that I own this voice or possess express rights to clone it, and agree to the Acceptable Use Policy.
              </label>
            </div>

            {error && (
              <div className="p-2.5 rounded-xl bg-red-50 border border-red-200 text-xs text-red-600 flex items-center space-x-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}
          </form>

          {/* Showing Counter Row */}
          <div className="pt-2 flex items-center space-x-2 text-xs text-gray-500">
            <Volume2 className="w-4 h-4 text-gray-400" />
            <span>
              Showing {currentVoice && matchesSearch ? 1 : 0} of {cloneStatus.max_clones} uploaded voices
            </span>
          </div>
        </div>

        {/* Voices List / Empty State */}
        <div className="p-6 overflow-y-auto flex-1 flex flex-col justify-center bg-white">
          {isLoading ? (
            <div className="flex flex-col items-center justify-center py-12 space-y-3 text-gray-400">
              <Loader2 className="w-8 h-8 animate-spin text-teal-600" />
              <p className="text-sm">Loading your uploaded voice...</p>
            </div>
          ) : currentVoice && matchesSearch ? (
            <div 
              onClick={() => handleSelectClonedVoice(currentVoice)}
              className="p-4 rounded-xl bg-white border border-gray-200 hover:border-teal-500/50 hover:shadow-md transition-all flex items-center justify-between cursor-pointer group"
            >
              <div className="flex items-center space-x-3.5">
                <button
                  type="button"
                  onClick={(e) => togglePlayPreview(currentVoice.preview_audio_url, e)}
                  disabled={!currentVoice.preview_audio_url}
                  className="w-10 h-10 rounded-xl bg-teal-50 hover:bg-teal-100 border border-teal-200 text-teal-700 flex items-center justify-center transition-colors shrink-0"
                  title="Preview audio sample"
                >
                  {playingAudio === currentVoice.preview_audio_url ? (
                    <Pause className="w-4 h-4 fill-current" />
                  ) : (
                    <Play className="w-4 h-4 fill-current ml-0.5" />
                  )}
                </button>

                <div>
                  <div className="flex items-center space-x-2">
                    <span className="font-bold text-base text-gray-900 group-hover:text-teal-600 transition-colors">
                      {currentVoice.name}
                    </span>
                    <span className="px-2 py-0.5 text-[10px] font-bold rounded-md bg-teal-50 text-teal-700 border border-teal-200">
                      Your Cloned Voice
                    </span>
                    <span className="px-2 py-0.5 text-[10px] font-bold rounded-md bg-gray-100 text-gray-600 border border-gray-200">
                      1 of 1 saved
                    </span>
                  </div>
                  <p className="text-xs text-gray-500 mt-0.5">
                    Private custom neural voice clone • Click to select for TTS
                  </p>
                </div>
              </div>

              <div className="flex items-center space-x-2.5">
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDeleteVoice(currentVoice.id);
                  }}
                  disabled={isDeleting}
                  title="Delete voice clone"
                  className="p-2 rounded-lg text-gray-400 hover:text-red-600 hover:bg-red-50 border border-transparent hover:border-red-100 transition-colors"
                >
                  <Trash2 className="w-4 h-4" />
                </button>

                {isSelected ? (
                  <span className="px-3.5 py-1.5 rounded-lg bg-teal-600 text-white text-xs font-semibold flex items-center space-x-1.5 shadow-sm">
                    <Check className="w-3.5 h-3.5" />
                    <span>Selected</span>
                  </span>
                ) : (
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleSelectClonedVoice(currentVoice);
                    }}
                    className="px-4 py-1.5 rounded-lg bg-gray-900 hover:bg-black text-white text-xs font-semibold shadow-sm transition-colors"
                  >
                    Select voice
                  </button>
                )}
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-12 text-center space-y-2">
              <div className="w-12 h-12 rounded-2xl bg-gray-100 border border-gray-200 flex items-center justify-center text-gray-400 mb-2">
                <Volume2 className="w-6 h-6" />
              </div>
              <h4 className="text-sm font-bold text-gray-900">No uploaded voices yet.</h4>
              <p className="text-xs text-gray-500 max-w-sm">
                Upload a recording above to create your 1 custom voice clone.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
