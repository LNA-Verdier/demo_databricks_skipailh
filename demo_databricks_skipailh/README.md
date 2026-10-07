# Démo Databricks — Skipailh (commerce · finance · RH)

Pack prêt à l'emploi pour présenter les principales fonctionnalités de Databricks sur une enseigne de sport fictive.

## Contenu

```
demo_databricks_skipailh/
├── SCENARIO_DEMO.md            ← déroulé minuté de la démo (à lire en premier)
├── data/                       ← jeu de données CSV (déjà généré, ~27 Mo)
├── data_generator/             ← scripts Python pour régénérer / modifier les données
├── notebooks/                  ← notebooks Databricks (format source .py, à importer)
│   ├── 00_setup.py                    Unity Catalog : catalogue, schémas, volume
│   ├── 01_ingestion_bronze.py         Batch + Auto Loader, évolution de schéma, simulation J+1
│   ├── 02_silver_delta.py             Nettoyage, qualité, quarantaine, MERGE, time travel, RESTORE
│   ├── 03_gold_kpis.py                KPI en SQL : ventes, RFM, budget vs réel, P&L, RH
│   ├── 04_ml_attrition_mlflow.py      Modèle de départ des salariés, MLflow, registre UC, scoring
│   ├── 05_ai_functions.py             IA générative en SQL sur les avis clients
│   ├── 06_gouvernance_unity_catalog.py Tags, GRANT, masquage, filtre de lignes, lineage
│   ├── 07_pipeline_declaratif.py      Lakeflow Declarative Pipelines + expectations
│   └── 99_reset_scenario_j1.py        Remise à zéro avant la démo
├── dashboard_genie/
│   ├── requetes_dashboard.sql  ← datasets du dashboard AI/BI
│   └── genie_space.md          ← configuration et questions de l'espace Genie
└── databricks.yml              ← (optionnel) job + pipeline en Asset Bundle
```

## Prérequis

- Workspace Databricks avec **Unity Catalog**, compute **Serverless** (notebooks, SQL warehouse) recommandé.
- Droit de créer un catalogue — sinon utiliser un catalogue existant via le widget `catalog` (et remplacer `skipailh_demo` dans les cellules SQL qui le citent en dur : `06`, fin de `01`, `requetes_dashboard.sql`).
- Pour `05` : AI Functions / Foundation Model APIs activées.

## Le jeu de données

Période : **01/2024 → 12/2025** (+ un fichier de ventes du 01/01/2026 pour la démo incrémentale). Données fictives, générées avec une graine fixe.

| Domaine | Fichier | Lignes | Description |
|---|---|---:|---|
| Commerce | `stores.csv` | 15 | 14 magasins (régions, format, surface) + e-commerce |
| | `products.csv` | 274 | 7 familles (running, cyclisme, montagne, nautique…), prix, coût |
| | `customers.csv` | 8 000 | Clients fidélité (niveau, âge, magasin de rattachement) |
| | `sales_tickets.csv` | 235 850 | Tickets : date/heure, magasin, client, canal, paiement |
| | `sales_lines.csv` | 412 566 | Lignes : produit, quantité, prix, remise, montant |
| | `product_reviews.csv` | 800 | Avis clients en texte libre + note |
| | `incremental/*_2026-01-01.csv` | 300 / 529 | Ventes « du lendemain », avec une colonne en plus (`loyalty_points`) |
| Finance | `budget.csv` | 360 | Budget mensuel CA et marge par magasin |
| | `expenses.csv` | 2 160 | Charges mensuelles : salaires, loyer, énergie, marketing… |
| RH | `employees.csv` | 405 | Salariés : poste, contrat, salaire, ancienneté, évaluation, départ |
| | `absences.csv` | ~2 000 | Absences par type |

**Ce qui rend les données « démontrables »** :
- saisonnalité marquée par famille (ski en hiver, nautique en été, fitness en janvier) et biais régionaux (Grenoble montagne, Biarritz/Brest nautique) ;
- pics Black Friday et soldes, croissance de ~6 %/an ;
- **anomalies volontaires** : 100 quantités négatives, 50 produits inconnus (`P9999`), 40 e-mails clients manquants ;
- départs de salariés (~25 %) corrélés à l'ancienneté, au salaire, à l'évaluation et aux heures sup → modèle ML interprétable (AUC ≈ 0,75).

Régénérer : `python data_generator/generate_data.py data && python data_generator/generate_reviews.py data` (pandas + numpy, ~1 min).

## Import des notebooks

*Workspace* → dossier de votre choix → **⋮ → Import** → sélectionner les fichiers `.py` du dossier `notebooks/` (Databricks les reconnaît comme notebooks grâce à l'en-tête `# Databricks notebook source`). Ou pousser le dossier dans un repo Git et l'ajouter en **Git folder**.
