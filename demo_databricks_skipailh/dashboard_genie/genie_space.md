# Espace Genie « Skipailh — Pilotage magasins »

Genie permet à un utilisateur métier de poser ses questions **en français** sur les tables Gold ; il génère le SQL, l'exécute et affiche le résultat (tableau ou graphique). Les droits Unity Catalog s'appliquent.

## Création (2 min, à préparer avant la démo)

*Genie* → *New* →

- **Tables** : `skipailh_demo.gold.sales_daily`, `gold.finance_budget_vs_actual`, `gold.finance_store_pnl`, `gold.hr_store_kpis`, `gold.customer_segments`, `gold.hr_attrition_risk`
- **SQL warehouse** : un warehouse Serverless
- **Instructions générales** (à coller) :

```
Tu réponds aux questions des équipes de Skipailh, enseigne de magasins de sport.
- Les montants sont en euros. Arrondis à l'euro et affiche les grands montants en k€ ou M€.
- "CA" = chiffre d'affaires = revenue_eur. "Marge" = gross_margin_eur.
- Le magasin S15 "Skipailh E-commerce" est le site web ; "magasins physiques" = tous les autres.
- Sauf précision, "cette année" = 2025 et "l'an dernier" = 2024.
- Turnover = turnover_rate_2025, absentéisme = absenteeism_rate_2025 (exprime-les en %).
```

- **Exemples de requêtes SQL** (onglet *SQL Queries*, facultatif) : reprendre DS1 et DS3 de `requetes_dashboard.sql` avec un titre en français.

## Questions à poser pendant la démo (de la plus simple à la plus « wow »)

1. Quel est le CA 2025 par région ?
2. Quels sont les 3 magasins qui ont le plus dépassé leur budget en 2025 ?
3. Montre l'évolution mensuelle du CA des sports nautiques et de la montagne sur 2 ans
4. Quel magasin a le meilleur taux d'EBITDA, et comment se compare-t-il au web ?
5. Y a-t-il un lien entre le turnover et le CA par salarié ? *(Genie propose un nuage de points)*
6. Combien de salariés à risque de départ élevé à Rennes, et quels postes ?
7. Question piège : *Quel est le salaire moyen des vendeurs ?* → Genie n'a pas la table (et le salaire est masqué) : il le dit au lieu d'inventer.

Astuce : cliquer sur **Show code** pour montrer le SQL généré, et sur 👍/👎 pour montrer qu'on peut améliorer l'espace avec les retours.
