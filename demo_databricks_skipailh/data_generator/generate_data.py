"""
Générateur du jeu de données fictif « Skipailh » (enseigne de sport type Decathlon).

Domaines :
  - Commerce : magasins, produits, clients, ventes (tickets + lignes)
  - Finance  : budget mensuel par magasin, dépenses opérationnelles
  - RH       : employés, absences

Usage : python generate_data.py [dossier_sortie]
Dépendances : pandas, numpy (pas de librairie externe).
Le jeu est déterministe (seed fixe) pour que la démo soit reproductible.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

rng = np.random.default_rng(42)
OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "data")
OUT.mkdir(parents=True, exist_ok=True)

START, END = pd.Timestamp("2024-01-01"), pd.Timestamp("2025-12-31")

# --------------------------------------------------------------------------
# Magasins
# --------------------------------------------------------------------------
stores = pd.DataFrame([
    ("S01", "Skipailh Paris La Défense", "Paris", "Île-de-France", "Grand", 4200, "2012-03-15"),
    ("S02", "Skipailh Paris Bercy", "Paris", "Île-de-France", "Moyen", 2500, "2016-09-01"),
    ("S03", "Skipailh Lyon Part-Dieu", "Lyon", "Auvergne-Rhône-Alpes", "Grand", 3800, "2013-05-20"),
    ("S04", "Skipailh Grenoble", "Grenoble", "Auvergne-Rhône-Alpes", "Moyen", 2800, "2015-11-10"),
    ("S05", "Skipailh Marseille Prado", "Marseille", "Provence-Alpes-Côte d'Azur", "Grand", 3900, "2014-02-01"),
    ("S06", "Skipailh Nice", "Nice", "Provence-Alpes-Côte d'Azur", "Moyen", 2300, "2018-06-12"),
    ("S07", "Skipailh Bordeaux Lac", "Bordeaux", "Nouvelle-Aquitaine", "Grand", 3600, "2013-10-05"),
    ("S08", "Skipailh Biarritz", "Biarritz", "Nouvelle-Aquitaine", "Petit", 1500, "2020-04-18"),
    ("S09", "Skipailh Lille", "Lille", "Hauts-de-France", "Grand", 3700, "2011-08-22"),
    ("S10", "Skipailh Rennes", "Rennes", "Bretagne", "Moyen", 2700, "2017-03-30"),
    ("S11", "Skipailh Brest", "Brest", "Bretagne", "Petit", 1400, "2021-09-15"),
    ("S12", "Skipailh Nantes", "Nantes", "Pays de la Loire", "Moyen", 2900, "2016-01-25"),
    ("S13", "Skipailh Toulouse", "Toulouse", "Occitanie", "Grand", 3500, "2014-07-07"),
    ("S14", "Skipailh Strasbourg", "Strasbourg", "Grand Est", "Moyen", 2600, "2019-02-14"),
    ("S15", "Skipailh E-commerce", "Web", "National", "Web", 0, "2015-01-01"),
], columns=["store_id", "store_name", "city", "region", "store_format", "surface_m2", "opening_date"])
# Poids de trafic par magasin (le web pèse lourd)
store_weight = dict(zip(stores.store_id,
    [1.6, 1.0, 1.4, 1.0, 1.4, 0.9, 1.3, 0.6, 1.3, 1.0, 0.5, 1.0, 1.2, 0.9, 2.2]))
# Biais sport par région (montagne, mer…)
region_bias = {"Grenoble": {"Montagne": 2.5}, "Lyon": {"Montagne": 1.5},
               "Biarritz": {"Sports nautiques": 2.5}, "Nice": {"Sports nautiques": 1.8},
               "Marseille": {"Sports nautiques": 1.6}, "Brest": {"Sports nautiques": 2.0},
               "Rennes": {"Running": 1.3}}

# --------------------------------------------------------------------------
# Produits
# --------------------------------------------------------------------------
catalog = {
    "Running":          (["Chaussures running", "T-shirt respirant", "Short running", "Montre GPS", "Gourde"],
                         [(60, 160), (10, 30), (12, 35), (80, 350), (5, 20)]),
    "Cyclisme":         (["Vélo route", "VTT", "Casque vélo", "Cuissard", "Antivol"],
                         [(400, 1800), (300, 1500), (25, 90), (20, 70), (15, 60)]),
    "Montagne":         (["Chaussures randonnée", "Sac à dos 30L", "Veste imperméable", "Bâtons de marche", "Ski alpin"],
                         [(50, 180), (30, 110), (40, 200), (15, 50), (200, 600)]),
    "Sports nautiques": (["Combinaison néoprène", "Planche de surf", "Masque tuba", "Maillot de bain", "Paddle gonflable"],
                         [(60, 250), (150, 600), (10, 40), (10, 40), (200, 550)]),
    "Sports collectifs":(["Ballon football", "Chaussures foot", "Ballon basket", "Maillot équipe", "Protège-tibias"],
                         [(10, 40), (40, 150), (15, 45), (20, 70), (8, 25)]),
    "Fitness":          (["Tapis de yoga", "Haltères", "Vélo d'appartement", "Élastiques", "Brassière sport"],
                         [(15, 60), (20, 120), (200, 700), (8, 30), (15, 45)]),
    "Raquettes":        (["Raquette tennis", "Balles tennis", "Raquette padel", "Raquette badminton", "Sac raquette"],
                         [(40, 220), (5, 15), (50, 250), (15, 80), (25, 80)]),
}
brands = ["Kipsta", "Kalenji", "Btwin", "Quechua", "Tribord", "Domyos", "Artengo", "Wedze", "Nike", "Adidas", "Asics", "Garmin"]
# Saisonnalité mensuelle par famille (index 1..12)
seasonality = {
    "Running":          [1.2, 1.0, 1.1, 1.2, 1.1, 1.0, 0.8, 0.8, 1.2, 1.1, 1.0, 1.3],
    "Cyclisme":         [0.6, 0.7, 1.0, 1.3, 1.5, 1.5, 1.3, 1.1, 1.0, 0.8, 0.7, 1.0],
    "Montagne":         [1.8, 1.6, 1.0, 0.8, 0.9, 1.0, 1.1, 1.0, 0.8, 0.9, 1.3, 1.9],
    "Sports nautiques": [0.3, 0.3, 0.5, 0.8, 1.3, 2.0, 2.4, 2.1, 0.9, 0.5, 0.3, 0.6],
    "Sports collectifs":[0.8, 0.8, 0.9, 0.9, 1.0, 1.1, 0.9, 1.5, 1.6, 1.0, 0.9, 1.1],
    "Fitness":          [2.0, 1.4, 1.1, 0.9, 0.9, 0.8, 0.7, 0.7, 1.2, 1.0, 1.0, 1.3],
    "Raquettes":        [0.7, 0.7, 0.9, 1.2, 1.4, 1.4, 1.2, 1.0, 1.1, 0.9, 0.8, 0.9],
}
rows = []
pid = 1
for cat, (subs, prices) in catalog.items():
    for sub, (pmin, pmax) in zip(subs, prices):
        for _ in range(rng.integers(6, 11)):
            brand = rng.choice(brands)
            price = round(float(rng.uniform(pmin, pmax)), 2)
            price = np.floor(price) + 0.99
            margin_rate = rng.uniform(0.35, 0.60) if brand not in ("Nike", "Adidas", "Asics", "Garmin") else rng.uniform(0.20, 0.35)
            rows.append({
                "product_id": f"P{pid:04d}",
                "product_name": f"{sub} {brand} {rng.choice(['100', '300', '500', '700', '900', 'Pro', 'Evo'])}",
                "category": cat,
                "sub_category": sub,
                "brand": brand,
                "unit_price": price,
                "unit_cost": round(price * (1 - margin_rate), 2),
                "launch_date": (START - pd.Timedelta(days=int(rng.integers(0, 1500)))).date(),
            })
            pid += 1
products = pd.DataFrame(rows)

# --------------------------------------------------------------------------
# Clients (programme de fidélité)
# --------------------------------------------------------------------------
first_names = ["Camille", "Léa", "Manon", "Chloé", "Emma", "Inès", "Sarah", "Julie", "Lucas", "Hugo", "Louis", "Nathan",
               "Thomas", "Théo", "Maxime", "Antoine", "Paul", "Jules", "Arthur", "Clara", "Alice", "Zoé", "Yanis", "Adam"]
last_names = ["Martin", "Bernard", "Dubois", "Thomas", "Robert", "Richard", "Petit", "Durand", "Leroy", "Moreau",
              "Simon", "Laurent", "Lefebvre", "Michel", "Garcia", "David", "Bertrand", "Roux", "Vincent", "Fournier",
              "Morel", "Girard", "André", "Le Gall", "Kerboul", "Mercier"]
N_CUST = 8000
home_store = rng.choice(stores.store_id[:-1], size=N_CUST, p=np.array([store_weight[s] for s in stores.store_id[:-1]]) / sum(store_weight[s] for s in stores.store_id[:-1]))
fn = rng.choice(first_names, N_CUST)
ln = rng.choice(last_names, N_CUST)
customers = pd.DataFrame({
    "customer_id": [f"C{i:05d}" for i in range(1, N_CUST + 1)],
    "first_name": fn,
    "last_name": ln,
    "email": [f"{f.lower()}.{l.lower().replace(' ', '')}{i}@example.com".replace("é", "e").replace("ï", "i")
              for i, (f, l) in enumerate(zip(fn, ln), 1)],
    "gender": rng.choice(["F", "M", "NC"], N_CUST, p=[0.48, 0.48, 0.04]),
    "birth_year": rng.integers(1955, 2008, N_CUST),
    "home_store_id": home_store,
    "loyalty_tier": rng.choice(["Bronze", "Argent", "Or"], N_CUST, p=[0.6, 0.3, 0.1]),
    "signup_date": [(START - pd.Timedelta(days=int(d))).date() for d in rng.integers(-600, 2500, N_CUST)],
    "optin_marketing": rng.choice([True, False], N_CUST, p=[0.55, 0.45]),
})
customers.loc[customers.signup_date > END.date(), "signup_date"] = END.date()
# Quelques anomalies volontaires pour la démo qualité
customers.loc[rng.choice(N_CUST, 40, replace=False), "email"] = None

# --------------------------------------------------------------------------
# Ventes : tickets + lignes
# --------------------------------------------------------------------------
days = pd.date_range(START, END, freq="D")
dow_factor = {0: 0.8, 1: 0.8, 2: 0.95, 3: 0.9, 4: 1.05, 5: 1.6, 6: 0.5}  # dimanche quasi fermé
cat_list = list(catalog.keys())
prod_by_cat = {c: products[products.category == c] for c in cat_list}

tickets, lines = [], []
tid = 1
for d in days:
    month = d.month
    growth = 1 + 0.06 * ((d - START).days / 365)   # +6 %/an
    promo = 1.4 if (d.month == 11 and d.day >= 24) or (d.month == 1 and 8 <= d.day <= 28) else 1.0  # Black Friday / soldes
    for _, s in stores.iterrows():
        sid = s.store_id
        dow = 1.0 if sid == "S15" else dow_factor[d.dayofweek]
        lam = 18 * store_weight[sid] * dow * growth * promo
        n_tickets = rng.poisson(lam)
        bias = region_bias.get(s.city, {})
        w = np.array([np.mean(seasonality[c]) * 0 + seasonality[c][month - 1] * bias.get(c, 1.0) for c in cat_list])
        w = w / w.sum()
        for _ in range(n_tickets):
            is_loyal = rng.random() < 0.65
            cust = rng.choice(customers.customer_id) if is_loyal else None
            ticket_id = f"T{tid:08d}"
            ts = d + pd.Timedelta(minutes=int(rng.integers(9 * 60, 20 * 60)))
            channel = "Web" if sid == "S15" else "Magasin"
            pay = rng.choice(["CB", "Espèces", "Carte cadeau", "Paypal"] if channel == "Web" else ["CB", "Espèces", "Carte cadeau"],
                             p=[0.7, 0.05, 0.05, 0.2] if channel == "Web" else [0.82, 0.12, 0.06])
            tickets.append((ticket_id, ts, sid, cust, channel, pay))
            for li in range(1, rng.choice([1, 2, 3, 4], p=[0.5, 0.3, 0.15, 0.05]) + 1):
                cat = rng.choice(cat_list, p=w)
                prod = prod_by_cat[cat].iloc[rng.integers(len(prod_by_cat[cat]))]
                qty = int(rng.choice([1, 1, 1, 2, 3])) if prod.unit_price < 50 else 1
                disc = 0.0
                if promo > 1:
                    disc = float(rng.choice([0, 0.1, 0.2, 0.3], p=[0.4, 0.3, 0.2, 0.1]))
                elif rng.random() < 0.08:
                    disc = 0.1
                lines.append((ticket_id, li, prod.product_id, qty, prod.unit_price, disc))
            tid += 1

sales_tickets = pd.DataFrame(tickets, columns=["ticket_id", "ticket_ts", "store_id", "customer_id", "channel", "payment_method"])
sales_lines = pd.DataFrame(lines, columns=["ticket_id", "line_number", "product_id", "quantity", "unit_price", "discount_rate"])
sales_lines["line_amount"] = (sales_lines.quantity * sales_lines.unit_price * (1 - sales_lines.discount_rate)).round(2)

# Anomalies volontaires : quantités négatives (retours mal saisis) et produits inconnus
bad = rng.choice(len(sales_lines), 150, replace=False)
sales_lines.loc[bad[:100], "quantity"] = -1
sales_lines.loc[bad[100:], "product_id"] = "P9999"

# Fichier "J+1" pour démontrer l'ingestion incrémentale (Auto Loader / MERGE)
inc_day = END + pd.Timedelta(days=1)
inc_t = sales_tickets.sample(300, random_state=1).copy()
inc_t["ticket_id"] = [f"T9{i:07d}" for i in range(len(inc_t))]
inc_t["ticket_ts"] = [inc_day + pd.Timedelta(minutes=int(m)) for m in rng.integers(540, 1200, len(inc_t))]
id_map = dict(zip(sales_tickets.loc[inc_t.index, "ticket_id"], inc_t.ticket_id))
inc_l = sales_lines[sales_lines.ticket_id.isin(id_map)].copy()
inc_l["ticket_id"] = inc_l.ticket_id.map(id_map)
inc_l["loyalty_points"] = (inc_l.line_amount // 10).astype(int)   # nouvelle colonne → schema evolution

# --------------------------------------------------------------------------
# RH : employés + absences
# --------------------------------------------------------------------------
jobs = [("Vendeur sport", "Magasin", 24000, 30000, 0.55),
        ("Hôte de caisse", "Magasin", 22000, 26000, 0.15),
        ("Responsable de rayon", "Magasin", 30000, 40000, 0.15),
        ("Logisticien", "Logistique", 23000, 29000, 0.10),
        ("Directeur de magasin", "Direction", 50000, 75000, 0.05)]
emp = []
eid = 1
for _, s in stores.iterrows():
    n = int(round(25 * store_weight[s.store_id])) if s.store_id != "S15" else 30
    for j in range(n):
        if s.store_id == "S15":
            job = rng.choice(["Data analyst", "Développeur web", "Chef de produit digital", "Logisticien"])
            dept, smin, smax = ("Digital", 38000, 60000) if job != "Logisticien" else ("Logistique", 23000, 29000)
        elif j == 0:
            job, dept, smin, smax, _ = jobs[4]
        else:
            k = rng.choice(4, p=np.array([0.55, 0.15, 0.15, 0.10]) / 0.95)
            job, dept, smin, smax, _ = jobs[k]
        hire = START - pd.Timedelta(days=int(rng.integers(-500, 4500)))
        contract = rng.choice(["CDI", "CDD", "Alternance"], p=[0.75, 0.17, 0.08])
        tenure_y = max((END - hire).days / 365, 0)
        salary = round(rng.uniform(smin, smax) * (1 + 0.015 * min(tenure_y, 15)), -2)
        satisfaction = int(np.clip(rng.normal(3.4, 0.9), 1, 5))
        overtime = int(np.clip(rng.normal(20, 15), 0, 90))
        # Probabilité de départ dépendante de facteurs explicatifs (pour le modèle ML)
        logit = (-0.8 - 0.6 * (satisfaction - 3) + 0.025 * (overtime - 20) - 0.12 * min(tenure_y, 10)
                 + (0.8 if contract == "CDD" else 0) + (0.5 if salary < 26000 else 0))
        left = rng.random() < 1 / (1 + np.exp(-logit))
        term = None
        if left:
            term = hire + pd.Timedelta(days=int(rng.integers(90, max(int((END - hire).days), 120))))
            term = min(term, END)
            if term < START:
                term = START + pd.Timedelta(days=int(rng.integers(0, 600)))
        emp.append({
            "employee_id": f"E{eid:04d}",
            "first_name": rng.choice(first_names),
            "last_name": rng.choice(last_names),
            "gender": rng.choice(["F", "M"]),
            "birth_year": int(rng.integers(1965, 2005)),
            "store_id": s.store_id,
            "department": dept,
            "job_title": job,
            "contract_type": contract,
            "hire_date": hire.date(),
            "termination_date": term.date() if term is not None else None,
            "annual_salary_eur": salary,
            "weekly_hours": 35 if contract != "Alternance" else 28,
            "overtime_hours_last_year": overtime,
            "last_review_score": satisfaction,
            "trainings_last_year": int(rng.poisson(2)),
        })
        eid += 1
employees = pd.DataFrame(emp)

abs_rows = []
for _, e in employees.iterrows():
    for _ in range(rng.poisson(3 + (5 - e.last_review_score))):
        st = START + pd.Timedelta(days=int(rng.integers(0, 720)))
        dur = int(rng.choice([1, 1, 2, 3, 5, 10]))
        abs_rows.append((e.employee_id, st.date(), (st + pd.Timedelta(days=dur - 1)).date(), dur,
                         rng.choice(["Maladie", "Congé payé", "RTT", "Formation", "Enfant malade"],
                                    p=[0.3, 0.35, 0.15, 0.1, 0.1])))
absences = pd.DataFrame(abs_rows, columns=["employee_id", "start_date", "end_date", "days", "absence_type"])

# --------------------------------------------------------------------------
# Finance : budget mensuel + dépenses
# --------------------------------------------------------------------------
tk = sales_tickets[["ticket_id", "store_id", "ticket_ts"]].merge(sales_lines[sales_lines.quantity > 0], on="ticket_id")
tk["month"] = tk.ticket_ts.dt.to_period("M").dt.to_timestamp()
actual = tk.groupby(["store_id", "month"]).line_amount.sum().reset_index()
budget = actual.copy()
budget["revenue_budget_eur"] = (budget.line_amount * rng.uniform(0.92, 1.10, len(budget))).round(-2)
budget["margin_budget_eur"] = (budget.revenue_budget_eur * rng.uniform(0.36, 0.42, len(budget))).round(-2)
budget = budget.drop(columns="line_amount").rename(columns={"month": "budget_month"})
budget["budget_month"] = budget.budget_month.dt.date

exp_rows = []
months = pd.date_range(START, END, freq="MS")
for _, s in stores.iterrows():
    staff_cost = employees[employees.store_id == s.store_id].annual_salary_eur.sum() * 1.45 / 12
    for m in months:
        base = [("Masse salariale", staff_cost),
                ("Loyer", s.surface_m2 * 18 if s.store_id != "S15" else 25000),
                ("Énergie", (s.surface_m2 * 2.2 if s.store_id != "S15" else 3000) * (1.4 if m.month in (1, 2, 12) else 1)),
                ("Marketing", rng.uniform(3000, 12000) * (2 if m.month in (11, 1) else 1)),
                ("Maintenance", rng.uniform(800, 4000)),
                ("Transport & logistique", rng.uniform(4000, 15000) * (1.8 if s.store_id == "S15" else 1))]
        for cat, amt in base:
            exp_rows.append((f"X{len(exp_rows)+1:06d}", s.store_id, m.date(), cat,
                             round(amt * rng.uniform(0.95, 1.05), 2),
                             rng.choice(["Fournisseur A", "Fournisseur B", "Fournisseur C", "Interne"])))
expenses = pd.DataFrame(exp_rows, columns=["expense_id", "store_id", "expense_month", "expense_category", "amount_eur", "supplier"])

# --------------------------------------------------------------------------
# Écriture
# --------------------------------------------------------------------------
files = {
    "commerce/stores.csv": stores, "commerce/products.csv": products, "commerce/customers.csv": customers,
    "commerce/sales_tickets.csv": sales_tickets, "commerce/sales_lines.csv": sales_lines,
    "commerce/incremental/sales_tickets_2026-01-01.csv": inc_t,
    "commerce/incremental/sales_lines_2026-01-01.csv": inc_l,
    "finance/budget.csv": budget, "finance/expenses.csv": expenses,
    "rh/employees.csv": employees, "rh/absences.csv": absences,
}
for name, df in files.items():
    p = OUT / name
    p.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(p, index=False)
    print(f"{name:55s} {len(df):>9,d} lignes")
