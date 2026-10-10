"use client";

import { useRef, useState } from "react";
import { api } from "@/lib/api";
import { images } from "@/lib/config";
import type { BillLine, DecodedBill, Level1 } from "@/lib/types";
import PageHeader from "./PageHeader";

const PROVIDERS = [
  { id: "auto", label: "From file name" },
  { id: "KE", label: "K-Electric" },
  { id: "LESCO", label: "LESCO" },
  { id: "IESCO", label: "IESCO" },
];

const SUGGESTED = [
  "How much of my bill is taxes?",
  "How much more will I pay after the due date?",
  "What is my average monthly consumption?",
  "Estimate my bill next month if I use the same units.",
];

type Row = [label: string, value: string];

const pkr = (n: number | null) =>
  n === null ? "not shown" : `PKR ${n.toLocaleString("en-PK", { maximumFractionDigits: 2 })}`;
const num = (n: number | null, unit = "") => (n === null ? "not shown" : `${n.toLocaleString("en-PK")}${unit}`);
const text = (s: string | null) => s ?? "not shown";
const LABELS: Record<string, string> = {
  fpa: "Fuel price adjustment (FPA)",
  gst: "GST / sales tax",
  quarterly_adjustment: "Quarterly adjustment",
  meter_rent: "Meter rent",
  electricity_duty: "Electricity duty",
  income_tax: "Income tax",
  municipal_tax: "Municipal tax",
  other_tax: "Other tax",
};
const label = (type: string) => LABELS[type] ?? type.charAt(0).toUpperCase() + type.slice(1).replace(/_/g, " ");

function summary(b: Level1): { title: string; rows: Row[] }[] {
  return [
    {
      title: "Account",
      rows: [
        ["Provider", text(b.provider)],
        ["Tariff", text(b.tariff)],
        ["Sanctioned load", num(b.sanctioned_load_kw, " kW")],
      ],
    },
    {
      title: "Dates",
      rows: [
        ["Bill month", text(b.bill_month)],
        ["Reading date", text(b.reading_date)],
        ["Issue date", text(b.issue_date)],
        ["Due date", text(b.due_date)],
      ],
    },
    {
      title: "Meter",
      rows: [
        ["Previous reading", num(b.previous_reading)],
        ["Current reading", num(b.current_reading)],
        ["Units consumed", num(b.units_consumed, " units")],
      ],
    },
    {
      title: "Amounts",
      rows: [
        ["Current bill", pkr(b.current_bill)],
        ["Arrears", pkr(b.arrears)],
        ["Payable by due date", pkr(b.payable_within_due_date)],
        ["Payable after due date", pkr(b.payable_after_due_date)],
      ],
    },
  ];
}

function Lines({ title, lines, total }: { title: string; lines: BillLine[]; total: number | null }) {
  return (
    <div>
      <h4 className="font-bold text-teal-dark">{title}</h4>
      <table className="data mt-2 w-full text-sm">
        <tbody>
          {lines.length === 0 && (
            <tr>
              <td className="py-1 text-muted">No separate lines printed</td>
              <td />
            </tr>
          )}
          {lines.map((l, i) => (
            <tr key={i} className="border-b border-line">
              <td className="py-1">{label(l.type)}</td>
              <td className="py-1 text-right tabular-nums">{pkr(l.amount)}</td>
            </tr>
          ))}
          <tr className="font-bold">
            <td className="py-1">Total</td>
            <td className="py-1 text-right tabular-nums">{pkr(total)}</td>
          </tr>
        </tbody>
      </table>
    </div>
  );
}

export default function BillDecoder() {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string>("");
  const [provider, setProvider] = useState("auto");
  const [bill, setBill] = useState<DecodedBill | null>(null);
  const [answers, setAnswers] = useState<{ question: string; answer: string }[]>([]);
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState<"" | "decode" | "ask">("");
  const [error, setError] = useState("");
  const [showJson, setShowJson] = useState(false);
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
    if (!file) return setError("Choose a bill image first.");
    setError("");
    setBusy("decode");
    try {
      setBill(await api.decodeBill(file, provider));
      setAnswers([]);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy("");
    }
  }

  async function ask(q: string) {
    if (!bill || !q.trim()) return;
    setError("");
    setBusy("ask");
    try {
      const res = await api.askBill(bill.token, q);
      setAnswers((a) => [res, ...a]);
      setQuestion("");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy("");
    }
  }

  return (
    <>
      <PageHeader
        title="Decode a bill"
        text="Upload a K-Electric, LESCO or IESCO bill. We read every detail, check it, and answer your questions in plain English."
        image={images.headerWorkspace}
      />

      <div className="mx-auto grid max-w-6xl gap-6 px-5 py-10 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]">
        {/* Left: upload and the bill image */}
        <section className="card p-5">
          <h2 className="text-xl font-bold text-teal-dark">1. Your bill</h2>
          <div
            className="mt-4 rounded-xl border-2 border-dashed border-line p-4 text-center"
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => {
              e.preventDefault();
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
            <button className="btn btn-ghost" onClick={() => fileRef.current?.click()}>
              {file ? "Choose another image" : "Choose a bill image"}
            </button>
            <p className="mt-2 text-sm text-muted">{file ? file.name : "or drop a .png / .jpg / .webp here"}</p>
          </div>

          <label className="mt-4 block text-sm font-bold text-teal-dark" htmlFor="provider">
            Provider
          </label>
          <select id="provider" className="field mt-1 w-full" value={provider} onChange={(e) => setProvider(e.target.value)}>
            {PROVIDERS.map((p) => (
              <option key={p.id} value={p.id}>
                {p.label}
              </option>
            ))}
          </select>

          <button className="btn btn-primary mt-4 w-full" disabled={!file || busy !== ""} onClick={decode}>
            {busy === "decode" ? "Reading and checking the bill..." : "Decode bill"}
          </button>

          {preview && (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={preview} alt="Uploaded bill" className="mt-5 w-full rounded-lg border border-line" />
          )}
        </section>

        {/* Right: results and questions */}
        <section className="space-y-6">
          {error && <p className="card border-l-4 border-danger p-4 text-danger">{error}</p>}

          {!bill && !error && (
            <div className="card p-6 text-muted">
              Results appear here: the billing details, charges and taxes, the checks we ran, and a box to ask
              anything about the bill.
            </div>
          )}

          {bill && (
            <>
              <div className="card p-5">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <h2 className="text-xl font-bold text-teal-dark">2. Bill details</h2>
                  {bill.checks.issues.length === 0 ? (
                    <span className="rounded-full bg-sky px-3 py-1 text-sm font-bold text-teal-dark">
                      ✓ All checks passed{bill.checks.repaired ? " (after a re-read)" : ""}
                    </span>
                  ) : (
                    <span className="rounded-full bg-sky px-3 py-1 text-sm font-bold text-danger">
                      {bill.checks.issues.length} check(s) need a look
                    </span>
                  )}
                </div>

                <div className="mt-4 grid gap-5 sm:grid-cols-2">
                  {summary(bill.level1).map((group) => (
                    <div key={group.title}>
                      <h3 className="font-bold text-teal-dark">{group.title}</h3>
                      <table className="data mt-2 w-full text-sm">
                        <tbody>
                          {group.rows.map(([k, v]) => (
                            <tr key={k} className="border-b border-line">
                              <td className="py-1 text-muted">{k}</td>
                              <td className={`py-1 text-right tabular-nums ${v === "not shown" ? "text-muted" : ""}`}>{v}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ))}
                  <Lines title="Charges" lines={bill.level1.charges} total={bill.level1.total_charges} />
                  <Lines title="Taxes" lines={bill.level1.taxes} total={bill.level1.total_taxes} />
                </div>

                {bill.checks.issues.length > 0 && (
                  <ul className="mt-4 list-disc pl-5 text-sm text-danger">
                    {bill.checks.issues.map((i) => (
                      <li key={i}>{i}</li>
                    ))}
                  </ul>
                )}

                {bill.messages.length > 0 && (
                  <div className="mt-4 rounded-lg bg-sky p-3 text-sm">
                    <p className="font-bold text-teal-dark">Notices on the bill (in English)</p>
                    <ul className="mt-1 list-disc pl-5">
                      {bill.messages.map((m) => (
                        <li key={m}>{m}</li>
                      ))}
                    </ul>
                  </div>
                )}

                <button className="btn btn-ghost mt-4 text-sm" onClick={() => setShowJson((s) => !s)}>
                  {showJson ? "Hide" : "Show"} Level 1 JSON
                </button>
                {showJson && (
                  <pre className="data mt-3 max-h-96 overflow-auto rounded-lg bg-sky p-3 text-xs">
                    {JSON.stringify(bill.level1, null, 2)}
                  </pre>
                )}
              </div>

              <div className="card p-5">
                <h2 className="text-xl font-bold text-teal-dark">3. Ask about this bill</h2>
                <form
                  className="mt-3 flex flex-col gap-2 sm:flex-row"
                  onSubmit={(e) => {
                    e.preventDefault();
                    ask(question);
                  }}
                >
                  <input
                    className="field flex-1"
                    placeholder="e.g. Why is my bill higher than last month?"
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                  />
                  <button className="btn btn-primary" disabled={busy !== "" || !question.trim()}>
                    {busy === "ask" ? "Thinking..." : "Ask"}
                  </button>
                </form>
                <div className="mt-3 flex flex-wrap gap-2">
                  {SUGGESTED.map((q) => (
                    <button key={q} className="btn btn-ghost text-sm" disabled={busy !== ""} onClick={() => ask(q)}>
                      {q}
                    </button>
                  ))}
                </div>
                <ul className="mt-5 space-y-4">
                  {answers.map((a, i) => (
                    <li key={i} className="border-l-4 border-sage pl-4">
                      <p className="font-bold text-teal-dark">{a.question}</p>
                      <p className="mt-1 leading-relaxed">{a.answer}</p>
                    </li>
                  ))}
                </ul>
              </div>
            </>
          )}
        </section>
      </div>
    </>
  );
}
