import { NextRequest, NextResponse } from "next/server";
import voiceCatalogData from "@/lib/voice-catalog.json";

// Standard CORS headers
const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, HEAD",
  "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With",
};

export async function OPTIONS() {
  return new NextResponse(null, { status: 204, headers: corsHeaders });
}

async function forwardToBackend(request: NextRequest, pathStr: string, backendBase: string): Promise<Response> {
  const targetUrl = new URL(`/v1/${pathStr}`, backendBase);
  // Forward search params
  request.nextUrl.searchParams.forEach((val, key) => {
    targetUrl.searchParams.set(key, val);
  });

  const headers = new Headers();
  request.headers.forEach((val, key) => {
    if (!["host", "connection", "content-length"].includes(key.toLowerCase())) {
      headers.set(key, val);
    }
  });

  const init: RequestInit = {
    method: request.method,
    headers,
    cache: "no-store",
  };

  if (request.method !== "GET" && request.method !== "HEAD") {
    const bodyBuffer = await request.arrayBuffer();
    if (bodyBuffer.byteLength > 0) {
      init.body = bodyBuffer;
    }
  }

  return fetch(targetUrl.toString(), init);
}

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const resolvedParams = await params;
  const path = resolvedParams.path ? resolvedParams.path.join("/") : "";
  const backendUrl = process.env.BACKEND_INTERNAL_URL || process.env.BACKEND_URL;

  // 1. If backend URL is provided, try forwarding first
  if (backendUrl) {
    try {
      const upstream = await forwardToBackend(request, path, backendUrl);
      if (upstream.ok || (path !== "voices" && !path.startsWith("image-prompts"))) {
        const body = await upstream.arrayBuffer();
        const resHeaders = new Headers(upstream.headers);
        Object.entries(corsHeaders).forEach(([k, v]) => resHeaders.set(k, v));
        return new NextResponse(body, {
          status: upstream.status,
          statusText: upstream.statusText,
          headers: resHeaders,
        });
      }
    } catch (err) {
      console.warn(`Upstream backend error for GET /v1/${path}:`, err);
    }
  }

  // 2. Health check endpoint
  if (path === "health") {
    return NextResponse.json({
      status: "ok",
      environment: process.env.NODE_ENV || "production",
      cloud_provider: "vercel",
      version: "1.0.0",
    }, { headers: corsHeaders });
  }

  // 3. Resilient Voice Catalog (serves all 322 real neural voices without external server)
  if (path === "voices") {
    const searchParams = request.nextUrl.searchParams;
    const search = searchParams.get("search")?.toLowerCase();
    const language = searchParams.get("language")?.toLowerCase();
    const gender = searchParams.get("gender")?.toLowerCase();
    const style = searchParams.get("style")?.toLowerCase();
    const provider = searchParams.get("provider")?.toLowerCase();

    let filtered = (voiceCatalogData as any[]).map((v) => ({
      ...v,
      id: v.slug || v.provider_voice_id || v.name,
    }));

    if (search) {
      filtered = filtered.filter(
        (v) =>
          v.name?.toLowerCase().includes(search) ||
          v.language?.toLowerCase().includes(search) ||
          v.locale?.toLowerCase().includes(search) ||
          v.accent?.toLowerCase().includes(search) ||
          v.style?.toLowerCase().includes(search) ||
          v.gender?.toLowerCase().includes(search) ||
          v.provider?.toLowerCase().includes(search)
      );
    }

    if (language && language !== "all") {
      filtered = filtered.filter(
        (v) =>
          v.language?.toLowerCase() === language ||
          v.locale?.toLowerCase().startsWith(language)
      );
    }

    if (gender && gender !== "all") {
      filtered = filtered.filter((v) => v.gender?.toLowerCase() === gender);
    }

    if (style && style !== "all") {
      filtered = filtered.filter(
        (v) =>
          v.style?.toLowerCase().includes(style) ||
          (Array.isArray(v.styles) && v.styles.some((s: string) => s.toLowerCase().includes(style)))
      );
    }

    if (provider && provider !== "all") {
      if (provider === "other") {
        filtered = filtered.filter((v) =>
          ["edge", "azure", "amazon", "google", "openai"].includes(v.provider?.toLowerCase())
        );
      } else {
        filtered = filtered.filter((v) => v.provider?.toLowerCase() === provider);
      }
    }

    return NextResponse.json(filtered, {
      headers: {
        ...corsHeaders,
        "Cache-Control": "public, s-maxage=3600, stale-while-revalidate=86400",
      },
    });
  }

  // 4. Style presets for Visual Prompt Generator
  if (path === "image-prompts/presets") {
    return NextResponse.json([
      { id: "cinematic", title: "Cinematic 35mm", prompt: "Cinematic 35mm film still, shallow depth of field, atmospheric volumetric lighting, anamorphic lens, 8k resolution, photorealistic masterpiece, highly detailed textures" },
      { id: "documentary", title: "Historical Documentary", prompt: "Archival historical photograph, authentic period atmosphere, documentary realism, National Geographic quality, natural chiaroscuro lighting, rich textured grain" },
      { id: "vintage", title: "Vintage Kodachrome", prompt: "1960s Kodachrome color photograph, warm vintage color palette, nostalgic film grain, authentic retro atmosphere, authentic lenses, fine documentary details" },
      { id: "cyberpunk", title: "Cyberpunk Sci-Fi", prompt: "Futuristic cyberpunk atmosphere, glowing neon reflections, holographic displays, high-tech dystopian city, moody volumetric fog, cinematic composition" },
      { id: "nature", title: "Nature & Landscape", prompt: "Breathtaking landscape photography, dramatic golden hour lighting, sweeping vistas, crisp organic detail, 8k resolution, shot on Hasselblad" },
    ], { headers: corsHeaders });
  }

  return NextResponse.json(
    { error: "Endpoint not found", path },
    { status: 404, headers: corsHeaders }
  );
}

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const resolvedParams = await params;
  const path = resolvedParams.path ? resolvedParams.path.join("/") : "";
  const backendUrl = process.env.BACKEND_INTERNAL_URL || process.env.BACKEND_URL;

  // 1. Try forwarding to cloud backend if configured
  if (backendUrl) {
    try {
      const upstream = await forwardToBackend(request, path, backendUrl);
      if (upstream.ok || !path.startsWith("image-prompts")) {
        const body = await upstream.arrayBuffer();
        const resHeaders = new Headers(upstream.headers);
        Object.entries(corsHeaders).forEach(([k, v]) => resHeaders.set(k, v));
        return new NextResponse(body, {
          status: upstream.status,
          statusText: upstream.statusText,
          headers: resHeaders,
        });
      }
    } catch (err) {
      console.warn(`Upstream backend error for POST /v1/${path}:`, err);
    }
  }

  // 2. Resilient Visual Prompt Generator (works 100% in cloud without external server)
  if (path === "image-prompts/generate") {
    try {
      const formData = await request.formData();
      const script = (formData.get("script") as string) || "";
      const visualStyle = (formData.get("visual_style_prompt") as string) ||
        "Cinematic 35mm film still, shallow depth of field, atmospheric volumetric lighting, anamorphic lens, 8k resolution, photorealistic masterpiece, highly detailed textures";
      const title = (formData.get("title") as string) || "Script Narration Prompts";

      if (!script.trim()) {
        return NextResponse.json({ error: "Script text is required" }, { status: 400, headers: corsHeaders });
      }

      // Split into clean narration sentences
      const rawSentences = script
        .split(/(?<=[.!?])\s+|\n+/)
        .map((s) => s.trim())
        .filter((s) => s.length > 0);

      const sentences = rawSentences.length > 0 ? rawSentences : [script.trim()];

      const strictNegative = "no text, no numbers, no letters, no captions, no labels, no typography, no written words, watermark, signature, logo, blurry, low quality, distorted";
      const cameraAngles = [
        "wide cinematic establishing shot",
        "medium narrative portrait shot",
        "dramatic low angle perspective",
        "intimate close-up detail shot",
        "sweeping cinematic vista",
        "over-the-shoulder observational angle"
      ];

      let runningTime = 0.0;
      const scenes = sentences.map((sentence, idx) => {
        const dur = Math.max(3.0, Math.min(6.5, Math.round((sentence.split(/\s+/).length * 0.4) * 10) / 10));
        const start = Math.round(runningTime * 10) / 10;
        runningTime += dur;
        const end = Math.round(runningTime * 10) / 10;

        const camera = cameraAngles[idx % cameraAngles.length];
        const cleanSceneVisual = sentence
          .replace(/["“”]/g, "")
          .replace(/\b(?:Scene|Shot|Prompt|Image)\s*\d+[:.]?\b/gi, "")
          .trim();

        // Image Prompt strictly adheres to negative instruction and clean visual aesthetics
        const prompt = `${camera}, ${cleanSceneVisual}, ${visualStyle}, photorealistic, masterpiece, highly detailed textures, dramatic lighting`;

        return {
          scene_index: idx + 1,
          sentence,
          transcript_text: sentence,
          image_prompt: prompt,
          negative_prompt: strictNegative,
          aspect_ratio: "16:9",
          start_time: start,
          end_time: end,
          duration: dur,
          start_time_formatted: `${Math.floor(start / 60)}:${Math.floor(start % 60).toString().padStart(2, "0")}`,
          end_time_formatted: `${Math.floor(end / 60)}:${Math.floor(end % 60).toString().padStart(2, "0")}`,
          duration_formatted: `${Math.floor(dur)}s`,
        };
      });

      // Assemble single large text box content for all scenes
      const outputLines: string[] = [];
      outputLines.push(`MASTER PROMPT:\n${visualStyle}\n`);
      outputLines.push(`NEGATIVE PROMPT:\n${strictNegative}\n`);
      outputLines.push("SCENE BREAKDOWN:");
      scenes.forEach((sc) => {
        outputLines.push(`Scene ${sc.scene_index} (${sc.start_time}s - ${sc.end_time}s):`);
        outputLines.push(`Narration: "${sc.sentence}"`);
        outputLines.push(`Prompt: ${sc.image_prompt}`);
        outputLines.push("");
      });

      return NextResponse.json({
        id: `gen_${Date.now()}`,
        title,
        total_duration: Math.round(runningTime * 10) / 10,
        total_scenes: scenes.length,
        aspect_ratio: "16:9",
        visual_style_prompt: visualStyle,
        negative_prompt: strictNegative,
        scenes,
        prompts_output: outputLines.join("\n").trim(),
      }, { headers: corsHeaders });
    } catch (e: any) {
      return NextResponse.json({ error: e?.message || "Failed to generate prompts" }, { status: 500, headers: corsHeaders });
    }
  }

  return NextResponse.json(
    { error: "Endpoint not found or external backend unavailable", path },
    { status: 404, headers: corsHeaders }
  );
}

export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const resolvedParams = await params;
  const path = resolvedParams.path ? resolvedParams.path.join("/") : "";
  const backendUrl = process.env.BACKEND_INTERNAL_URL || process.env.BACKEND_URL;
  if (backendUrl) {
    try {
      const upstream = await forwardToBackend(request, path, backendUrl);
      const body = await upstream.arrayBuffer();
      const resHeaders = new Headers(upstream.headers);
      Object.entries(corsHeaders).forEach(([k, v]) => resHeaders.set(k, v));
      return new NextResponse(body, {
        status: upstream.status,
        statusText: upstream.statusText,
        headers: resHeaders,
      });
    } catch (err) {
      console.warn(`Upstream backend error for PUT /v1/${path}:`, err);
    }
  }
  return NextResponse.json({ error: "Backend not reachable", path }, { status: 502, headers: corsHeaders });
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const resolvedParams = await params;
  const path = resolvedParams.path ? resolvedParams.path.join("/") : "";
  const backendUrl = process.env.BACKEND_INTERNAL_URL || process.env.BACKEND_URL;
  if (backendUrl) {
    try {
      const upstream = await forwardToBackend(request, path, backendUrl);
      const body = await upstream.arrayBuffer();
      const resHeaders = new Headers(upstream.headers);
      Object.entries(corsHeaders).forEach(([k, v]) => resHeaders.set(k, v));
      return new NextResponse(body, {
        status: upstream.status,
        statusText: upstream.statusText,
        headers: resHeaders,
      });
    } catch (err) {
      console.warn(`Upstream backend error for DELETE /v1/${path}:`, err);
    }
  }
  return NextResponse.json({ error: "Backend not reachable", path }, { status: 502, headers: corsHeaders });
}
