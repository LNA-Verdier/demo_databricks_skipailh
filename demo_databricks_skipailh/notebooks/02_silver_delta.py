# Databricks notebook source
# MAGIC %md
# MAGIC # 🥈 Skipailh — 02 · Silver & fonctionnalités Delta Lake
# MAGIC
# MAGIC 1. Nettoyage / typage des référentiels (PySpark)
# MAGIC 2. Ventes : jointure tickets × lignes, **règles qualité** et **quarantaine** des lignes en erreur
# MAGIC 3. Chargement incrémental idempotent avec **MERGE**
# MAGIC 4. Les super-pouvoirs Delta : **contraintes**, **historique**, **time travel**, **RESTORE**, **liquid clustering**

# COMMAND ----------

dbutils.widgets.text("catalog", "skipailh_demo", "Catalogue")
CATALOG = dbutils.widgets.get("catalog")
spark.sql(f"USE CATALOG {CATALOG}")

from pyspark.sql import functions as F
from delta.tables import DeltaTable

def save(df, table, comment=None):
    df.write.mode("overwrite").option("overwriteSchema", True).saveAsTable(table)
    if comment:
        spark.sql(f"COMMENT ON TABLE {table} IS '{comment}'")
    print(f"{table:<28} {spark.table(table).count():>9,} lignes")

TECH = ["_source_file", "_ingested_at", "_rescued_data"]
def bronze(name):
    df = spark.table(f"bronze.{name}")
    return df.drop(*[c for c in TECH if c in df.columns])

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Référentiels

# COMMAND ----------

save(bronze("stores")
     .withColumn("opening_date", F.to_date("opening_date"))
     .withColumn("is_physical", F.col("store_format") != "Web"),
     "silver.stores", "Magasins Skipailh (14 physiques + e-commerce)")

save(bronze("products")
     .withColumn("launch_date", F.to_date("launch_date"))
     .withColumn("margin_rate", F.round(1 - F.col("unit_cost") / F.col("unit_price"), 3)),
     "silver.products", "Catalogue produits avec prix, coût et taux de marge")

save(bronze("customers")
     .withColumn("signup_date", F.to_date("signup_date"))
     .withColumn("email", F.lower(F.trim("email")))
     .withColumn("age", F.year(F.current_date()) - F.col("birth_year"))
     .withColumn("age_band", F.when(F.col("age") < 25, "18-24").when(F.col("age") < 35, "25-34")
                 .when(F.col("age") < 50, "35-49").when(F.col("age") < 65, "50-64").otherwise("65+"))
     .dropDuplicates(["customer_id"]),
     "silver.customers", "Clients du programme de fidélité")

save(bronze("employees")
     .withColumn("hire_date", F.to_date("hire_date"))
     .withColumn("termination_date", F.to_date("termination_date"))
     .withColumn("is_active", F.col("termination_date").isNull())
     .withColumn("tenure_years", F.round(F.datediff(F.coalesce("termination_date", F.lit("2025-12-31").cast("date")),
                                                    "hire_date") / 365.25, 1)),
     "silver.employees", "Salariés Skipailh (données RH sensibles : salaires)")

save(bronze("absences").withColumn("start_date", F.to_date("start_date")).withColumn("end_date", F.to_date("end_date")),
     "silver.absences", "Absences des salariés")
save(bronze("budget").withColumn("budget_month", F.to_date("budget_month")),
     "silver.budget", "Budget mensuel de CA et de marge par magasin")
save(bronze("expenses").withColumn("expense_month", F.to_date("expense_month")),
     "silver.expenses", "Dépenses opérationnelles mensuelles par magasin et catégorie")
save(bronze("product_reviews").withColumn("review_date", F.to_date("review_date")),
     "silver.product_reviews", "Avis clients en texte libre")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Ventes : qualité de données et quarantaine
# MAGIC Règles appliquées :
# MAGIC - `quantity > 0` (des retours ont été mal saisis en caisse)
# MAGIC - le produit doit exister dans le catalogue
# MAGIC
# MAGIC Les lignes KO ne sont pas perdues : elles partent dans `silver.sales_quarantine` avec le motif du rejet.

# COMMAND ----------

products = spark.table("silver.products").select("product_id", "category", "unit_cost")

sales = (bronze("sales_lines").alias("l")
         .join(bronze("sales_tickets").alias("t"), "ticket_id")
         .join(products.alias("p"), "product_id", "left")
         .select(
             "ticket_id", "line_number",
             F.col("ticket_ts").cast("timestamp").alias("ticket_ts"),
             F.to_date("ticket_ts").alias("sale_date"),
             "store_id", "customer_id", "channel", "payment_method",
             "product_id", "category", "quantity", "unit_price", "discount_rate",
             F.col("line_amount").alias("revenue"),
             F.round(F.col("line_amount") - F.col("quantity") * F.col("unit_cost"), 2).alias("gross_margin"),
         )
         .withColumn("dq_issue",
                     F.when(F.col("quantity") <= 0, "quantité négative ou nulle")
                      .when(F.col("category").isNull(), "produit inconnu")))

valid = sales.filter("dq_issue IS NULL").drop("dq_issue")
rejected = sales.filter("dq_issue IS NOT NULL").withColumn("rejected_at", F.current_timestamp())

display(rejected.groupBy("dq_issue").count())

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. MERGE : chargement idempotent
# MAGIC Premier passage : création de la table. Passages suivants : `MERGE` sur la clé (ticket, ligne) → on peut relancer autant de fois qu'on veut sans doublon, et les nouvelles ventes (J+1) s'ajoutent.

# COMMAND ----------

if not spark.catalog.tableExists("silver.sales"):
    (valid.write
     .clusterBy("sale_date", "store_id")          # Liquid clustering : remplace partitionnement + ZORDER
     .saveAsTable("silver.sales"))
    spark.sql("COMMENT ON TABLE silver.sales IS 'Lignes de vente valides (magasins + web), avec CA et marge brute'")
    spark.sql("ALTER TABLE silver.sales ADD CONSTRAINT quantite_positive CHECK (quantity > 0)")
    print("Table silver.sales créée")
else:
    (DeltaTable.forName(spark, "silver.sales").alias("t")
     .merge(valid.alias("s"), "t.ticket_id = s.ticket_id AND t.line_number = s.line_number")
     .whenMatchedUpdateAll()
     .whenNotMatchedInsertAll()
     .execute())
    print("MERGE effectué")

rejected.write.mode("overwrite").saveAsTable("silver.sales_quarantine")
print(f"silver.sales : {spark.table('silver.sales').count():,} lignes")

# Les cellules suivantes sont pédagogiques : on les saute quand le notebook tourne dans un job
dbutils.widgets.dropdown("demo_delta", "oui", ["oui", "non"], "Démo Delta")
if dbutils.widgets.get("demo_delta") != "oui":
    dbutils.notebook.exit("Silver à jour (démo Delta ignorée)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. 🎬 Les super-pouvoirs de Delta Lake
# MAGIC ### 4.1 Contrainte : la base refuse une donnée invalide

# COMMAND ----------

try:
    spark.sql("""INSERT INTO silver.sales (ticket_id, line_number, quantity, revenue)
                 VALUES ('TEST', 1, -5, 10.0)""")
except Exception as e:
    print("❌ Insertion refusée :", str(e).split("\n")[0][:200])

# COMMAND ----------

# MAGIC %md
# MAGIC ### 4.2 Une erreur de manipulation… 😱

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Oups : quelqu'un supprime toutes les ventes de Lyon
# MAGIC DELETE FROM silver.sales WHERE store_id = 'S03';
# MAGIC SELECT count(*) AS lignes_lyon FROM silver.sales WHERE store_id = 'S03';

# COMMAND ----------

# MAGIC %md
# MAGIC ### 4.3 Historique et time travel : chaque écriture crée une version

# COMMAND ----------

# MAGIC %sql
# MAGIC DESCRIBE HISTORY silver.sales

# COMMAND ----------

# Version juste avant le DELETE
last_ok = (spark.sql("DESCRIBE HISTORY silver.sales")
           .filter("operation != 'DELETE'")
           .filter(F.col("version") < spark.sql("DESCRIBE HISTORY silver.sales").filter("operation = 'DELETE'")
                   .agg(F.max("version")).first()[0])
           .agg(F.max("version")).first()[0])
print("Dernière version saine :", last_ok)

display(spark.sql(f"""
  SELECT 'avant' AS etat, count(*) AS lignes_lyon FROM silver.sales VERSION AS OF {last_ok} WHERE store_id = 'S03'
  UNION ALL
  SELECT 'maintenant', count(*) FROM silver.sales WHERE store_id = 'S03'
"""))

# COMMAND ----------

# MAGIC %md
# MAGIC ### 4.4 RESTORE : retour arrière en une commande

# COMMAND ----------

spark.sql(f"RESTORE TABLE silver.sales TO VERSION AS OF {last_ok}")
print("Lignes Lyon après restauration :", spark.table("silver.sales").filter("store_id = 'S03'").count())

# COMMAND ----------

# MAGIC %md
# MAGIC ### 4.5 Maintenance (automatique avec *Predictive Optimization*, montrée ici pour la pédagogie)

# COMMAND ----------

# MAGIC %sql
# MAGIC OPTIMIZE silver.sales;
# MAGIC DESCRIBE DETAIL silver.sales;
