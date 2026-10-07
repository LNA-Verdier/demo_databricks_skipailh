# Databricks notebook source
# MAGIC %md
# MAGIC # ♻️ Remise à zéro du scénario « ventes J+1 »
# MAGIC À lancer **après** la répétition et **avant** la démo : retire les ventes du 01/01/2026 des tables et du checkpoint,
# MAGIC pour pouvoir rejouer le moment Auto Loader (notebook 01, partie 3) en direct.

# COMMAND ----------

dbutils.widgets.text("catalog", "skipailh_demo", "Catalogue")
CATALOG = dbutils.widgets.get("catalog")
spark.sql(f"USE CATALOG {CATALOG}")
RAW = f"/Volumes/{CATALOG}/landing/raw"

# 1. Retirer les fichiers J+1 des dossiers surveillés
for name in ["sales_tickets", "sales_lines"]:
    dbutils.fs.rm(f"{RAW}/stream/{name}/{name}_2026-01-01.csv")

# 2. Repartir de zéro côté bronze (tables + checkpoints Auto Loader) et retirer les ventes J+1 du silver
for t in ["sales_tickets", "sales_lines"]:
    spark.sql(f"DROP TABLE IF EXISTS bronze.{t}")
dbutils.fs.rm(f"{RAW}/stream/_checkpoints", recurse=True)
dbutils.fs.mkdirs(f"{RAW}/stream/_checkpoints")
if spark.catalog.tableExists("silver.sales"):
    spark.sql("DELETE FROM silver.sales WHERE sale_date >= '2026-01-01'")

print("✅ Scénario remis à zéro. Relancer maintenant 01 (widget Simuler J+1 = non).")
