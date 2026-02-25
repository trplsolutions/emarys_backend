# Emrays Trade Operations Platform — Backend

> Django REST Framework API powering the Emrays Vector Hub Platform.  
> Handles authentication, customer management, inquiry management, and file uploads.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Tech Stack](#2-tech-stack)
3. [Project Structure](#3-project-structure)
4. [File-by-File Documentation](#4-file-by-file-documentation)
5. [API Endpoints Reference](#5-api-endpoints-reference)
6. [Authentication Flow](#6-authentication-flow)
7. [Database Models](#7-database-models)
8. [Security Implementation](#8-security-implementation)
9. [Setup & Running Locally](#9-setup--running-locally)
10. [Environment Variables](#10-environment-variables)
11. [Next Steps for Developers](#11-next-steps-for-developers)

---

## 1. Project Overview

The Emrays backend is a **Django 6.0 REST API** that serves as the data and business logic layer for the trading operations platform. It currently handles:

- **User Authentication** — Signup, Login, Logout, Forgot Password, and session management via **HttpOnly JWT cookies**
- **Customer Management** — Create and retrieve customer records
- **Inquiry Management** — Full CRUD for trade inquiries, with optional file/document attachments
- **Role-Based Access** — Users have roles (`admin`, `manager`, `sales`) stored in the database

The frontend (a separate Next.js repo) communicates with this backend exclusively over REST API calls with credentials (cookies).

---

## 2. Tech Stack

| Technology | Version | Purpose |
|---|---|---|
| Python | 3.11+ | Runtime |
| Django | 6.0 | Web framework |
| Django REST Framework | Latest | API layer |
| djangorestframework-simplejwt | Latest | JWT token generation |
| django-cors-headers | Latest | CORS policy for frontend access |
| psycopg2-binary | Latest | PostgreSQL driver |
| python-dotenv | Latest | Load `.env` variables |
| PostgreSQL | 14+ | Primary database |

---

## 3. Project Structure

```
emarys_backend/
├── config/                  # Django project configuration
│   ├── settings.py          # All app settings (DB, CORS, JWT, security headers)
│   ├── urls.py              # Root URL routing
│   └── wsgi.py              # WSGI entry point for production
│
├── accounts/                # Core application — all business logic lives here
│   ├── models.py            # User, Customer, Inquiry database models
│   ├── serializers.py       # Data validation and transformation layer
│   ├── views.py             # All API view logic
│   ├── urls.py              # accounts app URL patterns
│   ├── admin.py             # Django admin registration
│   ├── tokens.py            # Password reset token generator
│   └── migrations/          # Auto-generated database migrations
│
├── templates/               # HTML templates (currently only used by email)
├── media/                   # Uploaded files stored here (auto-created)
├── staticfiles/             # Collected static files (for production)
├── manage.py                # Django CLI entry point
├── requirements.txt         # Python dependencies
└── .env                     # Local environment variables (NOT committed to git)
```

---

## 4. File-by-File Documentation

### `config/settings.py`
Central Django configuration file. Key decisions made here:

- **`AUTH_USER_MODEL = 'accounts.User'`** — Overrides Django's default user model to use our custom `User` model (which adds `role` and `phone` fields).
- **`SIMPLE_JWT`** — Configures access tokens to expire in **1 hour** and refresh tokens in **24 hours**. Refresh tokens rotate on use (new refresh token issued each time).
- **`CORS_ALLOW_CREDENTIALS = True`** — Required so the browser will send cookies cross-origin between `localhost:3000` (frontend) and `localhost:8000` (backend).
- **`AUTH_PASSWORD_VALIDATORS = []`** — Currently empty for development ease. **Must be re-populated before production deployment.**
- **`MEDIA_ROOT`** — Uploaded files (inquiry documents) are stored at `emarys_backend/media/`.
- **`DEFAULT_THROTTLE_RATES`** — Limits anonymous users to 60 requests/minute to prevent brute force attacks.
- **Security headers** — `X_FRAME_OPTIONS = "DENY"` and `SECURE_CONTENT_TYPE_NOSNIFF = True` are active. HTTPS-specific headers (HSTS, Secure cookies) are commented in and ready to enable for production.

---

### `config/urls.py`
Root URL dispatcher. Routes all `/api/` requests to `accounts.urls`. Also serves `media/` files during development (`DEBUG=True`).

```
/admin/           → Django admin panel
/api/             → accounts.urls (all API routes)
/media/<path>     → Uploaded files (dev only)
```

---

### `accounts/models.py`
Defines the three core database tables:

#### `User` (extends `AbstractUser`)
Django's built-in user model extended with:
- `role` — CharField with choices: `admin`, `manager`, `sales`. Default: `sales`.
- `phone` — Optional phone number string.

Authentication uses username + password internally (email/username lookup is handled in the view).

#### `Customer`
Represents a business customer or contact who submits inquiries.

| Field | Type | Notes |
|---|---|---|
| `name` | CharField | Contact person's name |
| `company_name` | CharField | Optional company |
| `email` | EmailField(unique) | Must be unique per customer |
| `phone` | CharField | Optional |
| `source` | CharField | Referral / Website / Direct / Other |
| `created_at` | DateTimeField | Auto-set on creation |

#### `Inquiry`
The core business object. Represents a trade inquiry from a customer.

| Field | Type | Notes |
|---|---|---|
| `customer` | ForeignKey → Customer | The customer who submitted it |
| `created_by` | ForeignKey → User | The sales user who recorded it |
| `inquiry_type` | CharField | `product` or `service` |
| `status` | CharField | `pending`, `quoted`, `confirmed`, `closed` |
| `priority` | CharField | `low`, `medium`, `high` |
| `subject` | CharField | Title/summary of the inquiry |
| `product` | CharField | Product being enquired about |
| `quantity` | CharField | Flexible — can be "100 pcs" or "5 tons" |
| `terms` | CharField | `FOB`, `CIF`, or `EXW` |
| `destination` | CharField | Shipping destination |
| `inquiry_date` | DateField | Optional date field from form |
| `description` | TextField | General description |
| `notes` | TextField | Sales rep remarks |
| `comments` | TextField | Additional comments |
| `follow_up_date` | DateField | Next follow-up date |
| `follow_up_notes` | TextField | Next steps / follow-up notes |
| `document` | FileField | Uploaded file (PDF/image/Word) |
| `document_description` | TextField | Description of the document |
| `created_at` | DateTimeField | Auto timestamp |
| `updated_at` | DateTimeField | Auto-updated on save |

---

### `accounts/serializers.py`
Data validation layer between raw request data and database models.

#### `RegisterSerializer`
- Validates `username`, `email`, `password` (min 9 chars), and optional fields.
- Checks email uniqueness with a custom `validate_email()` method.
- Uses `User.objects.create_user()` which **always hashes the password** securely via Django's PBKDF2 hasher.

#### `UserSerializer`
- Read-only safe representation of the user. **Never exposes the password field.**
- Used in the `/me` endpoint and login response.

#### `CustomerSerializer`
- Validates and serializes`Customer` model.
- Normalizes email to lowercase.

#### `InquirySerializer`
- Includes nested read-only fields: `customer_name`, `created_by_name`.
- `validate_document()` enforces:
  - **Max file size: 5MB**
  - **Allowed MIME types**: PDF, JPEG, PNG, WebP, DOC, DOCX
  - **Allowed extensions**: `.pdf`, `.jpg`, `.jpeg`, `.png`, `.webp`, `.doc`, `.docx`
- `create()` automatically attaches `created_by = request.user`.

---

### `accounts/views.py`
All API business logic. Organized into sections:

#### Auth Views

**`RegisterView`** (`POST /api/auth/register/`)
- Public endpoint (no auth required).
- Validates data via `RegisterSerializer`.
- Creates the user with hashed password.
- Returns the new user's public data.

**`LoginView`** (`POST /api/auth/login/`)
- Accepts `username` field which can be either an **email address OR a username**.
- Looks up the user via `Q(email=identifier) | Q(username=identifier)`.
- Calls Django's `authenticate()` for secure password checking.
- On success: generates JWT access + refresh tokens via `RefreshToken.for_user()`.
- Sets both tokens in **HttpOnly cookies** (not accessible to JavaScript — prevents XSS token theft).
- Returns basic user info (id, name, email, role) in the response body for immediate frontend use.

**`LogoutView`** (`POST /api/auth/logout/`)
- Requires authentication.
- Deletes both `access_token` and `refresh_token` cookies server-side.

**`MeView`** (`GET /api/auth/me/`)
- Requires authentication.
- Returns the currently authenticated user's profile.
- Used by the frontend on page refresh to restore the session from the cookie.

**`ForgotPasswordRequestView`** (`POST /api/auth/forgot-password/`)
- Accepts an email address.
- Generates a one-time UID + token using Django's `default_token_generator`.
- Sends an email with a reset link (console email in dev).
- **Always returns the same success message** regardless of whether the email exists (prevents email enumeration attacks).

**`ForgotPasswordConfirmView`** (`POST /api/auth/forgot-password/confirm/`)
- Accepts `uid`, `token`, `new_password`.
- Validates the token using `default_token_generator.check_token()`.
- Tokens are **single-use and expire** (Django invalidates them after the user's password changes).
- Sets the new password using `user.set_password()` which re-hashes it.

#### Customer Views

**`CustomerListCreateView`** (`GET/POST /api/customers/`)
- Requires authentication.
- `GET` — Returns paginated list with search (`?search=name`) and ordering (`?ordering=-created_at`).
- `POST` — Creates a new customer record.

**`CustomerDetailView`** (`GET/PUT/PATCH/DELETE /api/customers/<id>/`)
- Retrieve, update, or delete a single customer.

#### Inquiry Views

**`InquiryListCreateView`** (`GET/POST /api/inquiries/`)
- Requires authentication.
- Supports `MultiPartParser` and `FormParser` to accept **file uploads** alongside form data.
- `perform_create()` auto-attaches the logged-in user as `created_by`.

**`InquiryDetailView`** (`GET/PUT/PATCH/DELETE /api/inquiries/<id>/`)
- Full CRUD on a single inquiry.

---

### `accounts/urls.py`
Maps URL paths to view classes for all API routes. See [API Endpoints Reference](#5-api-endpoints-reference) below.

---

### `accounts/admin.py`
Registers all three models in Django's built-in admin panel at `/admin/`.

- `UserAdmin` — Extends the built-in admin with the custom `role` and `phone` fields.
- `CustomerAdmin` — List view with search on name/email, filter by source.
- `InquiryAdmin` — List view with filter on status/priority/type.

---

### `accounts/tokens.py`
Exports `password_reset_token = PasswordResetTokenGenerator()`.
Used to generate and validate one-time password reset tokens. Originally defined here; now views use Django's `default_token_generator` directly (this file is kept for backward compatibility).

---

## 5. API Endpoints Reference

All endpoints are prefixed with `/api/`.

### Authentication

| Method | Endpoint | Auth Required | Description |
|---|---|---|---|
| `POST` | `/api/auth/register/` | ❌ | Create a new user account |
| `POST` | `/api/auth/login/` | ❌ | Login (email or username), sets cookies |
| `POST` | `/api/auth/logout/` | ✅ | Clears auth cookies server-side |
| `GET` | `/api/auth/me/` | ✅ | Get current user's profile |
| `POST` | `/api/auth/token/refresh/` | ❌ | Refresh access token using refresh cookie |
| `POST` | `/api/auth/forgot-password/` | ❌ | Request a password reset link |
| `POST` | `/api/auth/forgot-password/confirm/` | ❌ | Confirm reset with UID + token |

### Customers

| Method | Endpoint | Auth Required | Description |
|---|---|---|---|
| `GET` | `/api/customers/` | ✅ | List all customers (supports `?search=`, `?ordering=`) |
| `POST` | `/api/customers/` | ✅ | Create a new customer |
| `GET` | `/api/customers/<id>/` | ✅ | Get a single customer |
| `PUT/PATCH` | `/api/customers/<id>/` | ✅ | Update a customer |
| `DELETE` | `/api/customers/<id>/` | ✅ | Delete a customer |

### Inquiries

| Method | Endpoint | Auth Required | Description |
|---|---|---|---|
| `GET` | `/api/inquiries/` | ✅ | List all inquiries (supports `?search=`, `?ordering=`) |
| `POST` | `/api/inquiries/` | ✅ | Create inquiry (supports multipart file upload) |
| `GET` | `/api/inquiries/<id>/` | ✅ | Get a single inquiry |
| `PUT/PATCH` | `/api/inquiries/<id>/` | ✅ | Update an inquiry |
| `DELETE` | `/api/inquiries/<id>/` | ✅ | Delete an inquiry |

---

## 6. Authentication Flow

```
[User] → POST /api/auth/login/ → [LoginView]
           ↓
    Lookup user by email OR username
           ↓
    django.authenticate() — verifies password hash
           ↓
    RefreshToken.for_user() — generate JWT pair
           ↓
    response.set_cookie("access_token", httponly=True)
    response.set_cookie("refresh_token", httponly=True)
           ↓
    Return { user: { id, name, email, role } }

[Later] → GET /api/auth/me/ → [simplejwt reads access_token cookie]
           ↓
    Returns user profile → Frontend restores Zustand session state
```

---

## 7. Database Models

```
User (AbstractUser)
 └─ role: admin | manager | sales
 └─ phone: optional

Customer
 └─ name, company_name, email (unique), phone, source, created_at

Inquiry
 └─ customer → Customer (FK)
 └─ created_by → User (FK)
 └─ inquiry_type, status, priority
 └─ product, quantity, terms, destination, inquiry_date
 └─ description, notes, comments
 └─ follow_up_date, follow_up_notes
 └─ document (FileField), document_description
 └─ created_at, updated_at
```

---

## 8. Security Implementation

| Concern | Implementation |
|---|---|
| **Password Storage** | Django's PBKDF2 hasher via `create_user()` — never plain text |
| **Token Storage** | HttpOnly cookies — inaccessible to JavaScript (XSS-safe) |
| **CORS** | Only `localhost:3000` allowed, credentials required |
| **Clickjacking** | `X_FRAME_OPTIONS = "DENY"` |
| **MIME Sniffing** | `SECURE_CONTENT_TYPE_NOSNIFF = True` |
| **Brute Force** | Rate limiting: 60 req/min (anon), 300 req/min (user) |
| **File Uploads** | MIME type + extension + size (max 5MB) validated server-side |
| **Email Enumeration** | Forgot password always returns same message |
| **Token Expiry** | Access: 1h, Refresh: 24h, single-use rotation |

---

## 9. Setup & Running Locally

### Prerequisites
- Python 3.11+
- PostgreSQL 14+ running locally
- A database named `emarys_db` (or configure via `.env`)

### Steps

```bash
# 1. Clone the repo
git clone <backend-repo-url>
cd emarys_backend

# 2. Create and activate virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create your .env file (see Environment Variables section)
cp .env.example .env   # edit the values

# 5. Run migrations
python manage.py makemigrations
python manage.py migrate

# 6. Create a superuser (for admin panel access)
python manage.py createsuperuser

# 7. Start the server
python manage.py runserver
# API is now available at: http://127.0.0.1:8000
# Admin panel: http://127.0.0.1:8000/admin
```

---

## 10. Environment Variables

Create a `.env` file in the `emarys_backend/` root (same level as `manage.py`):

```env
# Database
DB_NAME=emarys_db
DB_USER=postgres
DB_PASSWORD=your_db_password
DB_HOST=127.0.0.1
DB_PORT=5432

# Django
SECRET_KEY=your-very-long-random-secret-key-here
DEBUG=1

# CORS (comma-separated, no spaces)
ALLOWED_HOSTS=127.0.0.1,localhost
CORS_ALLOWED_ORIGINS=http://localhost:3000
```

> ⚠️ **Never commit `.env` to git.** It is listed in `.gitignore`.

---

## 11. Next Steps for Developers

### High Priority
- [ ] **Re-enable password validators** in `settings.py` before production
- [ ] **Enable HTTPS security headers** (HSTS, Secure cookies) — commented lines in `settings.py`
- [ ] **Email configuration** — Replace `console.EmailBackend` with real SMTP (SendGrid, SES)
- [ ] **Role-based permissions** — Currently all authenticated users can access all endpoints. Add `IsAdminUser` or custom permission classes based on `user.role`

### Features to Build
- [ ] `Quotation` model and CRUD API
- [ ] `Indent` / `Order` tracking model
- [ ] Search/filter improvements (DRF `django-filter` integration)
- [ ] Pagination configuration (currently DRF default)
- [ ] Audit trail (who changed what, when)
- [ ] File storage migration to S3/Cloudflare R2 for production (replace `FileField` with `django-storages`)

### Testing
- [ ] Write unit tests in `accounts/tests.py`
- [ ] Test all auth flows (valid/invalid credentials, expired tokens, etc.)
- [ ] Test file upload validation (oversized files, wrong types)
