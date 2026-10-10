import type { Chart } from "@/lib/types";

/** Simple horizontal bar chart in plain HTML/CSS (no chart library to install or break). */
export default function BarChart({ chart }: { chart: Chart }) {
  const max = Math.max(...chart.values.map((v) => Math.abs(v)), 1e-9);
  return (
    <div className="data" role="img" aria-label={chart.label ?? "bar chart"}>
      {chart.label && <p className="mb-2 font-semibold text-muted">{chart.label}</p>}
      <ul className="space-y-1.5">
        {chart.labels.map((label, i) => {
          const v = chart.values[i];
          return (
            <li key={`${label}-${i}`} className="grid grid-cols-[minmax(4rem,9rem)_1fr_auto] items-center gap-3">
              <span className="truncate text-right text-muted" title={label}>
                {label}
              </span>
              <span className="h-5 rounded-full bg-sky">
                <span
                  className="block h-5 rounded-full bg-teal"
                  style={{ width: `${Math.max((Math.abs(v) / max) * 100, 2)}%` }}
                />
              </span>
              <span className="w-14 text-left font-semibold tabular-nums">{Number.isInteger(v) ? v : v.toFixed(2)}</span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
