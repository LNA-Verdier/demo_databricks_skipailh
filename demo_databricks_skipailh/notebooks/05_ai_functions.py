# Databricks notebook source
# MAGIC %md
# MAGIC # ✨ Skipailh — 05 · IA générative directement en SQL (AI Functions)
# MAGIC
# MAGIC 800 avis clients en texte libre. Sans écrire une ligne de Python ni sortir les données de la plateforme :
# MAGIC sentiment, classification du motif d'insatisfaction, extraction d'informations, réponse rédigée par un LLM.
# MAGIC
# MAGIC > ⚠️ Prérequis : AI Functions activées sur le workspace (compute Serverless ou SQL Warehouse Pro/Serverless).
# MAGIC > Pour un workspace en Europe, l'admin peut devoir autoriser le *cross-geo processing* pour certains modèles.
# MAGIC > On se limite à quelques dizaines d'avis pour que la démo reste rapide.

# COMMAND ----------

dbutils.widgets.text("catalog", "skipailh_demo", "Catalogue")
spark.sql(f"USE CATALOG {dbutils.widgets.get('catalog')}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Sentiment + classification + extraction en une requête

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE TABLE gold.reviews_enriched
# MAGIC COMMENT 'Avis clients enrichis par IA : sentiment, motif, éléments extraits'
# MAGIC AS
# MAGIC SELECT r.review_id, r.review_date, r.rating, r.product_id, p.category, r.review_text,
# MAGIC        ai_analyze_sentiment(r.review_text)                                          AS sentiment,
# MAGIC        ai_classify(r.review_text,
# MAGIC                    ARRAY('qualité produit', 'taille', 'livraison', 'prix', 'conseil vendeur', 'autre')) AS motif,
# MAGIC        ai_extract(r.review_text, ARRAY('produit', 'défaut'))                         AS extraction
# MAGIC FROM silver.product_reviews r
# MAGIC JOIN silver.products p USING (product_id)
# MAGIC ORDER BY r.review_id
# MAGIC LIMIT 60;
# MAGIC
# MAGIC SELECT review_text, rating, sentiment, motif, extraction FROM gold.reviews_enriched;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Les motifs d'insatisfaction, par famille de produits
# MAGIC SELECT category, motif, count(*) AS nb_avis
# MAGIC FROM gold.reviews_enriched
# MAGIC WHERE sentiment = 'negative'
# MAGIC GROUP BY ALL ORDER BY nb_avis DESC

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. `ai_query` : appeler un LLM au choix pour rédiger une réponse au client
# MAGIC Les modèles disponibles sont listés dans **Serving** (Foundation Model APIs). Adapter le nom de l'endpoint si besoin.

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT review_text,
# MAGIC        ai_query(
# MAGIC          'databricks-meta-llama-3-3-70b-instruct',
# MAGIC          CONCAT('Tu es le service client de Skipailh, une enseigne de sport. ',
# MAGIC                 'Rédige en 2 phrases une réponse courtoise et concrète à cet avis client : ', review_text)
# MAGIC        ) AS proposition_reponse
# MAGIC FROM gold.reviews_enriched
# MAGIC WHERE sentiment = 'negative'
# MAGIC LIMIT 5

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Bonus : l'Assistant Databricks
# MAGIC Dans n'importe quelle cellule : icône ✨ ou `Cmd/Ctrl + I`, puis par exemple :
# MAGIC - *« Écris une requête qui donne le CA 2025 par région et par famille, trié décroissant »*
# MAGIC - *« Explique ce que fait cette cellule »* / *« Corrige l'erreur »* (bouton **Diagnose error** quand une cellule plante)
