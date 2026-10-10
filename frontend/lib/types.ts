export type Cell = string | number | boolean | null;

export type Table = { columns: string[]; rows: Cell[][]; truncated?: boolean };
export type Chart = { type: "bar"; labels: string[]; values: number[]; label?: string };
export type Source = { n: number; source: string; snippet: string; score: number };

export type RunResult = {
  ok: boolean;
  kind: string;
  title: string;
  text: string;
  table: Table | null;
  metrics: Record<string, Cell> | null;
  chart: Chart | null;
  code: string | null;
  sources: Source[];
  meta: Record<string, unknown>;
};

export type ColumnInfo = {
  name: string;
  dtype: string;
  missing: number;
  unique: number;
  sample: Cell[];
};

export type Profile = { rows: number; columns: number; column_info: ColumnInfo[]; preview: Table };

export type UploadResponse =
  | { kind: "dataset"; dataset_id: string; name: string; profile: Profile; also_loaded_document?: string }
  | { kind: "document"; name: string; chunks: number };

export type ChatMessage = { role: "user" | "assistant"; content: string };
