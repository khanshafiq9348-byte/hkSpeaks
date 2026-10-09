"use client";

import React, { useState, useEffect, useMemo, useRef } from "react";
import AudioPlayer from "@/components/AudioPlayer";
import VoiceSelectorModal, { Voice } from "@/components/VoiceSelectorModal";
import UploadedVoiceModal from "@/components/UploadedVoiceModal";
import { apiClient, ApiException, API_BASE_URL, getPlayableAudioUrl } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { 
  Sparkles, 
  Sliders, 
  Play, 
  Pause,
  Loader2, 
  AlertCircle, 
  CheckCircle2, 
  Volume2, 
  FileText, 
  Wand2,
  Crown,
  Upload,
  ArrowLeft,
  UserCheck,
  Trash2,
  Zap,
  Globe,
  Check,
  Clock
} from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";

interface Preset {
  name: string;
  speed: number;
  pitch: number;
  stability: number;
  style: number;
  expressiveness?: number;
  diversity?: number;
}

const PRESETS: Record<string, Preset> = {
  natural: { name: "Natural", speed: 1.0, pitch: 0.0, stability: 0.5, style: 0.0, expressiveness: 0.7, diversity: 0.7 },
  documentary: { name: "Documentary", speed: 0.9, pitch: -1.0, stability: 0.7, style: 0.2, expressiveness: 0.6, diversity: 0.5 },
  storytelling: { name: "Storytelling", speed: 0.95, pitch: 0.5, stability: 0.45, style: 0.4, expressiveness: 0.85, diversity: 0.8 },
  podcast: { name: "Podcast", speed: 1.0, pitch: 0.0, stability: 0.55, style: 0.3, expressiveness: 0.75, diversity: 0.7 },
  energetic: { name: "Energetic", speed: 1.15, pitch: 1.5, stability: 0.4, style: 0.6, expressiveness: 0.9, diversity: 0.85 },
  calm: { name: "Calm", speed: 0.85, pitch: -0.5, stability: 0.8, style: 0.1, expressiveness: 0.5, diversity: 0.6 },
};

const STARTER_PROMPTS = [
  {
    label: "YouTube intro",
    text: "Hey everyone, welcome back to the channel! Today we're diving into something truly game-changing that will transform how you create content."
  },
  {
    label: "Anime voiceover",
    text: "You really believed you could defeat me? The power awakened in this sword is beyond anything your realm has ever witnessed!"
  },
  {
    label: "Story narration",
    text: "The ancient cobblestone road wound quietly through the misty pine forest, where shadows danced under the pale autumn moon."
  },
  {
    label: "Podcast intro",
    text: "Welcome to today's episode. Grab your favorite coffee, relax, and join us as we explore the uncharted frontiers of technology and storytelling."
  },
  {
    label: "Language practice",
    text: "Good morning and welcome! In today's listening session, we will practice everyday conversational English phrases with natural cadence."
  },
  {
    label: "Meditation guidance",
    text: "Take a slow, deep breath in through your nose. Hold for a moment, and gently let it go. Feel your mind settle into calm focus."
  },
  {
    label: "Product demo",
    text: "Meet the next-generation AI speech platform. Fast, authentic, and built from the ground up to bring your creative stories to life."
  },
  {
    label: "Game character",
    text: "Keep your guard up, warrior! The cavern ahead is fraught with danger, but glory and ancient treasures await those bold enough to proceed."
  }
];

function StudioContent() {
  const { user } = useAuth();
  const searchParams = useSearchParams();
  const categoryParam = searchParams.get("category");
  const voiceParam = searchParams.get("voice") || searchParams.get("voice_id");
  const typeParam = searchParams.get("type");
  const textParam = searchParams.get("text");
  const docIdParam = searchParams.get("docId");

  const [text, setText] = useState(
    "Welcome to HK Speaks AI Voice Studio. Experience natural cadence, authentic emotional range, and studio-grade clarity across every line."
  );
  const [voices, setVoices] = useState<Voice[]>([]);
  const [selectedVoice, setSelectedVoice] = useState<Voice | null>(null);
  const [userCloneData, setUserCloneData] = useState<{
    voice: Voice | null;
    can_clone: boolean;
    max_clones: number;
    saved_count: number;
  } | null>(null);
  const [playingId, setPlayingId] = useState<string | null>(null);
  const previewAudioRef = useRef<HTMLAudioElement | null>(null);
  const [isVoiceModalOpen, setIsVoiceModalOpen] = useState(false);
  const [isUploadedModalOpen, setIsUploadedModalOpen] = useState(false);
  const [isVoiceCloneModalOpen, setIsVoiceCloneModalOpen] = useState(false);

  // Settings
  const [presetKey, setPresetKey] = useState<string>("natural");
  const [speed, setSpeed] = useState<number>(1.0);
  const [pitch, setPitch] = useState<number>(0.0);
  const [volume, setVolume] = useState<number>(0); // dB (-20 to +20, 0 = neutral)
  const [expressiveness, setExpressiveness] = useState<number>(0.7); // 0.0 to 1.0
  const [diversity, setDiversity] = useState<number>(0.7); // 0.0 to 1.0
  const [format, setFormat] = useState<"mp3" | "wav">("mp3");

  // Generation state
  const [isGenerating, setIsGenerating] = useState(false);
  const [generationStatus, setGenerationStatus] = useState<string | null>(null);
  const [generationId, setGenerationId] = useState<string | null>(null);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [audioDuration, setAudioDuration] = useState<number>(0);
  const [generatedSpeed, setGeneratedSpeed] = useState<number | null>(null);
  const [error, setError] = useState<{ code: string; message: string } | null>(null);

  // Entitlement usage
  const [usage, setUsage] = useState<any>(null);

  // Determine effective category based on URL or current voice
  const effectiveCategory = useMemo(() => {
    if (categoryParam) return categoryParam;
    if (selectedVoice) {
      if (selectedVoice.type === "cloned" || selectedVoice.tier === "custom" || selectedVoice.voice_type === "clone" || Boolean(selectedVoice.owner_user_id)) {
        return "clone";
      }
      if (selectedVoice.provider === "elevenlabs") return "elevenlabs";
      if (selectedVoice.tier === "premium" || selectedVoice.tier === "ultra") return "premium";
      if (selectedVoice.provider === "edge") return "edge";
      return "library";
    }
    return "library";
  }, [categoryParam, selectedVoice]);

  useEffect(() => {
    loadVoices();
    loadUsage();
  }, [user]);

  useEffect(() => {
    if (textParam) {
      try {
        setText(decodeURIComponent(textParam));
      } catch {
        setText(textParam);
      }
    }
  }, [textParam]);

  const handlePlayPreview = (voiceId: string, url?: string) => {
    if (playingId === voiceId) {
      if (previewAudioRef.current) {
        previewAudioRef.current.pause();
      }
      setPlayingId(null);
      return;
    }
    if (previewAudioRef.current) {
      previewAudioRef.current.pause();
    }
    const targetUrl = url ? (getPlayableAudioUrl(url) || url) : `${API_BASE_URL}/voices/${voiceId}/preview`;
    const audio = new Audio(targetUrl);
    previewAudioRef.current = audio;
    audio.play().catch(() => {});
    setPlayingId(voiceId);
    audio.onended = () => setPlayingId(null);
    audio.onerror = () => setPlayingId(null);
  };

  const handleDeleteClone = async (voiceId: string) => {
    if (!confirm("Are you sure you want to delete your custom voice clone? This will clear your slot back to 0 of 1 saved.")) return;
    try {
      await apiClient(`/voices/${voiceId}`, { method: "DELETE" });
      if (selectedVoice?.id === voiceId) {
        if (typeof window !== "undefined") {
          localStorage.removeItem("hk_selected_voice_id");
          localStorage.removeItem("hk_selected_voice_type");
        }
        setSelectedVoice(null);
      }
      await loadVoices();
    } catch {
      // ignore
    }
  };

  const loadVoices = async () => {
    try {
      const data = await apiClient<Voice[]>("/voices");

      let cloneVoice: Voice | null = null;
      try {
        const cloneData = await apiClient<{ has_clone?: boolean; voice?: Voice | null; can_clone?: boolean; max_clones?: number; saved_count?: number }>("/voices/user-clone");
        setUserCloneData(cloneData as any);
        if (cloneData && cloneData.voice) {
          cloneVoice = {
            ...cloneData.voice,
            type: "cloned",
            voice_type: "clone",
            tier: "custom",
          };
        }
      } catch (err) {
        console.error("Failed to load user clone:", err);
      }

      // Combine clone voice with library voices so VoiceSelectorModal has it in 'Your Clone' tab
      const allVoices = cloneVoice ? [cloneVoice, ...data.filter((v) => v.id !== cloneVoice!.id)] : data;
      setVoices(allVoices);

      const storedVoiceId = typeof window !== "undefined" ? localStorage.getItem("hk_selected_voice_id") : null;
      const storedVoiceType = typeof window !== "undefined" ? localStorage.getItem("hk_selected_voice_type") : null;
      const storedVoiceObj = typeof window !== "undefined" ? localStorage.getItem("hk_selected_voice_obj") : null;
      const targetVoiceId = voiceParam || storedVoiceId;
      const targetVoiceType = typeParam || storedVoiceType;

      // 0. If user is visiting clone view or target type is cloned, select user's cloned voice immediately!
      if ((categoryParam === "clone" || targetVoiceType === "cloned" || targetVoiceType === "clone") && cloneVoice) {
        setSelectedVoice(cloneVoice);
        return;
      }

      // 1. If user currently has a cloned voice selected and no new explicit voiceParam was passed in URL, preserve it
      if (selectedVoice && (selectedVoice.type === "cloned" || selectedVoice.tier === "custom") && !voiceParam) {
        if (cloneVoice && cloneVoice.id === selectedVoice.id) {
          setSelectedVoice(cloneVoice);
        }
        return;
      }

      // 2. Check if requested target is the cloned voice or target type is cloned
      if (
        targetVoiceType === "cloned" ||
        targetVoiceType === "clone" ||
        (cloneVoice && targetVoiceId === cloneVoice.id)
      ) {
        if (cloneVoice) {
          setSelectedVoice(cloneVoice);
          return;
        } else if (storedVoiceObj) {
          try {
            const parsed = JSON.parse(storedVoiceObj);
            if (parsed && (parsed.type === "cloned" || parsed.tier === "custom")) {
              setSelectedVoice({ ...parsed, type: "cloned", voice_type: "clone", tier: "custom" });
              return;
            }
          } catch {
            // ignore JSON error
          }
        }
        // If stored was cloned voice, NEVER auto-select or replace with a Library voice!
        return;
      }

      // 3. Match in library voices only if targetVoiceId was explicitly for a library voice
      if (targetVoiceId && targetVoiceType !== "cloned" && targetVoiceType !== "clone" && data.length > 0) {
        const matched = data.find((v) => v.id === targetVoiceId || v.slug === targetVoiceId);
        if (matched) {
          setSelectedVoice({ ...matched, type: "library", voice_type: "library" });
          return;
        }
      }

      // 4. If no voice is selected yet, and user has an active cloneVoice, select it
      if (!selectedVoice && cloneVoice && (!targetVoiceId || targetVoiceId === cloneVoice.id)) {
        setSelectedVoice(cloneVoice);
        return;
      }

      // 5. Default fallback to first library voice if no voice is selected and not cloned target
      if (!selectedVoice && data.length > 0 && targetVoiceType !== "cloned" && targetVoiceType !== "clone") {
        setSelectedVoice({ ...data[0], type: "library", voice_type: "library" });
      }
    } catch {
      // ignore
    }
  };

  const handleSelectVoice = (v: Voice) => {
    const isCloned = v.type === "cloned" || v.tier === "custom" || v.voice_type === "clone" || Boolean(v.owner_user_id);
    const enhancedVoice: Voice = {
      ...v,
      type: isCloned ? "cloned" : "library",
      voice_type: isCloned ? "clone" : "library",
      tier: isCloned ? "custom" : v.tier,
    };
    setSelectedVoice(enhancedVoice);
    if (typeof window !== "undefined") {
      localStorage.setItem("hk_selected_voice_id", enhancedVoice.id);
      localStorage.setItem("hk_selected_voice_type", isCloned ? "cloned" : "library");
      localStorage.setItem("hk_selected_voice_name", enhancedVoice.name);
      localStorage.setItem("hk_selected_voice_obj", JSON.stringify(enhancedVoice));
    }
  };

  // React to sidebar category changes without creating a second selector or auto-overwriting active voice
  useEffect(() => {
    if (!categoryParam) return;

    if (categoryParam === "clone") {
      if (userCloneData?.voice) {
        if (!selectedVoice || selectedVoice.id !== userCloneData.voice.id) {
          handleSelectVoice(userCloneData.voice);
        }
      } else if (userCloneData && !userCloneData.voice) {
        setIsUploadedModalOpen(true);
      }
    } else if (categoryParam === "premium" || categoryParam === "elevenlabs" || categoryParam === "edge" || categoryParam === "library") {
      setIsVoiceModalOpen(true);
    }
  }, [categoryParam, userCloneData?.voice, selectedVoice?.id]);

  const loadUsage = async () => {
    try {
      const data = await apiClient<any>("/billing/usage");
      setUsage(data);
    } catch {
      // ignore
    }
  };

  const applyPreset = (key: string) => {
    setPresetKey(key);
    const p = PRESETS[key];
    if (p) {
      setSpeed(p.speed);
      setPitch(p.pitch);
      if (p.expressiveness !== undefined) setExpressiveness(p.expressiveness);
      if (p.diversity !== undefined) setDiversity(p.diversity);
    }
  };

  const charCount = text.trim().length;
  const estimatedSeconds = Math.round(Math.max(1, charCount / (15 * speed)));

  const handleGenerate = async () => {
    if (charCount === 0) {
      setError({ code: "TEXT_REQUIRED", message: "Please enter text in the editor before generating speech." });
      return;
    }

    // Safety guard: determine effective voice
    // If user is on the clone screen and has an active clone, ensure it is selected and used
    let targetVoice = selectedVoice;
    if (effectiveCategory === "clone" && userCloneData?.voice) {
      if (!targetVoice || targetVoice.type !== "cloned" || targetVoice.id !== userCloneData.voice.id) {
        targetVoice = {
          ...userCloneData.voice,
          type: "cloned",
          voice_type: "clone",
          tier: "custom",
        };
        setSelectedVoice(targetVoice);
      }
    }

    if (!targetVoice) {
      const storedVoiceType = typeof window !== "undefined" ? localStorage.getItem("hk_selected_voice_type") : null;
      if (storedVoiceType === "cloned" || storedVoiceType === "clone") {
        setError({
          code: "CLONED_VOICE_MISSING",
          message: "Selected cloned voice is missing. Please create or select your cloned voice.",
        });
      } else {
        setError({
          code: "VOICE_REQUIRED",
          message: "Please select a voice before generating.",
        });
      }
      return;
    }

    const isCloned =
      targetVoice.type === "cloned" ||
      targetVoice.tier === "custom" ||
      targetVoice.voice_type === "clone" ||
      Boolean(targetVoice.owner_user_id);
    const voiceType: "cloned" | "library" = isCloned ? "cloned" : "library";

    if (isCloned && !targetVoice.id) {
      setError({
        code: "CLONED_VOICE_MISSING",
        message: "Cloned voice ID is missing. Please select or create your cloned voice.",
      });
      return;
    }

    console.log(`[Studio Voice Routing] Dispatching TTS request:`, {
      id: targetVoice.id,
      name: targetVoice.name,
      voice_type: voiceType,
      tier: targetVoice.tier,
      model: targetVoice.model,
      provider: targetVoice.provider,
    });

    setIsGenerating(true);
    setGenerationStatus("queued");
    setError(null);
    setAudioUrl(null);

    try {
      const payload = {
        text,
        voice_id: targetVoice.id,
        voice_type: voiceType,
        project_document_id: docIdParam || undefined,
        format,
        speed,
        pitch,
        volume,
        expressiveness,
        diversity,
        stability: PRESETS[presetKey]?.stability || 0.5,
        style: PRESETS[presetKey]?.style || 0.0,
      };

      const gen = await apiClient<any>("/text-to-speech", {
        method: "POST",
        body: JSON.stringify(payload),
      });

      setGenerationId(gen.id);

      // Poll status
      pollStatus(gen.id);
    } catch (err: any) {
      setIsGenerating(false);
      setGenerationStatus(null);
      if (err instanceof ApiException) {
        setError({ code: err.code, message: err.message });
      } else {
        setError({ code: "UNKNOWN", message: err.message || "Generation request failed." });
      }
    }
  };

  const pollStatus = async (id: string) => {
    const interval = setInterval(async () => {
      try {
        const res = await apiClient<any>(`/generations/${id}`);
        setGenerationStatus(res.status);

        if (res.status === "completed") {
          clearInterval(interval);
          setIsGenerating(false);
          setAudioUrl(res.audio_url);
          setAudioDuration(res.actual_audio_seconds);
          setGeneratedSpeed(res.settings_json?.speed ?? speed);
          console.log(`[Studio Voice Routing] TTS Completed successfully:`, {
            id: res.id,
            voice_id: res.voice_id,
            model: res.model,
            audio_url: res.audio_url,
          });
          loadUsage();
        } else if (res.status === "failed") {
          clearInterval(interval);
          setIsGenerating(false);
          setError({
            code: res.error_code || "GENERATION_FAILED",
            message: res.error_message || "Generation failed in worker.",
          });
          loadUsage();
        }
      } catch {
        clearInterval(interval);
        setIsGenerating(false);
      }
    }, 800);
  };

  return (
    <div className="flex-1 flex flex-col min-w-0 h-full overflow-y-auto bg-[#090A0F] text-gray-100">
      {/* Studio Header Bar */}
      <div className="h-16 px-6 border-b border-[#1E2333]/80 bg-[#0C0E17]/60 backdrop-blur-md flex items-center justify-between shrink-0">
        <div className="flex items-center space-x-4">
          <Link
            href="/"
            className="flex items-center space-x-2 px-3 py-1.5 rounded-xl bg-[#141724] hover:bg-[#1D2235] border border-[#21273C] text-xs font-semibold text-gray-300 hover:text-white transition-all shadow-sm group"
            title="Return to HK Speaks Landing Page"
          >
            <ArrowLeft className="w-3.5 h-3.5 group-hover:-translate-x-0.5 transition-transform" />
            <span>Back to HK Speaks</span>
          </Link>

          <div className="h-4 w-px bg-[#202538]" />

          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded-lg bg-indigo-500/10 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
              <Sparkles className="w-4 h-4" />
            </div>
            <div>
              <h1 className="text-base font-bold text-white tracking-tight">AI Voice Studio</h1>
              <p className="text-[11px] text-gray-400">Transform written words into hyper-realistic human voiceovers</p>
            </div>
          </div>
        </div>

        {/* Right header indicators */}
        <div className="flex items-center space-x-3">
          {selectedVoice && (
            <div className="hidden sm:flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-[#141724] border border-[#23283E] text-xs">
              <span className="text-gray-400">Active Voice:</span>
              <span className="font-semibold text-indigo-300">{selectedVoice.name}</span>
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-400 font-mono capitalize">
                {selectedVoice.tier}
              </span>
            </div>
          )}
          {usage && (
            <div className="hidden md:flex items-center space-x-2 text-xs text-gray-400 bg-[#141724] px-3 py-1.5 rounded-lg border border-[#23283E]">
              <span>Remaining:</span>
              <span className="font-mono text-emerald-400 font-semibold">{usage.characters_remaining?.toLocaleString() || 0}</span>
              <span>chars</span>
            </div>
          )}
        </div>
      </div>

      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Script Editor (7 cols) */}
        <div className="lg:col-span-7 flex flex-col space-y-4">
          <div className="p-5 rounded-2xl bg-[#12141F] border border-[#202436] flex-1 flex flex-col shadow-xl">
            {/* Header bar */}
            <div className="flex items-center justify-between pb-3 border-b border-[#1E2235]">
              <div className="flex items-center space-x-2">
                <FileText className="w-4 h-4 text-indigo-400" />
                <span className="font-semibold text-sm text-gray-200">Script Editor</span>
              </div>

              {/* Character & Credit counter & Estimated Duration */}
              <div className="flex items-center space-x-3 text-xs text-gray-400 font-mono">
                <span>{charCount.toLocaleString()} chars</span>
                <span>•</span>
                <span className="text-indigo-300 font-semibold">{charCount.toLocaleString()} credits (1 credit/char)</span>
                <span>•</span>
                <span>~{estimatedSeconds}s</span>
              </div>
            </div>

            {/* Editor Textarea */}
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Paste or type your script here, or select a starter template below..."
              rows={12}
              className="w-full mt-4 flex-1 bg-transparent text-gray-100 placeholder-gray-600 resize-none focus:outline-none text-base leading-relaxed"
            />

            {/* Quick Starter Chips */}
            <div className="mt-3 pt-3 border-t border-[#1C2030] space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-semibold text-gray-400 flex items-center space-x-1.5">
                  <Sparkles className="w-3 h-3 text-indigo-400" />
                  <span>Quick Starter Scripts</span>
                </span>
                {charCount > 0 && (
                  <button
                    type="button"
                    onClick={() => setText("")}
                    className="text-[11px] text-gray-500 hover:text-gray-300 transition-colors"
                  >
                    Clear Editor
                  </button>
                )}
              </div>
              <div className="flex flex-wrap gap-1.5">
                {STARTER_PROMPTS.map((starter) => (
                  <button
                    key={starter.label}
                    type="button"
                    onClick={() => setText(starter.text)}
                    className="px-2.5 py-1 rounded-lg bg-[#161826] hover:bg-[#202438] border border-[#23273D] text-[11px] font-medium text-gray-300 hover:text-white transition-all"
                  >
                    {starter.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Error banner if any */}
            {error && (
              <div className="mt-4 p-3.5 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-xs flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  <span>{error.message}</span>
                </div>
                {error.code === "PREMIUM_REQUIRED" || error.code === "QUOTA_EXCEEDED" ? (
                  <Link
                    href="/app/billing"
                    className="px-3 py-1 rounded-lg bg-red-500/20 hover:bg-red-500/30 text-red-300 font-semibold text-xs transition-colors shrink-0 ml-3"
                  >
                    Upgrade Plan
                  </Link>
                ) : null}
              </div>
            )}
          </div>

          {/* 5-Hour Auto-Delete Lifecycle Policy Notice */}
          <div className="p-3.5 rounded-xl bg-[#12141F] border border-[#202436] flex items-center justify-between text-xs text-gray-400 shadow-md">
            <div className="flex items-center space-x-2.5">
              <Clock className="w-4 h-4 text-amber-400 shrink-0" />
              <span>
                <strong className="text-gray-200">5-Hour Auto Cleanup:</strong> Generated voice-overs and temporary audio files are automatically purged after 5 hours.
              </span>
            </div>
            <span className="text-[10px] px-2 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/20 font-mono shrink-0 ml-3">
              Lifecycle Active
            </span>
          </div>

          {/* Generated Audio Player output */}
          <AudioPlayer
            src={audioUrl}
            title="Generated Audio"
            voiceName={selectedVoice?.name}
            duration={audioDuration}
            format={format}
            speed={generatedSpeed ?? speed}
          />
        </div>

        {/* Right Column: Voice & Studio Controls (5 cols) */}
        <div className="lg:col-span-5 space-y-4">
          {/* SINGLE UNIFIED VOICE SELECTION & CONTROL AREA */}
          <div className="p-5 rounded-2xl bg-[#12141F] border border-[#202436] shadow-xl space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-[#1E2235]">
              <div className="flex items-center space-x-2">
                <span className="text-xs font-bold text-gray-300 tracking-wider uppercase">
                  {effectiveCategory === "clone"
                    ? "Voice Cloning / Your Clone"
                    : effectiveCategory === "premium"
                    ? "Premium Voices"
                    : effectiveCategory === "elevenlabs"
                    ? "ElevenLabs"
                    : effectiveCategory === "edge"
                    ? "Edge TTS"
                    : "Voice Library"}
                </span>
              </div>
              <span className={`text-[10px] px-2.5 py-0.5 rounded-full font-bold uppercase tracking-wider border ${
                effectiveCategory === "clone"
                  ? "bg-teal-500/15 text-teal-300 border-teal-500/30"
                  : effectiveCategory === "premium"
                  ? "bg-purple-500/15 text-purple-300 border-purple-500/30"
                  : effectiveCategory === "elevenlabs"
                  ? "bg-cyan-500/15 text-cyan-300 border-cyan-500/30"
                  : effectiveCategory === "edge"
                  ? "bg-sky-500/15 text-sky-300 border-sky-500/30"
                  : "bg-indigo-500/15 text-indigo-300 border-indigo-500/30"
              }`}>
                {effectiveCategory === "clone"
                  ? userCloneData?.voice ? "Your Clone Active" : "1 of 1 Slot"
                  : effectiveCategory === "premium"
                  ? "Premium Tier"
                  : effectiveCategory === "elevenlabs"
                  ? "ElevenLabs"
                  : effectiveCategory === "edge"
                  ? "Edge Neural"
                  : "Voice Library"}
              </span>
            </div>

            {effectiveCategory === "clone" ? (
              // CLONE SOURCE: shows cloned voice + clone management/upload option
              userCloneData?.voice ? (
                <div className="space-y-3">
                  <div
                    onClick={() => handleSelectVoice(userCloneData.voice!)}
                    className={`p-3.5 rounded-xl bg-[#0B0C14] border transition-all cursor-pointer flex items-center justify-between ${
                      selectedVoice?.id === userCloneData.voice.id
                        ? "border-teal-500 ring-1 ring-teal-500/50 shadow-md shadow-teal-500/10"
                        : "border-[#22263C] hover:border-teal-500/40"
                    }`}
                  >
                    <div className="flex items-center space-x-3">
                      <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-teal-500/20 to-emerald-500/20 border border-teal-500/30 flex items-center justify-center text-teal-400 font-bold text-sm">
                        {userCloneData.voice.name[0]}
                      </div>
                      <div>
                        <div className="flex items-center space-x-2">
                          <span className="font-semibold text-sm text-white">{userCloneData.voice.name}</span>
                          {selectedVoice?.id === userCloneData.voice.id ? (
                            <span className="px-1.5 py-0.2 text-[9px] font-bold rounded flex items-center space-x-1 bg-teal-500/20 text-teal-300 border border-teal-500/30">
                              <Check className="w-2.5 h-2.5 stroke-[3]" />
                              <span>Selected</span>
                            </span>
                          ) : (
                            <span className="px-1.5 py-0.2 text-[9px] font-medium rounded bg-gray-800 text-gray-400 border border-gray-700">
                              Click to Select
                            </span>
                          )}
                          <span className="px-1.5 py-0.2 text-[9px] font-bold rounded bg-teal-500/20 text-teal-300 border border-teal-500/30">
                            1 of 1 Slot
                          </span>
                        </div>
                        <div className="text-xs text-gray-400 mt-0.5">
                          Model: {userCloneData.voice.model || "Custom Timbre"} • Private Voice Clone
                        </div>
                      </div>
                    </div>

                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        handlePlayPreview(userCloneData.voice!.id, userCloneData.voice!.preview_audio_url);
                      }}
                      className={`p-2 rounded-lg transition-colors flex items-center space-x-1.5 text-xs font-semibold ${
                        playingId === userCloneData.voice.id
                          ? "bg-teal-600 text-white shadow-md shadow-teal-600/30"
                          : "bg-[#151726] hover:bg-[#20253B] text-gray-300 hover:text-white"
                      }`}
                      title={playingId === userCloneData.voice.id ? "Pause sample" : "Preview sample"}
                    >
                      {playingId === userCloneData.voice.id ? (
                        <Pause className="w-4 h-4 fill-current" />
                      ) : (
                        <Volume2 className="w-4 h-4" />
                      )}
                      <span className="hidden sm:inline">{playingId === userCloneData.voice.id ? "Playing" : "Preview"}</span>
                    </button>
                  </div>

                  <div className="flex items-center space-x-2">
                    <button
                      type="button"
                      onClick={() => setIsUploadedModalOpen(true)}
                      className="flex-1 py-2 px-3 rounded-xl bg-[#141724] hover:bg-teal-600/20 border border-[#23273D] hover:border-teal-500/40 text-teal-300 text-xs font-semibold flex items-center justify-center space-x-1.5 transition-all"
                    >
                      <Upload className="w-3.5 h-3.5 text-teal-400" />
                      <span>Replace / Update Cloned Voice</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => handleDeleteClone(userCloneData.voice!.id)}
                      className="p-2 rounded-xl bg-[#141724] hover:bg-red-500/20 border border-[#23273D] hover:border-red-500/30 text-gray-400 hover:text-red-400 transition-all"
                      title="Delete Clone"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              ) : (
                <div className="p-4 rounded-xl bg-[#0B0C14] border border-[#22263C] text-center space-y-3">
                  <div className="w-9 h-9 rounded-xl bg-teal-500/10 border border-teal-500/20 text-teal-400 mx-auto flex items-center justify-center">
                    <UserCheck className="w-5 h-5" />
                  </div>
                  <div>
                    <h4 className="text-xs font-semibold text-gray-200">No Cloned Voice Active</h4>
                    <p className="text-[11px] text-gray-400 mt-0.5">Upload a clean audio sample to create your 1 private clone.</p>
                  </div>
                  <button
                    type="button"
                    onClick={() => setIsUploadedModalOpen(true)}
                    className="w-full py-2 px-3 rounded-xl bg-teal-600 hover:bg-teal-500 text-white text-xs font-semibold shadow-md shadow-teal-600/30 flex items-center justify-center space-x-1.5 transition-all"
                  >
                    <Upload className="w-3.5 h-3.5" />
                    <span>Upload Audio & Create Clone</span>
                  </button>
                </div>
              )
            ) : (
              // LIBRARY / PROVIDER SOURCE (Edge, Premium, ElevenLabs, Other)
              <div className="space-y-3">
                <div className="p-3.5 rounded-xl bg-[#0B0C14] border border-[#22263C] flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <div className={`w-10 h-10 rounded-xl border flex items-center justify-center font-bold text-sm ${
                      effectiveCategory === "premium"
                        ? "bg-purple-500/20 border-purple-500/30 text-purple-300"
                        : effectiveCategory === "elevenlabs"
                        ? "bg-cyan-500/20 border-cyan-500/30 text-cyan-300"
                        : effectiveCategory === "other"
                        ? "bg-amber-500/20 border-amber-500/30 text-amber-300"
                        : "bg-indigo-500/20 border-indigo-500/30 text-indigo-300"
                    }`}>
                      {selectedVoice?.name ? selectedVoice.name[0] : <Volume2 className="w-4 h-4" />}
                    </div>
                    <div>
                      <div className="flex items-center space-x-2">
                        <span className="font-semibold text-sm text-gray-100">
                          {selectedVoice ? selectedVoice.name : "Select Voice"}
                        </span>
                        {selectedVoice && (
                          <span className="px-1.5 py-0.2 text-[9px] font-bold rounded flex items-center space-x-1 bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                            <Check className="w-2.5 h-2.5 stroke-[3]" />
                            <span>Selected</span>
                          </span>
                        )}
                        <span className="px-1.5 py-0.2 text-[9px] font-bold rounded capitalize bg-[#1A1D2E] text-gray-300 border border-[#262C47]">
                          {selectedVoice?.tier || "Standard"}
                        </span>
                      </div>
                      <div className="text-xs text-gray-400 capitalize mt-0.5">
                        {selectedVoice ? `${selectedVoice.language || "en"} • ${selectedVoice.accent || "Neutral"} • ${selectedVoice.gender || "Voice"}` : "Choose from library"}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center space-x-2">
                    {selectedVoice && (
                      <button
                        type="button"
                        onClick={() => handlePlayPreview(selectedVoice.id, selectedVoice.preview_audio_url)}
                        className={`p-2 rounded-lg transition-colors flex items-center space-x-1.5 text-xs font-semibold ${
                          playingId === selectedVoice.id
                            ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/30"
                            : "bg-[#151726] hover:bg-[#20253B] text-gray-300 hover:text-white"
                        }`}
                        title={playingId === selectedVoice.id ? "Pause sample" : "Preview sample"}
                      >
                        {playingId === selectedVoice.id ? (
                          <Pause className="w-4 h-4 fill-current" />
                        ) : (
                          <Volume2 className="w-4 h-4" />
                        )}
                        <span className="hidden sm:inline">{playingId === selectedVoice.id ? "Playing" : "Preview"}</span>
                      </button>
                    )}
                    <button
                      type="button"
                      onClick={() => setIsVoiceModalOpen(true)}
                      className="px-3 py-1.5 rounded-lg bg-[#181B2B] hover:bg-indigo-600 hover:text-white text-xs font-semibold text-indigo-400 border border-[#262A40] transition-colors"
                    >
                      Change Voice
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Presets & Acoustic Parameters */}
          <div className="p-5 rounded-2xl bg-[#12141F] border border-[#202436] shadow-xl space-y-5">
            {!(selectedVoice?.type === "cloned" || selectedVoice?.tier === "custom" || selectedVoice?.voice_type === "clone") ? (
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-xs font-semibold text-gray-400 flex items-center space-x-1.5">
                    <Wand2 className="w-3.5 h-3.5 text-indigo-400" />
                    <span>Style Presets</span>
                  </label>
                </div>

                <div className="grid grid-cols-3 gap-2">
                  {Object.entries(PRESETS).map(([key, p]) => (
                    <button
                      key={key}
                      onClick={() => applyPreset(key)}
                      className={`py-2 px-2.5 rounded-xl text-xs font-medium text-center transition-all ${
                        presetKey === key
                          ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/30"
                          : "bg-[#0B0C14] text-gray-400 hover:text-gray-200 border border-[#202438]"
                      }`}
                    >
                      {p.name}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <div className="p-3 rounded-xl bg-teal-500/10 border border-teal-500/20 text-xs text-teal-300 flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <span className="font-semibold text-white">Your Cloned Voice Active</span>
                </div>
                <span className="text-[10px] px-2 py-0.5 rounded bg-teal-500/20 text-teal-300 font-mono">
                  Exact Cloned Audio
                </span>
              </div>
            )}

            {/* Sliders: Speed, Volume (dB), Expressiveness, Diversity, Pitch */}
            <div className="space-y-3.5 pt-2 border-t border-[#1C1F30]">
              <div>
                <div className="flex items-center justify-between text-xs text-gray-400 mb-1.5 font-medium">
                  <span>Speed</span>
                  <span className="font-mono text-gray-200">{speed}x</span>
                </div>
                <input
                  type="range"
                  min="0.5"
                  max="2.0"
                  step="0.05"
                  value={speed}
                  onChange={(e) => setSpeed(parseFloat(e.target.value))}
                  className="w-full h-1.5 bg-[#202438] rounded-lg appearance-none cursor-pointer accent-indigo-500"
                />
              </div>

              <div>
                <div className="flex items-center justify-between text-xs text-gray-400 mb-1.5 font-medium">
                  <span>Volume</span>
                  <span className="font-mono text-gray-200">{volume > 0 ? `+${volume}` : volume} dB</span>
                </div>
                <input
                  type="range"
                  min="-20"
                  max="20"
                  step="1"
                  value={volume}
                  onChange={(e) => setVolume(parseInt(e.target.value, 10))}
                  className="w-full h-1.5 bg-[#202438] rounded-lg appearance-none cursor-pointer accent-indigo-500"
                />
              </div>

              <div>
                <div className="flex items-center justify-between text-xs text-gray-400 mb-1.5 font-medium">
                  <span>Expressiveness</span>
                  <span className="font-mono text-indigo-300">{Math.round(expressiveness * 100)}%</span>
                </div>
                <input
                  type="range"
                  min="0.0"
                  max="1.0"
                  step="0.05"
                  value={expressiveness}
                  onChange={(e) => setExpressiveness(parseFloat(e.target.value))}
                  className="w-full h-1.5 bg-[#202438] rounded-lg appearance-none cursor-pointer accent-indigo-500"
                />
              </div>

              <div>
                <div className="flex items-center justify-between text-xs text-gray-400 mb-1.5 font-medium">
                  <span>Diversity</span>
                  <span className="font-mono text-indigo-300">{Math.round(diversity * 100)}%</span>
                </div>
                <input
                  type="range"
                  min="0.0"
                  max="1.0"
                  step="0.05"
                  value={diversity}
                  onChange={(e) => setDiversity(parseFloat(e.target.value))}
                  className="w-full h-1.5 bg-[#202438] rounded-lg appearance-none cursor-pointer accent-indigo-500"
                />
              </div>

              <div>
                <div className="flex items-center justify-between text-xs text-gray-400 mb-1.5 font-medium">
                  <span>Pitch Fine-Tuning</span>
                  <span className="font-mono text-gray-200">{pitch > 0 ? `+${pitch}` : pitch}</span>
                </div>
                <input
                  type="range"
                  min="-10"
                  max="10"
                  step="0.5"
                  value={pitch}
                  onChange={(e) => setPitch(parseFloat(e.target.value))}
                  className="w-full h-1.5 bg-[#202438] rounded-lg appearance-none cursor-pointer accent-indigo-500"
                />
              </div>

              {/* Format selection */}
              <div className="flex items-center justify-between pt-2">
                <span className="text-xs text-gray-400 font-medium">Output Container</span>
                <div className="flex items-center space-x-1 bg-[#0B0C14] p-1 rounded-xl border border-[#202438]">
                  <button
                    onClick={() => setFormat("mp3")}
                    className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
                      format === "mp3" ? "bg-indigo-600 text-white" : "text-gray-400"
                    }`}
                  >
                    MP3
                  </button>
                  <button
                    onClick={() => setFormat("wav")}
                    className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
                      format === "wav" ? "bg-indigo-600 text-white" : "text-gray-400"
                    }`}
                  >
                    WAV
                  </button>
                </div>
              </div>
            </div>

            {/* Generate Action Button */}
            <button
              onClick={handleGenerate}
              disabled={isGenerating || charCount === 0}
              className="w-full py-3.5 rounded-xl font-semibold text-sm bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white shadow-xl shadow-indigo-600/30 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center justify-center space-x-2"
            >
              {isGenerating ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span className="capitalize">{generationStatus || "Synthesizing"}...</span>
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 fill-current" />
                  <span>Generate Speech</span>
                </>
              )}
            </button>

            {/* Quota preview bar */}
            {usage && (
              <div className="pt-2 border-t border-[#1C1F30] text-xs space-y-1 text-gray-400">
                <div className="flex items-center justify-between">
                  <span>Quota ({usage.plan_name})</span>
                  <span>{usage.characters_remaining.toLocaleString()} chars left</span>
                </div>
                <div className="w-full h-1 bg-[#1C1F30] rounded-full overflow-hidden">
                  <div
                    className="h-full bg-indigo-500 rounded-full"
                    style={{
                      width: `${Math.min(100, (usage.characters_used / (usage.characters_limit || 1)) * 100)}%`,
                    }}
                  />
                </div>
              </div>
            )}
          </div>
        </div>
      </main>

      {/* Voice Selector Modal */}
      <VoiceSelectorModal
        isOpen={isVoiceModalOpen}
        onClose={() => setIsVoiceModalOpen(false)}
        voices={voices}
        selectedVoiceId={selectedVoice?.id || ""}
        onSelectVoice={handleSelectVoice}
        userCanPremium={usage?.can_use_premium ?? true}
        initialCategory={effectiveCategory}
      />

      {/* Uploaded Voice Modal (Single Cloned Voice UI matching clean white reference) */}
      <UploadedVoiceModal
        isOpen={isUploadedModalOpen || isVoiceCloneModalOpen}
        onClose={() => {
          setIsUploadedModalOpen(false);
          setIsVoiceCloneModalOpen(false);
          loadVoices();
        }}
        selectedVoiceId={selectedVoice?.id || ""}
        onSelectVoice={(voice) => {
          handleSelectVoice(voice);
          setUserCloneData((prev) => ({
            voice: voice,
            can_clone: true,
            max_clones: 1,
            saved_count: 1,
          }));
          loadVoices();
        }}
        onSuccess={(voice) => {
          if (voice) {
            handleSelectVoice(voice);
          }
          loadVoices();
        }}
      />
    </div>
  );
}

export default function StudioPage() {
  return (
    <React.Suspense fallback={<div className="min-h-screen bg-[#090A0F]" />}>
      <StudioContent />
    </React.Suspense>
  );
}
