# POSightful Backend

Django REST API for the POSightful multi-tenant lead tracking and ROI management system.

## Features

- Multi-tenant architecture with tenant isolation
- Lead capture and management system
- Conversion tracking with external system integration
- Configurable bonus calculation engine
- Daily KPI analytics for agents and outlets
- RESTful API with JWT authentication

## Tech Stack

- Python 3.x
- Django 5.x
- Django REST Framework
- PostgreSQL
- JWT Authentication
- CORS support for Angular frontend

## Project Structure

```
backend/
├── posightful/          # Main project settings
├── tenancy/             # Multi-tenant, users, agents, outlets
├── leads/               # Lead capture and campaigns
├── conversions/         # Sales conversions and external imports
├── bonuses/             # Bonus calculation engine
├── analytics/           # KPI and reporting models
└── manage.py
```

## Setup Instructions

### 1. Create Virtual Environment

```bash
python -m venv venv
```

### 2. Activate Virtual Environment

Windows:
```bash
venv\Scripts\activate
```

Linux/Mac:
```bash
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Database

Create a PostgreSQL database and update the `.env` file:

```bash
cp .env.example .env
```

Edit `.env` with your database credentials:

```
DB_NAME=posightful_db
DB_USER=postgres
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432
```

### 5. Run Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### 6. Create Superuser

```bash
python manage.py createsuperuser
```

You will be prompted to enter:
- **Username**: Required (used for login)
- **Email**: Required
- **Phone number**: Required (format: +998XXXXXXXXX or 998XXXXXXXXX)
- **Password**: Required

Example:
```
Username: admin
Email address: admin@example.com
Phone number: +998901234567
Password: ********
Password (again): ********
```

Note: Superusers are created without a tenant assignment.

### 7. Run Development Server

```bash
python manage.py runserver
```

The API will be available at `http://localhost:8000`

## API Documentation

After running the server, access:
- **Admin Panel**: `http://localhost:8000/admin`
- **Swagger UI**: `http://localhost:8000/swagger/`
- **ReDoc**: `http://localhost:8000/redoc/`
- **API Root**: `http://localhost:8000/api/` (to be implemented)

### Authentication Endpoints

Base URL: `http://127.0.0.1:8000/auth/`

- **Register**: `POST /auth/register/`
  - Create a new user account
  - Required fields: `username`, `email`, `phone_number`, `password`, `password2`
  - Optional fields: `full_name`, `tenant`
  - Returns user data and JWT tokens

- **Login**: `POST /auth/login/`
  - Login with username and password
  - Required fields: `username`, `password`
  - Returns user data and JWT tokens (access and refresh)

- **Logout**: `POST /auth/logout/`
  - Logout and blacklist refresh token
  - Requires authentication
  - Required field: `refresh_token`

- **Token Refresh**: `POST /auth/token/refresh/`
  - Refresh access token using refresh token
  - Required field: `refresh`
  - Returns new access token

- **Profile**: `GET /auth/profile/`
  - Get current authenticated user's profile
  - Requires authentication

- **Change Password**: `POST /auth/change-password/`
  - Change user password
  - Requires authentication
  - Required fields: `old_password`, `new_password`, `new_password2`

### Using JWT Authentication

To access protected endpoints, include the access token in the Authorization header:

```
Authorization: Bearer <your_access_token>
```

Example using curl:
```bash
curl -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc..." http://127.0.0.1:8000/auth/profile/
```

Access tokens expire after 1 hour. Use the refresh token endpoint to get a new access token without logging in again.

## Database Models

### Users Module
- **User**: Custom user model with username, email, and phone authentication
  - USERNAME_FIELD: `username`
  - REQUIRED_FIELDS: `email`, `phone_number`
  - Optional fields: `full_name`, `tenant`, `user_role`
- **UserRole**: User roles and permissions

### Tenancy Module
- **Tenant**: Organization entities
- **Region**: Geographic regions
- **Outlet**: Sales outlets/stores
- **Agent**: Sales agents

### Leads Module
- **Campaign**: Marketing campaigns
- **AttributionSource**: Lead sources
- **Lead**: Customer leads with tracking
- **LeadInteraction**: Agent-lead interactions
- **LeadStatusHistory**: Audit trail

### Conversions Module
- **Conversion**: Successful sales
- **ExternalImportBatch**: Import tracking
- **ExternalSalesImport**: External sales data
- **LedgerEntry**: Financial ledger

### Bonuses Module
- **BonusRuleSet**: Rule collections
- **BonusRule**: Calculation rules
- **BonusCalculationRun**: Calculation executions
- **BonusCalculationItem**: Individual bonuses
- **BonusPayoutExport**: Export records

### Analytics Module
- **KPIAgentDaily**: Agent performance metrics
- **KPIOutletDaily**: Outlet performance metrics

## Development Notes

- Custom user model with username as USERNAME_FIELD
  - Login with username
  - Email and phone number are required fields
  - Phone number format: +998XXXXXXXXX (Uzbekistan)
  - Tenant field is optional (null for superusers)
- All tenant-related models support multi-tenancy through tenant_id
- UUID used for lead deduplication from mobile devices
- PostgreSQL required for proper decimal and interval field support

## User Authentication

The system uses a custom User model with the following authentication setup:
- **Login Field**: Username
- **Required Fields**: Username, Email, Phone Number, Password
- **Optional Fields**: Full Name, Tenant, User Role
- **Phone Validation**: Must match pattern `^(\+998|998)\d{9}$`
- **Superusers**: Created without tenant assignment for system-wide access
