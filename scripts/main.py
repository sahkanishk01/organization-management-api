"""
Organization Management Service - FastAPI Backend
A multi-tenant architecture backend service for managing organizations
"""

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext
import jwt
import os
from bson import ObjectId

# =============================================================================
# Configuration
# =============================================================================

MONGO_URL = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DATABASE_NAME = "master_db"
JWT_SECRET = os.getenv("JWT_SECRET", "your-super-secret-jwt-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# =============================================================================
# FastAPI App Initialization
# =============================================================================

app = FastAPI(
    title="Organization Management Service",
    description="Multi-tenant backend service for managing organizations",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# Security & Authentication
# =============================================================================

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

class PasswordHandler:
    """Handles password hashing and verification"""
    
    @staticmethod
    def hash_password(password: str) -> str:
        return pwd_context.hash(password)
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

class JWTHandler:
    """Handles JWT token creation and verification"""
    
    @staticmethod
    def create_token(admin_id: str, org_id: str, org_name: str) -> str:
        payload = {
            "admin_id": admin_id,
            "org_id": org_id,
            "org_name": org_name,
            "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
            "iat": datetime.utcnow()
        }
        return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    
    @staticmethod
    def decode_token(token: str) -> dict:
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token has expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")

# =============================================================================
# Database Connection
# =============================================================================

class Database:
    """MongoDB Database Connection Manager"""
    client: AsyncIOMotorClient = None
    
    @classmethod
    async def connect(cls):
        cls.client = AsyncIOMotorClient(MONGO_URL)
        print("✅ Connected to MongoDB")
    
    @classmethod
    async def disconnect(cls):
        if cls.client:
            cls.client.close()
            print("❌ Disconnected from MongoDB")
    
    @classmethod
    def get_master_db(cls):
        return cls.client[DATABASE_NAME]
    
    @classmethod
    def get_org_collection(cls, org_name: str):
        """Get or create organization-specific collection"""
        collection_name = f"org_{org_name.lower().replace(' ', '_')}"
        return cls.client[DATABASE_NAME][collection_name]

# =============================================================================
# Pydantic Models (Request/Response Schemas)
# =============================================================================

class OrganizationCreate(BaseModel):
    organization_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=6)

class OrganizationUpdate(BaseModel):
    organization_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=6)

class OrganizationResponse(BaseModel):
    id: str
    organization_name: str
    collection_name: str
    admin_email: str
    created_at: datetime
    updated_at: Optional[datetime] = None

class AdminLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    org_name: str
    admin_email: str

class MessageResponse(BaseModel):
    message: str
    success: bool = True

# =============================================================================
# Dependency Injection
# =============================================================================

async def get_current_admin(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Dependency to get current authenticated admin from JWT token"""
    token = credentials.credentials
    payload = JWTHandler.decode_token(token)
    return payload

# =============================================================================
# Organization Service (Business Logic)
# =============================================================================

class OrganizationService:
    """Service class for organization management operations"""
    
    @staticmethod
    async def create_organization(data: OrganizationCreate) -> dict:
        db = Database.get_master_db()
        organizations = db["organizations"]
        admins = db["admins"]
        
        # Check if organization already exists
        existing_org = await organizations.find_one({"organization_name": data.organization_name})
        if existing_org:
            raise HTTPException(
                status_code=400, 
                detail="Organization with this name already exists"
            )
        
        # Check if admin email already exists
        existing_admin = await admins.find_one({"email": data.email})
        if existing_admin:
            raise HTTPException(
                status_code=400, 
                detail="Admin with this email already exists"
            )
        
        # Create collection name
        collection_name = f"org_{data.organization_name.lower().replace(' ', '_')}"
        
        # Create admin user
        admin_doc = {
            "email": data.email,
            "password_hash": PasswordHandler.hash_password(data.password),
            "created_at": datetime.utcnow()
        }
        admin_result = await admins.insert_one(admin_doc)
        admin_id = str(admin_result.inserted_id)
        
        # Create organization
        org_doc = {
            "organization_name": data.organization_name,
            "collection_name": collection_name,
            "admin_id": admin_id,
            "admin_email": data.email,
            "created_at": datetime.utcnow(),
            "updated_at": None
        }
        org_result = await organizations.insert_one(org_doc)
        
        # Create dynamic collection for the organization
        org_collection = Database.get_org_collection(data.organization_name)
        
        # Initialize collection with a metadata document
        await org_collection.insert_one({
            "_type": "metadata",
            "organization_name": data.organization_name,
            "initialized_at": datetime.utcnow(),
            "schema_version": "1.0"
        })
        
        return {
            "id": str(org_result.inserted_id),
            "organization_name": data.organization_name,
            "collection_name": collection_name,
            "admin_email": data.email,
            "created_at": org_doc["created_at"],
            "updated_at": None
        }
    
    @staticmethod
    async def get_organization(org_name: str) -> dict:
        db = Database.get_master_db()
        organizations = db["organizations"]
        
        org = await organizations.find_one({"organization_name": org_name})
        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")
        
        return {
            "id": str(org["_id"]),
            "organization_name": org["organization_name"],
            "collection_name": org["collection_name"],
            "admin_email": org["admin_email"],
            "created_at": org["created_at"],
            "updated_at": org.get("updated_at")
        }
    
    @staticmethod
    async def update_organization(old_name: str, data: OrganizationUpdate, admin_payload: dict) -> dict:
        db = Database.get_master_db()
        organizations = db["organizations"]
        admins = db["admins"]
        
        # Verify the admin owns this organization
        if admin_payload["org_name"] != old_name:
            raise HTTPException(status_code=403, detail="Not authorized to update this organization")
        
        # Get current organization
        org = await organizations.find_one({"organization_name": old_name})
        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")
        
        # Check if new name already exists (if name is being changed)
        if data.organization_name != old_name:
            existing = await organizations.find_one({"organization_name": data.organization_name})
            if existing:
                raise HTTPException(status_code=400, detail="Organization with this name already exists")
        
        # Create new collection name
        new_collection_name = f"org_{data.organization_name.lower().replace(' ', '_')}"
        old_collection_name = org["collection_name"]
        
        # If organization name changed, migrate data to new collection
        if data.organization_name != old_name:
            old_collection = db[old_collection_name]
            new_collection = db[new_collection_name]
            
            # Copy all documents from old to new collection
            async for doc in old_collection.find():
                doc.pop("_id", None)
                if doc.get("_type") == "metadata":
                    doc["organization_name"] = data.organization_name
                await new_collection.insert_one(doc)
            
            # Drop old collection
            await old_collection.drop()
        
        # Update admin credentials
        await admins.update_one(
            {"_id": ObjectId(org["admin_id"])},
            {"$set": {
                "email": data.email,
                "password_hash": PasswordHandler.hash_password(data.password),
                "updated_at": datetime.utcnow()
            }}
        )
        
        # Update organization
        update_data = {
            "organization_name": data.organization_name,
            "collection_name": new_collection_name,
            "admin_email": data.email,
            "updated_at": datetime.utcnow()
        }
        await organizations.update_one(
            {"_id": org["_id"]},
            {"$set": update_data}
        )
        
        return {
            "id": str(org["_id"]),
            "organization_name": data.organization_name,
            "collection_name": new_collection_name,
            "admin_email": data.email,
            "created_at": org["created_at"],
            "updated_at": update_data["updated_at"]
        }
    
    @staticmethod
    async def delete_organization(org_name: str, admin_payload: dict) -> dict:
        db = Database.get_master_db()
        organizations = db["organizations"]
        admins = db["admins"]
        
        # Verify the admin owns this organization
        if admin_payload["org_name"] != org_name:
            raise HTTPException(status_code=403, detail="Not authorized to delete this organization")
        
        # Get organization
        org = await organizations.find_one({"organization_name": org_name})
        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")
        
        # Delete organization collection
        org_collection = db[org["collection_name"]]
        await org_collection.drop()
        
        # Delete admin
        await admins.delete_one({"_id": ObjectId(org["admin_id"])})
        
        # Delete organization from master db
        await organizations.delete_one({"_id": org["_id"]})
        
        return {"message": f"Organization '{org_name}' deleted successfully", "success": True}

# =============================================================================
# Authentication Service
# =============================================================================

class AuthService:
    """Service class for authentication operations"""
    
    @staticmethod
    async def login(data: AdminLogin) -> dict:
        db = Database.get_master_db()
        admins = db["admins"]
        organizations = db["organizations"]
        
        # Find admin by email
        admin = await admins.find_one({"email": data.email})
        if not admin:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Verify password
        if not PasswordHandler.verify_password(data.password, admin["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Get organization for this admin
        org = await organizations.find_one({"admin_id": str(admin["_id"])})
        if not org:
            raise HTTPException(status_code=404, detail="Organization not found for this admin")
        
        # Generate JWT token
        token = JWTHandler.create_token(
            admin_id=str(admin["_id"]),
            org_id=str(org["_id"]),
            org_name=org["organization_name"]
        )
        
        return {
            "access_token": token,
            "token_type": "bearer",
            "org_name": org["organization_name"],
            "admin_email": data.email
        }

# =============================================================================
# API Routes
# =============================================================================

@app.on_event("startup")
async def startup():
    await Database.connect()

@app.on_event("shutdown")
async def shutdown():
    await Database.disconnect()

@app.get("/", tags=["Health"])
async def root():
    """Health check endpoint"""
    return {"status": "healthy", "service": "Organization Management Service"}

# Organization Routes
@app.post("/org/create", response_model=OrganizationResponse, tags=["Organization"])
async def create_organization(data: OrganizationCreate):
    """
    Create a new organization with admin user.
    
    - Creates organization entry in master database
    - Creates dedicated collection for the organization
    - Creates admin user with hashed password
    """
    return await OrganizationService.create_organization(data)

@app.get("/org/get", response_model=OrganizationResponse, tags=["Organization"])
async def get_organization(organization_name: str):
    """
    Get organization details by name.
    
    Returns organization metadata from master database.
    """
    return await OrganizationService.get_organization(organization_name)

@app.put("/org/update", response_model=OrganizationResponse, tags=["Organization"])
async def update_organization(
    organization_name: str,
    data: OrganizationUpdate,
    admin: dict = Depends(get_current_admin)
):
    """
    Update organization details.
    
    - Requires authentication (JWT token)
    - Only the organization's admin can update it
    - Handles collection migration if name changes
    """
    return await OrganizationService.update_organization(organization_name, data, admin)

@app.delete("/org/delete", response_model=MessageResponse, tags=["Organization"])
async def delete_organization(
    organization_name: str,
    admin: dict = Depends(get_current_admin)
):
    """
    Delete an organization.
    
    - Requires authentication (JWT token)
    - Only the organization's admin can delete it
    - Removes organization collection and all data
    """
    return await OrganizationService.delete_organization(organization_name, admin)

# Authentication Routes
@app.post("/admin/login", response_model=TokenResponse, tags=["Authentication"])
async def admin_login(data: AdminLogin):
    """
    Admin login endpoint.
    
    - Validates credentials
    - Returns JWT token containing admin and organization info
    """
    return await AuthService.login(data)

# =============================================================================
# Run the application
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
