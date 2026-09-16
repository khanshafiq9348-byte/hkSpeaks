"use client";

import React, { useState, useEffect, useMemo, useRef } from "react";
import { 
  Search, 
  X, 
  Volume2, 
  Crown, 
  Sparkles, 
  Check, 
  Lock, 
  UserCheck, 
  ArrowRight, 
  Upload, 
  Play, 
  Pause, 
  Globe, 
  Layers, 
  Cpu, 
  CheckCircle2,
  RotateCcw
} from "lucide-react";
import Link from "next/link";
import { API_BASE_URL } from "@/lib/api";
import UploadedVoiceModal from "./UploadedVoiceModal";

export interface Voice {
  id: string;
  name: string;
  slug?: string;
  description: string;
  language: string;
  locale: string;
  accent: string;
  gender: string;
  style: string;
  styles?: string[];
  tier: "free" | "standard" | "premium" | "ultra" | "custom" | string;
  type?: "cloned" | "library" | string;
  voice_type?: "library" | "clone";
  preview_audio_url?: string;
  is_public: boolean;
  provider_voice_id?: string;
  model?: string;
  provider?: string;
  owner_user_id?: string;
  created_at?: string;
}

interface VoiceSelectorModalProps {
  isOpen: boolean;
  onClose: () => void;
  voices: Voice[];
  selectedVoiceId: string;
  onSelectVoice: (voice: Voice) => void;
  userCanPremium?: boolean;
  initialCategory?: string;
}

const LANGUAGE_NAMES: Record<string, string> = {
  en: "English",
  es: "Spanish",
  fr: "French",
  de: "German",
  it: "Italian",
  pt: "Portuguese",
  hi: "Hindi",
  ar: "Arabic",
  ur: "Urdu",
  tr: "Turkish",
  ja: "Japanese",
  ko: "Korean",
  zh: "Chinese",
  ru: "Russian",
  nl: "Dutch",
  pl: "Polish",
  id: "Indonesian",
  vi: "Vietnamese",
  th: "Thai",
  sv: "Swedish",
  da: "Danish",
  fi: "Finnish",
  no: "Norwegian",
  el: "Greek",
  he: "Hebrew",
  cs: "Czech",
  hu: "Hungarian",
  ro: "Romanian",
  uk: "Ukrainian",
  mr: "Marathi",
  ta: "Tamil",
  te: "Telugu",
  bn: "Bengali",
  gu: "Gujarati",
  kn: "Kannada",
  ml: "Malayalam",
  pa: "Punjabi",
};

export const STYLE_OPTIONS = [
  { id: "all", label: "All Styles" },
  { id: "Documentary", label: "Documentary" },
  { id: "Storytelling", label: "Storytelling" },
  { id: "Cinematic", label: "Cinematic" },
  { id: "Narration", label: "Narration" },
  { id: "News", label: "News" },
  { id: "Conversational", label: "Conversational" },
  { id: "Character", label: "Character" },
  { id: "Educational", label: "Educational" },
  { id: "Commercial", label: "Commercial" },
];

export default function VoiceSelectorModal({
  isOpen,
  onClose,
  voices,
  selectedVoiceId,
  onSelectVoice,
  userCanPremium = true,
  initialCategory,
}: VoiceSelectorModalProps) {
  // State
  const [activeCategoryTab, setActiveCategoryTab] = useState<string>("all");
  const [search, setSearch] = useState("");
  const [selectedProvider, setSelectedProvider] = useState<string>("all");
  const [selectedStyle, setSelectedStyle] = useState<string>("all");
  const [selectedLanguage, setSelectedLanguage] = useState<string>("all");
  const [selectedTier, setSelectedTier] = useState<string>("all");

  // Audio Playback State
  const [playingVoiceId, setPlayingVoiceId] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  // Submodal for Cloned Voice Creation
  const [isCloneModalOpen, setIsCloneModalOpen] = useState(false);

  // Synchronize initial category preset
  useEffect(() => {
    if (!isOpen) {
      if (audioRef.current) {
        audioRef.current.pause();
      }
      setPlayingVoiceId(null);
      return;
    }

    if (initialCategory === "clone") {
      setActiveCategoryTab("clone");
      setSelectedTier("custom");
      setSelectedProvider("all");
      return;
    }
    if (initialCategory === "premium") {
      setActiveCategoryTab("premium");
      setSelectedTier("premium");
      setSelectedProvider("all");
      return;
    }
    if (initialCategory === "elevenlabs") {
      setActiveCategoryTab("elevenlabs");
      setSelectedProvider("elevenlabs");
      setSelectedTier("all");
      return;
    }
    if (initialCategory === "edge") {
      setActiveCategoryTab("edge");
      setSelectedProvider("edge");
      setSelectedTier("all");
      return;
    }
    if (initialCategory === "library") {
      setActiveCategoryTab("library");
      setSelectedTier("all");
      setSelectedProvider("all");
      return;
    }

    // Default to preserving current category tab
    const current = voices.find((v) => v.id === selectedVoiceId);
    if (current && (current.tier === "custom" || current.voice_type === "clone" || Boolean(current.owner_user_id))) {
      setActiveCategoryTab("clone");
    } else {
      setActiveCategoryTab("all");
    }
  }, [isOpen, initialCategory, selectedVoiceId, voices]);

  // Clean up audio on unmount
  useEffect(() => {
    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
      }
    };
  }, []);

  // Compute unique languages available
  const availableLanguages = useMemo(() => {
    const langSet = new Set<string>();
    voices.forEach((v) => {
      if (v.language) langSet.add(v.language.toLowerCase());
    });
    return Array.from(langSet).sort();
  }, [voices]);

  // Compute unique providers available
  const availableProviders = useMemo(() => {
    const pSet = new Set<string>();
    voices.forEach((v) => {
      if (v.provider) pSet.add(v.provider.toLowerCase());
    });
    return Array.from(pSet).sort();
  }, [voices]);

  // Helper to test if a voice is cloned
  const isClonedVoice = (v: Voice): boolean => {
    return v.tier === "custom" || v.voice_type === "clone" || v.type === "cloned" || Boolean(v.owner_user_id);
  };

  // Filtered voices
  const filteredVoices = useMemo(() => {
    return voices.filter((v) => {
      const isClone = isClonedVoice(v);

      // Category Tab filter
      if (activeCategoryTab === "clone" && !isClone) return false;
      if (activeCategoryTab === "library" && isClone) return false;
      if (activeCategoryTab === "premium" && !(v.tier === "premium" || v.tier === "ultra")) return false;
      if (activeCategoryTab === "edge" && !(v.provider === "edge" || v.slug?.includes("neural"))) return false;
      if (activeCategoryTab === "elevenlabs" && v.provider !== "elevenlabs") return false;

      // Provider filter
      if (selectedProvider !== "all") {
        if (selectedProvider === "cloned") {
          if (!isClone) return false;
        } else if (v.provider?.toLowerCase() !== selectedProvider.toLowerCase()) {
          return false;
        }
      }

      // Language filter
      if (selectedLanguage !== "all") {
        if (v.language?.toLowerCase() !== selectedLanguage.toLowerCase()) {
          return false;
        }
      }

      // Tier/Type filter
      if (selectedTier !== "all") {
        if (selectedTier === "custom" || selectedTier === "cloned") {
          if (!isClone) return false;
        } else if (v.tier?.toLowerCase() !== selectedTier.toLowerCase()) {
          return false;
        }
      }

      // Style filter
      if (selectedStyle !== "all") {
        const sTarget = selectedStyle.toLowerCase();
        const vStyles = (v.styles || []).map((s: string) => s.toLowerCase());
        const matchesStyleTag = vStyles.some((s: string) => s.includes(sTarget)) || (v.style || "").toLowerCase().includes(sTarget);
        if (!matchesStyleTag) return false;
      }

      // Search query filter (matches name, language, locale, accent, provider, style, description)
      if (search.trim()) {
        const q = search.toLowerCase().trim();
        const langFriendly = LANGUAGE_NAMES[v.language?.toLowerCase()] || "";
        const matches =
          v.name.toLowerCase().includes(q) ||
          v.accent?.toLowerCase().includes(q) ||
          v.style?.toLowerCase().includes(q) ||
          (v.styles && v.styles.some((s) => s.toLowerCase().includes(q))) ||
          v.language?.toLowerCase().includes(q) ||
          v.locale?.toLowerCase().includes(q) ||
          langFriendly.toLowerCase().includes(q) ||
          v.provider?.toLowerCase().includes(q) ||
          v.description?.toLowerCase().includes(q) ||
          v.gender?.toLowerCase().includes(q);
        if (!matches) return false;
      }

      return true;
    });
  }, [voices, activeCategoryTab, selectedProvider, selectedLanguage, selectedTier, selectedStyle, search]);

  // Audio preview handler
  const handlePlayPreview = (voiceId: string, customUrl?: string) => {
    if (playingVoiceId === voiceId) {
      // Toggle pause if already playing
      if (audioRef.current) {
        audioRef.current.pause();
      }
      setPlayingVoiceId(null);
      return;
    }

    if (audioRef.current) {
      audioRef.current.pause();
    }

    // Determine preview URL
    const targetUrl = customUrl || `${API_BASE_URL}/voices/${voiceId}/preview`;
    const audio = new Audio(targetUrl);
    audioRef.current = audio;

    setPlayingVoiceId(voiceId);
    audio.play().catch((err) => {
      console.warn("Audio preview playback failed:", err);
      setPlayingVoiceId(null);
    });

    audio.onended = () => {
      setPlayingVoiceId(null);
    };
    audio.onerror = () => {
      setPlayingVoiceId(null);
    };
  };

  // Voice tap handler (Selects voice, plays preview, updates storage & state)
  const handleVoiceTap = (voice: Voice) => {
    const isClone = isClonedVoice(voice);

    const voiceType: "cloned" | "library" = isClone ? "cloned" : "library";
    const voiceObj: Voice = {
      ...voice,
      type: voiceType,
      voice_type: isClone ? "clone" : "library",
      tier: isClone ? "custom" : voice.tier,
    };

    // 1. Select voice in Studio immediately
    onSelectVoice(voiceObj);

    // 2. Persist selection to localStorage
    if (typeof window !== "undefined") {
      localStorage.setItem("hk_selected_voice_id", voice.id);
      localStorage.setItem("hk_selected_voice_type", voiceType);
      localStorage.setItem("hk_selected_voice_name", voice.name);
      localStorage.setItem("hk_selected_voice_obj", JSON.stringify(voiceObj));
    }

    // 3. Play audio preview on tap
    handlePlayPreview(voice.id, voice.preview_audio_url);
  };

  const handleResetFilters = () => {
    setActiveCategoryTab("all");
    setSearch("");
    setSelectedProvider("all");
    setSelectedStyle("all");
    setSelectedLanguage("all");
    setSelectedTier("all");
  };

  const getTierBadge = (tier: string, isClone: boolean) => {
    if (isClone || tier === "custom") {
      return (
        <span className="px-2 py-0.5 text-[10px] font-bold rounded-full bg-teal-500/15 text-teal-300 border border-teal-500/30 flex items-center space-x-1">
          <UserCheck className="w-3 h-3 text-teal-400" />
          <span>Your Clone</span>
        </span>
      );
    }
    switch (tier) {
      case "free":
        return <span className="px-2 py-0.5 text-[10px] font-semibold rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">Free</span>;
      case "standard":
        return <span className="px-2 py-0.5 text-[10px] font-semibold rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20">Standard</span>;
      case "premium":
        return (
          <span className="px-2 py-0.5 text-[10px] font-semibold rounded-full bg-purple-500/15 text-purple-300 border border-purple-500/30 flex items-center space-x-1">
            <Crown className="w-3 h-3 text-purple-400" />
            <span>Premium</span>
          </span>
        );
      case "ultra":
        return (
          <span className="px-2 py-0.5 text-[10px] font-semibold rounded-full bg-amber-500/15 text-amber-300 border border-amber-500/30 flex items-center space-x-1">
            <Sparkles className="w-3 h-3 text-amber-400" />
            <span>Ultra</span>
          </span>
        );
      default:
        return <span className="px-2 py-0.5 text-[10px] font-semibold rounded-full bg-gray-500/10 text-gray-400 border border-gray-500/20 capitalize">{tier}</span>;
    }
  };

  const getProviderBadge = (provider?: string) => {
    const p = provider?.toLowerCase() || "standard";
    if (p === "edge") {
      return <span className="text-[10px] px-2 py-0.5 rounded bg-sky-500/15 text-sky-300 border border-sky-500/25 font-semibold">Edge TTS</span>;
    }
    if (p === "elevenlabs") {
      return <span className="text-[10px] px-2 py-0.5 rounded bg-cyan-500/15 text-cyan-300 border border-cyan-500/25 font-semibold">ElevenLabs</span>;
    }
    if (p === "azure") {
      return <span className="text-[10px] px-2 py-0.5 rounded bg-blue-500/15 text-blue-300 border border-blue-500/25 font-semibold">Azure</span>;
    }
    if (p === "mock" || p === "clone") {
      return <span className="text-[10px] px-2 py-0.5 rounded bg-teal-500/15 text-teal-300 border border-teal-500/25 font-semibold">Custom Neural</span>;
    }
    return <span className="text-[10px] px-2 py-0.5 rounded bg-indigo-500/15 text-indigo-300 border border-indigo-500/25 font-semibold capitalize">{p}</span>;
  };

  // Currently selected voice object
  const currentSelectedVoice = useMemo(() => {
    return voices.find((v) => v.id === selectedVoiceId) || null;
  }, [voices, selectedVoiceId]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-black/80 backdrop-blur-md animate-in fade-in duration-150">
      <div className="w-full max-w-4xl bg-[#0C0E17] border border-[#20253B] rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="p-4 sm:p-5 border-b border-[#1A1F33] flex items-center justify-between bg-[#0F121F]">
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-xl bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
              <Sparkles className="w-4 h-4" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h3 className="text-base sm:text-lg font-bold text-white tracking-tight">Voice Catalog & Search</h3>
                <span className="text-xs px-2 py-0.5 rounded-full bg-indigo-500/15 text-indigo-300 font-mono font-medium">
                  {filteredVoices.length} voices
                </span>
              </div>
              <p className="text-xs text-gray-400 mt-0.5">
                Tap any voice to preview audio, view details, and set as active generator voice.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-xl bg-[#15192A] hover:bg-[#1E233B] text-gray-400 hover:text-white transition-colors"
            title="Close voice catalog"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Category Quick Preset Tabs */}
        <div className="px-4 sm:px-5 pt-3 pb-0 bg-[#090B12] border-b border-[#1A1F33] flex items-center justify-between overflow-x-auto">
          <div className="flex items-center space-x-1.5 shrink-0">
            <button
              onClick={() => {
                setActiveCategoryTab("all");
                setSelectedTier("all");
                setSelectedProvider("all");
              }}
              className={`flex items-center space-x-1.5 px-3 py-2 text-xs font-bold rounded-t-xl border-b-2 transition-all ${
                activeCategoryTab === "all"
                  ? "border-indigo-500 text-indigo-300 bg-[#141727]"
                  : "border-transparent text-gray-400 hover:text-gray-200 hover:bg-[#111320]"
              }`}
            >
              <span>All Voices</span>
            </button>

            <button
              onClick={() => {
                setActiveCategoryTab("library");
                setSelectedTier("all");
                setSelectedProvider("all");
              }}
              className={`flex items-center space-x-1.5 px-3 py-2 text-xs font-bold rounded-t-xl border-b-2 transition-all ${
                activeCategoryTab === "library"
                  ? "border-indigo-500 text-indigo-300 bg-[#141727]"
                  : "border-transparent text-gray-400 hover:text-gray-200 hover:bg-[#111320]"
              }`}
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>Voice Library</span>
            </button>

            <button
              onClick={() => {
                setActiveCategoryTab("premium");
                setSelectedTier("premium");
                setSelectedProvider("all");
              }}
              className={`flex items-center space-x-1.5 px-3 py-2 text-xs font-bold rounded-t-xl border-b-2 transition-all ${
                activeCategoryTab === "premium"
                  ? "border-purple-500 text-purple-300 bg-[#141727]"
                  : "border-transparent text-gray-400 hover:text-gray-200 hover:bg-[#111320]"
              }`}
            >
              <Crown className="w-3.5 h-3.5 text-purple-400" />
              <span>Premium</span>
            </button>

            <button
              onClick={() => {
                setActiveCategoryTab("edge");
                setSelectedProvider("edge");
                setSelectedTier("all");
              }}
              className={`flex items-center space-x-1.5 px-3 py-2 text-xs font-bold rounded-t-xl border-b-2 transition-all ${
                activeCategoryTab === "edge"
                  ? "border-sky-500 text-sky-300 bg-[#141727]"
                  : "border-transparent text-gray-400 hover:text-gray-200 hover:bg-[#111320]"
              }`}
            >
              <Cpu className="w-3.5 h-3.5 text-sky-400" />
              <span>Edge TTS</span>
            </button>

            <button
              onClick={() => {
                setActiveCategoryTab("elevenlabs");
                setSelectedProvider("elevenlabs");
                setSelectedTier("all");
              }}
              className={`flex items-center space-x-1.5 px-3 py-2 text-xs font-bold rounded-t-xl border-b-2 transition-all ${
                activeCategoryTab === "elevenlabs"
                  ? "border-cyan-500 text-cyan-300 bg-[#141727]"
                  : "border-transparent text-gray-400 hover:text-gray-200 hover:bg-[#111320]"
              }`}
            >
              <Layers className="w-3.5 h-3.5 text-cyan-400" />
              <span>ElevenLabs</span>
            </button>

            <button
              onClick={() => {
                setActiveCategoryTab("clone");
                setSelectedTier("custom");
                setSelectedProvider("all");
              }}
              className={`flex items-center space-x-1.5 px-3 py-2 text-xs font-bold rounded-t-xl border-b-2 transition-all ${
                activeCategoryTab === "clone"
                  ? "border-teal-500 text-teal-300 bg-[#141727]"
                  : "border-transparent text-gray-400 hover:text-gray-200 hover:bg-[#111320]"
              }`}
            >
              <UserCheck className="w-3.5 h-3.5 text-teal-400" />
              <span>Your Clone</span>
            </button>
          </div>

          <button
            onClick={() => setIsCloneModalOpen(true)}
            className="flex items-center space-x-1 text-xs text-teal-400 hover:text-teal-300 font-semibold px-2.5 py-1.5 rounded-lg bg-teal-500/10 hover:bg-teal-500/20 border border-teal-500/30 transition-all shrink-0 ml-2 mb-1"
          >
            <Upload className="w-3 h-3" />
            <span>Upload New Clone</span>
          </button>
        </div>

        {/* Search Bar + Filters (Provider, Language, Type/Tier) */}
        <div className="p-4 bg-[#0A0C14] border-b border-[#181C2E] space-y-3">
          {/* Search Input */}
          <div className="relative">
            <Search className="w-4 h-4 text-gray-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search by voice name, language, accent, provider, or style..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-10 pr-10 py-2.5 bg-[#121524] border border-[#22273D] focus:border-indigo-500 rounded-xl text-sm text-gray-100 placeholder-gray-500 focus:outline-none transition-all shadow-inner"
            />
            {search && (
              <button
                type="button"
                onClick={() => setSearch("")}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white p-1"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>

          {/* Filter Dropdowns Row: Provider, Style, Language, Type/Tier, Reset */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-2.5">
            {/* 1. Provider Filter */}
            <div className="flex flex-col space-y-1">
              <label className="text-[10px] font-semibold uppercase tracking-wider text-gray-400 flex items-center space-x-1">
                <Cpu className="w-3 h-3 text-indigo-400" />
                <span>Provider</span>
              </label>
              <select
                value={selectedProvider}
                onChange={(e) => setSelectedProvider(e.target.value)}
                className="w-full px-2.5 py-1.5 bg-[#121524] border border-[#22273D] rounded-lg text-xs text-gray-200 focus:outline-none focus:border-indigo-500 capitalize"
              >
                <option value="all">All Providers</option>
                <option value="edge">Edge TTS (Microsoft Neural)</option>
                <option value="elevenlabs">ElevenLabs</option>
                <option value="cloned">Your Cloned Voices</option>
                {availableProviders
                  .filter((p) => !["edge", "elevenlabs", "cloned"].includes(p))
                  .map((p) => (
                    <option key={p} value={p}>
                      {p.toUpperCase()}
                    </option>
                  ))}
              </select>
            </div>

            {/* 2. Voice Style Filter */}
            <div className="flex flex-col space-y-1">
              <label className="text-[10px] font-semibold uppercase tracking-wider text-gray-400 flex items-center space-x-1">
                <Sparkles className="w-3 h-3 text-pink-400" />
                <span>Style</span>
              </label>
              <select
                value={selectedStyle}
                onChange={(e) => setSelectedStyle(e.target.value)}
                className="w-full px-2.5 py-1.5 bg-[#121524] border border-[#22273D] rounded-lg text-xs text-gray-200 focus:outline-none focus:border-indigo-500"
              >
                {STYLE_OPTIONS.map((st) => (
                  <option key={st.id} value={st.id}>
                    {st.label}
                  </option>
                ))}
              </select>
            </div>

            {/* 3. Language Filter */}
            <div className="flex flex-col space-y-1">
              <label className="text-[10px] font-semibold uppercase tracking-wider text-gray-400 flex items-center space-x-1">
                <Globe className="w-3 h-3 text-sky-400" />
                <span>Language</span>
              </label>
              <select
                value={selectedLanguage}
                onChange={(e) => setSelectedLanguage(e.target.value)}
                className="w-full px-2.5 py-1.5 bg-[#121524] border border-[#22273D] rounded-lg text-xs text-gray-200 focus:outline-none focus:border-indigo-500 capitalize"
              >
                <option value="all">All Languages ({availableLanguages.length})</option>
                <option value="en">English (Global)</option>
                <option value="es">Spanish (Español)</option>
                <option value="fr">French (Français)</option>
                <option value="de">German (Deutsch)</option>
                <option value="hi">Hindi (हिन्दी)</option>
                <option value="ar">Arabic (العربية)</option>
                <option value="ur">Urdu (اردو)</option>
                <option value="tr">Turkish (Türkçe)</option>
                <option value="ja">Japanese (日本語)</option>
                <option value="pt">Portuguese</option>
                <option value="it">Italian</option>
                {availableLanguages
                  .filter((l) => !["en", "es", "fr", "de", "hi", "ar", "ur", "tr", "ja", "pt", "it"].includes(l))
                  .map((l) => (
                    <option key={l} value={l}>
                      {LANGUAGE_NAMES[l] || l.toUpperCase()} ({l})
                    </option>
                  ))}
              </select>
            </div>

            {/* 4. Type / Tier Filter */}
            <div className="flex flex-col space-y-1">
              <label className="text-[10px] font-semibold uppercase tracking-wider text-gray-400 flex items-center space-x-1">
                <Crown className="w-3 h-3 text-purple-400" />
                <span>Type / Tier</span>
              </label>
              <select
                value={selectedTier}
                onChange={(e) => setSelectedTier(e.target.value)}
                className="w-full px-2.5 py-1.5 bg-[#121524] border border-[#22273D] rounded-lg text-xs text-gray-200 focus:outline-none focus:border-indigo-500 capitalize"
              >
                <option value="all">All Tiers & Types</option>
                <option value="free">Free Tier</option>
                <option value="standard">Standard Tier</option>
                <option value="premium">Premium Tier</option>
                <option value="ultra">Ultra Tier</option>
                <option value="custom">Your Clone (Private)</option>
              </select>
            </div>

            {/* 5. Reset Filters Action */}
            <div className="flex flex-col justify-end">
              <button
                type="button"
                onClick={handleResetFilters}
                className="w-full px-3 py-1.5 rounded-lg bg-[#141829] hover:bg-[#1E233C] border border-[#22273F] text-xs text-gray-300 hover:text-white flex items-center justify-center space-x-1.5 transition-colors h-[34px]"
              >
                <RotateCcw className="w-3.5 h-3.5 text-gray-400" />
                <span>Reset Filters</span>
              </button>
            </div>
          </div>
        </div>

        {/* Voice Cards Grid / List */}
        <div className="p-3 sm:p-4 overflow-y-auto space-y-2.5 flex-1 divide-y divide-[#15192C]">
          {filteredVoices.map((voice) => {
            const isSelected = voice.id === selectedVoiceId;
            const isLocked = (voice.tier === "premium" || voice.tier === "ultra") && !userCanPremium;
            const isClone = isClonedVoice(voice);
            const isPlaying = playingVoiceId === voice.id;

            return (
              <div
                key={voice.id}
                onClick={() => handleVoiceTap(voice)}
                className={`pt-2.5 first:pt-0 p-3 rounded-xl transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-3 cursor-pointer group ${
                  isSelected
                    ? isClone
                      ? "bg-teal-500/15 border-2 border-teal-500/60 shadow-lg shadow-teal-500/10"
                      : "bg-indigo-600/15 border-2 border-indigo-500/60 shadow-lg shadow-indigo-500/10"
                    : "hover:bg-[#121626] border border-transparent hover:border-[#21263D]"
                } ${isLocked ? "opacity-60 cursor-not-allowed" : ""}`}
              >
                {/* Voice Identity and Attributes */}
                <div className="flex items-start space-x-3 min-w-0">
                  {/* Avatar / Initials / Soundwave Animation */}
                  <div
                    className={`w-11 h-11 rounded-xl border flex items-center justify-center font-bold text-sm shrink-0 transition-all ${
                      isSelected
                        ? isClone
                          ? "bg-gradient-to-br from-teal-500/30 to-emerald-500/30 border-teal-400 text-teal-300"
                          : "bg-gradient-to-br from-indigo-500/30 to-purple-500/30 border-indigo-400 text-indigo-200"
                        : isClone
                        ? "bg-teal-500/10 border-teal-500/20 text-teal-400"
                        : "bg-gradient-to-br from-indigo-500/15 to-purple-500/15 border-indigo-500/25 text-indigo-300"
                    }`}
                  >
                    {isPlaying ? (
                      <div className="flex items-center space-x-0.5">
                        <span className="w-1 h-4 bg-current animate-pulse" />
                        <span className="w-1 h-2 bg-current animate-pulse delay-75" />
                        <span className="w-1 h-3 bg-current animate-pulse delay-150" />
                      </div>
                    ) : (
                      voice.name[0]
                    )}
                  </div>

                  {/* Voice Name & Meta */}
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-1.5">
                      <span className="font-semibold text-sm text-gray-100 group-hover:text-white">
                        {voice.name}
                      </span>
                      {getTierBadge(voice.tier, isClone)}
                      {getProviderBadge(voice.provider)}
                      {isClone && (
                        <span className="px-1.5 py-0.2 text-[9px] font-bold rounded bg-teal-500/20 text-teal-300 border border-teal-500/30">
                          1 of 1 Slot
                        </span>
                      )}
                    </div>

                    <p className="text-xs text-gray-400 mt-0.5 line-clamp-1">
                      {voice.description || `${voice.accent || "Neutral"} voice suitable for professional voiceover.`}
                    </p>

                    {/* Detailed Attribute Tags */}
                    <div className="flex flex-wrap items-center gap-x-2.5 gap-y-1 text-[11px] text-gray-400 mt-1.5 font-medium">
                      <span className="text-gray-300">
                        {LANGUAGE_NAMES[voice.language?.toLowerCase()] || voice.language?.toUpperCase() || "EN"} ({voice.locale || "Standard"})
                      </span>
                      <span>•</span>
                      <span className="capitalize">{voice.accent || "Neutral"}</span>
                      <span>•</span>
                      <span className="capitalize">{voice.gender || "Voice"}</span>
                      <span>•</span>
                      <span className="capitalize text-indigo-300">{voice.style || "Natural"}</span>
                      {voice.model && (
                        <>
                          <span>•</span>
                          <span className="text-gray-500 font-mono text-[10px]">{voice.model}</span>
                        </>
                      )}
                    </div>
                  </div>
                </div>

                {/* Right Action: Preview/Play Button & Selected Indicator */}
                <div className="flex items-center justify-end space-x-2 shrink-0 pt-1 sm:pt-0">
                  {/* Preview / Play Button */}
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      handlePlayPreview(voice.id, voice.preview_audio_url);
                    }}
                    className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center space-x-1.5 transition-all shadow-sm ${
                      isPlaying
                        ? isClone
                          ? "bg-teal-600 text-white shadow-teal-500/30"
                          : "bg-indigo-600 text-white shadow-indigo-500/30"
                        : "bg-[#15192C] hover:bg-[#1E243D] text-gray-200 border border-[#242A42]"
                    }`}
                    title={isPlaying ? "Pause voice sample" : "Listen to sample"}
                  >
                    {isPlaying ? (
                      <>
                        <Pause className="w-3.5 h-3.5 fill-current" />
                        <span>Playing</span>
                      </>
                    ) : (
                      <>
                        <Play className="w-3.5 h-3.5 fill-current" />
                        <span>Preview</span>
                      </>
                    )}
                  </button>

                  {/* Lock Indicator or Clear ✓ Selected Indicator */}
                  {isLocked ? (
                    <span className="flex items-center space-x-1 text-xs text-amber-400 bg-amber-500/10 px-2.5 py-1 rounded-lg border border-amber-500/25">
                      <Lock className="w-3 h-3" />
                      <span>Locked</span>
                    </span>
                  ) : isSelected ? (
                    <div
                      className={`px-2.5 py-1 rounded-lg text-xs font-bold flex items-center space-x-1.5 text-white shadow-md ${
                        isClone ? "bg-teal-600 shadow-teal-600/30" : "bg-indigo-600 shadow-indigo-600/30"
                      }`}
                    >
                      <Check className="w-3.5 h-3.5 stroke-[3]" />
                      <span>Selected</span>
                    </div>
                  ) : (
                    <div className="w-8 h-8 rounded-lg border border-transparent group-hover:border-[#22273E] flex items-center justify-center text-gray-500 group-hover:text-gray-300">
                      <CheckCircle2 className="w-4 h-4 opacity-40 group-hover:opacity-70" />
                    </div>
                  )}
                </div>
              </div>
            );
          })}

          {/* Empty State */}
          {filteredVoices.length === 0 && (
            <div className="p-8 text-center space-y-3 bg-[#0A0C14] rounded-xl border border-[#181C2E] my-4">
              <div className="w-12 h-12 rounded-2xl bg-[#141727] border border-[#22263C] text-gray-400 mx-auto flex items-center justify-center">
                <Search className="w-6 h-6 text-gray-500" />
              </div>
              <h4 className="text-sm font-semibold text-gray-200">No voices match your filters</h4>
              <p className="text-xs text-gray-400 max-w-sm mx-auto">
                Try searching for a different name, accent, or reset your filters to view all available voices.
              </p>
              <button
                type="button"
                onClick={handleResetFilters}
                className="inline-flex items-center space-x-1.5 px-4 py-2 rounded-xl text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white shadow-md shadow-indigo-600/30 transition-colors"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span>Reset All Filters</span>
              </button>
            </div>
          )}
        </div>

        {/* Footer / Selected Voice Action Bar */}
        <div className="p-3.5 sm:p-4 bg-[#0F121F] border-t border-[#1A1F33] flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="flex items-center space-x-3 w-full sm:w-auto">
            <span className="text-xs text-gray-400">Current Selection:</span>
            {currentSelectedVoice ? (
              <div className="flex items-center space-x-2 px-3 py-1 rounded-lg bg-[#15192C] border border-[#232840] text-xs">
                <span className="font-semibold text-white">{currentSelectedVoice.name}</span>
                <span className="text-[10px] px-1.5 py-0.2 rounded bg-indigo-500/20 text-indigo-300 font-mono capitalize">
                  {currentSelectedVoice.tier}
                </span>
                <span className="text-gray-400 capitalize">• {currentSelectedVoice.provider || "Neural"}</span>
              </div>
            ) : (
              <span className="text-xs text-amber-400">No voice selected</span>
            )}
          </div>

          <div className="flex items-center space-x-2 w-full sm:w-auto justify-end">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 sm:flex-initial px-4 py-2 rounded-xl text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white shadow-md shadow-indigo-600/30 flex items-center justify-center space-x-1.5 transition-all"
            >
              <Check className="w-3.5 h-3.5" />
              <span>Use Selected Voice</span>
            </button>
          </div>
        </div>
      </div>

      {/* Uploaded Voice Modal (For Creating / Managing Clone) */}
      <UploadedVoiceModal
        isOpen={isCloneModalOpen}
        onClose={() => setIsCloneModalOpen(false)}
        selectedVoiceId={selectedVoiceId}
        onSelectVoice={(cloned) => {
          onSelectVoice(cloned);
          setIsCloneModalOpen(false);
        }}
        onSuccess={(cloned) => {
          if (cloned) {
            onSelectVoice(cloned);
          }
          setIsCloneModalOpen(false);
        }}
      />
    </div>
  );
}
