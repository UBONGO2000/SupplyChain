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
   | Build Command | `pip install -r requirements.txt` |
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
| POST | `/api/orders` | Créer (réservation auto du stock) | Authentifié |
| GET | `/api/orders/{id}` | Détail | Propriétaire/Admin |

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

### Connexion

```bash
curl -X POST "https://ton-api.onrender.com/api/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=Admin123!"
```

### Créer une commande

```bash
curl -X POST "https://ton-api.onrender.com/api/orders" \
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
