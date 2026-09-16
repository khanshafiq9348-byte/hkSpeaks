"use client";

import Link from "next/link";
import { 
  Mic2, 
  Film, 
  Sparkles, 
  ArrowRight, 
  ShieldCheck, 
  Zap, 
  AudioWaveform, 
  Code, 
  Play, 
  Sliders, 
  Video, 
  Clock, 
  Cpu,
  Layers,
  Wand2,
  Copy,
  FileText
} from "lucide-react";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-[#090A0F] text-gray-100 selection:bg-indigo-500 selection:text-white">
      {/* Header */}
      <header className="border-b border-[#1E2235] bg-[#0E101A]/80 backdrop-blur-md sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-purple-500 flex items-center justify-center shadow-lg shadow-indigo-500/25">
              <Mic2 className="w-5 h-5 text-white" />
            </div>
            <span className="font-bold text-lg tracking-tight bg-gradient-to-r from-white via-gray-200 to-indigo-300 bg-clip-text text-transparent">
              HK Speaks
            </span>
          </div>

          <div className="flex items-center space-x-4">
            <Link href="/login" className="text-sm text-gray-400 hover:text-white transition-colors">
              Sign In
            </Link>
            <div className="flex items-center space-x-2">
              <Link
                href="/app/studio"
                className="px-3.5 py-2 rounded-xl text-xs font-semibold bg-[#181B2B] hover:bg-[#22273D] text-indigo-300 border border-indigo-500/30 transition-all flex items-center space-x-1.5"
              >
                <Mic2 className="w-3.5 h-3.5" />
                <span>Voice Studio</span>
              </Link>
              <Link
                href="/video-editor"
                className="px-3.5 py-2 rounded-xl text-xs font-semibold bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white shadow-md shadow-purple-600/25 transition-all flex items-center space-x-1.5"
              >
                <Film className="w-3.5 h-3.5" />
                <span>Video Editor</span>
              </Link>
              <Link
                href="/app/image-prompts"
                className="px-3.5 py-2 rounded-xl text-xs font-semibold bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-400 hover:to-orange-400 text-black shadow-md shadow-amber-500/25 transition-all flex items-center space-x-1.5 font-bold"
              >
                <Sparkles className="w-3.5 h-3.5 fill-current" />
                <span>Image Prompts</span>
              </Link>
            </div>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="relative pt-20 pb-16 px-6 max-w-5xl mx-auto text-center">
        <div className="inline-flex items-center space-x-2 px-3 py-1.5 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-xs font-medium mb-8">
          <Sparkles className="w-3.5 h-3.5" />
          <span>Triple-Engine Creative Suite • Voice Studio, Video Editor & Image Prompts</span>
        </div>

        <h1 className="text-5xl md:text-7xl font-extrabold tracking-tight leading-tight md:leading-none bg-gradient-to-b from-white via-gray-100 to-gray-400 bg-clip-text text-transparent mb-6">
          Produce Studio Audio. <br className="hidden md:inline" />
          <span className="bg-gradient-to-r from-indigo-400 via-purple-400 to-amber-400 bg-clip-text text-transparent">
            Direct Documentaries & Generate Visual Prompts.
          </span>
        </h1>

        <p className="text-lg md:text-xl text-gray-400 max-w-3xl mx-auto mb-10 leading-relaxed">
          HK Speaks is the unified creative suite offering three dedicated standalone tools: a hyper-realistic 
          AI Voice Studio, an intelligent Ken Burns Documentary Video Editor, and an AI Image Prompt Generator 
          that analyzes scripts and speech timing into scene-by-scene visual prompts.
        </p>

        {/* 3 Dedicated Creative Product Feature Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 max-w-4xl mx-auto">
          {/* Card 1: Voice Studio */}
          <Link
            href="/app/studio"
            className="p-5 rounded-2xl bg-gradient-to-b from-[#161A2B] to-[#0F111E] border border-[#212845] hover:border-indigo-500/50 transition-all flex flex-col items-center text-center group shadow-lg shadow-indigo-950/20 hover:shadow-indigo-500/10 cursor-pointer"
          >
            <div className="w-12 h-12 rounded-xl bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400 mb-3 group-hover:scale-110 transition-transform">
              <Mic2 className="w-6 h-6" />
            </div>
            <span className="font-bold text-base text-gray-100 mb-1">Voice Studio</span>
            <span className="text-xs text-gray-400 leading-normal">1000+ Voices & Custom Voice Cloning</span>
          </Link>

          {/* Card 2: Video Editor */}
          <Link
            href="/video-editor"
            className="p-5 rounded-2xl bg-gradient-to-b from-[#161A2B] to-[#0F111E] border border-[#212845] hover:border-purple-500/50 transition-all flex flex-col items-center text-center group shadow-lg shadow-purple-950/20 hover:shadow-purple-500/10 cursor-pointer"
          >
            <div className="w-12 h-12 rounded-xl bg-purple-600/20 border border-purple-500/30 flex items-center justify-center text-purple-400 mb-3 group-hover:scale-110 transition-transform">
              <Film className="w-6 h-6" />
            </div>
            <span className="font-bold text-base text-gray-100 mb-1">Video Editor</span>
            <span className="text-xs text-gray-400 leading-normal">Ken Burns Documentaries & 4K Export</span>
          </Link>

          {/* Card 3: Image Prompt Generator */}
          <Link
            href="/app/image-prompts"
            className="p-5 rounded-2xl bg-gradient-to-b from-[#1F1912] to-[#0F0E14] border border-[#3D2C1C] hover:border-amber-500/60 transition-all flex flex-col items-center text-center group shadow-lg shadow-amber-950/20 hover:shadow-amber-500/15 cursor-pointer"
          >
            <div className="w-12 h-12 rounded-xl bg-gradient-to-tr from-amber-500/20 to-orange-500/20 border border-amber-500/40 flex items-center justify-center text-amber-400 mb-3 group-hover:scale-110 transition-transform">
              <Sparkles className="w-6 h-6 fill-current" />
            </div>
            <span className="font-bold text-base text-amber-300 mb-1">Image Prompt Generator</span>
            <span className="text-xs text-gray-400 leading-normal">AI Script-to-Image Visual Prompts</span>
          </Link>
        </div>
      </section>

      {/* PRODUCT 3 SPOTLIGHT: AI IMAGE PROMPT GENERATOR */}
      <section className="py-16 px-6 max-w-6xl mx-auto border-t border-[#1C2033]">
        <div className="text-center mb-12">
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-amber-500/10 border border-amber-500/20 text-amber-400 text-xs font-semibold uppercase tracking-wider mb-3">
            <Sparkles className="w-3.5 h-3.5 fill-current" />
            <span>Product 3 • Dedicated Script-to-Image Engine</span>
          </div>
          <h2 className="text-3xl md:text-4xl font-extrabold text-white tracking-tight">
            Generate Cinematic Visual Prompts from Scripts & Spoken Audio
          </h2>
          <p className="text-sm md:text-base text-gray-400 max-w-2xl mx-auto mt-2">
            Break any narrative into individual sentence scenes. Customize your visual style, optionally synchronize with your voiceover timeline, and copy all prompts with a single click.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-left mb-10">
          <div className="p-6 rounded-2xl bg-[#12141F] border border-[#202436] space-y-3">
            <div className="w-10 h-10 rounded-xl bg-amber-500/20 border border-amber-500/30 flex items-center justify-center text-amber-400">
              <FileText className="w-5 h-5" />
            </div>
            <h3 className="font-bold text-base text-gray-100">1. Script Narration</h3>
            <p className="text-xs text-gray-400 leading-relaxed">
              Paste story paragraphs or voiceover scripts. Breaks naturally into sentence-level scenes with no artificial limits.
            </p>
          </div>

          <div className="p-6 rounded-2xl bg-[#12141F] border border-[#202436] space-y-3">
            <div className="w-10 h-10 rounded-xl bg-orange-500/20 border border-orange-500/30 flex items-center justify-center text-orange-400">
              <Sliders className="w-5 h-5" />
            </div>
            <h3 className="font-bold text-base text-gray-100">2. Image Visual Style Prompt</h3>
            <p className="text-xs text-gray-400 leading-relaxed">
              Define lighting, lens, and artistic mood. Preserved across all generated scenes for visual consistency.
            </p>
          </div>

          <div className="p-6 rounded-2xl bg-[#12141F] border border-[#202436] space-y-3">
            <div className="w-10 h-10 rounded-xl bg-purple-500/20 border border-purple-500/30 flex items-center justify-center text-purple-400">
              <Clock className="w-5 h-5" />
            </div>
            <h3 className="font-bold text-base text-gray-100">3. Optional Audio Alignment</h3>
            <p className="text-xs text-gray-400 leading-relaxed">
              Upload voiceover audio to compute exact spoken start/end timestamps and durations for each scene.
            </p>
          </div>
        </div>

        <div className="text-center">
          <Link
            href="/app/image-prompts"
            className="inline-flex items-center space-x-2 px-6 py-3 rounded-xl text-sm font-bold bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-400 hover:to-orange-400 text-black transition-all shadow-lg shadow-amber-500/20"
          >
            <span>Open Image Prompt Generator</span>
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>

      {/* PRODUCT 2 SPOTLIGHT: AI VIDEO EDITOR / DOCUMENTARY STUDIO */}
      <section className="py-16 px-6 max-w-6xl mx-auto border-t border-[#1C2033]">
        <div className="text-center mb-12">
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-purple-500/10 border border-purple-500/20 text-purple-400 text-xs font-semibold uppercase tracking-wider mb-3">
            <Film className="w-3.5 h-3.5" />
            <span>Product 2 • Autonomous Documentary Studio</span>
          </div>
          <h2 className="text-3xl md:text-4xl font-extrabold text-white tracking-tight">
            Turn Voiceover & Images into Finished 1080p Documentaries
          </h2>
          <p className="text-sm md:text-base text-gray-400 max-w-2xl mx-auto mt-2">
            No video editing timeline experience required. Upload your master voiceover and visual assets — our Auto-Director engine calculates dynamic scene durations and produces cinematic camera movement.
          </p>
        </div>

        {/* 4-Step Interactive Showcase Grid */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-10">
          <div className="p-5 rounded-2xl bg-[#121422] border border-[#21263D] flex flex-col justify-between">
            <div>
              <div className="w-9 h-9 rounded-xl bg-purple-600/20 border border-purple-500/30 flex items-center justify-center text-purple-400 mb-3">
                <AudioWaveform className="w-4 h-4" />
              </div>
              <span className="text-xs font-bold uppercase tracking-wider text-purple-400">Step 1</span>
              <h3 className="font-bold text-sm text-gray-100 mt-1 mb-2">Upload Voiceover & Stills</h3>
              <p className="text-xs text-gray-400 leading-relaxed">
                Provide a single master voiceover track (.mp3 / .wav) along with your archival photos or illustration assets.
              </p>
            </div>
          </div>

          <div className="p-5 rounded-2xl bg-[#121422] border border-[#21263D] flex flex-col justify-between">
            <div>
              <div className="w-9 h-9 rounded-xl bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400 mb-3">
                <Cpu className="w-4 h-4" />
              </div>
              <span className="text-xs font-bold uppercase tracking-wider text-indigo-400">Step 2</span>
              <h3 className="font-bold text-sm text-gray-100 mt-1 mb-2">Speech Rhythm Cadence</h3>
              <p className="text-xs text-gray-400 leading-relaxed">
                Detects natural speech cadences and pauses to build accurate sentence intervals and scene break timestamps.
              </p>
            </div>
          </div>

          <div className="p-5 rounded-2xl bg-[#121422] border border-[#21263D] flex flex-col justify-between">
            <div>
              <div className="w-9 h-9 rounded-xl bg-cyan-600/20 border border-cyan-500/30 flex items-center justify-center text-cyan-400 mb-3">
                <Sliders className="w-4 h-4" />
              </div>
              <span className="text-xs font-bold uppercase tracking-wider text-cyan-400">Step 3</span>
              <h3 className="font-bold text-sm text-gray-100 mt-1 mb-2">Dynamic Ken Burns Motion</h3>
              <p className="text-xs text-gray-400 leading-relaxed">
                Assigns dynamic clip durations matching voiceover sentences, with intelligent pan, zoom-in, and zoom-out camera motions.
              </p>
            </div>
          </div>

          <div className="p-5 rounded-2xl bg-[#121422] border border-[#21263D] flex flex-col justify-between">
            <div>
              <div className="w-9 h-9 rounded-xl bg-emerald-600/20 border border-emerald-500/30 flex items-center justify-center text-emerald-400 mb-3">
                <Video className="w-4 h-4" />
              </div>
              <span className="text-xs font-bold uppercase tracking-wider text-emerald-400">Step 4</span>
              <h3 className="font-bold text-sm text-gray-100 mt-1 mb-2">Native FFmpeg MP4 Export</h3>
              <p className="text-xs text-gray-400 leading-relaxed">
                Background rendering worker compiles high-bitrate H.264 MP4 with synchronized AAC audio ready to download and stream.
              </p>
            </div>
          </div>
        </div>

        <div className="text-center">
          <Link
            href="/video-editor"
            className="inline-flex items-center space-x-2 px-6 py-3 rounded-xl text-sm font-semibold bg-[#1C2038] hover:bg-[#242A4A] text-white border border-[#2F3657] transition-all"
          >
            <span>Create Your First Documentary Project</span>
            <ArrowRight className="w-4 h-4 text-purple-400" />
          </Link>
        </div>
      </section>

      {/* PRODUCT 1 SPOTLIGHT: AI VOICE STUDIO */}
      <section className="py-16 px-6 max-w-6xl mx-auto border-t border-[#1C2033]">
        <div className="text-center mb-12">
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-xs font-semibold uppercase tracking-wider mb-3">
            <Mic2 className="w-3.5 h-3.5" />
            <span>Product 1 • AI Voice Studio</span>
          </div>
          <h2 className="text-3xl md:text-4xl font-extrabold text-white tracking-tight">
            High-Fidelity Neural Speech & Private Voice Cloning
          </h2>
          <p className="text-sm md:text-base text-gray-400 max-w-2xl mx-auto mt-2">
            The studio standard for creators, animators, and enterprises. Clean, human speech with strict voice cloning routing and quota protection.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-left">
          <div className="p-6 rounded-2xl bg-[#12141F] border border-[#202436] space-y-3">
            <div className="w-10 h-10 rounded-xl bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
              <AudioWaveform className="w-5 h-5" />
            </div>
            <h3 className="font-bold text-base text-gray-100">Studio & Presets</h3>
            <p className="text-xs text-gray-400 leading-relaxed">
              Documentary, Podcast, Audiobook, and Narration presets with multi-voice mixing and full generation history.
            </p>
          </div>

          <div className="p-6 rounded-2xl bg-[#12141F] border border-[#202436] space-y-3">
            <div className="w-10 h-10 rounded-xl bg-purple-600/20 border border-purple-500/30 flex items-center justify-center text-purple-400">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <h3 className="font-bold text-base text-gray-100">Strict Voice Routing</h3>
            <p className="text-xs text-gray-400 leading-relaxed">
              When Your Clone is selected, generation is locked strictly to your cloned model. Zero silent fallbacks, total identity guarantee.
            </p>
          </div>

          <div className="p-6 rounded-2xl bg-[#12141F] border border-[#202436] space-y-3">
            <div className="w-10 h-10 rounded-xl bg-cyan-600/20 border border-cyan-500/30 flex items-center justify-center text-cyan-400">
              <Code className="w-5 h-5" />
            </div>
            <h3 className="font-bold text-base text-gray-100">RESTful TTS API</h3>
            <p className="text-xs text-gray-400 leading-relaxed">
              Secure hashed API keys, idempotency protections, and sub-second background task queueing for developer automation.
            </p>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-[#1E2235] py-10 px-6 text-center text-xs text-gray-500">
        <p>© 2026 HK Speaks. Production-grade AI Voice, Autonomous Video & Image Prompt Studio. All rights reserved.</p>
      </footer>
    </div>
  );
}
