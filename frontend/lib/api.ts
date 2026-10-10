import { API_URL } from "./config";
import type { ChatMessage, DecodedBill, RunResult, UploadResponse } from "./types";

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
    request<{ status: string; mock_mode: boolean; gemini_keys: number; model: string }>("/health"),

  decodeBill: (file: File, provider: string) => {
    const form = new FormData();
    form.append("file", file);
    form.append("provider", provider);
    return request<DecodedBill>("/api/bill", { method: "POST", body: form });
  },

  askBill: (token: string, question: string) =>
    request<{ question: string; answer: string }>("/api/bill/ask", json({ token, question })),

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
