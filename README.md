# Organization Management Service

A multi-tenant backend service built with **FastAPI** and **MongoDB** for managing organizations with dynamic collection creation.

## 🏗️ Architecture Overview

\`\`\`
┌─────────────────────────────────────────────────────────────────┐
│                        FastAPI Application                       │
├─────────────────────────────────────────────────────────────────┤
│  Routes Layer                                                    │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │POST /org │ │GET /org  │ │PUT /org  │ │DELETE    │           │
│  │/create   │ │/get      │ │/update   │ │/org/del  │           │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘           │
│       │            │            │            │                   │
│  ┌────▼────────────▼────────────▼────────────▼─────┐            │
│  │           Service Layer (Business Logic)         │            │
│  │  ┌─────────────────────┐ ┌──────────────────┐   │            │
│  │  │ OrganizationService │ │   AuthService    │   │            │
│  │  └─────────────────────┘ └──────────────────┘   │            │
│  └──────────────────────────┬──────────────────────┘            │
│                             │                                    │
│  ┌──────────────────────────▼──────────────────────┐            │
│  │              Database Layer (MongoDB)            │            │
│  │  ┌─────────────────────────────────────────────┐│            │
│  │  │              Master Database                ││            │
│  │  │  ┌─────────────┐  ┌─────────────────────┐  ││            │
│  │  │  │organizations│  │      admins         │  ││            │
│  │  │  │ collection  │  │    collection       │  ││            │
│  │  │  └─────────────┘  └─────────────────────┘  ││            │
│  │  └─────────────────────────────────────────────┘│            │
│  │  ┌─────────────────────────────────────────────┐│            │
│  │  │         Dynamic Org Collections             ││            │
│  │  │  ┌───────────┐ ┌───────────┐ ┌───────────┐ ││            │
│  │  │  │org_acme   │ │org_globex │ │org_initech│ ││            │
│  │  │  └───────────┘ └───────────┘ └───────────┘ ││            │
│  │  └─────────────────────────────────────────────┘│            │
│  └──────────────────────────────────────────────────┘            │
└─────────────────────────────────────────────────────────────────┘
\`\`\`

## 🚀 Tech Stack

| Component | Technology |
|-----------|------------|
| Framework | FastAPI (Python 3.9+) |
| Database | MongoDB with Motor (async driver) |
| Authentication | JWT (PyJWT) |
| Password Hashing | bcrypt via Passlib |
| Validation | Pydantic v2 |
| API Documentation | Swagger UI / ReDoc |

## 📋 Features Implemented

- ✅ **Create Organization** - Creates org with admin user and dynamic collection
- ✅ **Get Organization** - Fetch organization details by name
- ✅ **Update Organization** - Update org with data migration support
- ✅ **Delete Organization** - Delete org and all associated data
- ✅ **Admin Login** - JWT-based authentication
- ✅ **Password Security** - bcrypt hashing
- ✅ **Multi-tenant Collections** - Dynamic collection per organization
- ✅ **Input Validation** - Pydantic schemas
- ✅ **Error Handling** - HTTP exceptions with proper status codes

## 🛠️ Setup Instructions

### Prerequisites

- Python 3.9+
- MongoDB (local or Atlas)
- pip (Python package manager)

### Installation

1. **Clone the repository**
   \`\`\`bash
   git clone <repository-url>
   cd organization-management-service
   \`\`\`

2. **Create virtual environment**
   \`\`\`bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   \`\`\`

3. **Install dependencies**
   \`\`\`bash
   pip install -r scripts/requirements.txt
   \`\`\`

4. **Set environment variables**
   \`\`\`bash
   export MONGODB_URI="mongodb://localhost:27017"
   export JWT_SECRET="your-super-secret-key"
   \`\`\`

5. **Run the application**
   \`\`\`bash
   cd scripts
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   \`\`\`

6. **Access the API**
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

## 📚 API Endpoints

### Organization Management

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/org/create` | Create new organization | No |
| GET | `/org/get?organization_name=<name>` | Get organization details | No |
| PUT | `/org/update?organization_name=<name>` | Update organization | Yes (JWT) |
| DELETE | `/org/delete?organization_name=<name>` | Delete organization | Yes (JWT) |

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/admin/login` | Admin login, returns JWT |

## 📝 API Usage Examples

### 1. Create Organization
\`\`\`bash
curl -X POST "http://localhost:8000/org/create" \
  -H "Content-Type: application/json" \
  -d '{
    "organization_name": "Acme Corp",
    "email": "admin@acme.com",
    "password": "securePassword123"
  }'
\`\`\`

### 2. Admin Login
\`\`\`bash
curl -X POST "http://localhost:8000/admin/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@acme.com",
    "password": "securePassword123"
  }'
\`\`\`

### 3. Get Organization
\`\`\`bash
curl -X GET "http://localhost:8000/org/get?organization_name=Acme%20Corp"
\`\`\`

### 4. Update Organization (Authenticated)
\`\`\`bash
curl -X PUT "http://localhost:8000/org/update?organization_name=Acme%20Corp" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your-jwt-token>" \
  -d '{
    "organization_name": "Acme Corporation",
    "email": "admin@acme.com",
    "password": "newSecurePassword123"
  }'
\`\`\`

### 5. Delete Organization (Authenticated)
\`\`\`bash
curl -X DELETE "http://localhost:8000/org/delete?organization_name=Acme%20Corp" \
  -H "Authorization: Bearer <your-jwt-token>"
\`\`\`

## 🔐 Security Features

- **Password Hashing**: All passwords are hashed using bcrypt
- **JWT Authentication**: Secure token-based authentication
- **Authorization**: Only org admins can update/delete their organizations
- **Input Validation**: Pydantic models validate all inputs

## ⏱️ Time Spent

- Architecture Design: ~1 hour
- Core Implementation: ~2 hours
- Documentation: ~30 minutes
- **Total: ~3.5 hours**

## 🤔 Design Considerations & Trade-offs

### Current Architecture Pros
- **Simplicity**: Single database with dynamic collections is easy to manage
- **Flexibility**: MongoDB's schema-less nature allows for varied org data
- **Performance**: Collections in same DB reduce connection overhead

### Potential Trade-offs
1. **Single Database Limitation**: All orgs share one DB instance
   - *Solution*: For true multi-tenancy at scale, consider separate databases per org

2. **Collection Naming**: Using org names in collection names could cause issues
   - *Solution*: Use UUIDs or org IDs for collection names

3. **No Rate Limiting**: Current implementation lacks rate limiting
   - *Solution*: Add Redis-based rate limiting for production

### Suggested Improvements for Scale
- Implement database-per-tenant for complete isolation
- Add connection pooling with Redis caching
- Implement async task queues for heavy operations
- Add comprehensive logging and monitoring
- Consider using Kubernetes for horizontal scaling

## 📁 Project Structure

\`\`\`
├── scripts/
│   ├── main.py              # FastAPI application
│   └── requirements.txt     # Python dependencies
├── README.md                # This file
└── .gitignore               # Git ignore file
\`\`\`

## 📄 License

MIT License
