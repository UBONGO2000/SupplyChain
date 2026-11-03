# Supply Chain Management API

API REST pour la gestion de la chaîne d'approvisionnement. Construite avec **FastAPI**, **SQLAlchemy** et **MySQL**.

[![CI](https://github.com/UBONGO2000/SupplyChain/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/UBONGO2000/SupplyChain/actions/workflows/ci.yml)
[![Security](https://github.com/UBONGO2000/SupplyChain/actions/workflows/security.yml/badge.svg?branch=main)](https://github.com/UBONGO2000/SupplyChain/actions/workflows/security.yml)
[![codecov](https://codecov.io/gh/UBONGO2000/SupplyChain/branch/main/graph/badge.svg)](https://codecov.io/gh/UBONGO2000/SupplyChain)
![Tests](https://img.shields.io/badge/tests-104%20passed-brightgreen?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square)
![FastAPI](https://img.shields.io/badge/FastAPI-0.141+-005571?style=flat-square)
![MySQL](https://img.shields.io/badge/MySQL-8.0+-4479A1?style=flat-square)
![Deploy](https://img.shields.io/badge/Deploy-Render-46E3B7?style=flat-square)
![Démo](https://img.shields.io/website?url=https%3A%2F%2Fsupplychain-39y0.onrender.com%2Fhealth&label=d%C3%A9mo&style=flat-square)
![Docker](https://img.shields.io/badge/Docker-compose-2496ED?style=flat-square&logo=docker&logoColor=white)

---

## Démo en ligne

| Ressource | URL |
|-----------|-----|
| API | https://supplychain-39y0.onrender.com |
| Swagger UI | https://supplychain-39y0.onrender.com/docs |
| Santé | https://supplychain-39y0.onrender.com/health |

> ⏳ **Plan gratuit Render** : le service s'endort après ~15 minutes d'inactivité.
> La première requête peut donc prendre **~50 secondes** (réveil) ; les suivantes sont immédiates.
> Le workflow `.github/workflows/keepalive.yml` ping `/health` toutes les 10 minutes pour réduire ce délai.

**Compte de démonstration** : aucun mot de passe n'est publié pour l'instance en ligne. Créez-en un sur votre instance :

```bash
python -m cli create-demo-user
# → Demo account ready: demo <demo@example.com> (staff)
# → Password: <mot de passe aléatoire affiché une seule fois>
```

Relancer la commande régénère le mot de passe (pratique pour une démo publique). Avec Docker, le compte est créé automatiquement (voir plus bas).

---

## Fonctionnalités

- CRUD pour entrepôts, fournisseurs, produits, stocks, expéditions et commandes
- Authentification JWT avec rôles (Admin, Manager, Staff, Viewer)
- Requêtes SQL complexes : agrégations et JOINs
- Gestion des stocks avec réservation automatique lors des commandes
- Analytiques : résumé des ventes, alertes stock faible, top produits, performance fournisseurs
- Pagination standardisée sur tous les endpoints
- Validation des entrées avec Pydantic
- Documentation API auto-générée (Swagger UI + ReDoc)

---

## Structure du projet

```
SupplyChain/
├── .github/
│   └── workflows/
│       ├── ci.yml           # Lint (black, flake8) + tests (pytest) + coverage (codecov)
│       ├── security.yml     # Scan bandit + audit des dépendances pip-audit
│       ├── cd.yml           # Déploiement Render, gaté par le succès de CI
│       └── keepalive.yml    # Ping /health toutes les 10 min (anti cold start)
├── main.py                 # Point d'entrée de l'application
├── cli.py                  # Commandes d'exploitation (seed, compte de démo)
├── config.py               # Configuration centralisée (variables d'environnement)
├── database.py             # Connexion SQLAlchemy + pooling
├── models.py               # Modèles ORM (8 tables)
├── schema.py               # Schémas Pydantic de validation
├── auth.py                 # Authentification JWT + RBAC
├── seed_data.py             # Données de démonstration (idempotent)
├── alembic.ini              # Configuration Alembic
├── alembic/
│   ├── env.py               # Config des migrations (réutilise l'engine SSL de database.py)
│   ├── script.py.mako        # Template des fichiers de migration
│   └── versions/             # Historique des migrations de schéma
├── routers/
│   ├── __init__.py
│   ├── auth.py             # Register, login, profil
│   ├── warehouses.py       # CRUD entrepôts
│   ├── suppliers.py        # CRUD fournisseurs
│   ├── products.py         # CRUD produits
│   ├── inventory.py        # CRUD stocks + ajustements
│   ├── shipments.py        # CRUD expéditions
│   ├── orders.py           # Couche HTTP des commandes
│   └── analytics.py        # Rapports et statistiques
├── services/
│   └── orders.py           # Règles métier : prix serveur, réservation atomique, cycle de vie
├── tests/
│   ├── conftest.py         # Fixtures pytest (DB SQLite isolée par test)
│   ├── test_auth.py        # Auth, JWT, RBAC, 401 sur routes protégées
│   ├── test_orders.py      # Prix serveur, réservation atomique, statuts, annulation
│   ├── test_order_service.py  # Couche services testée sans HTTP
│   ├── test_inventory.py   # Ajustements de stock, intégrité des données
│   ├── test_health.py      # Endpoint /health
│   ├── test_security.py    # Régressions sécurité Phase 0 (bcrypt, CORS, /health)
│   ├── test_errors.py      # Handlers d'erreurs (409/503) et X-Request-ID
│   └── test_phase1.py      # Page d'accueil, compte de démo, seed non fatal
├── scripts/                # Scripts d'exploitation (rotation des comptes par défaut)
├── docs/
│   └── api.http            # Collection d'appels (VS Code REST Client)
├── Dockerfile              # Image de production
├── docker-compose.yml      # API + MySQL 8 en une commande
├── docker-entrypoint.sh    # Migrations + seed au démarrage du conteneur
├── pytest.ini              # Config pytest (pythonpath, testpaths)
├── setup.cfg               # Config flake8 (compatible black)
├── requirements.txt        # Dépendances de production
├── dev-requirements.txt    # Dépendances de développement
├── runtime.txt             # Version Python
├── build.sh                # Script de build (Render)
├── .env                    # Variables d'environnement (git-ignoré)
├── .env.example            # Modèle de configuration
├── .gitignore
└── README.md
```

---

## Modèles de données

| Modèle | Description | Relations |
|--------|-------------|-----------|
| **User** | Utilisateurs et authentification | 1→N Order |
| **Warehouse** | Entrepôts de stockage | 1→N Inventory, 1→N Shipment |
| **Supplier** | Fournisseurs | 1→N Product, 1→N Shipment |
| **Product** | Catalogue produits | 1→N Inventory, 1→N OrderItem |
| **Inventory** | Stock (jonction warehouse × product) | FK Warehouse, FK Product |
| **Shipment** | Expéditions | FK Warehouse, FK Supplier |
| **Order** | Commandes clients | 1→N OrderItem, FK User |
| **OrderItem** | Lignes de commande | FK Order, FK Product |

---

## Migrations de base de données (Alembic)

Le schéma de la base n'est plus créé via `Base.metadata.create_all()` (qui ne crée que les tables manquantes et ignore silencieusement toute modification de colonne sur une table existante — source d'un vrai bug de désynchronisation de schéma rencontré en production). La gestion du schéma passe désormais entièrement par **Alembic**.

### Workflow au quotidien

Après avoir modifié un modèle dans `models.py` :

```bash
# Génère un fichier de migration en comparant models.py à la base réelle
alembic revision --autogenerate -m "description du changement"

# Relis le fichier généré dans alembic/versions/ avant de l'appliquer
alembic upgrade head
```

### Commandes utiles

| Commande | Effet |
|----------|-------|
| `alembic current` | Affiche la révision actuellement appliquée en base |
| `alembic history` | Liste toutes les migrations, dans l'ordre |
| `alembic upgrade head` | Applique toutes les migrations en attente |
| `alembic downgrade -1` | Annule la dernière migration |
| `alembic stamp head` | Marque la base comme à jour **sans exécuter de SQL** (utile si les tables existent déjà manuellement) |

**Important** : `alembic/env.py` réutilise directement `database.engine` (celui de l'application) plutôt que de construire une connexion séparée. C'est nécessaire car TiDB Cloud refuse les connexions non chiffrées (`erreur 1105`) — utiliser un moteur distinct fait perdre la configuration SSL et fait échouer les migrations en silence.

### En production (Render)

Le **Build Command** applique les migrations automatiquement à chaque déploiement, avant même que l'application ne démarre :

```
pip install -r requirements.txt && alembic upgrade head
```

---

## Données de démonstration

`seed_data.py` peuple la base avec un jeu de données réaliste (3 entrepôts, 4 fournisseurs, 10 produits, 10 lignes de stock — dont volontairement 2 en stock faible pour tester les alertes —, 3 expéditions et 2 commandes). L'insertion est **idempotente** : elle ne fait rien si des entrepôts existent déjà, donc aucun risque de doublon à chaque redéploiement.

Le seed n'est **jamais exécuté sans opt-in** : une base de production ne reçoit pas de données de démonstration par défaut, et un échec du seed ne peut pas empêcher l'API de démarrer.

```bash
# À la demande, sur une base vide (recommandé)
python -m cli seed-demo

# Équivalent historique
python seed_data.py

# Ou au démarrage (démo uniquement) : un échec est journalisé, jamais fatal
SEED_DEMO_DATA=true
```

Les commandes de démonstration sont rattachées au premier utilisateur existant (l'administrateur bootstrap ou le compte de démo s'il est présent). Le seed ne crée **aucun compte**.

But : permettre de tester immédiatement tous les endpoints (Postman, Swagger, ou un futur frontend) sans avoir à créer des données à la main.

---

## Tests automatisés

Suite de **104 tests** (`pytest`), **100 % de réussite**, couvrant l'authentification, la logique métier des commandes (prix serveur, réservation atomique, cycle de vie), l'intégrité des stocks et les correctifs de sécurité Phase 0/1.

### Lancer les tests

```bash
pip install -r requirements.txt -r dev-requirements.txt
pytest -v
```

Aucune base MySQL réelle n'est nécessaire : `tests/conftest.py` redirige la dépendance `get_db` de l'application vers une base **SQLite en mémoire**, recréée à zéro avant chaque test. `DATABASE_URL` reste défini avec une URL MySQL factice (jamais contactée) uniquement pour satisfaire la validation au démarrage de `config.py`.

### Répartition des tests par fichier

| Fichier | Nb de tests | Couvre |
|---------|:-:|--------|
| `test_auth.py` | 33 | Inscription sans escalade de privilèges (`role`/flags → 422, rôle `viewer` forcé), doublons, mot de passe faible, login (mauvais mot de passe, compte désactivé, email), JWT (expiré, malformé, altéré), révocation immédiate après désactivation, RBAC, bootstrap admin, 401 sur 7 routes protégées |
| `test_orders.py` | 35 | Prix imposé par le serveur (le prix client est ignoré), réservation atomique (2ᵉ commande sur la dernière unité → 409), propriété de la commande, transitions de statut, annulation avec libération du stock, 404 sur produit/utilisateur inconnu, visibilité par rôle, IDOR |
| `test_order_service.py` | 9 | Couche `services/orders.py` testée sans HTTP : totaux, prix serveur, rollback sur stock insuffisant, permissions, transitions invalides, annulation idempotente une seule fois |
| `test_inventory.py` | 7 | Ajustements positifs/négatifs (avec vérification qu'un ajustement rejeté ne modifie rien en base), doublon d'inventaire, permissions staff/viewer |
| `test_health.py` | 3 | `/health` accessible sans authentification et reflet correct de l'état de la connexion DB |
| `test_security.py` | 8 | bcrypt direct (hash, hash corrompu, limite 72 octets), `/health` 200/503, CORS sans joker Vercel |
| `test_phase1.py` | 5 | Page d'accueil `/`, génération/création/rotation du compte de démo, seed non fatal |
| `test_errors.py` | 4 | `X-Request-ID` généré/propagé, `IntegrityError` → 409, panne DB → 503 |
| **Total** | **104** | |

### Couverture de code

Mesurée avec `pytest-cov` :

```bash
pytest --cov=. --cov-report=term-missing
```

| Module | Couverture | Détail |
|--------|:-:|--------|
| `routers/auth.py` | **100 %** | Register, login, `/me` entièrement couverts |
| `routers/orders.py` | **95 %** | Couche HTTP fine : création, liste, détail, `PATCH` de statut, annulation |
| `services/orders.py` | **95 %** | Prix serveur, réservation atomique, transitions, libération du stock |
| `models.py` | 95 % | Modèles ORM exercés indirectement via les routes testées |
| `schema.py` | 98 % | Validation Pydantic exercée par les payloads de test |
| `main.py` | 82 % | Bootstrap admin, page d'accueil, `/health`, seed non fatal, handlers d'erreurs |
| `routers/inventory.py` | 71 % | Création, ajustement, permissions couverts ; listing/pagination non testés (hors périmètre) |
| `auth.py` (module JWT/RBAC) | 80 % | `create_access_token`, `decode_token`, `require_role` couverts ; `create_refresh_token` non utilisé/non testé |
| `cli.py` | 58 % | Commandes `seed-demo` et `create-demo-user` couvertes ; branches d'erreur non testées |
| **Total du projet** | **86 %** | |

Les routers `products.py`, `warehouses.py`, `suppliers.py`, `shipments.py` et `analytics.py` (31–52 % de couverture) ne faisaient pas partie du périmètre demandé (Auth, Orders, Inventory) et n'ont donc pas de tests dédiés à ce stade. `seed_data.py` (28 %) est un script de peuplement de données de démo, exercé uniquement via les tests de la Phase 1.

### Bugs identifiés et corrigés grâce à cette suite

1. **Commande sans stock disponible acceptée silencieusement** (`services/orders.py`) — une commande sur un produit sans aucun enregistrement d'inventaire suffisant était créée sans réservation, sans erreur. Corrigé : renvoie désormais **409 Conflict**, la commande n'est pas créée.
2. **Collision de numéro de commande** (`services/orders.py`) — `order_number` était généré à partir d'un timestamp en secondes ; deux commandes créées dans la même seconde produisaient le même numéro et la seconde échouait avec une erreur 500 (contrainte UNIQUE). Corrigé en ajoutant un suffixe UUID.
3. **Rôle utilisateur stocké de façon incorrecte** (`routers/auth.py`, `main.py`) — le rôle était assigné comme chaîne brute en minuscules (`"staff"`) à une colonne `Enum(UserRole)` qui attend le nom de l'enum (`"STAFF"`). Sur MySQL ce défaut passait inaperçu grâce à la normalisation insensible à la casse des colonnes ENUM natives, mais restait un point fragile pouvant faire échouer la lecture d'un utilisateur (donc le login) sur un autre moteur ou après un changement de collation. Corrigé en assignant un véritable membre d'enum (`models.UserRole(...)`).
4. **Prix fixé par le client** (`services/orders.py`) — `unit_price` venait du payload : n'importe qui pouvait commander un produit à 0,01 €. Corrigé : le prix est toujours lu dans `Product.unit_price`, la valeur client est ignorée (test dédié).
5. **Réservation non atomique** (`services/orders.py`) — la vérification de stock et la réservation étaient deux requêtes distinctes : deux commandes simultanées pouvaient réserver la même dernière unité. Corrigé par `SELECT ... FOR UPDATE` dans un ordre de verrouillage déterministe (produits triés), et **409** si le stock total est insuffisant.
6. **Aucune libération de stock** (`services/orders.py`) — annuler une commande laissait la réservation en place. Corrigé : `POST /api/orders/{id}/cancel` libère la réservation, et l'expédition décrémente la quantité physique.
7. **Cycle de statut non validé** (`services/orders.py`) — n'importe quel statut pouvait être écrit. Corrigé par un graphe de transitions explicite (`Pending → Processing → Shipped → Delivered`, annulation avant expédition uniquement).

---

## CI/CD

Trois workflows GitHub Actions dans `.github/workflows/` :

| Workflow | Déclencheur | Ce qu'il fait |
|----------|-------------|----------------|
| **CI** (`ci.yml`) | Push sur `main`, Pull Request | `black --check` + `flake8` (lint), `pytest` (104 tests), couverture envoyée à Codecov |
| **Sécurité** (`security.yml`) | Push sur `main`, chaque lundi 06:00 UTC, déclenchement manuel | Scan statique `bandit`, audit des dépendances `pip-audit` |
| **CD** (`cd.yml`) | Fin du workflow CI sur `main`, uniquement s'il a réussi | Déclenche le déploiement sur Render via un *deploy hook* |

### Comment CD est réellement gaté par CI

Render a son propre système d'auto-déploiement sur push GitHub, indépendant de toute Action — il ne sait pas ce qu'est notre workflow CI et déploierait donc même si les tests échouent. Pour que le déploiement dépende réellement du succès de CI :

1. Dans **Render Dashboard → ton service → Settings**, désactive **Auto-Deploy** (sinon Render déploie sur chaque push, en plus du workflow CD).
2. Dans **Render Dashboard → ton service → Settings → Deploy Hook**, copie l'URL du hook.
3. Dans **GitHub → Settings → Secrets and variables → Actions**, ajoute un secret `RENDER_DEPLOY_HOOK_URL` avec cette URL.
4. `cd.yml` s'abonne aux fins d'exécution du workflow `CI` (`workflow_run`) et n'appelle le hook que si `conclusion == 'success'`.

### Secrets GitHub Actions à configurer

| Secret | Utilisé par | Où le trouver |
|--------|-------------|---------------|
| `RENDER_DEPLOY_HOOK_URL` | `cd.yml` | Render Dashboard → service → Settings → Deploy Hook |
| `CODECOV_TOKEN` | `ci.yml` | [codecov.io](https://codecov.io) → ajouter le repo → Settings → token (optionnel pour un repo public, mais évite les erreurs de rate-limit) |

### État du scan de sécurité (référence)

- `bandit` : **0 issue** (les faux positifs pré-existants — mots de passe de démo, bind `0.0.0.0`, littéral `"bearer"` — sont documentés avec `# nosec` inline, code par code, plutôt que masqués globalement).
- `pip-audit` : **0 finding ouvert**. En calibrant ce workflow, un premier scan avait remonté 34 vulnérabilités connues sur des dépendances figées (`fastapi`, `starlette`, `python-jose`, `python-multipart`, `gunicorn`, `pytest`, `python-dotenv`, `pymysql`, `black`). Toutes ont été corrigées en mettant à jour ces paquets (`fastapi` 0.109→0.141, `starlette` 0.35→1.6, `pytest` 7→9, etc.), en revalidant à chaque étape que les 104 tests, `black`, `flake8` et `bandit` restaient au vert.
  - La seule vulnérabilité restante, `ecdsa==0.19.2` (`PYSEC-2026-1325`), n'a **aucune version corrigée publiée** — c'est une attaque par canal temporel dans l'implémentation Python pure, que les mainteneurs ont explicitement choisi de ne pas corriger. C'est une dépendance transitive de `python-jose[cryptography]`, utilisée uniquement pour les algorithmes JWT à base d'ECDSA (`ES256`...) ; ce projet signe ses tokens en **`HS256`** (voir `ALGORITHM` dans `config.py`), donc le code vulnérable n'est jamais exécuté ici. Exclue explicitement via `--ignore-vuln PYSEC-2026-1325` dans `security.yml`, avec la justification en commentaire — pas masquée en silence.

---

## Démarrage rapide (Docker)

Une seule commande, sans installer MySQL ni Python :

```bash
docker compose up --build
```

| Ressource | URL / valeur |
|-----------|--------------|
| Swagger UI | http://localhost:8000/docs |
| Page d'accueil | http://localhost:8000/ |
| Santé | http://localhost:8000/health |
| Compte de démo | `demo` / `DemoPass123!` |

Au démarrage, le conteneur applique les migrations Alembic, crée le compte de démo et charge les données d'exemple. Les données MySQL sont conservées dans le volume `mysql_data`.

> ⚠️ Le mot de passe `DemoPass123!` et le `SECRET_KEY` présents dans `docker-compose.yml` sont **réservés au développement local**. Ne les réutilisez jamais sur un environnement exposé.

Pour repartir d'une base vierge :

```bash
docker compose down -v
docker compose up --build
```

---

## Installation locale

### Prérequis

- Python 3.11+
- MySQL 8.0+ (ou TiDB Cloud compatible MySQL)

### Configuration

```bash
# Créer l'environnement virtuel
python -m venv venv

# Activer l'environnement virtuel
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Installer les dépendances de production
pip install -r requirements.txt

# Installer les dépendances de développement (optionnel)
pip install -r dev-requirements.txt
```

### Variables d'environnement

```bash
# Copier le fichier d'exemple
copy .env.example .env   # Windows
cp .env.example .env     # Linux/Mac
```

Modifier `.env` :

```env
DATABASE_URL=mysql+pymysql://user:password@host:port/database_name
SECRET_KEY=une-clé-secrète-unique-et-longue   # 32 caractères minimum, obligatoire
ACCESS_TOKEN_EXPIRE_MINUTES=30
APP_ENV=development
SEED_DEMO_DATA=false
DB_SSL=true
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
CORS_ORIGIN_REGEX=

# Premier administrateur (optionnel, création unique au démarrage)
BOOTSTRAP_ADMIN_EMAIL=admin@example.com
BOOTSTRAP_ADMIN_PASSWORD=un-mot-de-passe-fort-et-unique
BOOTSTRAP_ADMIN_USERNAME=admin
```

> `SECRET_KEY` n'a **aucune valeur par défaut** : l'application refuse de démarrer si elle est absente ou trop courte. C'est volontaire — une clé de repli présente dans le dépôt permettrait de forger des jetons administrateur.

### Créer la base de données

```sql
CREATE DATABASE supply_chain_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### Appliquer les migrations

```bash
alembic upgrade head
```
Crée les 8 tables avec le schéma à jour. Aucun compte n'est créé automatiquement : voir « Création du premier administrateur » plus bas. Les données de démonstration sont opt-in (`python seed_data.py`).

### Lancer l'application

```bash
# Mode développement (rechargement automatique)
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Lancer les tests

```bash
pip install -r requirements.txt -r dev-requirements.txt
pytest
```

Les tests tournent sur une base **SQLite temporaire** : aucun MySQL, aucun réseau, aucun effet de bord sur une base existante. Ils couvrent notamment l'authentification, le RBAC, la désactivation de compte, la robustesse de `/health`, la politique CORS, la page d'accueil, la création/rotation du compte de démo et le caractère non fatal du seed.

---

## Déploiement sur Render

### Étapes

1. **Pousse ton code sur GitHub**

2. **Crée un nouveau Web Service sur Render** depuis ton dépôt

3. **Configure le service** :

   | Paramètre | Valeur |
   |-----------|--------|
   | Runtime | Python 3 |
   | Build Command | `pip install -r requirements.txt && alembic upgrade head` |
   | Start Command | `gunicorn main:app --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT` |

4. **Ajoute les variables d'environnement** dans Render Dashboard :

   | Variable | Description |
   |----------|-------------|
   | `DATABASE_URL` | Chaîne de connexion MySQL/TiDB |
   | `SECRET_KEY` | Clé secrète JWT — **obligatoire**, 32+ caractères |
   | `ACCESS_TOKEN_EXPIRE_MINUTES` | Durée de vie du token (ex: 60) |
   | `APP_ENV` | `production` |
   | `SEED_DEMO_DATA` | `false` en production |
   | `DB_SSL` | `true` pour TiDB Cloud |
   | `BOOTSTRAP_ADMIN_EMAIL` | Email du premier administrateur (optionnel) |
   | `BOOTSTRAP_ADMIN_PASSWORD` | Mot de passe fort, unique (optionnel) |
   | `DEBUG` | `false` en production |
   | `CORS_ORIGINS` | Origines autorisées (séparées par virgule) |
   | `CORS_ORIGIN_REGEX` | Regex optionnelle (previews), vide par défaut |

5. **Déploie** — Render exécute automatiquement le build et lance l'application

6. **Évite la mise en veille** — le workflow `.github/workflows/keepalive.yml` ping `/health` toutes les 10 minutes. Il s'active automatiquement sur le dépôt GitHub (aucun secret requis) ; lance-le une fois manuellement depuis l'onglet *Actions* pour vérifier l'URL. GitHub désactive les workflows planifiés après 60 jours sans activité du dépôt : relance-le manuellement si nécessaire.

---

## Configuration CORS

Le middleware CORS autorise :

| Origine | Méthode |
|---------|---------|
| Origines spécifiées dans `CORS_ORIGINS` | Variable d'environnement |
| `CORS_ORIGIN_REGEX` | Regex optionnelle, **vide par défaut** (aucun joker `*.vercel.app`) |
| `http://localhost:3000` | Dev React/Vue par défaut |
| `http://localhost:5173` | Dev Vite par défaut |

Pour ajouter un domaine de production personnalisé :

```env
CORS_ORIGINS=https://mon-domaine.com,https://www.mon-domaine.com
```

---

## Création du premier administrateur

Aucun compte n'est créé automatiquement et aucun mot de passe n'est présent dans le dépôt. Pour amorcer une instance :

```env
BOOTSTRAP_ADMIN_EMAIL=admin@example.com
BOOTSTRAP_ADMIN_PASSWORD=un-mot-de-passe-fort-et-unique
BOOTSTRAP_ADMIN_USERNAME=admin   # optionnel
```

Au démarrage, si les deux premières variables sont définies **et** qu'aucun compte avec cet email n'existe, un administrateur est créé. Un redéploiement ne réinitialise jamais son mot de passe. Retirez ensuite ces variables de l'environnement.

L'inscription publique (`POST /api/auth/register`) crée uniquement des comptes **lecture seule** (`viewer`) : le rôle n'est jamais choisi par le client. La promotion d'un compte est une action d'administration.

### Comptes historiques

Les anciennes versions créaient quatre comptes de démonstration avec des mots de passe publiés. Le code ne les crée plus, mais **une base existante les contient toujours**. Pour les neutraliser :

```bash
python scripts/disable_default_accounts.py          # simulation, aucune écriture
python scripts/disable_default_accounts.py --apply  # désactive les comptes encore vulnérables
```

Le script ne désactive un compte que si son mot de passe actuel correspond encore au mot de passe publié, et le désactive au lieu de le supprimer (les commandes référencent l'utilisateur).

---

## Endpoints API

### Authentification

| Méthode | Endpoint | Description | Accès |
|---------|----------|-------------|-------|
| POST | `/api/auth/register` | Inscription | Public |
| POST | `/api/auth/login` | Connexion (retourne JWT) | Public |
| GET | `/api/auth/me` | Profil utilisateur courant | Authentifié |

### Entrepôts

| Méthode | Endpoint | Description | Accès |
|---------|----------|-------------|-------|
| GET | `/api/warehouses` | Liste (paginée, filtrable) | Authentifié |
| POST | `/api/warehouses` | Créer | Admin/Manager |
| GET | `/api/warehouses/{id}` | Détail | Authentifié |
| PUT | `/api/warehouses/{id}` | Modifier | Admin/Manager |
| DELETE | `/api/warehouses/{id}` | Supprimer | Admin |

### Fournisseurs

| Méthode | Endpoint | Description | Accès |
|---------|----------|-------------|-------|
| GET | `/api/suppliers` | Liste (filtrable par pays, rating) | Authentifié |
| POST | `/api/suppliers` | Créer | Admin/Manager |
| GET | `/api/suppliers/{id}` | Détail | Authentifié |
| PUT | `/api/suppliers/{id}` | Modifier | Admin/Manager |

### Produits

| Méthode | Endpoint | Description | Accès |
|---------|----------|-------------|-------|
| GET | `/api/products` | Liste (filtrable par catégorie, prix, fournisseur) | Authentifié |
| POST | `/api/products` | Créer | Admin/Manager |
| GET | `/api/products/{id}` | Détail avec résumé stock | Authentifié |
| PUT | `/api/products/{id}` | Modifier | Admin/Manager |

### Stocks

| Méthode | Endpoint | Description | Accès |
|---------|----------|-------------|-------|
| GET | `/api/inventory` | Liste (filtrable par entrepôt, produit, stock faible) | Authentifié |
| POST | `/api/inventory` | Créer un enregistrement | Admin/Manager/Staff |
| GET | `/api/inventory/warehouse/{id}` | Stock d'un entrepôt | Authentifié |
| POST | `/api/inventory/adjust` | Ajuster les quantités | Admin/Manager/Staff |

### Commandes

| Méthode | Endpoint | Description | Accès |
|---------|----------|-------------|-------|
| GET | `/api/orders` | Liste (les utilisateurs voient les leurs) | Authentifié |
| POST | `/api/orders` | Créer : prix lu en base, réservation atomique, 409 si stock insuffisant | Authentifié |
| GET | `/api/orders/{id}` | Détail (403 si ce n'est pas le propriétaire, sauf Admin/Manager) | Propriétaire/Admin |
| PATCH | `/api/orders/{id}` | Changer le statut (`Pending → Processing → Shipped → Delivered`) ou l'adresse | Admin/Manager/Staff |
| POST | `/api/orders/{id}/cancel` | Annuler et libérer le stock réservé (impossible après expédition) | Propriétaire/Admin/Manager |

### Expéditions

| Méthode | Endpoint | Description | Accès |
|---------|----------|-------------|-------|
| GET | `/api/shipments` | Liste (filtrable par statut, fournisseur) | Authentifié |
| POST | `/api/shipments` | Créer | Admin/Manager/Staff |
| GET | `/api/shipments/{id}` | Détail | Authentifié |
| PUT | `/api/shipments/{id}` | Modifier | Admin/Manager/Staff |

### Analytiques

| Méthode | Endpoint | Description | Accès |
|---------|----------|-------------|-------|
| GET | `/api/analytics/inventory-summary` | Résumé stock par entrepôt | Authentifié |
| GET | `/api/analytics/sales-summary` | Statistiques ventes | Admin/Manager |
| GET | `/api/analytics/low-stock-alerts` | Alertes réapprovisionnement | Authentifié |
| GET | `/api/analytics/top-products` | Produits les plus vendus | Authentifié |
| GET | `/api/analytics/supplier-performance` | Performance fournisseurs | Admin/Manager |

### Système

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/` | Page d'accueil JSON (nom, version, liens, aide compte démo) |
| GET | `/health` | Vérification de santé |
| GET | `/docs` | Swagger UI |
| GET | `/redoc` | ReDoc |

---

## Exemples d'utilisation

**API en ligne** : [https://supplychain-39y0.onrender.com/docs](https://supplychain-39y0.onrender.com/docs)

> Première requête : jusqu'à ~50 s si le service Render était en veille.

Une collection prête à l'emploi se trouve dans [`docs/api.http`](docs/api.http) (VS Code REST Client) : login, produits, création de commande, stock faible, top produits.

### Connexion

```bash
# Le compte de démo se crée avec : python -m cli create-demo-user
curl -X POST "https://supplychain-39y0.onrender.com/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "demo", "password": "<mot_de_passe_affiche_par_la_cli>"}'
```

### Créer une commande

```bash
curl -X POST "https://supplychain-39y0.onrender.com/api/orders" \
  -H "Authorization: Bearer <votre_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "shipping_address": "123 Rue Example, Paris",
    "items": [
      {"product_id": 1, "quantity": 2, "discount_percent": 10}
    ]
  }'
```

Le prix n'est pas envoyé par le client : le serveur lit `Product.unit_price` au moment de la commande. `user_id` est optionnel et vaut par défaut l'utilisateur authentifié (seuls Admin/Manager peuvent commander pour un autre compte).

---

## Contrôle d'accès (RBAC)

| Rôle | Permissions |
|------|------------|
| **Admin** | Accès complet à toutes les opérations |
| **Manager** | CRUD sur les ressources, analytiques avancées |
| **Staff** | Ajustements stocks, création commandes/expéditions |
| **Viewer** | Lecture seule sur les données publiques |

---

## Stack technique

| Couche | Technologie |
|--------|-------------|
| Framework | FastAPI 0.141 |
| ORM | SQLAlchemy 2.0 |
| Base de données | MySQL 8.0+ / TiDB Cloud |
| Authentification | JWT (python-jose) |
| Hachage mot de passe | bcrypt |
| Validation | Pydantic 2.13 |
| Migrations | Alembic |
| Tests | Pytest + FastAPI TestClient (SQLite en mémoire) |
| CI/CD | GitHub Actions (lint, tests, sécurité, déploiement) |
| Sécurité statique | Bandit + pip-audit |
| Couverture | pytest-cov + Codecov |
| Serveur prod | Gunicorn + Uvicorn workers |
| Pool connexions | QueuePool (10+20 overflow) |
| Backend deploy | Render |
| Frontend deploy | Vercel |

---

## Sécurité

- **SECRET_KEY** : obligatoire (32+ caractères), aucune valeur de repli — l'application refuse de démarrer sans elle
- **Mots de passe** : hachés avec bcrypt directement (limite de 72 octets vérifiée explicitement, jamais de troncature silencieuse)
- **Comptes** : aucun compte ni mot de passe par défaut ; bootstrap administrateur opt-in par variables d'environnement
- **Inscription** : rôle impossible à choisir côté client, extra fields rejetés (`422`), compte créé en lecture seule
- **Désactivation** : un compte désactivé perd l'accès immédiatement, même avec un token encore valide
- **JWT** : tokens avec expiration configurable
- **RBAC** : 4 niveaux de rôles
- **CORS** : liste blanche explicite ; pas de joker `*.vercel.app`
- **Injection SQL** : requêtes paramétrées via SQLAlchemy ORM
- **Validation** : schémas Pydantic stricts, `422` sur champ inconnu

**Limites assumées** : pas de limitation de tentatives de connexion, pas de révocation immédiate des jetons (durée courte + vérification `is_active`). Voir `SECURITY.md`.

**Important** : ne jamais commiter le fichier `.env` dans Git.

---

## Licence

MIT  

## Author

Georges NTCHANGA
