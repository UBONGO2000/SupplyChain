# Supply Chain Management API

API REST pour la gestion de la chaîne d'approvisionnement. Construite avec **FastAPI**, **SQLAlchemy** et **MySQL**.

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-005571?style=flat-square)
![MySQL](https://img.shields.io/badge/MySQL-8.0+-4479A1?style=flat-square)
![Deploy](https://img.shields.io/badge/Deploy-Render-46E3B7?style=flat-square)

---

## Fonctionnalités

- CRUD complet pour entrepôts, fournisseurs, produits, stocks, expéditions et commandes
- Authentification JWT avec rôles (Admin, Manager, Staff, Viewer)
- Requêtes SQL complexes : agrégations, JOINs, sous-requêtes
- Gestion des stocks avec réservation automatique lors des commandes
- Analytiques : résumé des ventes, alertes stock faible, top produits, performance fournisseurs
- Pagination standardisée sur tous les endpoints
- Validation des entrées avec Pydantic
- Documentation API auto-générée (Swagger UI + ReDoc)

---

## Structure du projet

```
SupplyChain/
├── main.py                 # Point d'entrée de l'application
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
│   ├── orders.py           # CRUD commandes + réservation stock
│   └── analytics.py        # Rapports et statistiques
├── tests/
│   ├── conftest.py         # Fixtures pytest (DB SQLite isolée par test)
│   ├── test_auth.py        # Auth, JWT, RBAC, 401 sur routes protégées
│   ├── test_orders.py      # Calcul des totaux, réservation stock, IDOR
│   ├── test_inventory.py   # Ajustements de stock, intégrité des données
│   └── test_health.py      # Endpoint /health
├── pytest.ini              # Config pytest (pythonpath, testpaths)
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

`seed_data.py` peuple la base avec un jeu de données réaliste (3 entrepôts, 4 fournisseurs, 10 produits, 10 lignes de stock — dont volontairement 2 en stock faible pour tester les alertes —, 3 expéditions et 2 commandes). Cette fonction est appelée automatiquement au démarrage de l'application (voir `lifespan` dans `main.py`) et est **idempotente** : elle ne fait rien si des entrepôts existent déjà en base, donc aucun risque de doublon à chaque redéploiement.

But : permettre de tester immédiatement tous les endpoints (Postman, Swagger, ou un futur frontend) sans avoir à créer des données à la main.

---

## Tests automatisés

Suite de **42 tests** (`pytest`), **100 % de réussite**, couvrant l'authentification, la logique métier des commandes et l'intégrité des stocks.

### Lancer les tests

```bash
pip install -r requirements.txt -r dev-requirements.txt
pytest -v
```

Aucune base MySQL réelle n'est nécessaire : `tests/conftest.py` redirige la dépendance `get_db` de l'application vers une base **SQLite en mémoire**, recréée à zéro avant chaque test. `DATABASE_URL` reste défini avec une URL MySQL factice (jamais contactée) uniquement pour satisfaire la validation au démarrage de `config.py`.

### Répartition des tests par fichier

| Fichier | Nb de tests | Couvre |
|---------|:-:|--------|
| `test_auth.py` | 20 | Inscription (doublons, hash du mot de passe, rôle assigné), login (mauvais mot de passe, compte désactivé), JWT (expiré, malformé, altéré), RBAC (`require_role`), 401 sur 7 routes protégées |
| `test_orders.py` | 12 | Calcul du total (taxe 20 %, seuil de livraison gratuite à 100 €, remises), réservation de stock, 404 sur produit/utilisateur inconnu, visibilité des commandes par rôle, IDOR sur `get_order` |
| `test_inventory.py` | 7 | Ajustements positifs/négatifs (avec vérification qu'un ajustement rejeté ne modifie rien en base), doublon d'inventaire, permissions staff/viewer |
| `test_health.py` | 3 | `/health` accessible sans authentification et reflet correct de l'état de la connexion DB |
| **Total** | **42** | |

### Couverture de code

Mesurée avec `pytest-cov` :

```bash
pytest --cov=. --cov-report=term-missing
```

| Module | Couverture | Détail |
|--------|:-:|--------|
| `routers/auth.py` | **100 %** | Register, login, `/me` entièrement couverts |
| `routers/orders.py` | **97 %** | Totaux, réservation de stock, visibilité, IDOR — seules 2 lignes non exécutées (branche défensive) |
| `models.py` | 95 % | Modèles ORM exercés indirectement via les routes testées |
| `schema.py` | 98 % | Validation Pydantic exercée par les payloads de test |
| `routers/inventory.py` | 71 % | Création, ajustement, permissions couverts ; listing/pagination non testés (hors périmètre) |
| `auth.py` (module JWT/RBAC) | 77 % | `create_access_token`, `decode_token`, `require_role` couverts ; `create_refresh_token` non utilisé/non testé |
| **Total du projet** | **81 %** | |

Les routers `products.py`, `warehouses.py`, `suppliers.py`, `shipments.py` et `analytics.py` (33–52 % de couverture) ne faisaient pas partie du périmètre demandé (Auth, Orders, Inventory) et n'ont donc pas de tests dédiés à ce stade. `seed_data.py` (0 %) est un script de peuplement de données de démo, non testé par nature.

### Bugs identifiés et corrigés grâce à cette suite

1. **Commande sans stock disponible acceptée silencieusement** (`routers/orders.py`) — une commande sur un produit sans aucun enregistrement d'inventaire suffisant était créée sans réservation, sans erreur. Corrigé : renvoie désormais **409 Conflict**, la commande n'est pas créée.
2. **Collision de numéro de commande** (`routers/orders.py`) — `order_number` était généré à partir d'un timestamp en secondes ; deux commandes créées dans la même seconde produisaient le même numéro et la seconde échouait avec une erreur 500 (contrainte UNIQUE). Corrigé en ajoutant un suffixe UUID.
3. **Rôle utilisateur stocké de façon incorrecte** (`routers/auth.py`, `main.py`) — le rôle était assigné comme chaîne brute en minuscules (`"staff"`) à une colonne `Enum(UserRole)` qui attend le nom de l'enum (`"STAFF"`). Sur MySQL ce défaut passait inaperçu grâce à la normalisation insensible à la casse des colonnes ENUM natives, mais restait un point fragile pouvant faire échouer la lecture d'un utilisateur (donc le login) sur un autre moteur ou après un changement de collation. Corrigé en assignant un véritable membre d'enum (`models.UserRole(...)`).

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
SECRET_KEY=une-clé-secrète-unique-et-longue
ACCESS_TOKEN_EXPIRE_MINUTES=30
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

### Créer la base de données

```sql
CREATE DATABASE supply_chain_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### Appliquer les migrations

```bash
alembic upgrade head
```
Crée les 8 tables avec le schéma à jour. Les utilisateurs par défaut et les données de démonstration se créent automatiquement au premier démarrage de l'application (voir plus bas).

### Lancer l'application

```bash
# Mode développement (rechargement automatique)
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Ou directement
python main.py
```

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
   | `SECRET_KEY` | Clé secrète JWT (32+ caractères) |
   | `ACCESS_TOKEN_EXPIRE_MINUTES` | Durée de vie du token (ex: 60) |
   | `DEBUG` | `false` en production |
   | `CORS_ORIGINS` | Origines autorisées (séparées par virgule) |

5. **Déploie** — Render exécute automatiquement le build et lance l'application

---

## Configuration CORS

Le middleware CORS autorise :

| Origine | Méthode |
|---------|---------|
| Origines spécifiées dans `CORS_ORIGINS` | Variable d'environnement |
| `https://*.vercel.app` | Regex automatique (tous les déploiements Vercel) |
| `http://localhost:3000` | Dev React/Vue par défaut |
| `http://localhost:5173` | Dev Vite par défaut |

Pour ajouter un domaine de production personnalisé :

```env
CORS_ORIGINS=https://mon-domaine.com,https://www.mon-domaine.com
```

---

## Utilisateurs par défaut

Créés automatiquement au premier démarrage :

| Rôle | Email | Mot de passe |
|------|-------|-------------|
| Admin | admin@supplychain.com | Admin123! |
| Manager | manager@supplychain.com | Manager123! |
| Staff | staff@supplychain.com | Staff123! |
| Viewer | viewer@supplychain.com | Viewer123! |

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
| POST | `/api/orders` | Créer (réservation auto du stock, 409 si stock insuffisant) | Authentifié |
| GET | `/api/orders/{id}` | Détail (403 si ce n'est pas le propriétaire, sauf Admin/Manager) | Propriétaire/Admin |

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
| GET | `/health` | Vérification de santé |
| GET | `/docs` | Swagger UI |
| GET | `/redoc` | ReDoc |

---

## Exemples d'utilisation

**API en ligne** : [https://supplychain-39y0.onrender.com/docs](https://supplychain-39y0.onrender.com/docs)

### Connexion

```bash
curl -X POST "https://supplychain-39y0.onrender.com/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "Admin123!"}'
```

### Créer une commande

```bash
curl -X POST "https://supplychain-39y0.onrender.com/api/orders" \
  -H "Authorization: Bearer <votre_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "shipping_address": "123 Rue Example, Paris",
    "items": [
      {"product_id": 1, "quantity": 2, "unit_price": 29.99, "discount_percent": 10}
    ]
  }'
```

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
| Framework | FastAPI 0.109 |
| ORM | SQLAlchemy 2.0 |
| Base de données | MySQL 8.0+ / TiDB Cloud |
| Authentification | JWT (python-jose) |
| Hachage mot de passe | bcrypt |
| Validation | Pydantic 2.6 |
| Migrations | Alembic |
| Tests | Pytest + FastAPI TestClient (SQLite en mémoire) |
| Serveur prod | Gunicorn + Uvicorn workers |
| Pool connexions | QueuePool (10+20 overflow) |
| Backend deploy | Render |
| Frontend deploy | Vercel |

---

## Sécurité

- **SECRET_KEY** : chargée depuis `.env` (jamais en dur dans le code)
- **Mots de passe** : hachés avec bcrypt
- **JWT** : tokens avec expiration configurable
- **RBAC** : 4 niveaux de rôles
- **CORS** : whitelist configurable + regex `*.vercel.app` automatique
- **Injection SQL** : requêtes paramétrées via SQLAlchemy ORM
- **Validation** : tous les inputs validés par Pydantic

**Important** : ne jamais commiter le fichier `.env` dans Git.

---

## Licence

MIT

## Author

Georges NTCHANGA