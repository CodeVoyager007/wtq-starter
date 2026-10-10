"""First 2 minutes on event day: profile any dataset from the terminal.

    uv run python scripts/profile_data.py path/to/data.csv
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.modules.profiler import profile_dataframe  # noqa: E402

if len(sys.argv) < 2:
    sys.exit("Usage: uv run python scripts/profile_data.py path/to/data.csv")

path = Path(sys.argv[1])
if path.suffix.lower() in (".xlsx", ".xls"):
    df = pd.read_excel(path)
elif path.suffix.lower() == ".json":
    df = pd.read_json(path)
else:
    df = pd.read_csv(path)

p = profile_dataframe(df)
print(f"\n{path.name}: {p['rows']} rows x {p['columns']} columns\n")
print(f"{'column':28}{'type':12}{'missing':9}{'unique':8}examples")
print("-" * 90)
for c in p["column_info"]:
    print(f"{c['name'][:26]:28}{c['dtype']:12}{c['missing']:<9}{c['unique']:<8}{c['sample']}")
print("\nFirst rows:\n", df.head(5).to_string())
