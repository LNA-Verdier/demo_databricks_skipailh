# Databricks notebook source
# MAGIC %md
# MAGIC # 🤖 Skipailh — 04 · Data Science : prédire les départs de salariés (MLflow)
# MAGIC
# MAGIC Question RH : *quels salariés risquent de partir, et pourquoi ?*
# MAGIC
# MAGIC 1. Construire une table de **features** à partir des données RH Silver
# MAGIC 2. Entraîner un modèle scikit-learn, **tracé automatiquement par MLflow** (paramètres, métriques, artefacts)
# MAGIC 3. **Enregistrer** le modèle dans Unity Catalog (versionné, gouverné, avec alias `champion`)
# MAGIC 4. **Scorer** les salariés actifs en batch avec Spark et publier le résultat pour les RH
# MAGIC
# MAGIC ✅ Fonctionne sur compute Serverless (scikit-learn et MLflow sont préinstallés).

# COMMAND ----------

dbutils.widgets.text("catalog", "skipailh_demo", "Catalogue")
CATALOG = dbutils.widgets.get("catalog")
spark.sql(f"USE CATALOG {CATALOG}")

import mlflow
from pyspark.sql import functions as F

mlflow.set_registry_uri("databricks-uc")
MODEL_NAME = f"{CATALOG}.ml.attrition_model"

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Table de features

# COMMAND ----------

absences = (spark.table("silver.absences")
            .groupBy("employee_id")
            .agg(F.sum("days").alias("absence_days"),
                 F.sum(F.when(F.col("absence_type").isin("Maladie", "Enfant malade"), F.col("days")).otherwise(0))
                  .alias("sick_days"),
                 F.count("*").alias("absence_count")))

features = (spark.table("silver.employees")
            .join(absences, "employee_id", "left")
            .fillna(0, ["absence_days", "sick_days", "absence_count"])
            .select("employee_id", "store_id", "department", "job_title", "contract_type",
                    "annual_salary_eur", "weekly_hours", "overtime_hours_last_year",
                    "last_review_score", "trainings_last_year", "tenure_years",
                    (F.lit(2025) - F.col("birth_year")).alias("age"),
                    "absence_days", "sick_days", "absence_count",
                    (~F.col("is_active")).cast("int").alias("left_company")))

features.write.mode("overwrite").option("overwriteSchema", True).saveAsTable("ml.employee_features")
spark.sql("COMMENT ON TABLE ml.employee_features IS 'Features RH par salarié pour le modèle de départ (cible : left_company)'")
display(spark.table("ml.employee_features").groupBy("left_company").count())

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Entraînement + tracking MLflow
# MAGIC `mlflow.sklearn.autolog()` enregistre tout seul les hyperparamètres, les métriques et le modèle. On compare deux algorithmes dans l'onglet **Experiments**.

# COMMAND ----------

from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.metrics import f1_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

pdf = spark.table("ml.employee_features").toPandas()
CAT = ["department", "job_title", "contract_type"]
NUM = ["annual_salary_eur", "weekly_hours", "overtime_hours_last_year", "last_review_score",
       "trainings_last_year", "tenure_years", "age", "absence_days", "sick_days", "absence_count"]
X, y = pdf[CAT + NUM], pdf["left_company"]
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, stratify=y, random_state=42)

mlflow.sklearn.autolog(log_input_examples=True, silent=True)

candidates = {
    "random_forest": RandomForestClassifier(n_estimators=300, max_depth=6, class_weight="balanced", random_state=42),
    "gradient_boosting": GradientBoostingClassifier(n_estimators=200, max_depth=3, learning_rate=0.05, random_state=42),
}
results = {}
for name, clf in candidates.items():
    with mlflow.start_run(run_name=name) as run:
        pipe = Pipeline([
            ("prep", ColumnTransformer([("cat", OneHotEncoder(handle_unknown="ignore"), CAT)], remainder="passthrough")),
            ("clf", clf),
        ])
        pipe.fit(X_train, y_train)
        proba = pipe.predict_proba(X_test)[:, 1]
        auc = roc_auc_score(y_test, proba)
        f1 = f1_score(y_test, proba > 0.5)
        mlflow.log_metrics({"test_auc": auc, "test_f1": f1})
        results[name] = (auc, run.info.run_id)
        print(f"{name:<18} AUC test = {auc:.3f} | F1 = {f1:.3f}")

best_name, (best_auc, best_run_id) = max(results.items(), key=lambda kv: kv[1][0])
print(f"\n🏆 Meilleur modèle : {best_name} (AUC {best_auc:.3f})")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Enregistrement dans Unity Catalog
# MAGIC Le modèle devient un objet du catalogue comme une table : versionné, avec droits d'accès et lineage vers ses données d'entraînement.

# COMMAND ----------

from mlflow import MlflowClient

mv = mlflow.register_model(f"runs:/{best_run_id}/model", MODEL_NAME)
client = MlflowClient()
client.set_registered_model_alias(MODEL_NAME, "champion", mv.version)
client.update_registered_model(MODEL_NAME, description="Probabilité de départ d'un salarié Skipailh (démo)")
print(f"{MODEL_NAME} v{mv.version} → alias @champion")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Qu'est-ce qui explique les départs ?

# COMMAND ----------

import pandas as pd

model = mlflow.sklearn.load_model(f"models:/{MODEL_NAME}@champion")
names = model.named_steps["prep"].get_feature_names_out()
importances = (pd.DataFrame({"feature": [n.split("__")[-1] for n in names],
                             "importance": model.named_steps["clf"].feature_importances_})
               .sort_values("importance", ascending=False).head(10))
display(importances)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Scoring batch des salariés actifs (Spark, distribué)

# COMMAND ----------

# Le modèle @champion (chargé depuis Unity Catalog) est appliqué en parallèle sur Spark via un pandas UDF.
# (mlflow.pyfunc.spark_udf fait la même chose mais renvoie la classe 0/1 ; ici on veut la probabilité.)
from pyspark.sql.functions import pandas_udf

@pandas_udf("double")
def attrition_proba(*cols: pd.Series) -> pd.Series:
    df = pd.concat(cols, axis=1)
    df.columns = CAT + NUM
    return pd.Series(model.predict_proba(df)[:, 1])

active = spark.table("ml.employee_features").filter("left_company = 0")
scored = (active
          .withColumn("attrition_probability", F.round(attrition_proba(*[F.col(c) for c in CAT + NUM]), 3))
          .withColumn("risk_level", F.when(F.col("attrition_probability") >= 0.6, "Élevé")
                                     .when(F.col("attrition_probability") >= 0.3, "Moyen").otherwise("Faible"))
          .withColumn("model_version", F.lit(mv.version))
          .withColumn("scored_at", F.current_timestamp()))

(scored.select("employee_id", "store_id", "job_title", "contract_type", "tenure_years",
               "attrition_probability", "risk_level", "model_version", "scored_at")
 .write.mode("overwrite").option("overwriteSchema", True).saveAsTable("gold.hr_attrition_risk"))
spark.sql("COMMENT ON TABLE gold.hr_attrition_risk IS 'Risque de départ prédit pour chaque salarié actif (modèle ml.attrition_model)'")

display(spark.sql("""
  SELECT s.store_name, r.risk_level, count(*) AS salaries
  FROM gold.hr_attrition_risk r JOIN silver.stores s USING (store_id)
  GROUP BY ALL ORDER BY store_name, risk_level
"""))

# COMMAND ----------

# MAGIC %md
# MAGIC ### Pour aller plus loin (à mentionner)
# MAGIC - **AutoML** : *Experiments → Create AutoML experiment* sur `ml.employee_features` → Databricks génère les notebooks d'entraînement.
# MAGIC - **Model Serving** : exposer `attrition_model@champion` en API REST temps réel en quelques clics.
# MAGIC - **Lakehouse Monitoring** : surveiller la dérive des features et des prédictions dans le temps.
