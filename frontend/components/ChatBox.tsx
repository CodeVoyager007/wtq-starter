"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { ChatMessage } from "@/lib/types";

export default function ChatBox({ datasetId }: { datasetId: string | null }) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [messages, busy]);

  async function send() {
    const message = text.trim();
    if (!message || busy) return;
    const history = messages;
    setMessages([...history, { role: "user", content: message }]);
    setText("");
    setBusy(true);
    try {
      const { reply } = await api.chat(message, history, datasetId);
      setMessages((m) => [...m, { role: "assistant", content: reply }]);
    } catch (e) {
      setMessages((m) => [...m, { role: "assistant", content: `Sorry, that failed: ${(e as Error).message}` }]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card p-5">
      <h2 className="script text-3xl text-teal">Ask the assistant</h2>
      <p className="data mt-1 text-muted">Free chat. It knows the columns of your table if you loaded one.</p>

      <div className="mt-4 max-h-72 space-y-3 overflow-y-auto pr-1" aria-live="polite">
        {messages.length === 0 && <p className="text-muted italic">Nothing yet. Say hello.</p>}
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
            <p
              className={`max-w-[85%] whitespace-pre-wrap rounded-2xl px-4 py-2 ${
                m.role === "user" ? "bg-teal text-white" : "bg-sky text-ink"
              }`}
            >
              {m.content}
            </p>
          </div>
        ))}
        {busy && <p className="text-muted italic">Thinking...</p>}
        <div ref={endRef} />
      </div>

      <form
        className="mt-4 flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          send();
        }}
      >
        <input
          className="field"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Type a message..."
          aria-label="Chat message"
        />
        <button className="btn btn-primary" disabled={busy || !text.trim()} type="submit">
          Send
        </button>
      </form>
    </div>
  );
}
