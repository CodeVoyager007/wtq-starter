import { API_URL } from "./config";
import type { DecodedBill } from "./types";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, init);
  } catch {
    throw new Error(`Cannot reach the backend at ${API_URL}. Is it running?`);
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = Array.isArray(data.detail) ? data.detail[0]?.msg : data.detail;
    throw new Error(detail ?? `Request failed (${res.status})`);
  }
  return data as T;
}

export const api = {
  decodeBill: (file: File, provider: string) => {
    const form = new FormData();
    form.append("file", file);
    form.append("provider", provider);
    return request<DecodedBill>("/api/bill", { method: "POST", body: form });
  },

  askBill: (token: string, question: string) =>
    request<{ question: string; answer: string }>("/api/bill/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token, question }),
    }),
};
