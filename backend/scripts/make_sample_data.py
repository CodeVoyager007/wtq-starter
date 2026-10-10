"""Makes the demo files in sample_data/. Run: uv run python scripts/make_sample_data.py"""
import random
from pathlib import Path

import numpy as np
import pandas as pd

random.seed(7)
np.random.seed(7)
out = Path(__file__).resolve().parent.parent / "sample_data"
out.mkdir(exist_ok=True)

cities = ["Karachi", "Lahore", "Islamabad", "Rawalpindi", "Faisalabad"]
categories = {
    "billing": ["I was charged twice for my monthly plan.", "My invoice shows the wrong amount.", "I want a refund for last month."],
    "technical": ["The app crashes when I open the reports page.", "I cannot log in after the update.", "The export button does nothing."],
    "delivery": ["My order has not arrived after five days.", "The courier marked it delivered but I got nothing.", "The package arrived damaged."],
    "account": ["Please change the email on my account.", "How do I delete my profile?", "I did not get the verification code."],
}
channels = ["email", "chat", "phone", "app"]
rows = []
for i in range(1, 241):
    cat = random.choice(list(categories))
    prio = random.choices(["low", "medium", "high"], weights=[4, 4, 2])[0]
    base = {"low": 30, "medium": 18, "high": 8}[prio]
    hours = max(0.5, np.random.normal(base, 6))
    sat = int(np.clip(round(5 - hours / 12 + np.random.normal(0, 0.8)), 1, 5))
    resolved = "yes" if (sat >= 3 or random.random() < 0.25) else "no"
    rows.append(
        {
            "ticket_id": f"T{1000 + i}",
            "created_date": (pd.Timestamp("2026-08-01") + pd.Timedelta(days=random.randint(0, 55))).date().isoformat(),
            "city": random.choice(cities),
            "category": cat,
            "priority": prio,
            "channel": random.choice(channels),
            "response_hours": round(hours, 1),
            "satisfaction": sat,
            "resolved": resolved,
            "message": random.choice(categories[cat]),
        }
    )
df = pd.DataFrame(rows)
df.loc[df.sample(frac=0.05, random_state=1).index, "response_hours"] = np.nan  # a few missing values on purpose
df.to_csv(out / "support_tickets.csv", index=False)

(out / "faq.txt").write_text(
    """Support FAQ (demo document)

Refund policy: Customers can request a refund within 14 days of a charge. Refunds are sent to the original payment method within 5 to 7 working days. Duplicate charges are refunded in full after verification.

Response times: High priority tickets get a first reply within 8 hours. Medium priority tickets get a reply within 24 hours. Low priority tickets get a reply within 48 hours.

Delivery: Standard delivery takes 3 to 5 working days in Karachi, Lahore and Islamabad, and up to 7 days elsewhere. If an order is marked delivered but not received, contact support within 48 hours so we can open a courier investigation.

Account help: To change your email, open Settings, then Profile, then Email. Deleting a profile removes all data after 30 days. Verification codes expire after 10 minutes.

Technical issues: If the app crashes, update to the latest version and clear the cache. If login fails after an update, reset your password from the login page.
""",
    encoding="utf-8",
)
print("Wrote", out / "support_tickets.csv", "and", out / "faq.txt")
