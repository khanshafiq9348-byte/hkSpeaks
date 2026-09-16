"use client";

import React, { useState, useEffect, useMemo, useRef } from "react";
import { apiClient, API_BASE_URL } from "@/lib/api";
import { Voice } from "@/components/VoiceSelectorModal";
import { 
  Sparkles, 
  Search, 
  Volume2, 
  Crown, 
  Trash2, 
  Check, 
  UserCheck, 
  Upload, 
  ArrowRight,
  AlertCircle,
  CheckCircle2,
  RefreshCw,
  ChevronLeft,
  ChevronRight,
  Layers,
  Cpu,
  Play,
  Pause
} from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";

const PROVIDERS = [
  { id: "all", label: "All Providers" },
  { id: "elevenlabs", label: "ElevenLabs" },
  { id: "edge", label: "Microsoft Edge" },
  { id: "openai", label: "OpenAI" },
  { id: "amazon", label: "Amazon Polly" },
  { id: "google", label: "Google Cloud" },
  { id: "azure", label: "Azure Speech" },
  { id: "other", label: "Other Providers" },
];

const TIERS = [
  { id: "all", label: "All Tiers" },
  { id: "free", label: "Free" },
  { id: "standard", label: "Standard" },
  { id: "premium", label: "Premium" },
  { id: "ultra", label: "Ultra" },
];

const STYLE_OPTIONS = [
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

function VoicesContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const tabParam = searchParams.get("tab") || searchParams.get("source");
  const tierParam = searchParams.get("tier");
  const providerParam = searchParams.get("provider");

  // Tab: "library" vs "clone"
  const [activeSource, setActiveSource] = useState<"library" | "clone">(
    tabParam === "clone" ? "clone" : "library"
  );

  const [voices, setVoices] = useState<Voice[]>([]);
  const [userCloneData, setUserCloneData] = useState<{
    voice: Voice | null;
    can_clone: boolean;
    max_clones: number;
    saved_count: number;
  } | null>(null);

  const [currentSelectedVoiceId, setCurrentSelectedVoiceId] = useState<string | null>(null);
  const [currentSelectedVoiceType, setCurrentSelectedVoiceType] = useState<string | null>(null);

  // Filters
  const [search, setSearch] = useState("");
  const [selectedProvider, setSelectedProvider] = useState<string>(providerParam || "all");
  const [selectedStyle, setSelectedStyle] = useState<string>("all");
  const [selectedTier, setSelectedTier] = useState<string>(tierParam || "all");
  const [selectedGender, setSelectedGender] = useState<string>("all");
  const [selectedLanguage, setSelectedLanguage] = useState<string>("all");
  const [playingId, setPlayingId] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  // Pagination
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 24;

  // Clone upload form state
  const [cloneName, setCloneName] = useState("");
  const [cloneFile, setCloneFile] = useState<File | null>(null);
  const [consentConfirmed, setConsentConfirmed] = useState(false);
  const [rightsConfirmed, setRightsConfirmed] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);

  // Sync params with query string
  useEffect(() => {
    if (tabParam === "clone") {
      setActiveSource("clone");
    } else {
      setActiveSource("library");
    }

    if (tierParam) {
      setSelectedTier(tierParam.toLowerCase());
    }
    if (providerParam) {
      setSelectedProvider(providerParam.toLowerCase());
    }
  }, [tabParam, tierParam, providerParam]);

  useEffect(() => {
    loadVoices();
    loadUserClone();

    if (typeof window !== "undefined") {
      setCurrentSelectedVoiceId(localStorage.getItem("hk_selected_voice_id"));
      setCurrentSelectedVoiceType(localStorage.getItem("hk_selected_voice_type"));
    }
  }, []);

  // Cleanup audio on unmount
  useEffect(() => {
    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
      }
    };
  }, []);

  // Reset pagination on filter change
  useEffect(() => {
    setCurrentPage(1);
  }, [search, selectedProvider, selectedStyle, selectedTier, selectedGender, selectedLanguage]);

  const loadVoices = async () => {
    try {
      const data = await apiClient<Voice[]>("/voices");
      setVoices(data);
    } catch {
      // ignore
    }
  };

  const loadUserClone = async () => {
    try {
      const data = await apiClient<any>("/voices/user-clone");
      setUserCloneData(data);
    } catch {
      // ignore
    }
  };

  const handlePlayPreview = (voiceId: string, url?: string) => {
    if (playingId === voiceId) {
      if (audioRef.current) {
        audioRef.current.pause();
      }
      setPlayingId(null);
      return;
    }

    if (audioRef.current) {
      audioRef.current.pause();
    }

    const previewUrl = url || `${API_BASE_URL}/voices/${voiceId}/preview`;
    const audio = new Audio(previewUrl);
    audioRef.current = audio;
    setPlayingId(voiceId);

    audio.play().catch((err) => {
      console.warn("Audio preview failed:", err);
      setPlayingId(null);
    });

    audio.onended = () => {
      setPlayingId(null);
    };
    audio.onerror = () => {
      setPlayingId(null);
    };
  };

  const handleSelectVoice = (voice: Voice, type: "library" | "clone", navigate = false) => {
    const normalizedType: "cloned" | "library" = type === "clone" ? "cloned" : "library";
    const voiceObj: Voice = {
      ...voice,
      type: normalizedType,
      voice_type: type === "clone" ? "clone" : "library",
    };
    if (typeof window !== "undefined") {
      localStorage.setItem("hk_selected_voice_id", voice.id);
      localStorage.setItem("hk_selected_voice_type", normalizedType);
      localStorage.setItem("hk_selected_voice_name", voice.name);
      localStorage.setItem("hk_selected_voice_obj", JSON.stringify(voiceObj));
    }
    setCurrentSelectedVoiceId(voice.id);
    setCurrentSelectedVoiceType(normalizedType);
    if (navigate) {
      router.push(`/app/studio?voice=${voice.id}&type=${normalizedType}`);
    }
  };

  const handleDeleteClone = async (voiceId: string) => {
    if (!confirm("Are you sure you want to delete your custom voice clone? This will clear your slot back to 0 of 1 saved.")) return;
    try {
      await apiClient(`/voices/${voiceId}`, { method: "DELETE" });
      if (currentSelectedVoiceId === voiceId) {
        if (typeof window !== "undefined") {
          localStorage.removeItem("hk_selected_voice_id");
          localStorage.removeItem("hk_selected_voice_type");
        }
        setCurrentSelectedVoiceId(null);
        setCurrentSelectedVoiceType(null);
      }
      await loadVoices();
      await loadUserClone();
    } catch {
      // ignore
    }
  };

  const handleUploadClone = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!cloneFile) {
      setUploadError("Please choose an audio recording (.wav or .mp3)");
      return;
    }
    if (!consentConfirmed || !rightsConfirmed) {
      setUploadError("You must confirm voice consent and rights to proceed.");
      return;
    }

    setIsUploading(true);
    setUploadError(null);
    setUploadSuccess(null);

    const formData = new FormData();
    formData.append("name", cloneName.trim() || "My Cloned Voice");
    formData.append("gender", "neutral");
    formData.append("consent_confirmed", "true");
    formData.append("rights_confirmed", "true");
    formData.append("audio_file", cloneFile);

    try {
      const createdVoice = await apiClient<Voice>("/voices/clone", {
        method: "POST",
        body: formData,
      });

      setUploadSuccess(`Voice '${createdVoice.name}' saved and ready for use!`);
      setCloneFile(null);
      setCloneName("");
      setConsentConfirmed(false);
      setRightsConfirmed(false);

      await loadVoices();
      await loadUserClone();

      // Automatically select the cloned voice
      handleSelectVoice(createdVoice, "clone");
    } catch (err: any) {
      setUploadError(err.message || "Failed to upload and clone voice.");
    } finally {
      setIsUploading(false);
    }
  };

  // Separate library voices
  const libraryVoices = useMemo(() => {
    return voices.filter(
      (v) => (v.voice_type === "library" || v.tier !== "custom") && !v.owner_user_id
    );
  }, [voices]);

  // Unique languages for dropdown
  const availableLanguages = useMemo(() => {
    const langs = new Set<string>();
    libraryVoices.forEach((v) => {
      if (v.language) langs.add(v.language);
    });
    return Array.from(langs).sort();
  }, [libraryVoices]);

  // Filtered library voices
  const filteredVoices = useMemo(() => {
    return libraryVoices.filter((v) => {
      // Search
      const q = search.toLowerCase();
      const matchesSearch =
        !q ||
        v.name.toLowerCase().includes(q) ||
        (v.accent && v.accent.toLowerCase().includes(q)) ||
        (v.language && v.language.toLowerCase().includes(q)) ||
        (v.style && v.style.toLowerCase().includes(q)) ||
        (v.provider && v.provider.toLowerCase().includes(q));

      // Provider
      let matchesProvider = true;
      if (selectedProvider !== "all") {
        if (selectedProvider === "elevenlabs") {
          matchesProvider = v.provider === "elevenlabs";
        } else if (selectedProvider === "edge") {
          matchesProvider = v.provider === "edge";
        } else if (selectedProvider === "openai") {
          matchesProvider = v.provider === "openai";
        } else if (selectedProvider === "amazon") {
          matchesProvider = v.provider === "amazon";
        } else if (selectedProvider === "google") {
          matchesProvider = v.provider === "google";
        } else if (selectedProvider === "azure") {
          matchesProvider = v.provider === "azure";
        } else if (selectedProvider === "other") {
          matchesProvider = v.provider !== "elevenlabs" && v.provider !== "edge";
        }
      }

      // Style
      let matchesStyle = true;
      if (selectedStyle !== "all") {
        const sTarget = selectedStyle.toLowerCase();
        const vStyles = (v.styles || []).map((s: string) => s.toLowerCase());
        matchesStyle = vStyles.some((s: string) => s.includes(sTarget)) || (v.style || "").toLowerCase().includes(sTarget);
      }

      // Tier
      let matchesTier = true;
      if (selectedTier !== "all") {
        matchesTier = v.tier?.toLowerCase() === selectedTier;
      }

      // Gender
      let matchesGender = true;
      if (selectedGender !== "all") {
        matchesGender = v.gender?.toLowerCase() === selectedGender;
      }

      // Language
      let matchesLanguage = true;
      if (selectedLanguage !== "all") {
        matchesLanguage = v.language === selectedLanguage;
      }

      return matchesSearch && matchesProvider && matchesTier && matchesGender && matchesLanguage && matchesStyle;
    });
  }, [libraryVoices, search, selectedProvider, selectedStyle, selectedTier, selectedGender, selectedLanguage]);

  // Pagination calculation
  const totalPages = Math.ceil(filteredVoices.length / pageSize) || 1;
  const paginatedVoices = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return filteredVoices.slice(start, start + pageSize);
  }, [filteredVoices, currentPage, pageSize]);

  // Active voice obj
  const activeVoiceObj = voices.find((v) => v.id === currentSelectedVoiceId) || userCloneData?.voice;

  const getProviderBadge = (provider?: string) => {
    switch (provider?.toLowerCase()) {
      case "elevenlabs":
        return <span className="px-2 py-0.5 text-[10px] font-bold rounded-md bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">ElevenLabs</span>;
      case "edge":
        return <span className="px-2 py-0.5 text-[10px] font-bold rounded-md bg-sky-500/20 text-sky-300 border border-sky-500/30">Edge Neural</span>;
      case "openai":
        return <span className="px-2 py-0.5 text-[10px] font-bold rounded-md bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">OpenAI</span>;
      case "google":
        return <span className="px-2 py-0.5 text-[10px] font-bold rounded-md bg-blue-500/20 text-blue-300 border border-blue-500/30">Google Cloud</span>;
      case "amazon":
        return <span className="px-2 py-0.5 text-[10px] font-bold rounded-md bg-amber-500/20 text-amber-300 border border-amber-500/30">Amazon Polly</span>;
      case "azure":
        return <span className="px-2 py-0.5 text-[10px] font-bold rounded-md bg-purple-500/20 text-purple-300 border border-purple-500/30">Azure Speech</span>;
      default:
        return <span className="px-2 py-0.5 text-[10px] font-bold rounded-md bg-gray-500/20 text-gray-400 border border-gray-500/30">Studio</span>;
    }
  };

  return (
    <div className="flex-1 flex flex-col min-w-0 h-full overflow-y-auto bg-[#090A0F] text-gray-100">
      {/* Top Header */}
      <div className="h-16 px-6 border-b border-[#1E2333]/80 bg-[#0C0E17]/60 backdrop-blur-md flex items-center justify-between shrink-0">
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 rounded-lg bg-indigo-500/10 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
            <Sparkles className="w-4 h-4" />
          </div>
          <div>
            <h1 className="text-base font-bold text-white tracking-tight">Voice Catalog & Cloning</h1>
            <p className="text-[11px] text-gray-400">1,000+ authentic neural AI voices and your private voice clone</p>
          </div>
        </div>

        {/* Active voice indicator */}
        {activeVoiceObj && (
          <div className="hidden sm:flex items-center space-x-3 bg-[#12141F] border border-[#23273D] px-3.5 py-1.5 rounded-xl shadow-md">
            <div className="text-xs">
              <span className="text-gray-400">Active in Studio: </span>
              <span className="font-bold text-white">{activeVoiceObj.name}</span>
              <span className="ml-2 text-[10px] px-2 py-0.5 rounded-full font-medium bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 capitalize">
                {activeVoiceObj.tier === "custom" || activeVoiceObj.voice_type === "clone"
                  ? "Your Clone"
                  : `${activeVoiceObj.provider || "Library"} • ${activeVoiceObj.tier}`}
              </span>
            </div>
            <Link
              href={`/app/studio?voice=${activeVoiceObj.id}`}
              className="text-xs font-semibold text-indigo-400 hover:text-indigo-300 flex items-center space-x-1 pl-2 border-l border-[#22263C]"
            >
              <span>Studio</span>
              <ArrowRight className="w-3 h-3" />
            </Link>
          </div>
        )}
      </div>

      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 space-y-6">
        {/* Source Switcher: Voice Library vs Your Clone */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 p-1.5 rounded-2xl bg-[#12141F] border border-[#202436]">
          {/* Source 1: Voice Library */}
          <button
            onClick={() => setActiveSource("library")}
            className={`p-4 rounded-xl flex items-center justify-between transition-all text-left ${
              activeSource === "library"
                ? "bg-[#181B2B] text-white border border-indigo-500/40 shadow-lg shadow-indigo-600/10"
                : "text-gray-400 hover:text-gray-200 hover:bg-[#151724] border border-transparent"
            }`}
          >
            <div className="flex items-center space-x-3.5">
              <div className={`w-10 h-10 rounded-xl flex items-center justify-center font-bold transition-all ${
                activeSource === "library"
                  ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/30"
                  : "bg-[#1C1F30] text-gray-400"
              }`}>
                <Sparkles className="w-5 h-5" />
              </div>
              <div>
                <div className="flex items-center space-x-2">
                  <h3 className="font-bold text-sm tracking-tight text-white">Voice Library</h3>
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-[#20253B] text-gray-300 font-semibold">
                    {libraryVoices.length} Voices
                  </span>
                </div>
                <p className="text-xs text-gray-400 mt-0.5">1,000+ AI neural voices across 7 providers</p>
              </div>
            </div>
            {activeSource === "library" && (
              <div className="w-2.5 h-2.5 rounded-full bg-indigo-500 shadow-sm shadow-indigo-400" />
            )}
          </button>

          {/* Source 2: Your Clone */}
          <Link
            href="/app/clone"
            className="p-4 rounded-xl flex items-center justify-between transition-all text-left text-gray-400 hover:text-gray-200 hover:bg-[#151724] border border-transparent"
          >
            <div className="flex items-center space-x-3.5">
              <div className="w-10 h-10 rounded-xl flex items-center justify-center font-bold bg-[#1C1F30] text-teal-400 transition-all">
                <UserCheck className="w-5 h-5" />
              </div>
              <div>
                <div className="flex items-center space-x-2">
                  <h3 className="font-bold text-sm tracking-tight text-white">Voice Cloning / Your Clone</h3>
                  <span className={`text-[10px] px-2 py-0.5 rounded-full font-semibold ${
                    userCloneData?.saved_count ? "bg-teal-500/20 text-teal-300" : "bg-[#20253B] text-gray-400"
                  }`}>
                    {userCloneData ? `${userCloneData.saved_count} of ${userCloneData.max_clones} saved` : "1 of 1 slot"}
                  </span>
                </div>
                <p className="text-xs text-gray-400 mt-0.5">Upload audio and train your private voice clone</p>
              </div>
            </div>
            <ArrowRight className="w-4 h-4 text-gray-500" />
          </Link>
        </div>

        {/* ==================== SOURCE 1: VOICE LIBRARY VIEW ==================== */}
        {activeSource === "library" && (
          <div className="space-y-6 animate-in fade-in duration-200">
            {/* Search and Filters Bar */}
            <div className="p-4 rounded-2xl bg-[#12141F] border border-[#202436] space-y-3.5">
              <div className="flex flex-col md:flex-row items-center justify-between gap-3">
                {/* Search Bar */}
                <div className="relative w-full md:w-96">
                  <Search className="w-4 h-4 text-gray-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
                  <input
                    type="text"
                    placeholder="Search by voice name, language, accent, style..."
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    className="w-full pl-10 pr-4 py-2 bg-[#0B0C14] border border-[#23273D] rounded-xl text-xs text-gray-100 placeholder-gray-500 focus:outline-none focus:border-indigo-500"
                  />
                </div>

                {/* Secondary Filters: Style, Language & Gender */}
                <div className="flex items-center space-x-2 w-full md:w-auto overflow-x-auto">
                  <select
                    value={selectedStyle}
                    onChange={(e) => setSelectedStyle(e.target.value)}
                    className="px-3 py-2 bg-[#0B0C14] border border-[#23273D] rounded-xl text-xs text-gray-300 focus:outline-none focus:border-indigo-500 font-medium"
                  >
                    {STYLE_OPTIONS.map((st) => (
                      <option key={st.id} value={st.id}>
                        {st.label}
                      </option>
                    ))}
                  </select>

                  <select
                    value={selectedLanguage}
                    onChange={(e) => setSelectedLanguage(e.target.value)}
                    className="px-3 py-2 bg-[#0B0C14] border border-[#23273D] rounded-xl text-xs text-gray-300 focus:outline-none focus:border-indigo-500"
                  >
                    <option value="all">All Languages</option>
                    {availableLanguages.map((lang) => (
                      <option key={lang} value={lang}>
                        {lang}
                      </option>
                    ))}
                  </select>

                  <select
                    value={selectedGender}
                    onChange={(e) => setSelectedGender(e.target.value)}
                    className="px-3 py-2 bg-[#0B0C14] border border-[#23273D] rounded-xl text-xs text-gray-300 focus:outline-none focus:border-indigo-500"
                  >
                    <option value="all">All Genders</option>
                    <option value="female">Female</option>
                    <option value="male">Male</option>
                    <option value="neutral">Neutral</option>
                  </select>
                </div>
              </div>

              {/* Provider Pills */}
              <div className="pt-2 border-t border-[#1C1F30] flex items-center justify-between gap-2 overflow-x-auto">
                <div className="flex items-center space-x-1.5 shrink-0">
                  <span className="text-[11px] font-semibold text-gray-400 mr-1.5 flex items-center space-x-1">
                    <Cpu className="w-3.5 h-3.5 text-indigo-400" />
                    <span>Provider:</span>
                  </span>
                  {PROVIDERS.map((p) => (
                    <button
                      key={p.id}
                      onClick={() => setSelectedProvider(p.id)}
                      className={`px-3 py-1.5 rounded-xl text-xs font-medium transition-all shrink-0 ${
                        selectedProvider === p.id
                          ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/30"
                          : "bg-[#0B0C14] text-gray-400 hover:text-gray-200 border border-[#202438]"
                      }`}
                    >
                      {p.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Tier Pills */}
              <div className="flex items-center space-x-1.5 overflow-x-auto">
                <span className="text-[11px] font-semibold text-gray-400 mr-1.5 flex items-center space-x-1">
                  <Layers className="w-3.5 h-3.5 text-purple-400" />
                  <span>Tier:</span>
                </span>
                {TIERS.map((t) => (
                  <button
                    key={t.id}
                    onClick={() => setSelectedTier(t.id)}
                    className={`px-3 py-1 rounded-lg text-xs font-medium capitalize transition-all ${
                      selectedTier === t.id
                        ? "bg-purple-600 text-white shadow-md shadow-purple-600/30"
                        : "bg-[#0B0C14] text-gray-400 hover:text-gray-200 border border-[#202438]"
                    }`}
                  >
                    {t.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Results count & Pagination stats */}
            <div className="flex items-center justify-between text-xs text-gray-400 px-1">
              <div>
                Showing <span className="text-white font-semibold">{(currentPage - 1) * pageSize + 1}</span> to{" "}
                <span className="text-white font-semibold">
                  {Math.min(currentPage * pageSize, filteredVoices.length)}
                </span>{" "}
                of <span className="text-white font-semibold">{filteredVoices.length.toLocaleString()}</span> voices
              </div>

              {/* Pagination controls top */}
              {totalPages > 1 && (
                <div className="flex items-center space-x-2">
                  <button
                    onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                    disabled={currentPage === 1}
                    className="p-1.5 rounded-lg bg-[#12141F] border border-[#202438] text-gray-400 hover:text-white disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    <ChevronLeft className="w-4 h-4" />
                  </button>
                  <span className="font-mono text-xs text-gray-300">
                    {currentPage} / {totalPages}
                  </span>
                  <button
                    onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                    disabled={currentPage === totalPages}
                    className="p-1.5 rounded-lg bg-[#12141F] border border-[#202438] text-gray-400 hover:text-white disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    <ChevronRight className="w-4 h-4" />
                  </button>
                </div>
              )}
            </div>

            {/* Voices Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
              {paginatedVoices.map((voice) => {
                const isSelected = voice.id === currentSelectedVoiceId;

                return (
                  <div
                    key={voice.id}
                    onClick={() => handleSelectVoice(voice, "library", false)}
                    className={`p-5 rounded-2xl bg-[#12141F] border transition-all flex flex-col justify-between space-y-4 group cursor-pointer ${
                      isSelected
                        ? "border-indigo-500 shadow-xl shadow-indigo-600/20 ring-2 ring-indigo-500/50 bg-[#151829]"
                        : "border-[#202436] hover:border-[#2E334D] hover:bg-[#141624]"
                    }`}
                  >
                    <div>
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex items-center space-x-3">
                          <div className={`w-11 h-11 rounded-xl flex items-center justify-center font-bold text-base shrink-0 transition-all ${
                            isSelected
                              ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/30"
                              : "bg-gradient-to-br from-indigo-500/20 to-purple-500/20 border border-indigo-500/30 text-indigo-400"
                          }`}>
                            {voice.name[0]}
                          </div>
                          <div>
                            <h3 className={`font-bold text-sm transition-colors line-clamp-1 ${
                              isSelected ? "text-white" : "text-gray-100 group-hover:text-indigo-300"
                            }`}>
                              {voice.name}
                            </h3>
                            <div className="text-[11px] text-gray-400 capitalize mt-0.5">
                              {voice.language} • {voice.accent} • {voice.gender}
                            </div>
                          </div>
                        </div>

                        <div className="flex flex-col items-end space-y-1 shrink-0">
                          {getProviderBadge(voice.provider)}
                          <span
                            className={`px-2 py-0.5 text-[10px] font-semibold rounded capitalize ${
                              voice.tier === "free"
                                ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                                : voice.tier === "premium"
                                ? "bg-purple-500/10 text-purple-400 border border-purple-500/20"
                                : voice.tier === "ultra"
                                ? "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                                : "bg-blue-500/10 text-blue-400 border border-blue-500/20"
                            }`}
                          >
                            {voice.tier}
                          </span>
                        </div>
                      </div>

                      <p className="text-xs text-gray-400 mt-3 line-clamp-2 leading-relaxed">
                        {voice.description || `High-fidelity ${voice.accent} voice for narration and studio production.`}
                      </p>

                      {/* Style Tag Badges */}
                      <div className="flex flex-wrap gap-1 mt-2.5">
                        {((voice.styles && voice.styles.length > 0)
                          ? voice.styles
                          : (voice.style ? voice.style.split(",").map((s) => s.trim()) : ["Conversational"])
                        ).slice(0, 3).map((st) => (
                          <span
                            key={st}
                            className="px-2 py-0.5 text-[10px] font-medium rounded-md bg-[#0C0E18] text-indigo-300/90 border border-[#23273D]"
                          >
                            {st}
                          </span>
                        ))}
                      </div>
                    </div>

                    <div className="pt-3 border-t border-[#1C1F30] flex items-center justify-between gap-2">
                      {/* Audio Preview Button (works for EVERY voice) */}
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          handlePlayPreview(voice.id, voice.preview_audio_url);
                        }}
                        className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all shadow-sm ${
                          playingId === voice.id
                            ? "bg-indigo-600 text-white shadow-indigo-600/30"
                            : "bg-[#181B2B] hover:bg-indigo-600 hover:text-white text-gray-300 border border-[#23273D]"
                        }`}
                        title={playingId === voice.id ? "Pause preview" : "Listen to sample"}
                      >
                        {playingId === voice.id ? (
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

                      <div className="flex items-center space-x-2">
                        {isSelected && (
                          <span className="text-[11px] font-bold text-emerald-400 flex items-center space-x-1">
                            <Check className="w-3.5 h-3.5" />
                            <span className="hidden sm:inline">Active</span>
                          </span>
                        )}

                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleSelectVoice(voice, "library", true);
                          }}
                          className={`text-xs font-semibold px-3 py-1.5 rounded-lg transition-all flex items-center space-x-1 ${
                            isSelected
                              ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/30 hover:bg-indigo-500"
                              : "bg-[#181B2B] text-indigo-400 hover:bg-indigo-600 hover:text-white border border-[#23273D]"
                          }`}
                        >
                          <span>Use in Studio</span>
                          <ArrowRight className="w-3 h-3" />
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Bottom Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-center space-x-2 pt-6 pb-8">
                <button
                  onClick={() => setCurrentPage(1)}
                  disabled={currentPage === 1}
                  className="px-3 py-1.5 rounded-lg bg-[#12141F] border border-[#202438] text-xs text-gray-400 hover:text-white disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  First
                </button>
                <button
                  onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                  disabled={currentPage === 1}
                  className="px-3 py-1.5 rounded-lg bg-[#12141F] border border-[#202438] text-xs text-gray-400 hover:text-white disabled:opacity-40 disabled:cursor-not-allowed flex items-center space-x-1"
                >
                  <ChevronLeft className="w-3.5 h-3.5" />
                  <span>Previous</span>
                </button>
                <span className="px-4 py-1.5 rounded-lg bg-[#181B2B] border border-[#252A42] font-mono text-xs text-indigo-300 font-semibold">
                  Page {currentPage} of {totalPages}
                </span>
                <button
                  onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                  disabled={currentPage === totalPages}
                  className="px-3 py-1.5 rounded-lg bg-[#12141F] border border-[#202438] text-xs text-gray-400 hover:text-white disabled:opacity-40 disabled:cursor-not-allowed flex items-center space-x-1"
                >
                  <span>Next</span>
                  <ChevronRight className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={() => setCurrentPage(totalPages)}
                  disabled={currentPage === totalPages}
                  className="px-3 py-1.5 rounded-lg bg-[#12141F] border border-[#202438] text-xs text-gray-400 hover:text-white disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  Last
                </button>
              </div>
            )}
          </div>
        )}

        {/* ==================== SOURCE 2: YOUR CLONE VIEW ==================== */}
        {activeSource === "clone" && (
          <div className="space-y-6 animate-in fade-in duration-200">
            {/* Slot & Plan Status Bar */}
            <div className="p-5 rounded-2xl bg-[#12141F] border border-[#202436] flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div>
                <div className="flex items-center space-x-2.5">
                  <span className="text-xs font-bold text-gray-400 tracking-wider uppercase">Your Cloned Voice Allocation</span>
                  <span className={`text-xs font-bold px-2.5 py-0.5 rounded-full ${
                    userCloneData?.saved_count
                      ? "bg-teal-500/20 text-teal-300 border border-teal-500/30"
                      : "bg-[#1C2033] text-gray-400"
                  }`}>
                    {userCloneData ? `${userCloneData.saved_count} of ${userCloneData.max_clones} saved` : "1 of 1 slot"}
                  </span>
                </div>
                <p className="text-xs text-gray-400 mt-1">
                  Each user can have one uploaded voice and one corresponding cloned voice at a time. Uploading a new recording updates and replaces your previous clone.
                </p>
              </div>

              {!userCloneData?.can_clone && (
                <Link
                  href="/app/billing"
                  className="px-4 py-2 rounded-xl text-xs font-semibold bg-gradient-to-r from-purple-600 to-indigo-600 text-white shadow-md hover:opacity-95 transition-opacity shrink-0 flex items-center space-x-1.5"
                >
                  <Crown className="w-3.5 h-3.5" />
                  <span>Upgrade Plan</span>
                </Link>
              )}
            </div>

            {/* If user HAS an active cloned voice (1 of 1) */}
            {userCloneData?.voice && (
              <div className="space-y-4">
                <h3 className="text-sm font-bold text-gray-200">Your Active Cloned Voice</h3>
                
                <div className={`p-5 rounded-2xl bg-[#12141F] border transition-all flex flex-col md:flex-row md:items-center justify-between gap-4 ${
                  userCloneData.voice.id === currentSelectedVoiceId
                    ? "border-teal-500/60 shadow-lg shadow-teal-600/10 ring-1 ring-teal-500/30"
                    : "border-[#202436] hover:border-[#2E334D]"
                }`}>
                  <div className="flex items-center space-x-4">
                    <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-teal-500/20 to-emerald-500/20 border border-teal-500/30 flex items-center justify-center text-teal-400 font-bold text-lg">
                      {userCloneData.voice.name[0]}
                    </div>
                    <div>
                      <div className="flex items-center space-x-2.5">
                        <h4 className="font-bold text-base text-white">{userCloneData.voice.name}</h4>
                        <span className="px-2.5 py-0.5 text-[11px] font-semibold rounded-full bg-teal-500/15 text-teal-400 border border-teal-500/25">
                          Your Clone (Custom)
                        </span>
                      </div>
                      <div className="text-xs text-gray-400 mt-1 flex items-center space-x-3">
                        <span>Model: {userCloneData.voice.model || "Custom Timbre"}</span>
                        <span>•</span>
                        <span>Accent: {userCloneData.voice.accent}</span>
                        <span>•</span>
                        <span>Single Cloned Voice Slot</span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center space-x-3">
                    {userCloneData.voice.preview_audio_url && (
                      <button
                        onClick={() => handlePlayPreview(userCloneData.voice!.id, userCloneData.voice!.preview_audio_url)}
                        className="flex items-center space-x-1.5 px-3.5 py-2 rounded-xl bg-[#181B2B] hover:bg-teal-600 hover:text-white text-gray-300 text-xs font-semibold transition-colors"
                      >
                        <Volume2 className="w-4 h-4" />
                        <span>{playingId === userCloneData.voice.id ? "Playing..." : "Preview Voice"}</span>
                      </button>
                    )}

                    <button
                      onClick={() => handleSelectVoice(userCloneData.voice!, "clone")}
                      className={`text-xs font-semibold px-4 py-2 rounded-xl transition-all flex items-center space-x-1.5 ${
                        userCloneData.voice.id === currentSelectedVoiceId
                          ? "bg-teal-600 text-white shadow-md shadow-teal-600/30"
                          : "bg-teal-600/20 text-teal-300 hover:bg-teal-600 hover:text-white border border-teal-500/30"
                      }`}
                    >
                      {userCloneData.voice.id === currentSelectedVoiceId ? (
                        <>
                          <Check className="w-4 h-4" />
                          <span>Active in Studio</span>
                        </>
                      ) : (
                        <span>Select Your Clone for Studio →</span>
                      )}
                    </button>

                    <button
                      onClick={() => handleDeleteClone(userCloneData.voice!.id)}
                      className="p-2 rounded-xl bg-[#181B2B] hover:bg-red-500/20 text-gray-400 hover:text-red-400 transition-colors"
                      title="Delete custom voice (resets to 0 of 1)"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* Upload or Replace Voice Form */}
            <div className="p-6 rounded-2xl bg-[#12141F] border border-[#202436] space-y-4">
              <div className="flex items-center space-x-2">
                <Upload className="w-4 h-4 text-teal-400" />
                <h3 className="font-bold text-sm text-white">
                  {userCloneData?.voice ? "Replace Your Cloned Voice" : "Create Your Cloned Voice"}
                </h3>
              </div>
              <p className="text-xs text-gray-400">
                {userCloneData?.voice
                  ? "Uploading a new audio sample will automatically update and replace your current clone. The new voice will immediately become active."
                  : "Upload a clean audio recording (10–30 seconds) of your voice to train and activate your private clone."}
              </p>

              {uploadError && (
                <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-xs flex items-center space-x-2">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  <span>{uploadError}</span>
                </div>
              )}

              {uploadSuccess && (
                <div className="p-3 rounded-xl bg-teal-500/10 border border-teal-500/20 text-teal-400 text-xs flex items-center space-x-2">
                  <CheckCircle2 className="w-4 h-4 shrink-0" />
                  <span>{uploadSuccess}</span>
                </div>
              )}

              <form onSubmit={handleUploadClone} className="space-y-4 pt-2">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-semibold text-gray-300 mb-1.5">
                      Voice name (optional)
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. My Studio Voice"
                      value={cloneName}
                      onChange={(e) => setCloneName(e.target.value)}
                      className="w-full px-3.5 py-2.5 bg-[#0B0C14] border border-[#23273D] rounded-xl text-xs text-gray-100 placeholder-gray-500 focus:outline-none focus:border-teal-500"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-gray-300 mb-1.5">
                      Upload audio file (.mp3 or .wav, max 10 MB)
                    </label>
                    <input
                      type="file"
                      accept=".mp3,.wav"
                      onChange={(e) => setCloneFile(e.target.files?.[0] || null)}
                      className="w-full px-3 py-2 bg-[#0B0C14] border border-[#23273D] rounded-xl text-xs text-gray-400 file:mr-3 file:py-1 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-teal-600 file:text-white hover:file:bg-teal-500"
                    />
                  </div>
                </div>

                {/* Consent checkboxes */}
                <div className="space-y-2 pt-2 border-t border-[#1C1F30]">
                  <label className="flex items-start space-x-2 text-xs text-gray-300 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={consentConfirmed}
                      onChange={(e) => setConsentConfirmed(e.target.checked)}
                      className="mt-0.5 rounded border-[#23273D] text-teal-600 focus:ring-0"
                    />
                    <span>I confirm that I own or have all necessary rights and explicit consent to clone and use this voice.</span>
                  </label>
                  <label className="flex items-start space-x-2 text-xs text-gray-300 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={rightsConfirmed}
                      onChange={(e) => setRightsConfirmed(e.target.checked)}
                      className="mt-0.5 rounded border-[#23273D] text-teal-600 focus:ring-0"
                    />
                    <span>I agree to the HK Speaks voice cloning terms and commercial license guidelines.</span>
                  </label>
                </div>

                <div className="pt-2 flex justify-end">
                  <button
                    type="submit"
                    disabled={isUploading || !cloneFile || !consentConfirmed || !rightsConfirmed}
                    className="px-5 py-2.5 rounded-xl text-xs font-semibold bg-teal-600 hover:bg-teal-500 disabled:opacity-50 disabled:cursor-not-allowed text-white shadow-lg shadow-teal-600/30 flex items-center space-x-2 transition-all"
                  >
                    {isUploading ? (
                      <>
                        <RefreshCw className="w-4 h-4 animate-spin" />
                        <span>Processing & Cloning Voice...</span>
                      </>
                    ) : (
                      <>
                        <Upload className="w-4 h-4" />
                        <span>{userCloneData?.voice ? "Replace & Save Voice" : "Save Voice"}</span>
                      </>
                    )}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default function VoicesPage() {
  return (
    <React.Suspense fallback={<div className="min-h-screen bg-[#090A0F]" />}>
      <VoicesContent />
    </React.Suspense>
  );
}
