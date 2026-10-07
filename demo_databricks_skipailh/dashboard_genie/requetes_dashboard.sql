-- =====================================================================
-- Skipailh — Requêtes pour le dashboard AI/BI (Dashboards → Create dashboard → onglet Data)
-- Créer un dataset par requête, puis glisser les visualisations sur le canvas.
-- Ajouter un filtre global « Région » (champ region) et un filtre « Année ».
-- =====================================================================

-- [DS1] Ventes quotidiennes  → compteurs + courbe + barres
--   Compteur « CA »         : SUM(revenue_eur)
--   Compteur « Marge %»     : SUM(gross_margin_eur) / SUM(revenue_eur)
--   Compteur « Tickets »    : SUM(nb_tickets)
--   Courbe  « CA mensuel »  : X = sale_date (mois), Y = SUM(revenue_eur), couleur = channel
--   Barres  « CA par famille » : X = category, Y = SUM(revenue_eur)
SELECT sale_date, year(sale_date) AS annee, store_name, region, channel, category,
       revenue_eur, gross_margin_eur, nb_tickets, nb_items
FROM skipailh_demo.gold.sales_daily;

-- [DS2] Budget vs réalisé  → barres groupées + tableau avec mise en forme conditionnelle
SELECT month, year(month) AS annee, store_name, region,
       revenue_actual_eur, revenue_budget_eur, revenue_gap_eur, revenue_gap_pct
FROM skipailh_demo.gold.finance_budget_vs_actual;

-- [DS3] P&L magasins 2025  → barres horizontales EBITDA % par magasin
SELECT store_name, region,
       sum(revenue_eur) AS revenue_eur,
       sum(ebitda_eur) AS ebitda_eur,
       sum(ebitda_eur) / sum(revenue_eur) AS ebitda_margin_pct
FROM skipailh_demo.gold.finance_store_pnl
WHERE year(month) = 2025
GROUP BY ALL;

-- [DS4] RH  → nuage de points turnover vs CA/salarié, taille = effectif
SELECT store_name, region, headcount_active, turnover_rate_2025,
       absenteeism_rate_2025, revenue_per_employee_eur
FROM skipailh_demo.gold.hr_store_kpis;

-- [DS5] Risque de départ (issu du modèle ML)  → barres empilées par magasin
SELECT s.store_name, s.region, r.risk_level, count(*) AS salaries
FROM skipailh_demo.gold.hr_attrition_risk r
JOIN skipailh_demo.silver.stores s USING (store_id)
GROUP BY ALL;

-- [DS6] Segments clients  → camembert / barres
SELECT segment, loyalty_tier, count(*) AS clients, round(avg(monetary_eur)) AS ca_moyen_client
FROM skipailh_demo.gold.customer_segments
GROUP BY ALL;
