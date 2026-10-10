export type BillLine = { type: string; amount: number };

export type Level1 = {
  provider: string | null;
  tariff: string | null;
  sanctioned_load_kw: number | null;
  bill_month: string | null;
  reading_date: string | null;
  issue_date: string | null;
  due_date: string | null;
  previous_reading: number | null;
  current_reading: number | null;
  units_consumed: number | null;
  charges: BillLine[];
  total_charges: number | null;
  taxes: BillLine[];
  total_taxes: number | null;
  current_bill: number | null;
  arrears: number | null;
  payable_within_due_date: number | null;
  payable_after_due_date: number | null;
};

export type HistoryRow = { month: string | null; units: number | null; bill: number | null; payment: number | null };

export type DecodedBill = {
  token: string;
  bill_id: string;
  level1: Level1;
  checks: { issues: string[]; repaired: boolean };
  history: HistoryRow[];
  messages: string[];
};
