"use client";

import React, { useState, useRef, useMemo } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  Upload,
  FileAudio,
  Sparkles,
  Copy,
  Check,
  FileText,
  RefreshCw,
  AlertCircle,
  Sliders,
  X,
  Clock,
  Music
} from "lucide-react";

interface ScenePrompt {
  scene_index: number;
  sentence: string;
  transcript_text?: string;
  image_prompt: string;
  start_time: number;
  end_time: number;
  duration: number;
  start_time_formatted?: string;
  end_time_formatted?: string;
  duration_formatted?: string;
}

export default function ImagePromptsPage() {
  // 1. SCRIPT
  const [scriptText, setScriptText] = useState<string>(
    "In the heart of an ancient observatory, astronomer Jonathan adjusted the brass lens.\n\nBeyond the telescope, an unexpected supernova pulsed with brilliant sapphire light.\n\nAs the cosmic shockwave reached the edge of the galaxy, alarms echoed through the station.\n\nWithout hesitation, he activated the emergency distress beacon and aimed the transmitter toward Earth."
  );

  // 2. IMAGE VISUAL STYLE PROMPT
  const [visualStylePrompt, setVisualStylePrompt] = useState<string>(
    "Cinematic 35mm film still, shallow depth of field, atmospheric volumetric lighting, anamorphic lens, 8k resolution, photorealistic masterpiece, highly detailed textures"
  );

  // 3. OPTIONAL VOICEOVER / AUDIO UPLOAD
  const [audioFile, setAudioFile] = useState<File | null>(null);
  const [audioPreviewUrl, setAudioPreviewUrl] = useState<string | null>(null);

  // Processing & Output States
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [scenes, setScenes] = useState<ScenePrompt[]>([]);
  const [hasAudioUploaded, setHasAudioUploaded] = useState<boolean>(false);
  const [audioTotalDuration, setAudioTotalDuration] = useState<number>(0);

  // Single large text box content for all generated prompts
  const [promptsOutput, setPromptsOutput] = useState<string>("");

  // Copy State
  const [isCopiedAll, setIsCopiedAll] = useState<boolean>(false);

  const fileInputRef = useRef<HTMLInputElement | null>(null);

  // Word & Sentence statistics
  const scriptStats = useMemo(() => {
    const text = scriptText.trim();
    if (!text) return { words: 0, sentences: 0 };
    const words = text.split(/\s+/).filter(Boolean).length;
    const sentences = text
      .split(/(?<=[.!?])\s+|\n+/)
      .map((s) => s.trim())
      .filter(Boolean).length;
    return { words, sentences };
  }, [scriptText]);

  // Handle audio selection
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setAudioFile(file);
      const url = URL.createObjectURL(file);
      setAudioPreviewUrl(url);
      setErrorMessage(null);
    }
  };

  const handleRemoveAudio = () => {
    setAudioFile(null);
    if (audioPreviewUrl) {
      URL.revokeObjectURL(audioPreviewUrl);
      setAudioPreviewUrl(null);
    }
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  // Clean prompt text from any meta instructions, template tags, or line breaks
  const sanitizePromptForGenerator = (text: string): string => {
    if (!text) return "";
    return text
      .replace(/\[\s*(?:ROLE|INPUT|GLOBAL\s+VISUAL\s+STYLE[^\]]*|INSTRUCTIONS[^\]]*|OUTPUT\s+TEMPLATE|OUTPUT\s+FORMAT|OUTPUT|TEMPLATE|INSERT\s+[^\]]+|RULES|SYSTEM|META|CINEMATIC\s+RULES|specific\s+visual\s+scene[^\]]*|characters[^\]]*|action[^\]]*|environment[^\]]*|camera[^\]]*|composition[^\]]*|lighting[^\]]*|color[^\]]*|visual\s+style\s+details[^\]]*|scene[^\]]*|characters\/action\/environment|camera\/composition|lighting\/color)\s*\]/gi, " ")
      .replace(/<\s*(?:INSERT\s+[^>]+|ROLE|INPUT|OUTPUT|TEMPLATE)\s*>/gi, " ")
      .replace(/^(?:\d+\.|\bINSERT\s+NUMBER\s+HERE\b\.*)\s*/gi, "")
      .replace(/^(?:\*\*)?(?:role|input|output\s+template|instructions|global\s+visual\s+style|rules)(?:\*\*)?\s*:\s*/gi, "")
      .replace(/[\r\n]+/g, " ")
      .replace(/\s+/g, " ")
      .replace(/\s*,\s*/g, ", ")
      .replace(/,\s*,+/g, ",")
      .replace(/^[,.\s]+/, "")
      .replace(/[,.\s]+$/, "")
      .trim();
  };

  // Generate Image Prompts
  const handleGeneratePrompts = async () => {
    setErrorMessage(null);

    if (!scriptText.trim()) {
      setErrorMessage("Please enter your narration script in Input 1.");
      return;
    }

    setIsProcessing(true);

    try {
      const formData = new FormData();
      formData.append("script", scriptText.trim());
      formData.append("visual_style_prompt", visualStylePrompt.trim());
      formData.append(
        "title",
        audioFile ? audioFile.name.replace(/\.[^/.]+$/, "") : "Script Narration Prompts"
      );

      if (audioFile) {
        formData.append("audio_file", audioFile);
      }

      const res = await fetch("http://127.0.0.1:8000/v1/image-prompts/generate", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || "Failed to generate image prompts.");
      }

      const data = await res.json();
      const generatedScenes: ScenePrompt[] = data.scenes || [];
      const hasAudio = Boolean(data.has_audio);
      setScenes(generatedScenes);
      setHasAudioUploaded(hasAudio);
      setAudioTotalDuration(data.total_duration || 0);

      // Format all prompts sequentially: each prompt is ONE continuous paragraph
      // No internal line breaks, no blank lines inside a prompt, only ONE blank line between numbered prompts
      // Strictly contains ONLY the visual description for the image generator
      const formattedPromptsText = generatedScenes
        .map((s, idx) => {
          const num = idx + 1;
          const cleanPrompt = sanitizePromptForGenerator(s.image_prompt || "");
          return `${num}. ${cleanPrompt}`;
        })
        .join("\n\n");

      setPromptsOutput(formattedPromptsText);

      // Scroll smoothly to results
      setTimeout(() => {
        const el = document.getElementById("generated-prompts-results");
        if (el) {
          el.scrollIntoView({ behavior: "smooth" });
        }
      }, 100);
    } catch (err: any) {
      console.error("Error generating prompts:", err);
      setErrorMessage(err.message || "Failed to generate image prompts. Please try again.");
    } finally {
      setIsProcessing(false);
    }
  };

  // ONE-CLICK "COPY ALL PROMPTS" button: Copies all prompts together in numbered format
  const handleCopyAllPrompts = () => {
    if (!promptsOutput.trim()) return;

    navigator.clipboard.writeText(promptsOutput);
    setIsCopiedAll(true);
    setTimeout(() => setIsCopiedAll(false), 2200);
  };

  return (
    <div className="min-h-screen w-full bg-[#08090E] text-gray-100 flex flex-col selection:bg-amber-500 selection:text-black">
      {/* STANDALONE MINIMAL HEADER */}
      <header className="h-16 px-6 border-b border-[#181C2B] bg-[#0C0E17]/95 backdrop-blur-md flex items-center justify-between flex-shrink-0 z-20">
        <div className="flex items-center space-x-4">
          <Link
            href="/"
            className="flex items-center space-x-2 px-3 py-1.5 rounded-xl bg-[#141724] hover:bg-[#1D2235] border border-[#21273C] text-xs font-semibold text-gray-300 hover:text-white transition-all shadow-sm group"
            title="Return to HK Speaks Homepage"
          >
            <ArrowLeft className="w-3.5 h-3.5 group-hover:-translate-x-0.5 transition-transform" />
            <span>Back to HK Speaks</span>
          </Link>

          <div className="h-4 w-px bg-[#202538]" />

          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-amber-500 to-orange-500 flex items-center justify-center shadow-md shadow-amber-500/20 text-black">
              <Sparkles className="w-4 h-4 fill-current" />
            </div>
            <div>
              <h1 className="text-sm font-bold text-white tracking-tight">Image Prompt Generator</h1>
              <p className="text-[11px] text-amber-400 font-medium">
                AI Script-to-Image Visual Prompts &bull; Standalone Feature
              </p>
            </div>
          </div>
        </div>
      </header>

      {/* MAIN CONTAINER */}
      <main className="flex-1 max-w-4xl w-full mx-auto p-6 md:p-8 flex flex-col space-y-8">
        {errorMessage && (
          <div className="p-4 rounded-xl bg-rose-950/40 border border-rose-800/50 flex items-center space-x-3 text-xs text-rose-300">
            <AlertCircle className="w-4 h-4 text-rose-400 flex-shrink-0" />
            <span>{errorMessage}</span>
          </div>
        )}

        {/* INPUTS CONTAINER: CONTAINS ONLY 3 INPUTS */}
        <section className="bg-[#0C0E18] border border-[#1B1F32] rounded-2xl p-6 shadow-xl flex flex-col space-y-6">
          {/* INPUT 1: SCRIPT */}
          <div className="flex flex-col space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-xs font-bold text-gray-200 uppercase tracking-wider flex items-center space-x-2">
                <span className="w-5 h-5 rounded-md bg-amber-500/15 text-amber-400 border border-amber-500/30 flex items-center justify-center font-mono text-[11px]">
                  1
                </span>
                <span className="flex items-center space-x-1.5">
                  <FileText className="w-3.5 h-3.5 text-amber-400" />
                  <span>Script</span>
                </span>
              </label>
              <span className="text-[11px] text-gray-400 font-mono">
                {scriptStats.words} words &bull; {scriptStats.sentences} sentence{scriptStats.sentences === 1 ? "" : "s"}
              </span>
            </div>

            <textarea
              value={scriptText}
              onChange={(e) => setScriptText(e.target.value)}
              placeholder="Paste your voiceover script or story narration paragraphs here..."
              rows={7}
              className="w-full bg-[#08090F] border border-[#1E2336] rounded-xl p-4 text-xs text-gray-100 placeholder-gray-600 focus:outline-none focus:border-amber-500 font-mono leading-relaxed resize-y"
            />
          </div>

          {/* INPUT 2: IMAGE VISUAL STYLE PROMPT */}
          <div className="flex flex-col space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-xs font-bold text-gray-200 uppercase tracking-wider flex items-center space-x-2">
                <span className="w-5 h-5 rounded-md bg-amber-500/15 text-amber-400 border border-amber-500/30 flex items-center justify-center font-mono text-[11px]">
                  2
                </span>
                <span className="flex items-center space-x-1.5">
                  <Sliders className="w-3.5 h-3.5 text-amber-400" />
                  <span>Image Visual Style Prompt</span>
                </span>
              </label>
              <span className="text-[10px] text-gray-500">Applied to every generated prompt</span>
            </div>

            <textarea
              value={visualStylePrompt}
              onChange={(e) => setVisualStylePrompt(e.target.value)}
              placeholder="Define lighting, camera lens, art style, atmosphere, rendering quality...&#10;e.g. Cinematic 35mm film still, shallow depth of field, atmospheric volumetric lighting, anamorphic lens, 8k resolution, photorealistic masterpiece"
              rows={3}
              className="w-full bg-[#08090F] border border-[#1E2336] rounded-xl p-3.5 text-xs text-amber-200/90 placeholder-gray-600 focus:outline-none focus:border-amber-500 font-mono leading-relaxed resize-y"
            />
          </div>

          {/* INPUT 3: OPTIONAL VOICEOVER / AUDIO UPLOAD */}
          <div className="flex flex-col space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-xs font-bold text-gray-200 uppercase tracking-wider flex items-center space-x-2">
                <span className="w-5 h-5 rounded-md bg-amber-500/15 text-amber-400 border border-amber-500/30 flex items-center justify-center font-mono text-[11px]">
                  3
                </span>
                <span className="flex items-center space-x-1.5">
                  <Music className="w-3.5 h-3.5 text-amber-400" />
                  <span>Optional Voiceover / Audio Upload</span>
                </span>
              </label>
              <span className="text-[10px] text-amber-400/90 font-mono px-2 py-0.5 rounded bg-amber-500/10 border border-amber-500/20">
                Optional
              </span>
            </div>

            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileChange}
              accept="audio/*,video/mp4"
              className="hidden"
            />

            {audioFile ? (
              <div className="p-3.5 rounded-xl bg-[#121524] border border-amber-500/35 flex flex-col space-y-2.5">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3 overflow-hidden">
                    <div className="w-9 h-9 rounded-lg bg-amber-500/20 text-amber-400 flex items-center justify-center flex-shrink-0">
                      <FileAudio className="w-5 h-5" />
                    </div>
                    <div className="overflow-hidden">
                      <p className="text-xs font-bold text-white truncate">{audioFile.name}</p>
                      <p className="text-[11px] text-gray-400 font-mono">
                        {(audioFile.size / (1024 * 1024)).toFixed(2)} MB &bull; Spoken timing synchronization active
                      </p>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={handleRemoveAudio}
                    className="p-1.5 rounded-lg bg-[#1D2235] hover:bg-rose-900/50 text-gray-400 hover:text-rose-300 transition-colors"
                    title="Remove audio file"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>

                {audioPreviewUrl && (
                  <audio
                    src={audioPreviewUrl}
                    controls
                    className="w-full h-8 rounded-lg opacity-90"
                  />
                )}
              </div>
            ) : (
              <div
                onClick={() => fileInputRef.current?.click()}
                className="border-2 border-dashed border-[#20253B] hover:border-amber-500/60 rounded-xl p-5 text-center cursor-pointer transition-all bg-[#08090F]/70 hover:bg-[#0E111B] flex flex-col items-center justify-center group"
              >
                <Upload className="w-6 h-6 text-gray-500 group-hover:text-amber-400 mb-2 transition-colors" />
                <span className="text-xs font-semibold text-gray-300 group-hover:text-white">
                  Click to select voiceover audio file (.mp3, .wav, .m4a)
                </span>
                <span className="text-[11px] text-gray-500 mt-1">
                  Optional: If uploaded, sentence start time, end time, and duration will be calculated from actual speech
                </span>
              </div>
            )}
          </div>

          {/* GENERATE IMAGE PROMPTS BUTTON */}
          <div className="pt-2">
            <button
              onClick={handleGeneratePrompts}
              disabled={isProcessing || !scriptText.trim()}
              className="w-full py-3.5 rounded-xl bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-400 hover:to-orange-400 text-black font-extrabold text-sm shadow-lg shadow-amber-500/20 transition-all disabled:opacity-40 flex items-center justify-center space-x-2 active:scale-[0.99] cursor-pointer"
            >
              {isProcessing ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  <span>Analyzing Script &amp; Generating Prompts...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4 fill-current" />
                  <span>Generate Image Prompts</span>
                </>
              )}
            </button>
          </div>
        </section>

        {/* OUTPUT SECTION: ALL PROMPTS INSIDE ONE SINGLE LARGE TEXT BOX */}
        <section id="generated-prompts-results" className="bg-[#0C0E18] border border-[#1B1F32] rounded-2xl p-6 shadow-xl flex flex-col space-y-4">
          {/* Section Header with ONLY ONE "COPY ALL PROMPTS" BUTTON */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-[#181C2B] gap-3">
            <div className="flex items-center space-x-3">
              <h2 className="text-sm font-bold uppercase tracking-wider text-gray-200 flex items-center space-x-2">
                <Sparkles className="w-4 h-4 text-amber-400" />
                <span>Generated Image Prompts</span>
              </h2>

              {scenes.length > 0 && (
                <span className="text-xs font-mono px-2.5 py-0.5 rounded-md bg-amber-500/15 text-amber-300 border border-amber-500/30 font-bold">
                  {scenes.length} {scenes.length === 1 ? "Prompt" : "Prompts"}
                </span>
              )}

              {hasAudioUploaded && audioTotalDuration > 0 && (
                <span className="text-[11px] font-mono px-2.5 py-0.5 rounded-md bg-purple-500/15 text-purple-300 border border-purple-500/30">
                  Audio: {audioTotalDuration.toFixed(2)}s
                </span>
              )}
            </div>

            {/* ONLY ONE "COPY ALL PROMPTS" BUTTON */}
            <div>
              <button
                type="button"
                onClick={handleCopyAllPrompts}
                disabled={!promptsOutput.trim()}
                className="flex items-center space-x-2 px-4 py-2 rounded-xl bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-400 hover:to-orange-400 text-black text-xs font-extrabold transition-all disabled:opacity-40 shadow-md shadow-amber-500/20 active:scale-95 cursor-pointer"
                title="Copy all prompts together in numbered format"
              >
                {isCopiedAll ? (
                  <>
                    <Check className="w-4 h-4 stroke-[3]" />
                    <span>Copied!</span>
                  </>
                ) : (
                  <>
                    <Copy className="w-4 h-4" />
                    <span>COPY ALL PROMPTS</span>
                  </>
                )}
              </button>
            </div>
          </div>

          {/* ONE SINGLE LARGE EDITABLE TEXT BOX */}
          <div className="flex flex-col space-y-2">
            <textarea
              value={promptsOutput}
              onChange={(e) => setPromptsOutput(e.target.value)}
              placeholder="All generated image prompts will appear here numbered sequentially (1., 2., 3., 4., etc.) with one blank line between each prompt.&#10;&#10;You can freely select, edit, or copy text directly from this box."
              rows={16}
              className="w-full min-h-[380px] bg-[#07080F] border border-[#1E2336] focus:border-amber-500 rounded-xl p-4 text-xs font-mono text-amber-100 placeholder-gray-600 leading-relaxed resize-y select-text focus:outline-none"
            />
            <div className="flex items-center justify-between text-[11px] text-gray-500 font-mono pt-1">
              <span>Editable &bull; Selectable &bull; Numbered format</span>
              <span>Click &ldquo;COPY ALL PROMPTS&rdquo; to copy all to clipboard</span>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
