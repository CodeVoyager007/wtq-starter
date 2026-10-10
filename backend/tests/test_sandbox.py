"""Checks that AI-written pandas code runs when it is safe, and is stopped when it is not."""
import os

os.environ["LLM_MOCK"] = "1"

import pandas as pd  # noqa: E402
import pytest  # noqa: E402

from app.modules import csv_analyst as c  # noqa: E402

DF = pd.read_csv(os.path.join(os.path.dirname(__file__), "..", "sample_data", "support_tickets.csv"))

SHOULD_WORK = [
    # strftime used to crash with KeyError: '__import__'
    "result = pd.to_datetime(df['created_date']).dt.strftime('%B').value_counts()",
    "result = df['created_date'].apply(lambda s: pd.Timestamp(s).strftime('%A')).value_counts()",
    # AI models often add imports even when told not to
    "import pandas as pd\nimport numpy as np\nresult = df['city'].value_counts()",
    "from datetime import timedelta\nresult = pd.Timestamp('2026-08-01') + timedelta(days=3)",
    "result = format(df['response_hours'].mean(), '.2f')",
    "result = round(df.groupby('city')['response_hours'].mean().min(), 1)",
]

SHOULD_BLOCK = [
    "import os\nresult = os.listdir('.')",
    "from os import system\nresult = 1",
    "result = open('secret.txt').read()",
    "result = __import__('os').getcwd()",
    "result = df.__class__.__mro__",
    "result = pd.read_csv('other.csv')",
    "df.to_csv('leak.csv')\nresult = 1",
    "result = pd.io.common.os.system('echo hi')",
    "result = getattr(df, 'shape')",
    "result = eval('1+1')",
    "result = df[",  # syntax error
]


@pytest.mark.parametrize("code", SHOULD_WORK)
def test_safe_code_runs(code):
    c._run(code, DF)


@pytest.mark.parametrize("code", SHOULD_BLOCK)
def test_unsafe_code_is_blocked(code):
    with pytest.raises(ValueError):
        c._run(code, DF)
