import BarChart from "./BarChart";
import DataTable from "./DataTable";
import type { RunResult } from "@/lib/types";

/** Shows any result from the backend. If a field is empty it is simply not drawn. */
export default function ResultView({ result }: { result: RunResult }) {
  return (
    <div className="space-y-5">
      {result.title && <h3 className="script text-3xl text-teal">{result.title}</h3>}

      {result.text && <p className="whitespace-pre-wrap text-lg text-ink/90">{result.text}</p>}

      {result.metrics && (
        <dl className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          {Object.entries(result.metrics).map(([k, v]) => (
            <div key={k} className="rounded-xl bg-sky/70 px-4 py-3">
              <dt className="data text-muted">{k.replaceAll("_", " ")}</dt>
              <dd className="text-2xl font-bold text-teal-dark">{v === null ? "-" : String(v)}</dd>
            </div>
          ))}
        </dl>
      )}

      {result.chart && <BarChart chart={result.chart} />}
      {result.table && <DataTable table={result.table} />}

      {result.sources.length > 0 && (
        <div>
          <h4 className="mb-2 font-bold text-teal-dark">Sources</h4>
          <ul className="data space-y-2">
            {result.sources.map((s) => (
              <li key={s.n} className="rounded-xl border border-line bg-white p-3">
                <span className="font-semibold text-teal-dark">
                  [{s.n}] {s.source}
                </span>
                <span className="ml-2 text-muted">match {s.score}</span>
                <p className="mt-1 text-muted">{s.snippet}...</p>
              </li>
            ))}
          </ul>
        </div>
      )}

      {result.code && (
        <details className="rounded-xl border border-line bg-white p-3">
          <summary className="cursor-pointer font-bold text-teal-dark">Show the code the AI wrote</summary>
          <pre className="data mt-3 overflow-x-auto rounded-lg bg-ink p-4 text-mist">{result.code}</pre>
        </details>
      )}
    </div>
  );
}
