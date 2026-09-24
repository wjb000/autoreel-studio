const BASE = import.meta.env.VITE_SIDECAR_URL || "http://127.0.0.1:8765";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
  });
  if (!r.ok) {
    const text = await r.text();
    throw new Error(text || r.statusText);
  }
  return r.json() as Promise<T>;
}

export const api = {
  base: BASE,
  health: () => req<{ status: string }>("/health"),
  system: () => req<SystemInfo>("/system"),
  listModels: () => req<{ models: ModelInfo[] }>("/models"),
  downloadModel: (model_id: string, mock = true) =>
    req<{ ok: boolean }>("/models/download", {
      method: "POST",
      body: JSON.stringify({ model_id, mock }),
    }),
  listJobs: () => req<{ jobs: Job[] }>("/jobs"),
  getJob: (id: string) => req<Job>(`/jobs/${id}`),
  createJob: (body: CreateJobBody) =>
    req<Job>("/jobs", { method: "POST", body: JSON.stringify(body) }),
  youtubeStatus: () => req<YtStatus>("/youtube/auth/status"),
  youtubeConnect: () => req<YtStatus>("/youtube/auth/start", { method: "POST" }),
  youtubeDisconnect: () =>
    req<YtStatus>("/youtube/auth/disconnect", { method: "POST" }),
  youtubeUpload: (body: UploadBody) =>
    req<{ ok: boolean; video_id: string; url: string }>("/youtube/upload", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  xStatus: () => req<XStatus>("/x/status"),
  xPublish: (body: XPublishBody) =>
    req<{ ok: boolean; url?: string | null; message?: string; tweet_id?: string }>(
      "/x/publish",
      { method: "POST", body: JSON.stringify(body) }
    ),
  listPlatforms: () => req<{ platforms: PlatformInfo[] }>("/x/platforms"),
  getSettings: () => req<AppSettings>("/settings"),
  saveSettings: (body: Partial<AppSettings>) =>
    req<AppSettings>("/settings", { method: "POST", body: JSON.stringify(body) }),
};

export type SystemInfo = {
  os: string;
  arch: string;
  cpu_count: number;
  ram_gb: number;
  ram_available_gb: number;
  disk_free_gb: number;
  gpu: { available: boolean; name: string | null; backend: string; vram_gb: number | null };
  ffmpeg: string;
  mock_wan: boolean;
  app_data: string;
  ready_for_wan: boolean;
};

export type ModelInfo = {
  id: string;
  name: string;
  size_gb: number;
  required: boolean;
  description: string;
  installed: boolean;
  path: string;
  size_on_disk_gb: number;
  download: { status: string; progress: number; message: string };
  license: string;
};

export type Job = {
  id: string;
  topic: string;
  niche: string;
  duration: string;
  mode?: string;
  status: string;
  stage: string;
  progress: number;
  message: string;
  created_at: string;
  output?: {
    video?: string;
    thumbnail?: string;
    title?: string;
    description?: string;
    tags?: string[];
    mode?: string;
  } | null;
  error?: string | null;
};

export type CreateJobBody = {
  topic: string;
  niche: string;
  duration: string;
  voice?: string;
  upload?: boolean;
  privacy?: string;
  mock?: boolean;
  mode?: "animated_short" | "explainer" | string;
};

export type YtStatus = {
  status: string;
  channel_name: string | null;
  channel_id: string | null;
  error: string | null;
};

export type XStatus = {
  status: string;
  platform?: string;
  connected?: boolean;
  username?: string | null;
  user_id?: string | null;
  error: string | null;
};

export type PlatformInfo = {
  id: string;
  name: string;
  status: string;
  detail?: string | null;
  available: boolean;
};

export type UploadBody = {
  video_path: string;
  title: string;
  description?: string;
  tags?: string[];
  privacy?: string;
  thumbnail_path?: string;
};

export type XPublishBody = {
  video_path: string;
  text: string;
  dry_run?: boolean;
};

export type AppSettings = {
  default_niche: string;
  default_voice: string;
  default_duration: string;
  default_privacy: string;
  default_mode?: string;
  pexels_api_key: string;
  output_path: string;
  auto_upload: boolean;
};

export function subscribeSSE(
  path: string,
  onEvent: (data: Record<string, unknown>) => void,
  onError?: (e: Event) => void
): () => void {
  const es = new EventSource(`${BASE}${path}`);
  es.onmessage = (ev) => {
    try {
      onEvent(JSON.parse(ev.data));
    } catch {
      /* ignore */
    }
  };
  es.onerror = (e) => {
    onError?.(e);
    es.close();
  };
  return () => es.close();
}
