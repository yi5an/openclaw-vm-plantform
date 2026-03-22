# OpenClaw VM Platform Backend

FastAPI-based backend for OpenClaw VM Platform.

## Tech Stack

- **Python 3.11+**
- **FastAPI** - Modern async web framework
- **SQLAlchemy 2.0** - ORM with async support
- **PostgreSQL** - Relational database
- **Redis** - Caching and session management
- **Libvirt** - KVM virtualization management

## Project Structure

```
backend/
├── app/
│   ├── api/                # API layer (adapters)
│   │   ├── v1/            # API version 1
│   │   │   ├── auth.py    # Authentication endpoints
│   │   │   ├── users.py   # User management
│   │   │   └── vms.py     # VM management
│   │   └── deps.py        # Dependencies
│   │
│   ├── core/              # Application core
│   │   ├── config.py      # Configuration
│   │   ├── security.py    # Security utilities
│   │   └── exceptions.py  # Exception definitions
│   │
│   ├── infrastructure/    # Infrastructure layer
│   │   ├── database/      # Database models and repositories
│   │   ├── cache/         # Redis client
│   │   └── vm/            # Libvirt integration
│   │
│   └── main.py            # FastAPI application
│
├── tests/                 # Test suite
├── alembic/              # Database migrations
├── requirements.txt      # Python dependencies
└── .env.example         # Environment variables template
```

## Quick Start

### 1. Install Dependencies

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your configuration
```

### 3. Setup Database

```bash
# Create PostgreSQL database
createdb openclaw

# Run migrations (when implemented)
alembic upgrade head
```

### 4. Run Development Server

```bash
uvicorn app.main:app --reload
```

API will be available at:
- API: http://localhost:8000
- Documentation: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login and get tokens
- `POST /api/v1/auth/refresh` - Refresh access token

### Users
- `GET /api/v1/users/me` - Get current user info
- `PATCH /api/v1/users/me` - Update user info
- `POST /api/v1/users/me/recharge` - Recharge balance

### Virtual Machines
- `GET /api/v1/vms/plans` - List available plans
- `POST /api/v1/vms` - Create new VM
- `GET /api/v1/vms` - List user's VMs
- `GET /api/v1/vms/{vm_id}` - Get VM details
- `POST /api/v1/vms/{vm_id}/start` - Start VM
- `POST /api/v1/vms/{vm_id}/stop` - Stop VM
- `DELETE /api/v1/vms/{vm_id}` - Delete VM
- `POST /api/v1/vms/{vm_id}/renew` - Renew VM subscription

## Development

### Run Tests

```bash
pytest
```

### Code Formatting

```bash
black app/
flake8 app/
mypy app/
```

## Architecture

This project follows **Hexagonal Architecture** (Ports and Adapters):

- **API Layer**: FastAPI routes and request/response handling
- **Core Layer**: Business logic and domain models
- **Infrastructure Layer**: External integrations (DB, Redis, Libvirt)

## TODO

- [ ] Implement Agent management API
- [ ] Implement Channel configuration API
- [ ] Implement Billing and Token usage tracking
- [ ] Integrate Libvirt for actual VM operations
- [ ] Implement SSH deployment automation
- [ ] Add rate limiting middleware
- [ ] Add API versioning
- [ ] Write comprehensive tests
- [ ] Setup CI/CD pipeline

## License

MIT
