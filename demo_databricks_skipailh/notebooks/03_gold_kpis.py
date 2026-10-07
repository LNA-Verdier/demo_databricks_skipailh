# Databricks notebook source
# MAGIC %md
# MAGIC # 🥇 Skipailh — 03 · Gold : KPI Commerce, Finance, RH (en SQL)
# MAGIC
# MAGIC Même notebook, autre langage : la couche Gold est écrite **100 % en SQL** — les analystes peuvent contribuer sans Python.
# MAGIC Ces tables alimentent le **dashboard AI/BI**, l'espace **Genie** et les outils BI externes (Power BI, Tableau…).

# COMMAND ----------

dbutils.widgets.text("catalog", "skipailh_demo", "Catalogue")
spark.sql(f"USE CATALOG {dbutils.widgets.get('catalog')}")
spark.sql("USE SCHEMA gold")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 🛒 Commerce

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE TABLE gold.sales_daily
# MAGIC COMMENT 'Ventes quotidiennes par magasin et famille de produits : CA, marge brute, nb tickets, articles vendus'
# MAGIC AS
# MAGIC SELECT s.sale_date,
# MAGIC        s.store_id,
# MAGIC        st.store_name,
# MAGIC        st.city,
# MAGIC        st.region,
# MAGIC        s.channel,
# MAGIC        s.category,
# MAGIC        round(sum(s.revenue), 2)        AS revenue_eur,
# MAGIC        round(sum(s.gross_margin), 2)   AS gross_margin_eur,
# MAGIC        count(DISTINCT s.ticket_id)     AS nb_tickets,
# MAGIC        sum(s.quantity)                 AS nb_items
# MAGIC FROM silver.sales s
# MAGIC JOIN silver.stores st USING (store_id)
# MAGIC GROUP BY ALL;
# MAGIC
# MAGIC ALTER TABLE gold.sales_daily ALTER COLUMN revenue_eur COMMENT 'Chiffre d''affaires TTC après remise, en euros';
# MAGIC ALTER TABLE gold.sales_daily ALTER COLUMN gross_margin_eur COMMENT 'Marge brute = CA - coût d''achat des produits, en euros';

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Top familles par saison : la saisonnalité saute aux yeux (ski l'hiver, nautique l'été)
# MAGIC SELECT date_trunc('MONTH', sale_date) AS mois, category, round(sum(revenue_eur)) AS ca
# MAGIC FROM gold.sales_daily
# MAGIC GROUP BY ALL
# MAGIC ORDER BY mois

# COMMAND ----------

# MAGIC %md
# MAGIC 💡 *Dans la cellule ci-dessus : cliquer sur **+** → **Visualisation** → courbe, X = mois, Y = ca, groupe = category.*

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE TABLE gold.customer_segments
# MAGIC COMMENT 'Segmentation RFM des clients fidélité (récence, fréquence, montant) sur 2024-2025'
# MAGIC AS
# MAGIC WITH rfm AS (
# MAGIC   SELECT customer_id,
# MAGIC          datediff(DATE'2025-12-31', max(sale_date)) AS recency_days,
# MAGIC          count(DISTINCT ticket_id)                  AS frequency,
# MAGIC          round(sum(revenue), 2)                     AS monetary_eur
# MAGIC   FROM silver.sales
# MAGIC   WHERE customer_id IS NOT NULL
# MAGIC   GROUP BY customer_id
# MAGIC ), scored AS (
# MAGIC   SELECT *,
# MAGIC          ntile(4) OVER (ORDER BY recency_days DESC) AS r_score,
# MAGIC          ntile(4) OVER (ORDER BY frequency)         AS f_score,
# MAGIC          ntile(4) OVER (ORDER BY monetary_eur)      AS m_score
# MAGIC   FROM rfm
# MAGIC )
# MAGIC SELECT s.*, c.loyalty_tier, c.age_band, c.home_store_id,
# MAGIC        CASE WHEN r_score >= 3 AND f_score >= 3 AND m_score >= 3 THEN 'Champions'
# MAGIC             WHEN r_score >= 3 AND f_score >= 2                  THEN 'Fidèles'
# MAGIC             WHEN r_score <= 1 AND f_score >= 3                  THEN 'À risque'
# MAGIC             WHEN r_score <= 1                                   THEN 'Endormis'
# MAGIC             ELSE 'Occasionnels' END AS segment
# MAGIC FROM scored s
# MAGIC JOIN silver.customers c USING (customer_id);
# MAGIC
# MAGIC SELECT segment, count(*) AS clients, round(avg(monetary_eur)) AS panier_cumule_moyen
# MAGIC FROM gold.customer_segments GROUP BY segment ORDER BY clients DESC;

# COMMAND ----------

# MAGIC %md
# MAGIC ## 💶 Finance

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE TABLE gold.finance_budget_vs_actual
# MAGIC COMMENT 'Réalisé vs budget mensuel par magasin : CA et marge, écarts en euros et en %'
# MAGIC AS
# MAGIC WITH actual AS (
# MAGIC   SELECT store_id, date_trunc('MONTH', sale_date)::date AS month,
# MAGIC          sum(revenue) AS revenue_actual, sum(gross_margin) AS margin_actual
# MAGIC   FROM silver.sales
# MAGIC   WHERE sale_date <= DATE'2025-12-31'
# MAGIC   GROUP BY ALL
# MAGIC )
# MAGIC SELECT b.budget_month AS month, b.store_id, st.store_name, st.region,
# MAGIC        round(a.revenue_actual, 0)                         AS revenue_actual_eur,
# MAGIC        b.revenue_budget_eur,
# MAGIC        round(a.revenue_actual - b.revenue_budget_eur, 0)  AS revenue_gap_eur,
# MAGIC        round(a.revenue_actual / b.revenue_budget_eur - 1, 4) AS revenue_gap_pct,
# MAGIC        round(a.margin_actual, 0)                          AS margin_actual_eur,
# MAGIC        b.margin_budget_eur,
# MAGIC        round(a.margin_actual - b.margin_budget_eur, 0)    AS margin_gap_eur
# MAGIC FROM silver.budget b
# MAGIC JOIN actual a ON a.store_id = b.store_id AND a.month = b.budget_month
# MAGIC JOIN silver.stores st ON st.store_id = b.store_id;

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE TABLE gold.finance_store_pnl
# MAGIC COMMENT 'Compte de résultat simplifié mensuel par magasin : CA, marge brute, charges par nature, EBITDA'
# MAGIC AS
# MAGIC WITH opex AS (
# MAGIC   SELECT store_id, expense_month AS month,
# MAGIC          sum(amount_eur) FILTER (WHERE expense_category = 'Masse salariale') AS staff_costs,
# MAGIC          sum(amount_eur) FILTER (WHERE expense_category = 'Loyer')           AS rent,
# MAGIC          sum(amount_eur) FILTER (WHERE expense_category = 'Énergie')         AS energy,
# MAGIC          sum(amount_eur) FILTER (WHERE expense_category = 'Marketing')       AS marketing,
# MAGIC          sum(amount_eur) FILTER (WHERE expense_category NOT IN ('Masse salariale','Loyer','Énergie','Marketing')) AS other_opex,
# MAGIC          sum(amount_eur) AS total_opex
# MAGIC   FROM silver.expenses GROUP BY ALL
# MAGIC )
# MAGIC SELECT o.month, o.store_id, st.store_name, st.region,
# MAGIC        round(b.revenue_actual_eur)  AS revenue_eur,
# MAGIC        round(b.margin_actual_eur)   AS gross_margin_eur,
# MAGIC        round(o.staff_costs) AS staff_costs_eur, round(o.rent) AS rent_eur, round(o.energy) AS energy_eur,
# MAGIC        round(o.marketing) AS marketing_eur, round(o.other_opex) AS other_opex_eur,
# MAGIC        round(b.margin_actual_eur - o.total_opex)                       AS ebitda_eur,
# MAGIC        round((b.margin_actual_eur - o.total_opex) / b.revenue_actual_eur, 4) AS ebitda_margin_pct
# MAGIC FROM opex o
# MAGIC JOIN gold.finance_budget_vs_actual b ON b.store_id = o.store_id AND b.month = o.month
# MAGIC JOIN silver.stores st ON st.store_id = o.store_id;
# MAGIC
# MAGIC SELECT store_name, round(sum(revenue_eur)/1e6, 2) AS ca_meur, round(sum(ebitda_eur)/1e6, 2) AS ebitda_meur,
# MAGIC        round(sum(ebitda_eur)/sum(revenue_eur)*100, 1) AS ebitda_pct
# MAGIC FROM gold.finance_store_pnl WHERE year(month) = 2025
# MAGIC GROUP BY store_name ORDER BY ebitda_pct DESC;

# COMMAND ----------

# MAGIC %md
# MAGIC ## 👥 RH

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE TABLE gold.hr_store_kpis
# MAGIC COMMENT 'Indicateurs RH par magasin : effectif, turnover 2025, absentéisme, ancienneté, CA par salarié'
# MAGIC AS
# MAGIC WITH emp AS (
# MAGIC   SELECT store_id,
# MAGIC          count_if(is_active)                                           AS headcount_active,
# MAGIC          count_if(year(termination_date) = 2025)                       AS departures_2025,
# MAGIC          count_if(hire_date <= DATE'2025-12-31' AND (termination_date IS NULL OR termination_date >= DATE'2025-01-01')) AS headcount_2025,
# MAGIC          round(avg(tenure_years) FILTER (WHERE is_active), 1)          AS avg_tenure_years,
# MAGIC          round(avg(last_review_score), 2)                              AS avg_review_score,
# MAGIC          round(sum(annual_salary_eur) FILTER (WHERE is_active))        AS payroll_eur
# MAGIC   FROM silver.employees GROUP BY store_id
# MAGIC ), abs AS (
# MAGIC   SELECT e.store_id,
# MAGIC          sum(a.days) FILTER (WHERE year(a.start_date) = 2025 AND a.absence_type IN ('Maladie','Enfant malade')) AS sick_days_2025
# MAGIC   FROM silver.absences a JOIN silver.employees e USING (employee_id)
# MAGIC   GROUP BY e.store_id
# MAGIC ), rev AS (
# MAGIC   SELECT store_id, sum(revenue) AS revenue_2025 FROM silver.sales WHERE year(sale_date) = 2025 GROUP BY store_id
# MAGIC )
# MAGIC SELECT st.store_id, st.store_name, st.region,
# MAGIC        e.headcount_active, e.departures_2025,
# MAGIC        round(e.departures_2025 / e.headcount_2025, 3)                 AS turnover_rate_2025,
# MAGIC        round(a.sick_days_2025 / (e.headcount_2025 * 218), 4)          AS absenteeism_rate_2025,
# MAGIC        e.avg_tenure_years, e.avg_review_score, e.payroll_eur,
# MAGIC        round(r.revenue_2025 / e.headcount_active)                     AS revenue_per_employee_eur
# MAGIC FROM emp e
# MAGIC JOIN silver.stores st USING (store_id)
# MAGIC LEFT JOIN abs a USING (store_id)
# MAGIC LEFT JOIN rev r USING (store_id);
# MAGIC
# MAGIC SELECT * FROM gold.hr_store_kpis ORDER BY turnover_rate_2025 DESC;

# COMMAND ----------

# MAGIC %md
# MAGIC ## Vue « métier » réutilisable : une seule définition du KPI pour tout le monde

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE VIEW gold.v_kpi_store_2025
# MAGIC COMMENT 'Vue de synthèse 2025 par magasin croisant commerce, finance et RH'
# MAGIC AS
# MAGIC SELECT p.store_id, p.store_name, p.region,
# MAGIC        sum(p.revenue_eur)              AS revenue_eur,
# MAGIC        sum(p.ebitda_eur)               AS ebitda_eur,
# MAGIC        sum(p.ebitda_eur)/sum(p.revenue_eur) AS ebitda_margin_pct,
# MAGIC        any_value(h.headcount_active)   AS headcount,
# MAGIC        any_value(h.turnover_rate_2025) AS turnover_rate,
# MAGIC        any_value(h.revenue_per_employee_eur) AS revenue_per_employee_eur
# MAGIC FROM gold.finance_store_pnl p
# MAGIC JOIN gold.hr_store_kpis h USING (store_id)
# MAGIC WHERE year(p.month) = 2025
# MAGIC GROUP BY ALL;
# MAGIC
# MAGIC SELECT * FROM gold.v_kpi_store_2025 ORDER BY revenue_eur DESC;
