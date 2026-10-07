"""
Génère des avis clients en texte libre (français) pour démontrer les AI Functions
de Databricks (ai_analyze_sentiment, ai_classify, ai_extract, ai_query…).

Usage : python generate_reviews.py [dossier_data]   (à lancer après generate_data.py)
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

rng = np.random.default_rng(7)
DATA = Path(sys.argv[1] if len(sys.argv) > 1 else "data")
products = pd.read_csv(DATA / "commerce/products.csv")
customers = pd.read_csv(DATA / "commerce/customers.csv")

positive = [
    "Très satisfait de {p}, excellent rapport qualité prix. Je recommande !",
    "{p} au top, confortable dès la première utilisation.",
    "Super produit, livré rapidement. Le vendeur en magasin m'a très bien conseillé.",
    "J'utilise {p} depuis trois mois, aucun souci, solide et léger.",
    "Parfait pour débuter, {p} fait exactement ce qu'on attend.",
]
negative = [
    "Déçu par {p} : la couture a lâché au bout de deux semaines.",
    "Livraison avec 10 jours de retard et aucun suivi, service client injoignable.",
    "{p} taille beaucoup trop petit, retour obligatoire. Dommage.",
    "Prix trop élevé pour la qualité, {p} s'est abîmé très vite.",
    "Produit reçu incomplet, il manquait des pièces. Très mauvaise expérience.",
]
neutral = [
    "{p} correct sans plus, fait le travail.",
    "Bon produit mais la notice est peu claire.",
    "Conforme à la description. Rien à signaler de particulier.",
    "{p} sympa mais la couleur est différente de la photo.",
]

rows = []
for i in range(1, 801):
    prod = products.sample(1, random_state=int(rng.integers(1e9))).iloc[0]
    kind = rng.choice(["pos", "neg", "neu"], p=[0.55, 0.25, 0.20])
    tpl = rng.choice({"pos": positive, "neg": negative, "neu": neutral}[kind])
    rating = {"pos": rng.choice([4, 5]), "neg": rng.choice([1, 2]), "neu": 3}[kind]
    rows.append({
        "review_id": f"R{i:05d}",
        "product_id": prod.product_id,
        "customer_id": customers.customer_id.iloc[int(rng.integers(len(customers)))],
        "review_date": (pd.Timestamp("2024-01-01") + pd.Timedelta(days=int(rng.integers(0, 730)))).date(),
        "rating": int(rating),
        "review_text": tpl.format(p=prod.sub_category.lower()),
    })

out = DATA / "commerce/product_reviews.csv"
pd.DataFrame(rows).to_csv(out, index=False)
print(f"{out} : {len(rows)} avis")
