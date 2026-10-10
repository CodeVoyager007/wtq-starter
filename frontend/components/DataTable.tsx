import type { Table } from "@/lib/types";

export default function DataTable({ table }: { table: Table }) {
  return (
    <div className="data max-h-96 overflow-auto rounded-xl border border-line">
      <table className="w-full border-collapse text-left">
        <thead className="sticky top-0 bg-sky text-teal-dark">
          <tr>
            {table.columns.map((c) => (
              <th key={c} className="whitespace-nowrap px-3 py-2 font-semibold">
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {table.rows.map((row, i) => (
            <tr key={i} className="border-t border-line odd:bg-white even:bg-mist/60">
              {row.map((cell, j) => (
                <td key={j} className="max-w-xs px-3 py-1.5 align-top">
                  {cell === null || cell === "" ? <span className="text-muted">-</span> : String(cell)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {table.truncated && <p className="px-3 py-2 text-muted">Showing the first rows only.</p>}
    </div>
  );
}
