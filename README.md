# RetailPro - Retail Billing & Inventory Web App
Mini-project Topic 2: Retail billing application with item-wise data processing, calculations and file storage.
Python 3.8+ standard library only (no installs, works offline). Frontend: HTML/CSS/JavaScript with hand-built SVG charts.

## Run
Windows: double-click `run.bat`   |   Any OS: `python app.py`   -> opens http://127.0.0.1:8000

## Tabs
Dashboard (KPIs, charts, recent invoices, low-stock alerts) - New Bill (point-of-sale screen) - Inventory - Invoices (view/print/void) - Reports (analytics + CSV export)

## Architecture
browser UI  <-- JSON REST API -->  app.py (http.server)  -->  retailpro/ (billing, inventory, reports, storage)  -->  data/*.json, invoices/*.txt, exports/*.csv

## Tests
python -m unittest discover -s tests
