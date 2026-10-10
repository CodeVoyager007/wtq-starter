import { API_URL } from "./config";
import type { ChatMessage, RunResult, UploadResponse } from "./types";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, init);
  } catch {
    throw new Error(`Cannot reach the backend at ${API_URL}. Is it running?`);
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail ?? `Request failed (${res.status})`);
  return data as T;
}

const json = (body: unknown): RequestInit => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

export const api = {
  health: () =>
    request<{ status: string; mock_mode: boolean; gemini_keys: number; fallback: boolean; model: string }>("/health"),

  uploadFile: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<UploadResponse>("/api/upload", { method: "POST", body: form });
  },

  loadSample: () => request<UploadResponse>("/api/sample", { method: "POST" }),

  run: (payload: { mode: string; input: string; dataset_id: string | null; options: Record<string, string> }) =>
    request<RunResult>("/api/run", json(payload)),

  chat: (message: string, history: ChatMessage[], dataset_id: string | null) =>
    request<{ reply: string }>("/api/chat", json({ message, history, dataset_id })),
};
