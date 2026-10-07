# Databricks notebook source
# MAGIC %md
# MAGIC # 🔐 Skipailh — 06 · Gouvernance avec Unity Catalog
# MAGIC
# MAGIC Un seul endroit pour : **droits d'accès**, **masquage de colonnes**, **filtrage de lignes**, **tags / classification**, **lineage** et **audit**.
# MAGIC Ces règles s'appliquent partout : notebooks, SQL, dashboards, Genie, Power BI…
# MAGIC
# MAGIC > Les groupes `rh_admins` et `direction` n'ont pas besoin d'exister pour la démo : l'intérêt est justement de montrer que **vous** ne voyez plus les salaires.

# COMMAND ----------

dbutils.widgets.text("catalog", "skipailh_demo", "Catalogue")
spark.sql(f"USE CATALOG {dbutils.widgets.get('catalog')}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Documenter et classifier : commentaires et tags
# MAGIC Visible dans *Catalog Explorer* et exploité par la recherche, Genie et l'Assistant.

# COMMAND ----------

# MAGIC %sql
# MAGIC ALTER TABLE silver.employees SET TAGS ('domaine' = 'RH', 'sensibilite' = 'confidentiel');
# MAGIC ALTER TABLE silver.employees ALTER COLUMN annual_salary_eur SET TAGS ('donnee_personnelle' = 'salaire');
# MAGIC ALTER TABLE silver.customers ALTER COLUMN email SET TAGS ('donnee_personnelle' = 'email');
# MAGIC ALTER TABLE gold.finance_store_pnl SET TAGS ('domaine' = 'Finance');
# MAGIC ALTER TABLE gold.sales_daily SET TAGS ('domaine' = 'Commerce', 'certifie' = 'oui');

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Retrouver toutes les colonnes contenant des données personnelles du catalogue
# MAGIC SELECT schema_name, table_name, column_name, tag_value
# MAGIC FROM information_schema.column_tags
# MAGIC WHERE tag_name = 'donnee_personnelle'

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Droits d'accès : un `GRANT` standard SQL
# MAGIC Exemple : tous les utilisateurs lisent la couche Gold, mais pas la Silver (données détaillées).

# COMMAND ----------

# MAGIC %sql
# MAGIC GRANT USE CATALOG ON CATALOG skipailh_demo TO `account users`;
# MAGIC GRANT USE SCHEMA, SELECT ON SCHEMA skipailh_demo.gold TO `account users`;
# MAGIC SHOW GRANTS ON SCHEMA skipailh_demo.gold;

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Masquage de colonne : les salaires ne sont visibles que par les RH

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE FUNCTION silver.mask_salary(salary DOUBLE)
# MAGIC RETURNS DOUBLE
# MAGIC COMMENT 'Salaire visible uniquement par le groupe rh_admins'
# MAGIC RETURN CASE WHEN is_account_group_member('rh_admins') THEN salary ELSE NULL END;
# MAGIC
# MAGIC ALTER TABLE silver.employees ALTER COLUMN annual_salary_eur SET MASK silver.mask_salary;
# MAGIC
# MAGIC -- Même le propriétaire de la table voit maintenant NULL 👇
# MAGIC SELECT employee_id, first_name, job_title, store_id, annual_salary_eur FROM silver.employees LIMIT 10;

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Filtrage de lignes : un directeur régional ne voit que sa région

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE FUNCTION gold.filter_region(region STRING)
# MAGIC RETURNS BOOLEAN
# MAGIC COMMENT 'La direction voit tout, les autres uniquement la Bretagne (exemple)'
# MAGIC RETURN is_account_group_member('direction') OR region = 'Bretagne';
# MAGIC
# MAGIC ALTER TABLE gold.finance_budget_vs_actual SET ROW FILTER gold.filter_region ON (region);
# MAGIC
# MAGIC SELECT region, count(*) AS nb_lignes FROM gold.finance_budget_vs_actual GROUP BY region;

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Lineage
# MAGIC 👉 *Catalog Explorer* → `gold.finance_store_pnl` → onglet **Lineage** → **See lineage graph** : on remonte jusqu'aux CSV du volume, colonne par colonne.
# MAGIC
# MAGIC Le même graphe est requêtable via les *system tables* (si elles sont activées sur le workspace) :

# COMMAND ----------

try:
    display(spark.sql(f"""
        SELECT DISTINCT source_table_full_name, target_table_full_name
        FROM system.access.table_lineage
        WHERE target_table_catalog = '{dbutils.widgets.get('catalog')}'
          AND source_table_full_name IS NOT NULL
        ORDER BY target_table_full_name
    """))
except Exception as e:
    print("System tables non disponibles sur ce workspace :", str(e)[:150])

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. Audit & coûts (system tables, optionnel)

# COMMAND ----------

try:
    display(spark.sql("""
        SELECT usage_date, billing_origin_product, round(sum(usage_quantity), 1) AS dbus
        FROM system.billing.usage
        WHERE usage_date >= current_date() - INTERVAL 30 DAYS
        GROUP BY ALL ORDER BY usage_date
    """))
except Exception as e:
    print("system.billing non accessible :", str(e)[:150])

# COMMAND ----------

# MAGIC %md
# MAGIC ## 🧹 Nettoyage (à lancer après la démo : sinon le dashboard, Genie et le scoring ML voient des données filtrées/masquées)

# COMMAND ----------

# MAGIC %sql
# MAGIC ALTER TABLE gold.finance_budget_vs_actual DROP ROW FILTER;
# MAGIC ALTER TABLE silver.employees ALTER COLUMN annual_salary_eur DROP MASK;
