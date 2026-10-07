# 🎬 Scénario de démo Databricks — « Skipailh »

**Durée** : 45 min (+ 15 min de questions) · **Public** : collègues data/BI/métier, niveaux mixtes
**Fil rouge** : Skipailh (« équipe » en breton), enseigne de 14 magasins de sport + un site e-commerce. Le DG veut **une seule plateforme** pour piloter le commerce, la finance et les RH — de la donnée brute jusqu'à l'IA.

> **Message clé à répéter** : *une plateforme, une copie de la donnée, une gouvernance* — ingénieurs, analystes, data scientists et métiers travaillent sur les mêmes tables.

---

## ✅ Préparation (la veille — ~30 min)

| # | Action | Où |
|---|---|---|
| 1 | Importer le dossier `notebooks/` dans votre workspace (*Workspace → Import*, ou dossier Git) | Workspace |
| 2 | Lancer `00_setup` puis uploader `data/commerce`, `data/finance`, `data/rh` dans le volume, relancer la dernière cellule de `00_setup` | Notebook + Catalog |
| 3 | Lancer **une fois** `01` → `02` → `03` → `04` → `05` en entier (pour avoir toutes les tables et le modèle) | Notebooks |
| 4 | Si vous avez joué la partie J+1 de `01` en répétition : lancer `99_reset_scenario_j1`, puis `01` (widget *Simuler J+1* = `non`) | Notebook |
| 5 | Créer le **pipeline** à partir de `07` (instructions en tête du notebook) et le lancer une fois | Jobs & Pipelines |
| 6 | Créer le **job** « Skipailh - chargement quotidien » (01 → 02 → 03 / 04) et le lancer une fois | Jobs & Pipelines |
| 7 | Construire le **dashboard** avec `dashboard_genie/requetes_dashboard.sql` et le publier | Dashboards |
| 8 | Créer l'**espace Genie** avec `dashboard_genie/genie_space.md` et tester les 7 questions | Genie |
| 9 | Ouvrir les onglets dans l'ordre de la démo, police du navigateur à 125 % | — |

💡 Le jour J, **rien ne doit attendre un calcul long** : on exécute en direct uniquement les cellules courtes (marquées ⚡ ci-dessous) ; le reste est déjà calculé, on montre le résultat.

---

## Déroulé

### 1. Introduction — le problème (3 min)
**Écran** : page d'accueil du workspace.

- Présenter Skipailh : 15 points de vente, 2 ans d'historique, ~240 000 tickets, 400 salariés.
- Aujourd'hui (fictif) : fichiers CSV éparpillés, un Excel finance, un outil RH à part, des chiffres de CA qui ne concordent jamais entre services.
- Objectif : montrer le parcours **fichier brut → tables fiables → tableaux de bord → IA**, et qui fait quoi.
- Faire le tour de la barre latérale : *Workspace, Catalog, Jobs & Pipelines, Compute, SQL Editor, Dashboards, Genie, Experiments, Models, Serving*.

### 2. Unity Catalog & ingestion des fichiers (6 min)
**Écran** : *Catalog Explorer* puis notebook `00_setup`.

- Montrer la hiérarchie **catalogue → schéma → table / volume / modèle / fonction**, et les schémas `landing / bronze / silver / gold / ml` = architecture **médaillon**.
- ⚡ Uploader un CSV par glisser-déposer dans le volume `landing.raw` → « pas besoin de ticket à l'IT pour déposer un fichier ».
- ⚡ Dernière cellule de `00_setup` : `read_files` interroge un CSV **sans l'avoir chargé**.
- **Point à souligner** : les données restent dans votre stockage cloud, au format ouvert (Delta / Parquet).

### 3. Ingestion incrémentale avec Auto Loader (6 min)
**Écran** : notebook `01_ingestion_bronze`.

- Expliquer la partie 1 (batch des référentiels) sans l'exécuter : métadonnées `_source_file`, `_ingested_at` → traçabilité.
- Partie 2 : `cloudFiles` = Auto Loader. Montrer le code, expliquer *checkpoint* et `availableNow`.
- 🎬 **Moment fort** : passer le widget **Simuler J+1** à `oui` puis ⚡ exécuter la partie 3.
  - Seules ~300 tickets / ~530 lignes nouvelles sont ingérées, pas les 400 000 de l'historique.
  - Le fichier contient une **nouvelle colonne `loyalty_points`** → Auto Loader l'ajoute à la table tout seul (message 🔄).
- Montrer la cellule SQL finale : même chose possible en SQL pour les analystes.

### 4. Silver & les super-pouvoirs de Delta Lake (8 min)
**Écran** : notebook `02_silver_delta`.

- ⚡ Exécuter la partie 2 → tableau des rejets : 100 quantités négatives, 50 produits inconnus partent en **quarantaine** (rien n'est perdu, on peut les corriger).
- ⚡ Partie 3 : **MERGE** → les ventes du 1er janvier arrivent en Silver sans doublon (relancer pour prouver l'idempotence).
- 🎬 **Séquence « catastrophe »** (la plus appréciée en général) :
  1. ⚡ 4.1 Contrainte : la table **refuse** une quantité négative.
  2. ⚡ 4.2 « Un stagiaire » supprime toutes les ventes de Lyon → 0 ligne.
  3. ⚡ 4.3 `DESCRIBE HISTORY` : qui a fait quoi, quand. *Time travel* : la donnée d'avant est toujours là.
  4. ⚡ 4.4 `RESTORE` → Lyon est revenu. « Une commande, quelques secondes, pas de restauration de backup. »
- Mentionner : liquid clustering & Predictive Optimization = plus de réglages de partitions à la main.

### 5. Gold & SQL pour les analystes (5 min)
**Écran** : notebook `03_gold_kpis`, puis **SQL Editor**.

- Le même notebook passe en **SQL** : on peut mixer Python et SQL cellule par cellule.
- ⚡ Cellule « saisonnalité » → ajouter une **visualisation** en direct (courbe par famille) : ski l'hiver, nautique l'été, Biarritz/Brest très « nautique », Grenoble très « montagne ».
- Montrer `finance_store_pnl` (P&L par magasin) et `hr_store_kpis` : commerce, finance et RH **croisés** dans `v_kpi_store_2025`.
- Ouvrir le **SQL Editor** sur un SQL Warehouse Serverless : même table, interface « type outil BI ». Démarrage du warehouse en quelques secondes.
- ⚡ Assistant : `Ctrl+I` → *« CA 2025 par région et par famille, trié décroissant »* → exécuter la requête générée.

### 6. Orchestration : Jobs & pipeline déclaratif (5 min)
**Écran** : *Jobs & Pipelines*.

- Ouvrir le **job** : graphe 01 → 02 → (03 ‖ 04), planification quotidienne 6h, alertes e-mail, reprises automatiques, paramètres (`demo_delta = non`). Montrer l'historique des exécutions et la durée de chaque tâche.
- Ouvrir le **pipeline déclaratif** (`07`) :
  - le code **déclare** les tables, Databricks déduit le graphe ;
  - cliquer sur `silver_sales` → onglet **Data quality** : lignes rejetées par règle (`quantite_positive`, `produit_connu`) ;
  - mentionner que le job et le pipeline sont versionnables « as code » (`databricks.yml`, Asset Bundles, CI/CD).

### 7. Dashboard AI/BI & Genie — la vue métier (6 min)
**Écran** : dashboard publié, puis espace Genie.

- Dashboard : compteurs CA / marge / tickets, filtre **Région** → tout se met à jour. Budget vs réalisé, EBITDA par magasin, turnover vs CA/salarié.
- Montrer le partage : lien pour des utilisateurs **sans licence de développement**, abonnement par e-mail.
- 🎬 **Genie** : poser 3–4 questions de `genie_space.md` en français ; cliquer sur **Show code** pour montrer le SQL généré.
  - Finir par la question piège sur les salaires → Genie ne l'invente pas.

### 8. Data Science & IA (5 min)
**Écran** : notebook `04_ml_attrition_mlflow`, puis *Experiments*, puis notebook `05_ai_functions`.

- Question RH : *qui risque de partir ?* Montrer l'entraînement (résultat déjà calculé) : deux algorithmes comparés.
- Onglet **Experiments** : chaque run est tracé (paramètres, métriques, modèle) — comparer les deux runs en graphique.
- Le modèle est **enregistré dans Unity Catalog** avec l'alias `@champion` → onglet *Models*. Facteurs explicatifs : ancienneté, salaire, évaluation, heures sup.
- Résultat : `gold.hr_attrition_risk` est déjà dans le dashboard / Genie (question 6) → la boucle est bouclée.
- `05_ai_functions` : ⚡ exécuter la requête des motifs d'insatisfaction ; montrer `ai_query` qui rédige une réponse au client. « Du LLM en une ligne de SQL, sur vos données, sans les envoyer ailleurs. »

### 9. Gouvernance — tout ça est sous contrôle (4 min)
**Écran** : notebook `06_gouvernance_unity_catalog`, puis *Catalog Explorer*.

- ⚡ Tags : retrouver toutes les colonnes de **données personnelles** du catalogue en une requête.
- ⚡ **Masquage** : après `SET MASK`, même le propriétaire voit `NULL` à la place des salaires.
- ⚡ **Filtre de lignes** : on ne voit plus que la Bretagne dans le budget.
- *Catalog Explorer* → `gold.finance_store_pnl` → **Lineage** : remonter jusqu'au fichier CSV d'origine, colonne par colonne.
- ⚠️ **Lancer la cellule de nettoyage** à la fin (sinon dashboard/Genie restent filtrés).

### 10. Conclusion (2 min)
- Récapituler le parcours sur une slide ou au tableau : **Ingestion → Delta → Gold → BI/Genie → ML/IA**, le tout gouverné par Unity Catalog.
- Qui fait quoi : data engineer (01, 02, 07), analyste (03, SQL, dashboard), data scientist (04), métier (dashboard, Genie), gouvernance (06).
- Proposer la suite : un cas réel de l'équipe à porter sur ce modèle.

---

## Variantes selon le temps et le public

| Si… | Alors |
|---|---|
| **30 min seulement** | Garder 2 (rapide), 3, 4 (séquence catastrophe), 7, 9 — sauter ML et pipeline |
| Public **métier / direction** | Insister sur 7 (Genie), 9 (gouvernance), montrer le code le moins possible |
| Public **data engineers** | Approfondir 3, 4, 6 (pipeline, expectations, bundles), montrer le Spark UI d'une requête |
| Public **data scientists** | Approfondir 8 : AutoML, Model Serving (endpoint REST), monitoring |

## Plan B si quelque chose casse en direct
- **Auto Loader J+1 déjà joué** : le relancer n'ingère rien (c'est justement l'exactly-once !) → le dire tel quel, ou lancer `99_reset_scenario_j1` + `01` (~2 min).
- **AI Functions indisponibles** (région / droits) : montrer la table `gold.reviews_enriched` calculée la veille, ou passer.
- **Genie répond mal** : cliquer 👎, ajouter une instruction, reposer la question → c'est aussi une démo de l'amélioration continue.
- **Serverless indisponible** : tout fonctionne sur un cluster *All-purpose* DBR 15.4 LTS ou plus (ML : runtime ML).

## Questions fréquentes (réponses courtes)
- *« Combien ça coûte ? »* → paiement à l'usage (DBU), Serverless facturé à la seconde ; les *system tables* (notebook 06 §6) donnent le coût par produit.
- *« Et Power BI / Tableau ? »* → connexion directe au SQL Warehouse, les droits Unity Catalog s'appliquent ; Partner Connect.
- *« Nos données sortent-elles ? »* → non, elles restent dans le stockage cloud de l'entreprise, au format ouvert Delta.
- *« Différence avec Snowflake / Fabric ? »* → rester factuel : Lakehouse ouvert, Spark + SQL + ML natifs sur la même copie.
