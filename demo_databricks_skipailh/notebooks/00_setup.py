# Databricks notebook source
# MAGIC %md
# MAGIC # 🏃 Skipailh — 00 · Mise en place
# MAGIC
# MAGIC **Objectif** : créer l'espace de la démo dans **Unity Catalog** (catalogue, schémas, volume) et y déposer les fichiers bruts.
# MAGIC
# MAGIC | Couche | Schéma | Contenu |
# MAGIC |---|---|---|
# MAGIC | Landing | `landing` | Volume `raw` : fichiers CSV tels que reçus |
# MAGIC | Bronze | `bronze` | Données brutes ingérées en Delta, sans transformation |
# MAGIC | Silver | `silver` | Données nettoyées, typées, dédoublonnées |
# MAGIC | Gold | `gold` | Tables métier / KPI prêtes pour BI, Genie et ML |
# MAGIC | ML | `ml` | Features, modèles, prédictions |
# MAGIC
# MAGIC 👉 Paramétrage via les **widgets** en haut du notebook (fonctionne avec un compute *Serverless*).

# COMMAND ----------

dbutils.widgets.text("catalog", "skipailh_demo", "Catalogue")
CATALOG = dbutils.widgets.get("catalog")
print(f"Catalogue utilisé : {CATALOG}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Catalogue et schémas
# MAGIC Si vous n'avez pas le droit de créer un catalogue, mettez dans le widget un catalogue existant (ex : `main`) et commentez la 1re ligne.

# COMMAND ----------

spark.sql(f"CREATE CATALOG IF NOT EXISTS {CATALOG} COMMENT 'Démo Databricks - enseigne de sport fictive Skipailh'")
spark.sql(f"USE CATALOG {CATALOG}")

for schema, comment in [
    ("landing", "Zone de dépôt des fichiers bruts"),
    ("bronze", "Données brutes ingérées (Delta)"),
    ("silver", "Données nettoyées et conformes"),
    ("gold", "Tables métier et KPI (commerce, finance, RH)"),
    ("ml", "Features, modèles et prédictions"),
    ("pipeline", "Tables produites par le pipeline déclaratif (notebook 07)"),
]:
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {schema} COMMENT '{comment}'")

spark.sql("CREATE VOLUME IF NOT EXISTS landing.raw COMMENT 'Fichiers CSV sources Skipailh'")
display(spark.sql("SHOW SCHEMAS"))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Déposer les fichiers
# MAGIC
# MAGIC **Option A (à montrer en démo — 30 s)** : *Catalog Explorer* → `skipailh_demo` → `landing` → volume `raw` → **Upload to this volume** → glisser les dossiers `commerce`, `finance`, `rh`.
# MAGIC
# MAGIC Arborescence attendue :
# MAGIC ```
# MAGIC /Volumes/skipailh_demo/landing/raw/
# MAGIC ├── commerce/  stores, products, customers, sales_tickets, sales_lines, product_reviews (.csv)
# MAGIC ├── finance/   budget, expenses (.csv)
# MAGIC └── rh/        employees, absences (.csv)
# MAGIC ```
# MAGIC Le sous-dossier `commerce/incremental/` peut être uploadé aussi : il n'est lu qu'au moment où l'on simule l'arrivée des ventes du lendemain (notebook 01).
# MAGIC
# MAGIC **Option B** : CLI Databricks depuis votre poste
# MAGIC ```bash
# MAGIC databricks fs cp -r data/commerce dbfs:/Volumes/skipailh_demo/landing/raw/commerce
# MAGIC databricks fs cp -r data/finance  dbfs:/Volumes/skipailh_demo/landing/raw/finance
# MAGIC databricks fs cp -r data/rh       dbfs:/Volumes/skipailh_demo/landing/raw/rh
# MAGIC ```

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Préparer les dossiers « streaming »
# MAGIC Auto Loader (notebook 01) surveille un dossier par flux. On y range les fichiers de ventes historiques.

# COMMAND ----------

RAW = f"/Volumes/{CATALOG}/landing/raw"

for d in ["sales_tickets", "sales_lines", "_checkpoints"]:
    dbutils.fs.mkdirs(f"{RAW}/stream/{d}")

# Déplace les CSV de ventes historiques dans leur dossier de flux (idempotent)
existing = {f.name for f in dbutils.fs.ls(f"{RAW}/commerce")}
for name in ["sales_tickets", "sales_lines"]:
    if f"{name}.csv" in existing:
        dbutils.fs.mv(f"{RAW}/commerce/{name}.csv", f"{RAW}/stream/{name}/{name}_historique.csv")

display(dbutils.fs.ls(f"{RAW}/stream/sales_lines"))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Vérification rapide — on peut requêter un fichier sans l'avoir chargé
# MAGIC `read_files` lit directement le CSV depuis le volume, avec inférence de schéma.

# COMMAND ----------

display(spark.sql(f"SELECT * FROM read_files('{RAW}/commerce/stores.csv', format => 'csv', header => true)"))
