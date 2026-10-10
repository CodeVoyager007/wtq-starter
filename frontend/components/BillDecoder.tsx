"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { BillLine, DecodedBill, Level1 } from "@/lib/types";
import PageHeader from "./PageHeader";

const PROVIDERS = [
  { id: "auto", label: "Auto" },
  { id: "KE", label: "K-Electric" },
  { id: "LESCO", label: "LESCO" },
  { id: "IESCO", label: "IESCO" },
];

const SUGGESTED = [
  "How much of my bill is taxes?",
  "What happens if I pay late?",
  "What is my average monthly consumption?",
  "Estimate my bill next month if I use the same units.",
];

const STAGES = ["Reading the bill", "Transcribing every line", "Checking the bill's own sums"];

const LABELS: Record<string, string> = {
  fpa: "Fuel price adjustment",
  gst: "GST / sales tax",
  quarterly_adjustment: "Quarterly adjustment",
  meter_rent: "Meter rent",
  electricity_duty: "Electricity duty",
  income_tax: "Income tax",
  municipal_tax: "Municipal tax",
  other_tax: "Other tax",
};

const label = (type: string) => LABELS[type] ?? type.charAt(0).toUpperCase() + type.slice(1).replace(/_/g, " ");
const pkr = (n: number | null) =>
  n === null ? "—" : `PKR ${n.toLocaleString("en-PK", { maximumFractionDigits: 2 })}`;
const num = (n: number | null, unit = "") => (n === null ? "—" : `${n.toLocaleString("en-PK")}${unit}`);
const text = (s: string | null) => s ?? "—";
const delay = (i: number) => ({ animationDelay: `${i * 70}ms` });

type Answer = { question: string; answer: string | null };

/** Pretty JSON in the video's data colours: keys amber, numbers blue, text green, nulls red. */
function JsonView({ value }: { value: unknown }) {
  const json = JSON.stringify(value, null, 2);
  const parts = json.split(/("(?:[^"\\]|\\.)*"|-?\d+(?:\.\d+)?|null)/g);
  return (
    <>
      {parts.map((part, i) => {
        if (i % 2 === 0) return part;
        const cls = parts[i + 1]?.trimStart().startsWith(":")
          ? "json-key"
          : part === "null"
            ? "json-null"
            : part.startsWith('"')
              ? "json-string"
              : "json-number";
        return (
          <span key={i} className={cls}>
            {part}
          </span>
        );
      })}
    </>
  );
}

function Tile({ title, value, hint, index, big }: { title: string; value: string; hint?: string; index: number; big?: boolean }) {
  return (
    <div className="tile reveal" style={delay(index)}>
      <p className="label text-sm text-muted">{title}</p>
      <p className={`mono mt-1 text-number ${big ? "text-2xl" : "text-xl"}`}>{value}</p>
      {hint && <p className="mt-1 text-xs text-muted">{hint}</p>}
    </div>
  );
}

function Breakdown({ title, lines, total }: { title: string; lines: BillLine[]; total: number | null }) {
  const scale = Math.max(...lines.map((l) => Math.abs(l.amount)), 1);
  return (
    <div>
      <div className="flex items-baseline justify-between">
        <h4 className="text-lg text-teal-dark">{title}</h4>
        <span className="data text-number">{pkr(total)}</span>
      </div>
      {lines.length === 0 ? (
        <p className="mt-2 text-sm text-muted">The bill prints one combined figure, no separate lines.</p>
      ) : (
        <ul className="mt-3 space-y-3">
          {lines.map((l, i) => (
            <li key={i} className="reveal" style={delay(i)}>
              <div className="flex justify-between gap-3 text-sm">
                <span>{label(l.type)}</span>
                <span className={`data ${l.amount < 0 ? "text-ok" : "text-number"}`}>{pkr(l.amount)}</span>
              </div>
              <div className="mt-1 h-1.5 rounded-full bg-sky">
                <div className="bar" style={{ width: `${(Math.abs(l.amount) / scale) * 100}%` }} />
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function Details({ bill }: { bill: Level1 }) {
  const groups: [string, [string, string][]][] = [
    ["Account", [["Provider", text(bill.provider)], ["Tariff", text(bill.tariff)], ["Sanctioned load", num(bill.sanctioned_load_kw, " kW")]]],
    ["Dates", [["Bill month", text(bill.bill_month)], ["Reading", text(bill.reading_date)], ["Issued", text(bill.issue_date)], ["Due", text(bill.due_date)]]],
    ["Meter", [["Previous", num(bill.previous_reading)], ["Current", num(bill.current_reading)], ["Units", num(bill.units_consumed)]]],
    ["Amounts", [["Arrears", pkr(bill.arrears)], ["After due date", pkr(bill.payable_after_due_date)], ["Total charges", pkr(bill.total_charges)], ["Total taxes", pkr(bill.total_taxes)]]],
  ];
  return (
    <div className="grid gap-x-8 gap-y-6 sm:grid-cols-2">
      {groups.map(([title, rows], g) => (
        <div key={title} className="reveal" style={delay(g)}>
          <h4 className="text-lg text-teal-dark">{title}</h4>
          <dl className="mt-2 divide-y divide-line">
            {rows.map(([k, v]) => (
              <div key={k} className="flex justify-between gap-4 py-1.5 text-sm">
                <dt className="text-muted">{k}</dt>
                <dd className={`data ${v === "—" ? "text-danger" : "text-number"}`}>{v}</dd>
              </div>
            ))}
          </dl>
        </div>
      ))}
    </div>
  );
}

function Decoding() {
  const [stage, setStage] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setStage((s) => Math.min(s + 1, STAGES.length - 1)), 3500);
    return () => clearInterval(id);
  }, []);
  return (
    <div className="card reveal p-6 sm:p-8">
      <ol className="space-y-3">
        {STAGES.map((s, i) => (
          <li key={s} className={`flex items-center gap-3 ${i > stage ? "text-muted" : ""}`}>
            <span
              className={`grid h-7 w-7 place-items-center rounded-full border text-sm ${
                i < stage ? "border-ok text-ok" : i === stage ? "glow border-teal text-teal" : "border-line"
              }`}
            >
              {i < stage ? "✓" : i + 1}
            </span>
            <span className="label text-lg">{s}</span>
            {i === stage && (
              <span aria-hidden>
                <span className="dot" />
                <span className="dot" />
                <span className="dot" />
              </span>
            )}
          </li>
        ))}
      </ol>
      <div className="mt-8 grid gap-3 sm:grid-cols-4">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="skeleton h-20" />
        ))}
      </div>
      <div className="skeleton mt-4 h-40" />
    </div>
  );
}

export default function BillDecoder() {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState("");
  const [provider, setProvider] = useState("auto");
  const [bill, setBill] = useState<DecodedBill | null>(null);
  const [answers, setAnswers] = useState<Answer[]>([]);
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState<"" | "decode" | "ask">("");
  const [error, setError] = useState("");
  const [showJson, setShowJson] = useState(false);
  const [dragging, setDragging] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  function choose(f: File | undefined) {
    if (!f) return;
    if (preview) URL.revokeObjectURL(preview);
    setFile(f);
    setPreview(URL.createObjectURL(f));
    setBill(null);
    setAnswers([]);
    setError("");
  }

  async function decode() {
    if (!file) return;
    setError("");
    setBill(null);
    setBusy("decode");
    try {
      setBill(await api.decodeBill(file, provider));
      setAnswers([]);
      setShowJson(false);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy("");
    }
  }

  async function ask(q: string) {
    if (!bill || !q.trim() || busy) return;
    setError("");
    setBusy("ask");
    setQuestion("");
    setAnswers((a) => [...a, { question: q, answer: null }]);
    try {
      const res = await api.askBill(bill.token, q);
      setAnswers((a) => a.map((x, i) => (i === a.length - 1 ? { question: q, answer: res.answer } : x)));
    } catch (e) {
      setAnswers((a) => a.slice(0, -1));
      setError((e as Error).message);
    } finally {
      setBusy("");
    }
  }

  const l1 = bill?.level1;
  const passed = bill && bill.checks.issues.length === 0;

  return (
    <>
      <PageHeader
        title="Decode a bill"
        text="Upload a K-Electric, LESCO or IESCO bill. Every value is read, checked against the bill's own sums, and explained in plain English."
      />

      <div className="mx-auto grid max-w-7xl gap-8 px-5 py-10 sm:px-8 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)] lg:py-14">
        {/* Left: the bill */}
        <section className="card self-start p-6 sm:p-7 lg:sticky lg:top-20">
          <p className="label text-sm text-muted">Step 1</p>
          <h2 className="text-3xl text-teal">Your bill</h2>

          <div
            role="button"
            tabIndex={0}
            className={`dropzone mt-5 cursor-pointer p-6 text-center ${dragging ? "active" : ""}`}
            onClick={() => fileRef.current?.click()}
            onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && fileRef.current?.click()}
            onDragOver={(e) => {
              e.preventDefault();
              setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragging(false);
              choose(e.dataTransfer.files[0]);
            }}
          >
            <input
              ref={fileRef}
              type="file"
              accept="image/png,image/jpeg,image/webp"
              className="hidden"
              onChange={(e) => choose(e.target.files?.[0])}
            />
            <svg viewBox="0 0 24 24" className="mx-auto h-9 w-9 text-teal" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden>
              <path d="M12 16V4m0 0-4 4m4-4 4 4M4 16v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            <p className="mt-2 font-semibold">{file ? file.name : "Drop a bill photo or click to choose"}</p>
            <p className="mt-1 text-sm text-muted">PNG, JPG or WEBP · up to 10 MB</p>
          </div>

          <p className="label mt-5 text-sm text-muted">Provider</p>
          <div className="mt-2 grid grid-cols-4 gap-2" role="radiogroup" aria-label="Provider">
            {PROVIDERS.map((p) => (
              <button
                key={p.id}
                role="radio"
                aria-checked={provider === p.id}
                onClick={() => setProvider(p.id)}
                className={`rounded-lg border px-2 py-2 text-sm transition ${
                  provider === p.id ? "border-teal bg-sky text-teal" : "border-line text-muted hover:text-ink"
                }`}
              >
                {p.label}
              </button>
            ))}
          </div>

          <button
            className={`btn btn-primary mt-6 w-full text-lg ${file && !busy && !bill ? "glow" : ""}`}
            disabled={!file || busy !== ""}
            onClick={decode}
          >
            {busy === "decode" ? "Decoding…" : "Decode bill"}
          </button>

          {preview && (
            <div className={`scan-frame mt-6 border border-line ${busy === "decode" ? "scanning" : ""}`}>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={preview} alt="Uploaded bill" className="block w-full" />
            </div>
          )}
        </section>

        {/* Right: results and questions */}
        <section className="min-w-0 space-y-8">
          {error && (
            <p role="alert" className="card reveal border-l-4 border-l-danger p-4 text-danger">
              {error}
            </p>
          )}

          {!bill && busy !== "decode" && (
            <div className="card reveal p-6 sm:p-8">
              <p className="label text-sm text-muted">What you get</p>
              <ul className="mt-4 grid gap-4 sm:grid-cols-3">
                {[
                  ["Every detail", "Dates, readings, each charge and tax line, arrears and late amounts."],
                  ["Checked", "Sums are verified and every value is matched to a second reading of the bill."],
                  ["Explained", "Ask anything. Numbers are calculated in code, never guessed."],
                ].map(([t, d], i) => (
                  <li key={t} className="tile reveal" style={delay(i)}>
                    <p className="label text-lg text-teal">{t}</p>
                    <p className="mt-1 text-sm text-muted">{d}</p>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {busy === "decode" && <Decoding />}

          {bill && l1 && (
            <>
              <div className="card reveal p-6 sm:p-8">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="label text-sm text-muted">Step 2 · {bill.bill_id}</p>
                    <h2 className="text-3xl text-teal">Bill details</h2>
                  </div>
                  <span
                    className={`label rounded-full border px-4 py-1.5 text-sm ${
                      passed ? "border-ok text-ok" : "border-danger text-danger"
                    }`}
                  >
                    {passed
                      ? `✓ Grounded in the bill${bill.checks.repaired ? " · corrected on re-read" : ""}`
                      : `${bill.checks.issues.length} check(s) need a look`}
                  </span>
                </div>

                <div className="mt-6 grid grid-cols-2 gap-3 md:grid-cols-4">
                  <Tile index={0} big title="Payable by due date" value={pkr(l1.payable_within_due_date)} />
                  <Tile index={1} title="Due date" value={text(l1.due_date)} />
                  <Tile index={2} title="Units" value={num(l1.units_consumed)} hint={text(l1.bill_month)} />
                  <Tile index={3} title="Current bill" value={pkr(l1.current_bill)} />
                </div>

                <div className="mt-8 grid gap-8 md:grid-cols-2">
                  <Breakdown title="Charges" lines={l1.charges} total={l1.total_charges} />
                  <Breakdown title="Taxes" lines={l1.taxes} total={l1.total_taxes} />
                </div>

                <hr className="my-8 border-line" />
                <Details bill={l1} />

                {bill.checks.issues.length > 0 && (
                  <ul className="mt-6 list-disc space-y-1 pl-5 text-sm text-danger">
                    {bill.checks.issues.map((i) => (
                      <li key={i}>{i}</li>
                    ))}
                  </ul>
                )}

                {bill.messages.length > 0 && (
                  <div className="mt-6 rounded-xl border border-line bg-sky p-4 text-sm">
                    <p className="label text-base text-teal-dark">Notices on the bill · in English</p>
                    <ul className="mt-1 list-disc space-y-1 pl-5">
                      {bill.messages.map((m) => (
                        <li key={m}>{m}</li>
                      ))}
                    </ul>
                  </div>
                )}

                <button className="btn btn-ghost mt-6 text-sm" onClick={() => setShowJson((s) => !s)} aria-expanded={showJson}>
                  {showJson ? "Hide" : "Show"} Level 1 JSON
                </button>
                {showJson && (
                  <pre className="data reveal mt-4 max-h-[28rem] overflow-auto rounded-xl border border-line bg-mist p-4 text-xs">
                    <JsonView value={l1} />
                  </pre>
                )}
              </div>

              <div className="card reveal p-6 sm:p-8" style={delay(2)}>
                <p className="label text-sm text-muted">Step 3</p>
                <h2 className="text-3xl text-teal">Ask about this bill</h2>

                <div className="mt-5 flex flex-wrap gap-2">
                  {SUGGESTED.map((q) => (
                    <button key={q} className="btn btn-ghost px-4 py-1.5 text-sm" disabled={busy !== ""} onClick={() => ask(q)}>
                      {q}
                    </button>
                  ))}
                </div>

                {answers.length > 0 && (
                  <ul className="mt-6 space-y-4" aria-live="polite">
                    {answers.map((a, i) => (
                      <li key={i} className="reveal space-y-2">
                        <p className="ml-auto w-fit max-w-[85%] rounded-2xl rounded-br-sm bg-teal px-4 py-2 font-semibold text-mist">
                          {a.question}
                        </p>
                        <div className="w-fit max-w-[92%] rounded-2xl rounded-bl-sm border border-line bg-sky px-4 py-3 leading-relaxed">
                          {a.answer ?? (
                            <span aria-label="Thinking">
                              <span className="dot" />
                              <span className="dot" />
                              <span className="dot" />
                            </span>
                          )}
                        </div>
                      </li>
                    ))}
                  </ul>
                )}

                <form
                  className="mt-6 flex flex-col gap-2 sm:flex-row"
                  onSubmit={(e) => {
                    e.preventDefault();
                    ask(question);
                  }}
                >
                  <input
                    className="field flex-1"
                    placeholder="Ask anything, e.g. Why is my bill higher than last month?"
                    maxLength={500}
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                  />
                  <button className="btn btn-primary" disabled={busy !== "" || !question.trim()}>
                    Ask
                  </button>
                </form>
              </div>
            </>
          )}
        </section>
      </div>
    </>
  );
}
