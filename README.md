# 🛍️ Kirana Backend - Django REST API

A comprehensive REST API backend for the Kirana platform built with Django and Django REST Framework.

## 📋 Table of Contents

1. [Features](#-features)
2. [API Endpoints](#-api-endpoints)
3. [Installation & Setup](#-installation--setup)
4. [Database Models](#-database-models)
5. [Authentication](#-authentication)
6. [Deployment](#-deployment)
7. [Development](#-development)
8. [Project Structure](#-project-structure)
9. [Technologies](#-technologies)
10. [API Documentation](#-api-documentation)

---

## ⭐ Features

- 🔐 **User Authentication** - Token-based authentication with registration, login, logout
- 👥 **User Management** - Dealer and Shopkeeper profiles with email verification
- 🛒 **Product Management** - Full CRUD operations for products with categories
- ⭐ **Product Reviews** - Rating and review system for products
- 📦 **Order Management** - Complete order lifecycle (pending, confirmed, shipped, delivered, cancelled)
- 💳 **Order Items** - Detailed line items with pricing and quantities
- 🏪 **Dealer Profiles** - Business verification, documents, analytics
- 🛍️ **Shopkeeper Profiles** - Shop management, dealer following, order history
- 📊 **Analytics** - Order and sales statistics
- 🔍 **Search & Filter** - Full-text search, advanced filtering, sorting
- 📖 **API Documentation** - Auto-generated Swagger/Redoc documentation
- 🐳 **Docker Ready** - Complete containerized setup with PostgreSQL, Redis

---

## 🔌 API Endpoints

### Base URL: `http://localhost:8000/api/v1/`

### Users

```
POST   /users/register/          - Register new user
POST   /users/login/             - Login user
POST   /users/logout/            - Logout user
GET    /users/profile/           - Get current user profile
PUT    /users/update_profile/    - Update user profile
POST   /users/change_password/   - Change password
```

### Products

```
GET    /products/                - List all products
POST   /products/                - Create product (dealer only)
GET    /products/{id}/           - Product details
PUT    /products/{id}/           - Update product
DELETE /products/{id}/           - Delete product
GET    /products/my_products/    - My products (dealer only)
GET    /products/by_category/    - Filter by category
GET    /products/by_dealer/      - Filter by dealer
GET    /products/{id}/reviews/   - Product reviews
POST   /products/{id}/add_review/- Add review
```

### Categories

```
GET    /categories/              - List all categories
GET    /categories/{slug}/       - Category details
```

### Dealers

```
GET    /dealers/                 - List all dealers
GET    /dealers/{id}/            - Dealer details
GET    /dealers/my_profile/      - My dealer profile
POST   /dealers/create_profile/  - Create dealer profile
PUT    /dealers/update_profile/  - Update dealer profile
POST   /dealers/upload_document/ - Upload verification document
GET    /dealers/my_documents/    - My documents
```

### Shopkeepers

```
GET    /shopkeepers/             - List all shopkeepers
GET    /shopkeepers/{id}/        - Shopkeeper details
GET    /shopkeepers/my_profile/  - My shopkeeper profile
POST   /shopkeepers/create_profile/ - Create shopkeeper profile
PUT    /shopkeepers/update_profile/ - Update shopkeeper profile
POST   /shopkeepers/{id}/follow_dealer/   - Follow dealer
POST   /shopkeepers/{id}/unfollow_dealer/ - Unfollow dealer
GET    /shopkeepers/my_followed_dealers/  - My followed dealers
```

### Orders

```
GET    /orders/                  - List orders
POST   /orders/                  - Create order
GET    /orders/{id}/             - Order details
PUT    /orders/{id}/             - Update order
DELETE /orders/{id}/             - Cancel order
POST   /orders/{id}/cancel/      - Cancel order
POST   /orders/{id}/update_status/ - Update order status
GET    /orders/my_orders/        - My orders
GET    /orders/stats/            - Order statistics
```

---

## 🚀 Installation & Setup

### Prerequisites

- Python 3.10+
- PostgreSQL 12+ (or use SQLite for development)
- Redis
- Docker & Docker Compose (optional)

### Option 1: Local Development

#### Step 1: Clone/Navigate to Project

```bash
cd /home/rahul/Desktop/Kirana/backend
```

#### Step 2: Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

#### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

#### Step 4: Create Environment File

```bash
cp .env.example .env
```

Edit `.env` with your settings:

```env
DEBUG=True
SECRET_KEY=your-secret-key-here
DB_ENGINE=django.db.backends.sqlite3
DB_NAME=db.sqlite3
```

#### Step 5: Run Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

#### Step 6: Create Superuser

```bash
python manage.py createsuperuser
```

#### Step 7: Start Development Server

```bash
python manage.py runserver
```

The API will be available at: `http://localhost:8000/api/v1/`

### Option 2: Docker Deployment

#### Method 1: Individual Backend Container

```bash
cd backend
docker build -t kirana-backend .
docker run -p 8000:8000 -e DEBUG=True kirana-backend
```

#### Method 2: Full Stack with Docker Compose

```bash
cd /home/rahul/Desktop/Kirana
docker-compose up -d
```

This will start:

- PostgreSQL database
- Redis cache
- Django backend
- Next.js frontend

---

## 📊 Database Models

### User (Extended AbstractUser)

- username, email, password
- first_name, last_name
- user_type (dealer/shopkeeper)
- phone_number, profile_picture
- address, city, state, postal_code, country
- is_verified, verification_token
- created_at, updated_at

### Dealer

- user (OneToOneField)
- business_name, business_license, gst_number
- business_category, years_in_business
- total_products, rating, total_orders
- is_verified, is_banned
- documents (ForeignKey to DealerDocument)
- created_at, updated_at

### Shopkeeper

- user (OneToOneField)
- shop_name, shop_image
- business_type, employees_count
- monthly_budget
- preferred_dealers (ManyToManyField)
- rating, total_orders, total_spent
- is_verified
- created_at, updated_at

### Product

- dealer (ForeignKey)
- category (ForeignKey)
- name, description, price, unit
- stock_quantity, image
- is_available
- reviews (ForeignKey to ProductReview)
- created_at, updated_at

### Order

- order_number (unique)
- shopkeeper (ForeignKey)
- dealer (ForeignKey)
- items (ForeignKey to OrderItem)
- status (pending/confirmed/shipped/delivered/cancelled)
- payment_status (pending/paid/failed/refunded)
- total_amount, discount, net_amount
- shipping_address, notes
- created_at, updated_at, delivered_at

### OrderItem

- order (ForeignKey)
- product (ForeignKey)
- product_name, product_price
- quantity, unit, subtotal

### Category

- name, description, icon
- slug
- is_active
- created_at, updated_at

---

## 🔐 Authentication

### Token-Based Authentication

#### Registration

```bash
POST /api/v1/users/register/
{
    "username": "john_dealer",
    "email": "john@example.com",
    "password": "securepass123",
    "password_confirm": "securepass123",
    "first_name": "John",
    "last_name": "Dealer",
    "user_type": "dealer",
    "phone_number": "+919876543210"
}
```

#### Response

```json
{
  "user": {
    "id": 1,
    "username": "john_dealer",
    "email": "john@example.com",
    "user_type": "dealer",
    "first_name": "John",
    "last_name": "Dealer"
  },
  "token": "9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b",
  "message": "User registered successfully"
}
```

#### Login

```bash
POST /api/v1/users/login/
{
    "username": "john_dealer",
    "password": "securepass123"
}
```

#### Using Token in Requests

```bash
curl -H "Authorization: Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b" \
     http://localhost:8000/api/v1/users/profile/
```

---

## 🎯 Common API Operations

### List Products with Filtering

```bash
GET /api/v1/products/?search=rice&category=grains&ordering=-price
```

### Create Order

```bash
POST /api/v1/orders/
{
    "dealer_id": 1,
    "items": [
        {
            "product": 1,
            "product_name": "Basmati Rice",
            "product_price": 150.00,
            "quantity": 50,
            "unit": "kg",
            "subtotal": 7500.00
        }
    ],
    "shipping_address": "123 Main St, Mumbai, 400001",
    "discount": 500.00,
    "notes": "Urgent delivery"
}
```

### Update Order Status

```bash
POST /api/v1/orders/1/update_status/
{
    "status": "shipped"
}
```

---

## 📝 Management Commands

```bash
# Create superuser
python manage.py createsuperuser

# Create new migration
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Create test data
python manage.py shell

# Collect static files
python manage.py collectstatic --noinput

# Run tests
python manage.py test

# Clear cache
python manage.py clear_cache
```

---

## 🐳 Docker Setup

### Start Full Stack

```bash
docker-compose up -d
```

### View Logs

```bash
docker-compose logs -f backend
```

### Stop Services

```bash
docker-compose down
```

### Access Database

```bash
docker-compose exec db psql -U kirana_user -d kirana_db
```

### Reset Database

```bash
docker-compose down -v
docker-compose up -d
```

---

## 📁 Project Structure

```
backend/
├── kirana/                 # Main project folder
│   ├── __init__.py
│   ├── settings.py        # Django settings
│   ├── urls.py            # Main URL configuration
│   ├── wsgi.py            # WSGI configuration
│
├── users/                 # User management app
│   ├── models.py         # User model
│   ├── views.py          # User viewsets
│   ├── serializers.py    # User serializers
│   └── urls.py           # User URLs
│
├── products/             # Product management app
│   ├── models.py         # Product, ProductReview
│   ├── views.py          # Product viewsets
│   ├── serializers.py    # Product serializers
│   └── urls.py           # Product URLs
│
├── dealers/              # Dealer profile app
│   ├── models.py         # Dealer, DealerDocument
│   ├── views.py          # Dealer viewsets
│   ├── serializers.py    # Dealer serializers
│   └── urls.py           # Dealer URLs
│
├── shopkeepers/          # Shopkeeper profile app
│   ├── models.py         # Shopkeeper model
│   ├── views.py          # Shopkeeper viewsets
│   ├── serializers.py    # Shopkeeper serializers
│   └── urls.py           # Shopkeeper URLs
│
├── orders/               # Order management app
│   ├── models.py         # Order, OrderItem
│   ├── views.py          # Order viewsets
│   ├── serializers.py    # Order serializers
│   └── urls.py           # Order URLs
│
├── categories/           # Category management app
│   ├── models.py         # Category model
│   ├── views.py          # Category viewsets
│   ├── serializers.py    # Category serializers
│   └── urls.py           # Category URLs
│
├── manage.py             # Django CLI
├── requirements.txt      # Python dependencies
├── Dockerfile            # Docker configuration
├── .env.example          # Environment variables template
├── .gitignore            # Git ignore rules
└── README.md             # This file
```

---

## 🛠️ Technologies

| Technology | Version | Purpose       |
| ---------- | ------- | ------------- |
| Django     | 4.2.8   | Web framework |
| DRF        | 3.14.0  | REST API      |
| PostgreSQL | 15      | Database      |
| Redis      | 7       | Cache         |
| Gunicorn   | 21.2.0  | WSGI server   |
| Python     | 3.10+   | Runtime       |

---

## 📚 API Documentation

### Auto-Generated Documentation

- **Swagger UI**: `http://localhost:8000/api/docs/`
- **ReDoc**: `http://localhost:8000/api/redoc/`

### Admin Panel

- **URL**: `http://localhost:8000/admin/`
- **Username**: (from createsuperuser)
- **Password**: (from createsuperuser)

---

## 🔧 Configuration

### Settings (.env)

```env
# Django
DEBUG=True
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0

# Database
DB_ENGINE=django.db.backends.postgresql
DB_NAME=kirana_db
DB_USER=postgres
DB_PASSWORD=password
DB_HOST=localhost
DB_PORT=5432

# CORS
CORS_ALLOWED_ORIGINS=http://localhost:3000

# JWT
JWT_SECRET_KEY=your-jwt-secret

# API
API_BASE_URL=http://localhost:8000
FRONTEND_URL=http://localhost:3000
```

---

## 📖 Useful Resources

- [Django Documentation](https://docs.djangoproject.com/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [PostgreSQL](https://www.postgresql.org/docs/)
- [Docker](https://docs.docker.com/)

---

## 🤝 Contributing

1. Create a feature branch: `git checkout -b feature/new-feature`
2. Make changes and commit: `git commit -am 'Add new feature'`
3. Push to branch: `git push origin feature/new-feature`
4. Submit Pull Request

---

## 📜 License

MIT License - See LICENSE file

---

## 📞 Support

For issues, questions, or suggestions:

1. Check existing issues
2. Create new issue with details
3. Contact development team

---

**Version:** 1.0.0  
**Status:** Development  
**Last Updated:** March 2026

**Happy coding! 🚀**
