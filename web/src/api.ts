export type SessionSummary = {
  session_id: string;
  name: string | null;
  project_path: string | null;
  transcript_path: string;
  created_at: string | null;
  updated_at: string | null;
  first_user_text: string | null;
  message_count: number;
  snippet: string | null;
  resume_command: string;
};

export type SessionMessage = {
  id: number;
  ordinal: number;
  role: string;
  timestamp: string | null;
  uuid: string | null;
  parent_uuid: string | null;
  text: string;
};

export type SessionDetail = SessionSummary & {
  messages: SessionMessage[];
  chunks: { id: number; chunk_index: number; text: string }[];
};

export type Health = {
  ok: boolean;
  db_path: string;
  session_count: number;
};

export type ScanReport = {
  roots: string[];
  scanned_files: number;
  indexed_sessions: number;
  session_count: number;
  warnings: string[];
};

export type ScanStatus = {
  running: boolean;
  phase: "idle" | "starting" | "discovering" | "indexing" | "done" | "failed";
  roots: { path: string; exists: boolean }[];
  total_files: number;
  scanned_files: number;
  indexed_sessions: number;
  current_file: string | null;
  warnings: string[];
  error: string | null;
  started_at: string | null;
  finished_at: string | null;
  session_count: number;
};

export type LanguageOption = {
  code: string;
  name: string;
  native_name: string;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {})
    }
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json() as Promise<T>;
}

export function getHealth() {
  return request<Health>("/api/health");
}

export function getProjects() {
  return request<string[]>("/api/projects");
}

export function getLanguages() {
  return request<LanguageOption[]>("/api/i18n/languages");
}

export function scan(rebuild = false) {
  return request<ScanReport>("/api/scan", {
    method: "POST",
    body: JSON.stringify({ rebuild })
  });
}

export function startScan(rebuild = false) {
  return request<ScanStatus>("/api/scan/start", {
    method: "POST",
    body: JSON.stringify({ rebuild })
  });
}

export function getScanStatus() {
  return request<ScanStatus>("/api/scan/status");
}

export function searchSessions(query: string, project: string) {
  const params = new URLSearchParams();
  params.set("q", query);
  if (project) params.set("project", project);
  params.set("limit", "50");
  return request<SessionSummary[]>(`/api/search?${params.toString()}`);
}

export function getSession(sessionId: string) {
  return request<SessionDetail>(`/api/sessions/${encodeURIComponent(sessionId)}`);
}
