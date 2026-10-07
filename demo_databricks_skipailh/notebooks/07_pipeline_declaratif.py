# Databricks notebook source
# MAGIC %md
# MAGIC # 🔁 Skipailh — 07 · Pipeline déclaratif (Lakeflow Declarative Pipelines, ex-DLT)
# MAGIC
# MAGIC **Ce notebook ne s'exécute pas cellule par cellule** : il est le code source d'un *pipeline*.
# MAGIC On **déclare** les tables et leurs dépendances ; Databricks se charge de l'ordre d'exécution, de l'incrémental,
# MAGIC des reprises sur erreur, de l'infrastructure et des **contrôles qualité** (expectations).
# MAGIC
# MAGIC **Création** : *Jobs & Pipelines* → *Create* → *ETL pipeline* →
# MAGIC - Source code : ce notebook
# MAGIC - Default catalog : `skipailh_demo` · Default schema : `pipeline`
# MAGIC - Configuration : `source_path` = `/Volumes/skipailh_demo/landing/raw`
# MAGIC - Compute : Serverless · Mode : *Triggered*
# MAGIC
# MAGIC Puis **Start** et regarder le graphe se construire 🎬
# MAGIC
# MAGIC > Syntaxe historique `import dlt`, toujours supportée. La syntaxe la plus récente est `from pyspark import pipelines as dp`
# MAGIC > (`@dp.table`, `@dp.materialized_view`, `@dp.expect…`) : le principe est identique.

# COMMAND ----------

import dlt
from pyspark.sql import functions as F

SRC = spark.conf.get("source_path", "/Volumes/skipailh_demo/landing/raw")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Bronze — ingestion incrémentale (streaming tables + Auto Loader)

# COMMAND ----------

def autoloader(folder):
    return (spark.readStream.format("cloudFiles")
            .option("cloudFiles.format", "csv")
            .option("header", True)
            .option("cloudFiles.inferColumnTypes", True)
            .load(f"{SRC}/stream/{folder}")
            .withColumn("_source_file", F.col("_metadata.file_path")))

@dlt.table(comment="Tickets de caisse bruts")
def bronze_sales_tickets():
    return autoloader("sales_tickets")

@dlt.table(comment="Lignes de ticket brutes")
def bronze_sales_lines():
    return autoloader("sales_lines")

@dlt.table(comment="Référentiel produits")
def bronze_products():
    return spark.read.option("header", True).option("inferSchema", True).csv(f"{SRC}/commerce/products.csv")

@dlt.table(comment="Référentiel magasins")
def bronze_stores():
    return spark.read.option("header", True).option("inferSchema", True).csv(f"{SRC}/commerce/stores.csv")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Silver — règles qualité déclaratives
# MAGIC - `expect` : on garde la ligne mais on **mesure** le taux d'anomalies
# MAGIC - `expect_or_drop` : la ligne est **écartée**
# MAGIC - `expect_or_fail` : le pipeline **s'arrête**
# MAGIC
# MAGIC Les compteurs apparaissent dans l'onglet *Data quality* de chaque table du graphe.

# COMMAND ----------

@dlt.table(comment="Lignes de vente nettoyées et valorisées")
@dlt.expect("client_identifie", "customer_id IS NOT NULL")
@dlt.expect_or_drop("quantite_positive", "quantity > 0")
@dlt.expect_or_drop("produit_connu", "category IS NOT NULL")
@dlt.expect_or_fail("montant_non_nul", "revenue IS NOT NULL")
def silver_sales():
    # dlt.read (lecture batch) → vue matérialisée, recalculée de façon incrémentale par le moteur
    tickets = dlt.read("bronze_sales_tickets").select(
        "ticket_id", F.col("ticket_ts").cast("timestamp").alias("ticket_ts"),
        "store_id", "customer_id", "channel")
    lines = dlt.read("bronze_sales_lines")
    products = dlt.read("bronze_products").select("product_id", "category", "unit_cost")
    return (lines.join(tickets, "ticket_id")
            .join(products, "product_id", "left")
            .select("ticket_id", "line_number", "ticket_ts", F.to_date("ticket_ts").alias("sale_date"),
                    "store_id", "customer_id", "channel", "product_id", "category", "quantity",
                    F.col("line_amount").alias("revenue"),
                    F.round(F.col("line_amount") - F.col("quantity") * F.col("unit_cost"), 2).alias("gross_margin")))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Gold — vues matérialisées (recalcul incrémental automatique)

# COMMAND ----------

@dlt.table(comment="CA et marge par jour et par magasin")
def gold_sales_by_store_day():
    return (dlt.read("silver_sales")
            .join(dlt.read("bronze_stores").select("store_id", "store_name", "region"), "store_id")
            .groupBy("sale_date", "store_id", "store_name", "region")
            .agg(F.round(F.sum("revenue"), 2).alias("revenue_eur"),
                 F.round(F.sum("gross_margin"), 2).alias("gross_margin_eur"),
                 F.countDistinct("ticket_id").alias("nb_tickets")))

@dlt.table(comment="CA mensuel par famille de produits")
def gold_sales_by_category_month():
    return (dlt.read("silver_sales")
            .groupBy(F.date_trunc("month", "sale_date").cast("date").alias("month"), "category")
            .agg(F.round(F.sum("revenue"), 2).alias("revenue_eur")))
