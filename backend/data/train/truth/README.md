# Reference answers for the training bills

- `KESC_0008.json` is official (participant guide, section 5.7).
- The other four are hand-read by us from the images. Judgment calls, not confirmed by the organisers:
  - Net metering bills with several meter registers: `previous_reading` and `current_reading` are `null`;
    `units_consumed` is the single printed total if there is one (KESC_0004: 901), else `null` (LESCO_0005).
  - LESCO / IESCO print only a combined tax figure, so `taxes` is `[]` and the figure is in `total_taxes`.
  - LESCO / IESCO "Total Electricity Charges" is one `energy` line; "Net Electricity Charges" is `total_charges`.
  - IESCO "Total FPA" (side column of the charges section) is an `fpa` charge line.
  - "NOT TO BE PAID" late amount means `payable_after_due_date` is `null`.
