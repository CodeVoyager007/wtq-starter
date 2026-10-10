"use client";

import { useRef, useState } from "react";
import Photo from "./Photo";
import { api } from "@/lib/api";
import { images, modes, type ModeId } from "@/lib/config";
import PageHeader from "./PageHeader";
import type { Profile, RunResult } from "@/lib/types";
import ChatBox from "./ChatBox";
import DataTable from "./DataTable";
import ResultView from "./ResultView";

type Dataset = { id: string; name: string; profile: Profile };

export default function Workspace() {
  const [dataset, setDataset] = useState<Dataset | null>(null);
  const [docs, setDocs] = useState<string[]>([]);
  const [mode, setMode] = useState<ModeId>("analyze");
  const [input, setInput] = useState("");
  const [options, setOptions] = useState({ labels: "", fields: "", column: "", target: "" });
  const [result, setResult] = useState<RunResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [drag, setDrag] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const current = modes.find((m) => m.id === mode)!;
  const columns = dataset?.profile.column_info.map((c) => c.name) ?? [];

  async function handleFiles(files: FileList | File[]) {
    setError("");
    setNotice("");
    setUploading(true);
    try {
      for (const file of Array.from(files)) {
        const res = await api.uploadFile(file);
        if (res.kind === "dataset") {
          setDataset({ id: res.dataset_id, name: res.name, profile: res.profile });
          setNotice(`Loaded ${res.name} (${res.profile.rows} rows).`);
        } else {
          setDocs((d) => [...d, res.name]);
          setNotice(`Added ${res.name} (${res.chunks} pieces of text).`);
        }
      }
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  async function loadSample() {
    setError("");
    setNotice("");
    setUploading(true);
    try {
      const res = await api.loadSample();
      if (res.kind === "dataset") {
        setDataset({ id: res.dataset_id, name: res.name, profile: res.profile });
        setDocs(res.also_loaded_document ? [res.also_loaded_document] : []);
        setNotice("Sample table and FAQ document loaded. Try: Which city has the slowest average response time?");
      }
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setUploading(false);
    }
  }

  async function run() {
    setError("");
    setResult(null);
    if (current.needs === "dataset" && !dataset) return setError("Load a table first (upload a file or use the sample).");
    if (current.needs === "docs" && docs.length === 0) return setError("Upload a document first (.txt, .md or .pdf).");
    setBusy(true);
    try {
      const res = await api.run({
        mode,
        input,
        dataset_id: dataset?.id ?? null,
        options: {
          labels: options.labels,
          fields: options.fields,
          column: options.column,
          target: options.target,
        },
      });
      setResult(res);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const showTextInput = mode !== "predict";
  const needsLabels = mode === "classify";
  const needsFields = mode === "extract";
  const needsColumn = mode === "extract" || mode === "classify";

  return (
    <>
    <PageHeader title="Workspace" text="Add your data, choose what to do, and press Run." image={images.headerWorkspace} />
    <div className="mx-auto max-w-6xl px-5 pt-8">
      <div className="grid gap-6 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]">
        {/* LEFT: inputs */}
        <div className="space-y-6">
          <section className="card p-5">
            <h2 className="script text-3xl text-teal">1. Your data</h2>

            <div
              onDragOver={(e) => {
                e.preventDefault();
                setDrag(true);
              }}
              onDragLeave={() => setDrag(false)}
              onDrop={(e) => {
                e.preventDefault();
                setDrag(false);
                handleFiles(e.dataTransfer.files);
              }}
              className={`mt-4 rounded-2xl border-2 border-dashed p-6 text-center transition ${
                drag ? "border-teal bg-sky" : "border-sage bg-mist"
              }`}
            >
              <p className="text-lg">Drop a file here</p>
              <p className="data mt-1 text-muted">.csv .xlsx .json (tables) or .txt .md .pdf (documents)</p>
              <div className="mt-4 flex flex-wrap justify-center gap-2">
                <button className="btn btn-ghost" onClick={() => fileRef.current?.click()} disabled={uploading} type="button">
                  Choose file
                </button>
                <button className="btn btn-ghost" onClick={loadSample} disabled={uploading} type="button">
                  Load sample data
                </button>
              </div>
              <input
                ref={fileRef}
                type="file"
                multiple
                accept=".csv,.xlsx,.xls,.json,.txt,.md,.pdf"
                className="hidden"
                onChange={(e) => e.target.files && handleFiles(e.target.files)}
              />
            </div>

            {uploading && <p className="mt-3 text-muted italic">Reading file...</p>}
            {notice && <p className="data mt-3 rounded-lg bg-sky px-3 py-2 text-teal-dark">{notice}</p>}

            {dataset && (
              <div className="mt-4">
                <p className="font-bold text-teal-dark">
                  {dataset.name} <span className="data font-normal text-muted">{dataset.profile.rows} rows, {dataset.profile.columns} columns</span>
                </p>
                <ul className="data mt-2 max-h-40 space-y-1 overflow-auto">
                  {dataset.profile.column_info.map((c) => (
                    <li key={c.name} className="flex justify-between gap-3 border-b border-line py-1">
                      <span className="font-semibold">{c.name}</span>
                      <span className="text-muted">
                        {c.dtype}
                        {c.missing > 0 && ` · ${c.missing} missing`}
                      </span>
                    </li>
                  ))}
                </ul>
                <details className="mt-3">
                  <summary className="cursor-pointer font-bold text-teal-dark">Preview rows</summary>
                  <div className="mt-2">
                    <DataTable table={dataset.profile.preview} />
                  </div>
                </details>
              </div>
            )}
            {docs.length > 0 && (
              <p className="data mt-3 text-muted">
                Documents loaded: <span className="font-semibold text-teal-dark">{docs.join(", ")}</span>
              </p>
            )}
          </section>

          <section className="card p-5">
            <h2 className="script text-3xl text-teal">2. What should it do?</h2>
            <div className="mt-4 flex flex-wrap gap-2" role="tablist" aria-label="Mode">
              {modes.map((m) => (
                <button
                  key={m.id}
                  role="tab"
                  aria-selected={mode === m.id}
                  onClick={() => {
                    setMode(m.id);
                    setResult(null);
                    setError("");
                  }}
                  className={`rounded-full border px-4 py-1.5 text-base transition ${
                    mode === m.id
                      ? "border-teal bg-teal font-bold text-white"
                      : "border-line bg-white text-ink hover:border-sage"
                  }`}
                  type="button"
                >
                  {m.label}
                </button>
              ))}
            </div>
            <p className="mt-3 italic text-muted">{current.hint}</p>

            <div className="mt-4 space-y-3">
              {showTextInput && (
                <textarea
                  className="field min-h-28"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder={current.placeholder}
                  aria-label="Input"
                />
              )}
              {needsLabels && (
                <label className="block">
                  <span className="data font-semibold text-muted">Labels (comma separated)</span>
                  <input
                    className="field mt-1"
                    value={options.labels}
                    onChange={(e) => setOptions({ ...options, labels: e.target.value })}
                    placeholder="billing, delivery, technical, account"
                  />
                </label>
              )}
              {needsFields && (
                <label className="block">
                  <span className="data font-semibold text-muted">Fields to extract (comma separated, optional)</span>
                  <input
                    className="field mt-1"
                    value={options.fields}
                    onChange={(e) => setOptions({ ...options, fields: e.target.value })}
                    placeholder="people, organizations, locations, dates"
                  />
                </label>
              )}
              {needsColumn && (
                <label className="block">
                  <span className="data font-semibold text-muted">Or run on a text column of your table (first 10 rows)</span>
                  <input
                    className="field mt-1"
                    list="columns"
                    value={options.column}
                    onChange={(e) => setOptions({ ...options, column: e.target.value })}
                    placeholder={columns[0] ? `e.g. ${columns[columns.length - 1]}` : "column name"}
                  />
                </label>
              )}
              {mode === "predict" && (
                <label className="block">
                  <span className="data font-semibold text-muted">Column to predict</span>
                  <input
                    className="field mt-1"
                    list="columns"
                    value={options.target}
                    onChange={(e) => setOptions({ ...options, target: e.target.value })}
                    placeholder="e.g. resolved"
                  />
                </label>
              )}
              <datalist id="columns">
                {columns.map((c) => (
                  <option key={c} value={c} />
                ))}
              </datalist>
            </div>

            <button className="btn btn-primary mt-5 w-full text-lg" onClick={run} disabled={busy} type="button">
              {busy ? "Working..." : "Run"}
            </button>
          </section>
        </div>

        {/* RIGHT: results + chat */}
        <div className="space-y-6">
          <section className="card min-h-64 p-5" aria-live="polite">
            <h2 className="script text-3xl text-teal">3. Result</h2>
            <div className="mt-4">
              {busy && <p className="text-lg italic text-muted">Thinking, this can take a few seconds...</p>}
              {error && (
                <p role="alert" className="rounded-xl border border-danger/40 bg-danger/5 px-4 py-3 text-danger">
                  {error}
                </p>
              )}
              {!busy && !error && !result && (
                <div className="relative overflow-hidden rounded-xl">
                  <Photo pic={images.empty} className="h-44 w-full object-cover" />
                  <p className="absolute inset-0 flex items-center justify-center bg-[#06192a]/45 px-4 text-center text-xl italic text-white">
                    Your answer will appear here.
                  </p>
                </div>
              )}
              {result && <ResultView result={result} />}
            </div>
          </section>
          <ChatBox datasetId={dataset?.id ?? null} />
        </div>
      </div>
    </div>
    </>
  );
}
