# Databricks notebook source
# MAGIC %md
# MAGIC # 🥉 Skipailh — 01 · Ingestion Bronze
# MAGIC
# MAGIC Deux façons d'ingérer dans le Lakehouse :
# MAGIC 1. **Batch** pour les référentiels (magasins, produits, clients, finance, RH) — `spark.read` → table Delta.
# MAGIC 2. **Incrémental avec Auto Loader** pour les ventes — Databricks ne traite **que les nouveaux fichiers**, gère l'évolution de schéma et garantit l'*exactly-once*.
# MAGIC
# MAGIC Chaque ligne est enrichie de métadonnées techniques : fichier source et date d'ingestion (traçabilité).

# COMMAND ----------

dbutils.widgets.text("catalog", "skipailh_demo", "Catalogue")
CATALOG = dbutils.widgets.get("catalog")
spark.sql(f"USE CATALOG {CATALOG}")
RAW = f"/Volumes/{CATALOG}/landing/raw"

from pyspark.sql import functions as F

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Référentiels en batch

# COMMAND ----------

def ingest_csv(rel_path: str, table: str):
    """Lit un CSV du volume et l'écrit tel quel en table Delta bronze (+ métadonnées)."""
    df = (spark.read
          .option("header", True)
          .option("inferSchema", True)
          .csv(f"{RAW}/{rel_path}")
          .withColumn("_source_file", F.col("_metadata.file_path"))
          .withColumn("_ingested_at", F.current_timestamp()))
    df.write.mode("overwrite").option("overwriteSchema", True).saveAsTable(f"bronze.{table}")
    print(f"bronze.{table:<16} {df.count():>8,} lignes")

for rel_path, table in [
    ("commerce/stores.csv", "stores"),
    ("commerce/products.csv", "products"),
    ("commerce/customers.csv", "customers"),
    ("commerce/product_reviews.csv", "product_reviews"),
    ("finance/budget.csv", "budget"),
    ("finance/expenses.csv", "expenses"),
    ("rh/employees.csv", "employees"),
    ("rh/absences.csv", "absences"),
]:
    ingest_csv(rel_path, table)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Ventes en incrémental avec Auto Loader
# MAGIC - `cloudFiles` = Auto Loader : mémorise les fichiers déjà traités (checkpoint).
# MAGIC - `trigger(availableNow=True)` : traite tout ce qui est nouveau puis s'arrête → idéal en job planifié, compatible Serverless.
# MAGIC - `schemaEvolutionMode = addNewColumns` : une nouvelle colonne dans les fichiers est ajoutée automatiquement à la table.

# COMMAND ----------

def autoload(stream_name: str, table: str, max_retries: int = 2):
    """Ingestion incrémentale d'un dossier CSV vers une table Delta bronze."""
    for attempt in range(max_retries + 1):
        try:
            q = (spark.readStream
                 .format("cloudFiles")
                 .option("cloudFiles.format", "csv")
                 .option("header", True)
                 .option("cloudFiles.inferColumnTypes", True)
                 .option("cloudFiles.schemaLocation", f"{RAW}/stream/_checkpoints/{table}/schema")
                 .option("cloudFiles.schemaEvolutionMode", "addNewColumns")
                 .load(f"{RAW}/stream/{stream_name}")
                 .withColumn("_source_file", F.col("_metadata.file_path"))
                 .withColumn("_ingested_at", F.current_timestamp())
                 .writeStream
                 .option("checkpointLocation", f"{RAW}/stream/_checkpoints/{table}/cp")
                 .option("mergeSchema", True)
                 .trigger(availableNow=True)
                 .toTable(f"bronze.{table}"))
            q.awaitTermination()
            break
        except Exception as e:
            # Comportement normal d'Auto Loader : nouvelle colonne détectée → schéma mis à jour → on relance
            if "UNKNOWN_FIELD" in str(e) and attempt < max_retries:
                print(f"🔄 Nouvelle colonne détectée dans {stream_name}, schéma mis à jour, redémarrage…")
                continue
            raise
    print(f"bronze.{table:<16} {spark.table(f'bronze.{table}').count():>8,} lignes")

autoload("sales_tickets", "sales_tickets")
autoload("sales_lines", "sales_lines")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. 🎬 Moment démo : « les ventes du 1er janvier arrivent »
# MAGIC On dépose les fichiers du lendemain dans les dossiers surveillés, puis on **relance la cellule précédente** (ou ci-dessous).
# MAGIC
# MAGIC À faire remarquer :
# MAGIC - seules **les nouvelles lignes** sont ingérées (pas de re-lecture de l'historique) ;
# MAGIC - le fichier de lignes contient une **nouvelle colonne `loyalty_points`** → ajoutée automatiquement à la table.

# COMMAND ----------

# Garde-fou : passer le widget à "oui" pendant la démo (reste à "non" quand le notebook tourne dans un job)
dbutils.widgets.dropdown("simuler_j_plus_1", "non", ["non", "oui"], "Simuler J+1")
if dbutils.widgets.get("simuler_j_plus_1") != "oui":
    dbutils.notebook.exit("Simulation J+1 non demandée — fin du notebook")

before = {t: spark.table(f"bronze.{t}").count() for t in ["sales_tickets", "sales_lines"]}

for name in ["sales_tickets", "sales_lines"]:
    dbutils.fs.cp(f"{RAW}/commerce/incremental/{name}_2026-01-01.csv",
                  f"{RAW}/stream/{name}/{name}_2026-01-01.csv")

autoload("sales_tickets", "sales_tickets")
autoload("sales_lines", "sales_lines")

for t, n in before.items():
    print(f"{t}: {n:,} → {spark.table(f'bronze.{t}').count():,} lignes")

# COMMAND ----------

# MAGIC %md
# MAGIC La nouvelle colonne est bien là (vide pour l'historique, renseignée pour le 01/01) :

# COMMAND ----------

display(spark.table("bronze.sales_lines")
        .groupBy(F.col("loyalty_points").isNotNull().alias("a_des_points"))
        .agg(F.count("*").alias("nb_lignes"), F.min("_source_file").alias("exemple_fichier")))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Même chose en SQL
# MAGIC Pour les profils SQL : `read_files` + `CREATE TABLE AS`, ou `COPY INTO` (idempotent : un fichier n'est chargé qu'une fois).

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT store_id, store_name, city, region
# MAGIC FROM read_files('/Volumes/skipailh_demo/landing/raw/commerce/stores.csv', format => 'csv', header => true)
# MAGIC LIMIT 5
