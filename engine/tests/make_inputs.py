"""Create synthetic test inputs (no client data): an Excel campaign report."""
from pathlib import Path

from openpyxl import Workbook

out = Path(__file__).parent / "inputs"
out.mkdir(exist_ok=True)
wb = Workbook()
ws = wb.active
ws.title = "Quarterly KPIs"
ws.append(["Quarter", "Reach (M)", "Engagement rate %", "Leads", "Cost per lead EUR", "Brand awareness %"])
for row in [("Q1 2026", 4.2, 2.1, 820, 46, 31), ("Q2 2026", 5.8, 2.6, 1140, 41, 34),
            ("Q3 2026", 7.1, 3.4, 1625, 33, 39)]:
    ws.append(row)
ws2 = wb.create_sheet("Channels Q3")
ws2.append(["Channel", "Share of leads %", "Engagement rate %"])
for row in [("LinkedIn", 46, 4.1), ("Trade media", 21, 1.8), ("Events", 18, 6.2), ("Search", 10, 1.2), ("Email", 5, 2.9)]:
    ws2.append(row)
ws3 = wb.create_sheet("Notes")
ws3.append(["Campaign: 'Powering Progress' – B2B brand campaign for a fictional industrial client, Northwind Energy"])
ws3.append(["Goal: grow awareness among plant managers in DACH and Nordics; 3 waves Jan-Sep 2026"])
ws3.append(["Wave 3 introduced customer video stories; events delivered the highest engagement"])
ws3.append(["Next: Q4 plan focuses on retargeting engaged accounts and a webinar series"])
wb.save(out / "campaign_q3.xlsx")
print("wrote", out / "campaign_q3.xlsx")
