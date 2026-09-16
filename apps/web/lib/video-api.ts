import { apiClient } from "./api";

export interface VideoAsset {
  id: string;
  project_id: string;
  asset_type: "image" | "voiceover" | "video";
  filename: string;
  url: string;
  duration?: number;
  width?: number;
  height?: number;
  file_size?: number;
  mime_type?: string;
  created_at: string;
}

export interface Voiceover {
  id: string;
  project_id: string;
  asset_id: string;
  filename: string;
  url: string;
  duration: number;
  sample_rate?: number;
  channels?: number;
  status: string;
}

export interface Scene {
  id: string;
  project_id: string;
  scene_index: number;
  title: string;
  narrative_text?: string;
  start_time: number;
  end_time: number;
  duration: number;
  primary_asset_id?: string;
  primary_asset?: VideoAsset;
}

export interface TimelineClip {
  id: string;
  project_id: string;
  scene_id?: string;
  asset_id: string;
  track_index: number;
  clip_index: number;
  start_time: number;
  end_time: number;
  duration: number;
  motion_type: "zoom_in" | "zoom_out" | "pan_left" | "pan_right" | "ken_burns" | "static";
  scale_factor: number;
  framing: string;
  asset?: VideoAsset;
}

export interface TimelineTransition {
  id: string;
  project_id: string;
  from_clip_id?: string;
  to_clip_id?: string;
  transition_type: "xfade" | "fade" | "dissolve" | "wipeleft" | "none";
  duration: number;
  offset_time: number;
}

export interface RenderOutput {
  id: string;
  project_id: string;
  filename: string;
  download_url: string;
  url?: string;
  duration?: number;
  resolution?: string;
  file_size?: number;
  created_at: string;
}

export interface RenderJob {
  id: string;
  project_id: string;
  status: "queued" | "processing" | "rendering" | "completed" | "failed";
  progress: number;
  current_step: string;
  error_message?: string;
  resolution: string;
  aspect_ratio: string;
  fps: number;
  created_at: string;
  started_at?: string;
  completed_at?: string;
}

export interface VideoProjectSummary {
  id: string;
  title: string;
  description?: string;
  status: "draft" | "ready" | "rendering" | "completed";
  aspect_ratio: string;
  resolution: string;
  fps: number;
  total_duration: number;
  created_at: string;
  updated_at: string;
}

export interface VideoProjectDetail extends VideoProjectSummary {
  assets: VideoAsset[];
  voiceover?: Voiceover;
  scenes: Scene[];
  timeline_clips: TimelineClip[];
  transitions: TimelineTransition[];
  render_outputs: RenderOutput[];
  latest_render?: RenderJob;
}

export async function listVideoProjects(): Promise<VideoProjectSummary[]> {
  return apiClient<VideoProjectSummary[]>("/video-editor/projects");
}

export async function createVideoProject(data: {
  title: string;
  description?: string;
  aspect_ratio?: string;
  resolution?: string;
  fps?: number;
}): Promise<VideoProjectSummary> {
  return apiClient<VideoProjectSummary>("/video-editor/projects", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function getVideoProject(projectId: string): Promise<VideoProjectDetail> {
  return apiClient<VideoProjectDetail>(`/video-editor/projects/${projectId}`);
}

export async function updateVideoProject(
  projectId: string,
  data: Partial<VideoProjectSummary>
): Promise<VideoProjectSummary> {
  return apiClient<VideoProjectSummary>(`/video-editor/projects/${projectId}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function deleteVideoProject(projectId: string): Promise<{ status: string; id: string }> {
  return apiClient<{ status: string; id: string }>(`/video-editor/projects/${projectId}`, {
    method: "DELETE",
  });
}

export async function uploadVideoAssets(
  projectId: string,
  files: File[],
  assetType?: string
): Promise<VideoAsset[]> {
  const formData = new FormData();
  files.forEach((file) => formData.append("files", file));
  if (assetType) {
    formData.append("asset_type", assetType);
  }

  return apiClient<VideoAsset[]>(`/video-editor/projects/${projectId}/assets`, {
    method: "POST",
    body: formData,
  });
}

export async function deleteVideoAsset(
  projectId: string,
  assetId: string
): Promise<{ status: string; id: string }> {
  return apiClient<{ status: string; id: string }>(
    `/video-editor/projects/${projectId}/assets/${assetId}`,
    {
      method: "DELETE",
    }
  );
}

export async function generateDocumentaryTimeline(
  projectId: string
): Promise<VideoProjectDetail> {
  return apiClient<VideoProjectDetail>(`/video-editor/projects/${projectId}/generate`, {
    method: "POST",
  });
}

export async function updateVideoTimeline(
  projectId: string,
  clips: {
    id: string;
    asset_id: string;
    start_time: number;
    end_time: number;
    duration: number;
    motion_type: string;
    scale_factor: number;
    framing: string;
  }[]
): Promise<VideoProjectDetail> {
  return apiClient<VideoProjectDetail>(`/video-editor/projects/${projectId}/timeline`, {
    method: "PUT",
    body: JSON.stringify({ clips }),
  });
}

export async function submitVideoRender(
  projectId: string,
  options?: {
    aspect_ratio?: string;
    resolution?: string;
    format?: string;
    fps?: number;
  }
): Promise<RenderJob> {
  return apiClient<RenderJob>(`/video-editor/projects/${projectId}/render`, {
    method: "POST",
    body: JSON.stringify(options || {}),
  });
}

export async function getRenderJobStatus(jobId: string): Promise<RenderJob> {
  return apiClient<RenderJob>(`/video-editor/renders/${jobId}`);
}

export async function listProjectRenders(projectId: string): Promise<RenderOutput[]> {
  return apiClient<RenderOutput[]>(`/video-editor/projects/${projectId}/renders`);
}
