# 📦 API de Gestion de la Chaîne d'Approvisionnement

Une API REST prête pour la production pour la gestion des opérations de chaîne d'approvisionnement avec FastAPI, SQLAlchemy et MySQL.

![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-005571?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge)
![MySQL](https://img.shields.io/badge/MySQL-8.0+-4479A1?style=for-the-badge)
![License](https://img.shields.io/badge/Licence-MIT-green?style=for-the-badge)

---

## ✨ Fonctionnalités

### Fonctionnalités Principales

- ✅ **Opérations CRUD complètes** - Créer, Lire, Mettre à jour, Supprimer pour toutes les entités
- ✅ **Requêtes MySQL complexes** - Agrégations, JOINs, sous-requêtes et filtrage
- ✅ **Gestion des stocks** - Suivi des stocks, réservations et ajustements
- ✅ **Gestion des commandes** - Création de commandes avec réservation automatique des stocks
- ✅ **Gestion des fournisseurs** - Suivi des fournisseurs avec métriques de performance
- ✅ **Suivi des expéditions** - Statut d'expédition et suivi de livraison
- ✅ **Analyses et rapports** - Résumés des ventes, alertes de stock, produits populaires

### Sécurité et Authentification

- ✅ **Authentification JWT** - Authentification sécurisée par jetons
- ✅ **Contrôle d'accès basé sur les rôles (RBAC)** - Rôles Admin, Manager, Personnel, Lecteur
- ✅ **Hachage de mot de passe** - Bcrypt pour le stockage sécurisé des mots de passe
- ✅ **Validation des entrées** - Modèles Pydantic avec validation complète
- ✅ **Prévention des injections SQL** - Requêtes paramétrées via SQLAlchemy

### Bonnes Pratiques

- ✅ **Pooling de connexions** - Gestion efficace des connexions à la base de données
- ✅ **Conception d'API RESTful** - Méthodes HTTP standard et codes de statut
- ✅ **Documentation de l'API** - Swagger UI et ReDoc auto-générés
- ✅ **Gestion des erreurs** - Exceptions HTTP appropriées avec messages significatifs
- ✅ **Pagination** - Réponses paginées standard pour tous les points de terminaison de liste

---

## 📁 Structure du Projet

```text
SupplyChain/
├── auth.py              # Authentification JWT et hachage de mot de passe
├── database.py          # Configuration et connexion SQLAlchemy
├── models.py           # Modèles ORM (User, Warehouse, Product, etc.)
├── schema.py           # Schémas de validation Pydantic
├── main.py            # Application FastAPI et routes
├── requirements.txt    # Dépendances Python
├── .env               # Variables d'environnement (local)
├── .env.example       # Modèle des variables d'environnement
└── README.md         # Ce fichier
```

---

## 🛠️ Installation

### Prérequis

- Python 3.11+
- MySQL 8.0+
- pip ou poetry

### Configuration Git

```bash
# Initialiser git (si non déjà fait)
git init

# Créer le fichier .gitignore (déjà inclus dans le projet)
# Ce fichier exclut les fichiers sensibles comme .env
```

### Étape 1 : Cloner et Configurer

```bash
# Naviguer vers le répertoire du projet
cd SupplyChain

# Créer un environnement virtuel (recommandé)
python -m venv venv

# Activer l'environnement virtuel
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Installer les dépendances
pip install -r requirements.txt
```

### Étape 2 : Configuration de l'Environnement

```bash
# Copier le fichier d'environnement d'exemple
copy .env.example .env

# Modifier .env avec vos identifiants de base de données
# Exemple:
# DATABASE_URL=mysql+pymysql://root:Mysql2026@localhost:3306/supply_chain_db
```

### Étape 3 : Configuration de la Base de Données

```sql
-- Créer la base de données dans MySQL
CREATE DATABASE supply_chain_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### Étape 4 : Lancer l'Application

```bash
# Serveur de développement avec rechargement automatique
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Ou exécuter directement
python main.py
```

### Étape 5 : Accéder à l'API

- **Swagger UI** : <http://localhost:8000/docs>
- **ReDoc** : <http://localhost:8000/redoc>
- **Vérification de santé** : <http://localhost:8000/health>

---

## 🔐 Utilisateurs par Défaut

L'application crée automatiquement les utilisateurs suivants au premier démarrage :

| Rôle | Email | Nom d'utilisateur | Mot de passe |
| :--- | :--- | :--- | :--- |
| Admin | `admin@supplychain.com` | admin | Admin123! |
| Manager | `manager@supplychain.com` | manager | Manager123! |
| Staff | `staff@supplychain.com` | staff | Staff123! |
| Viewer | `viewer@supplychain.com` | viewer | Viewer123! |

**Remarque :** Ces utilisateurs ne seront pas créés s'ils existent déjà dans la base de données.

Pour vous connecter :

```bash
# Connexion Admin
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=Admin123!"
```

---

## 📡 Points de Terminaison de l'API

### Authentification

| Méthode | Point de Terminaison | Description |
| -------- | ---------- | ------------- |
| POST | `/api/auth/register` | Enregistrer un nouvel utilisateur |
| POST | `/api/auth/login` | Connexion et obtenir un jeton JWT |
| GET | `/api/auth/me` | Obtenir les informations de l'utilisateur actuel |

### Entrepôts

| Méthode | Point de Terminaison | Description | Accès |
| -------- | ---------- | ------------- | -------- |
| GET | `/api/warehouses` | Liste de tous les entrepôts | Tous |
| POST | `/api/warehouses` | Créer un entrepôt | Admin/Manager |
| GET | `/api/warehouses/{id}` | Obtenir un entrepôt | Tous |
| PUT | `/api/warehouses/{id}` | Mettre à jour un entrepôt | Admin/Manager |
| DELETE | `/api/warehouses/{id}` | Supprimer un entrepôt | Admin |

### Produits

| Méthode | Point de Terminaison | Description | Accès |
| -------- | ---------- | ------------- | -------- |
| GET | `/api/products` | Liste des produits (avec filtres) | Tous |
| POST | `/api/products` | Créer un produit | Admin/Manager |
| GET | `/api/products/{id}` | Obtenir un produit avec le stock | Tous |
| PUT | `/api/products/{id}` | Mettre à jour un produit | Admin/Manager |

### Stocks

| Méthode | Point de Terminaison | Description | Accès |
| -------- | ---------- | ------------- | -------- |
| GET | `/api/inventory` | Liste de tous les stocks | Tous |
| POST | `/api/inventory` | Créer un enregistrement de stock | Personnel+ |
| GET | `/api/inventory/warehouse/{id}` | Stock de l'entrepôt | Tous |
| POST | `/api/inventory/adjust` | Ajuster la quantité en stock | Personnel+ |

### Commandes

| Méthode | Point de Terminaison | Description | Accès |
| -------- | ---------- | ------------- | -------- |
| GET | `/api/orders` | Liste des commandes | Tous (propres) / Admin |
| POST | `/api/orders` | Créer une commande | Authentifié |
| GET | `/api/orders/{id}` | Obtenir les détails de la commande | Propriétaire / Admin |

### Expéditions

| Méthode | Point de Terminaison | Description | Accès |
| -------- | ---------- | ------------- | -------- |
| GET | `/api/shipments` | Liste des expéditions | Tous |
| POST | `/api/shipments` | Créer une expédition | Personnel+ |
| PUT | `/api/shipments/{id}` | Mettre à jour une expédition | Personnel+ |

### Analytiques

| Méthode | Point de Terminaison | Description | Accès |
| -------- | ---------- | ------------- | -------- |
| GET | `/api/analytics/inventory-summary` | Stock par entrepôt | Admin/Manager |
| GET | `/api/analytics/sales-summary` | Statistiques des ventes | Admin/Manager |
| GET | `/api/analytics/low-stock-alerts` | Alertes de réapprovisionnement | Tous |
| GET | `/api/analytics/top-products` | Meilleures ventes | Tous |
| GET | `/api/analytics/supplier-performance` | Métriques des fournisseurs | Admin/Manager |

---

## 🔍 Exemples de Requêtes MySQL Complexes

### 1. Résumé des Stocks par Entrepôt (Agrégation + JOIN)

```sql
SELECT
    w.id, w.name,
    COUNT(i.product_id) as total_products,
    SUM(i.quantity) as total_quantity,
    SUM(i.quantity * p.unit_price) as total_value
FROM warehouses w
JOIN inventory i ON w.id = i.warehouse_id
JOIN products p ON i.product_id = p.id
GROUP BY w.id;
```

### 2. Produits les Plus Vendus (JOIN + Agrégation + ORDER BY)

```sql
SELECT
    p.id, p.name, p.sku,
    SUM(oi.quantity) as total_sold,
    COUNT(DISTINCT oi.order_id) as order_count
FROM products p
JOIN order_items oi ON p.id = oi.product_id
JOIN orders o ON oi.order_id = o.id
GROUP BY p.id
ORDER BY total_sold DESC
LIMIT 10;
```

### 3. Alertes de Stock Faible (Sous-requête + JOIN)

```sql
SELECT
    p.id, p.name, p.sku,
    i.warehouse_id, w.name,
    i.quantity, i.reorder_level
FROM products p
JOIN inventory i ON p.id = i.product_id
JOIN warehouses w ON i.warehouse_id = w.id
WHERE i.quantity < i.reorder_level;
```

### 4. Résumé des Ventes avec Plage de Dates (Agrégation Conditionnelle)

```sql
SELECT
    COUNT(*) as total_orders,
    SUM(total_amount) as total_revenue,
    AVG(total_amount) as avg_order_value,
    SUM(CASE WHEN status = 'Delivered' THEN 1 ELSE 0 END) as delivered
FROM orders
WHERE ordered_at BETWEEN '2024-01-01' AND '2024-12-31';
```

---

## 🔒 Contrôle d'Accès Basé sur les Rôles

| Rôle | Permissions |
| ------ | ------------ |
| **Admin** | Accès complet à toutes les opérations |
| **Manager** | CRUD sur les ressources, voir les analytiques |
| **Staff** | Ajustements de stocks, créer des commandes/expéditions |
| **Viewer** | Accès en lecture seule aux données publiques |

---

## 📱 Pile Technologique

| Couche | Technologie |
| ----- | ------------ |
| Framework | FastAPI |
| ORM | SQLAlchemy |
| Base de données | MySQL |
| Authentification | JWT (python-jose) |
| Hachage de mot de passe | Bcrypt |
| Validation | Pydantic |
| Serveur | Uvicorn |

---

## 🧪 Tests

```bash
# Exécuter avec pytest
pytest -v

# Avec couverture
pytest --cov=. --cov-report=html
```

---

## 🚀 Déploiement en Production

1. **Définir les Variables d'Environnement**

   ```bash
   # .env
   DATABASE_URL=mysql+pymysql://user:pass@prod-host:3306/prod_db
   SECRET_KEY=votre-clé-sécurisée-aléatoire
   DEBUG=false
   ```

2. **Utiliser un Serveur de Production**

   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
   ```

3. **Envisager l'Utilisation de**

   - Gunicorn comme gestionnaire de processus
   - Nginx comme proxy inverse
   - Docker pour la conteneurisation

---

## 📝 Licence

Licence MIT - n'hésitez pas à utiliser ce projet à des fins d'apprentissage ou commerciales.

---

## 🔐 Sécurité

**Important :** Ne jamais commiter vos fichiers `.env` ou secrets dans Git !

Le fichier `.gitignore` inclus dans le projet exclut automatiquement :
- `.env` (variables d'environnement avec mots de passe)
- Fichiers de cache Python
- Environments virtuels
- Fichiers de base de données locales

Si vous avez accidentellement commité des fichiers sensibles, utilisez :
```bash
git rm --cached .env
git commit -m "Remove sensitive file from git tracking"
```

---

## 🙏 Remerciements

- Documentation FastAPI
- Guide ORM SQLAlchemy
- Python-Jose pour l'implémentation JWT
