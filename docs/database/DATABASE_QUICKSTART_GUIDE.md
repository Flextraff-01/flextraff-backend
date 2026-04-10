# FLEXTRAFF DATABASE - QUICK START IMPLEMENTATION GUIDE

## Prerequisites
- PostgreSQL 14+ (Supabase)
- Python 3.9+
- FastAPI
- asyncpg (async PostgreSQL driver)

---

## Step 1: Database Setup

### 1.1 Create Database on Supabase
```bash
# Log into Supabase dashboard
# Create new project: "flextraff"
# Note down the connection string
```

### 1.2 Run Schema Migration
```bash
# Download the schema file
# Connect via psql or Supabase SQL Editor
psql "postgresql://user:pass@host:5432/flextraff" -f flextraff_database_schema.sql
```

### 1.3 Verify Installation
```sql
-- Check all tables created
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public';

-- Should return: users, junctions, lanes, edge_devices, etc.
```

---

## Step 2: Python Backend Setup

### 2.1 Install Dependencies
```bash
pip install fastapi uvicorn asyncpg databases python-jose[cryptography] passlib[bcrypt] python-multipart pydantic-settings aiomqtt
```

### 2.2 Create `.env` Configuration
```bash
# .env
DATABASE_URL=postgresql://user:pass@host:5432/flextraff
SECRET_KEY=your-secret-key-here-change-this-in-production
MQTT_BROKER_HOST=localhost
MQTT_BROKER_PORT=1883
MQTT_USERNAME=flextraff
MQTT_PASSWORD=secure_password
```

### 2.3 Database Connection (`database.py`)
```python
# database.py
from databases import Database
from sqlalchemy import MetaData
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Create database instance
database = Database(DATABASE_URL)
metadata = MetaData()

async def connect_db():
    """Connect to database on startup"""
    await database.connect()
    print("✅ Database connected")

async def disconnect_db():
    """Disconnect from database on shutdown"""
    await database.disconnect()
    print("❌ Database disconnected")
```

### 2.4 Models (`models.py`)
```python
# models.py
from pydantic import BaseModel, EmailStr, UUID4
from typing import Optional, List
from datetime import datetime
from enum import Enum

# Enums
class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"

class JunctionStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"
    ERROR = "error"

class JunctionMode(str, Enum):
    AUTOMATIC = "automatic"
    MANUAL_OVERRIDE = "manual_override"
    EMERGENCY = "emergency"

class DeviceType(str, Enum):
    RFID_COUNTER = "rfid_counter"
    LIGHT_CONTROLLER = "light_controller"

# Pydantic Models
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    is_admin: bool = False

class UserResponse(BaseModel):
    user_id: UUID4
    username: str
    email: EmailStr
    full_name: Optional[str]
    is_admin: bool
    is_active: bool
    created_at: datetime

class JunctionCreate(BaseModel):
    junction_name: str
    city: str
    latitude: float
    longitude: float
    min_cycle_time: int = 30
    max_cycle_time: int = 120
    base_cycle_time: int = 60

class JunctionResponse(BaseModel):
    junction_id: UUID4
    junction_name: str
    city: str
    latitude: float
    longitude: float
    status: JunctionStatus
    current_mode: JunctionMode
    min_cycle_time: int
    max_cycle_time: int
    base_cycle_time: int
    created_at: datetime

class ManualOverrideRequest(BaseModel):
    total_cycle_time: int
    north_lane_time: int
    south_lane_time: int
    east_lane_time: int
    west_lane_time: Optional[int] = None  # Auto-calculated
    reason: Optional[str] = None

class CarCountData(BaseModel):
    junction_id: UUID4
    lane_id: UUID4
    vehicle_count: int
    epc_ids: List[str]  # Array of FASTag EPC identifiers
    timestamp: datetime

class GreenTimeData(BaseModel):
    junction_id: UUID4
    lane_times: List[int]  # [N, S, E, W]
    total_cycle_time: int
    timestamp: datetime
```

### 2.5 Authentication (`auth.py`)
```python
# auth.py
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import os

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    """Get current user from JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    # Fetch user from database
    from database import database
    query = "SELECT * FROM users WHERE username = :username AND is_active = TRUE"
    user = await database.fetch_one(query=query, values={"username": username})
    
    if user is None:
        raise credentials_exception
    
    return dict(user)

async def get_current_admin_user(current_user: dict = Depends(get_current_user)):
    """Ensure current user is admin"""
    if not current_user['is_admin']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough privileges"
        )
    return current_user
```

### 2.6 User Routes (`routes/users.py`)
```python
# routes/users.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from models import UserCreate, UserResponse
from auth import (
    get_password_hash, 
    verify_password, 
    create_access_token, 
    get_current_user,
    get_current_admin_user,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from database import database
from datetime import timedelta
from typing import List

router = APIRouter(prefix="/api/users", tags=["users"])

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(user: UserCreate):
    """Register a new user (admin only in production)"""
    
    # Check if username/email already exists
    check_query = """
        SELECT user_id FROM users 
        WHERE username = :username OR email = :email
    """
    existing = await database.fetch_one(
        query=check_query, 
        values={"username": user.username, "email": user.email}
    )
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already registered"
        )
    
    # Hash password
    hashed_password = get_password_hash(user.password)
    
    # Insert user
    insert_query = """
        INSERT INTO users (username, email, password_hash, full_name, is_admin)
        VALUES (:username, :email, :password_hash, :full_name, :is_admin)
        RETURNING *
    """
    
    new_user = await database.fetch_one(
        query=insert_query,
        values={
            "username": user.username,
            "email": user.email,
            "password_hash": hashed_password,
            "full_name": user.full_name,
            "is_admin": user.is_admin
        }
    )
    
    return dict(new_user)

@router.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Login and get access token"""
    
    # Fetch user
    query = "SELECT * FROM users WHERE username = :username"
    user = await database.fetch_one(query=query, values={"username": form_data.username})
    
    if not user or not verify_password(form_data.password, user['password_hash']):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user['is_active']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    # Update last_login
    await database.execute(
        query="UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE user_id = :user_id",
        values={"user_id": user['user_id']}
    )
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user['username']}, 
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Get current user information"""
    return current_user

@router.get("/", response_model=List[UserResponse])
async def list_users(current_user: dict = Depends(get_current_admin_user)):
    """List all users (admin only)"""
    query = "SELECT * FROM users ORDER BY created_at DESC"
    users = await database.fetch_all(query=query)
    return [dict(user) for user in users]
```

### 2.7 Junction Routes (`routes/junctions.py`)
```python
# routes/junctions.py
from fastapi import APIRouter, Depends, HTTPException, status
from models import JunctionCreate, JunctionResponse, ManualOverrideRequest
from auth import get_current_user, get_current_admin_user
from database import database
from typing import List
import uuid

router = APIRouter(prefix="/api/junctions", tags=["junctions"])

@router.post("/", response_model=JunctionResponse, status_code=status.HTTP_201_CREATED)
async def create_junction(
    junction: JunctionCreate, 
    current_user: dict = Depends(get_current_admin_user)
):
    """Create a new junction (admin only)"""
    
    insert_query = """
        INSERT INTO junctions (junction_name, city, latitude, longitude, 
                               min_cycle_time, max_cycle_time, base_cycle_time)
        VALUES (:junction_name, :city, :latitude, :longitude,
                :min_cycle_time, :max_cycle_time, :base_cycle_time)
        RETURNING *
    """
    
    new_junction = await database.fetch_one(
        query=insert_query,
        values=junction.dict()
    )
    
    # Create 4 lanes for this junction
    junction_id = new_junction['junction_id']
    lanes = [
        ("North", 1, "N"),
        ("South", 2, "S"),
        ("East", 3, "E"),
        ("West", 4, "W")
    ]
    
    for lane_name, lane_index, direction in lanes:
        await database.execute(
            query="""
                INSERT INTO lanes (junction_id, lane_index, lane_name, direction_enum)
                VALUES (:junction_id, :lane_index, :lane_name, :direction_enum)
            """,
            values={
                "junction_id": junction_id,
                "lane_index": lane_index,
                "lane_name": lane_name,
                "direction_enum": direction
            }
        )
    
    return dict(new_junction)

@router.get("/", response_model=List[JunctionResponse])
async def list_junctions(current_user: dict = Depends(get_current_user)):
    """List junctions user has access to"""
    
    if current_user['is_admin']:
        # Admin sees all junctions
        query = "SELECT * FROM junctions ORDER BY junction_name"
        junctions = await database.fetch_all(query=query)
    else:
        # Regular user sees only assigned junctions
        query = """
            SELECT j.* FROM junctions j
            JOIN user_junction_access uja ON j.junction_id = uja.junction_id
            WHERE uja.user_id = :user_id
            ORDER BY j.junction_name
        """
        junctions = await database.fetch_all(
            query=query, 
            values={"user_id": current_user['user_id']}
        )
    
    return [dict(j) for j in junctions]

@router.get("/{junction_id}", response_model=JunctionResponse)
async def get_junction(junction_id: uuid.UUID, current_user: dict = Depends(get_current_user)):
    """Get junction details"""
    
    # Check access
    if not current_user['is_admin']:
        access_query = """
            SELECT 1 FROM user_junction_access 
            WHERE user_id = :user_id AND junction_id = :junction_id
        """
        has_access = await database.fetch_one(
            query=access_query,
            values={"user_id": current_user['user_id'], "junction_id": junction_id}
        )
        
        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No access to this junction"
            )
    
    # Fetch junction
    query = "SELECT * FROM junctions WHERE junction_id = :junction_id"
    junction = await database.fetch_one(query=query, values={"junction_id": junction_id})
    
    if not junction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Junction not found"
        )
    
    return dict(junction)

@router.put("/{junction_id}/mode")
async def set_junction_mode(
    junction_id: uuid.UUID,
    override: ManualOverrideRequest,
    current_user: dict = Depends(get_current_user)
):
    """Set junction to manual override mode"""
    
    # Verify access (same as get_junction)
    # ... access check code ...
    
    # Auto-calculate west lane time
    if override.west_lane_time is None:
        override.west_lane_time = (
            override.total_cycle_time - 
            override.north_lane_time - 
            override.south_lane_time - 
            override.east_lane_time
        )
    
    # Validate times
    if override.west_lane_time < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Lane times exceed total cycle time"
        )
    
    # Update junction mode
    await database.execute(
        query="UPDATE junctions SET current_mode = 'manual_override' WHERE junction_id = :junction_id",
        values={"junction_id": junction_id}
    )
    
    # Insert override history
    await database.execute(
        query="""
            INSERT INTO manual_override_history 
            (junction_id, user_id, total_cycle_time, north_lane_time, 
             south_lane_time, east_lane_time, west_lane_time, reason)
            VALUES (:junction_id, :user_id, :total_cycle_time, :north_lane_time,
                    :south_lane_time, :east_lane_time, :west_lane_time, :reason)
        """,
        values={
            "junction_id": junction_id,
            "user_id": current_user['user_id'],
            **override.dict()
        }
    )
    
    # TODO: Publish to MQTT green-time topic
    # await publish_green_times(junction_id, [north, south, east, west])
    
    return {"status": "success", "message": "Manual override activated"}
```

### 2.8 MQTT Integration (`mqtt_client.py`)
```python
# mqtt_client.py
import aiomqtt
import asyncio
import json
import os
from typing import Callable

MQTT_BROKER = os.getenv("MQTT_BROKER_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_BROKER_PORT", 1883))

class FlextraffMQTT:
    def __init__(self):
        self.client = None
        self.car_count_handlers = []
    
    async def connect(self):
        """Connect to MQTT broker"""
        self.client = aiomqtt.Client(hostname=MQTT_BROKER, port=MQTT_PORT)
        await self.client.__aenter__()
        print(f"✅ Connected to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}")
    
    async def disconnect(self):
        """Disconnect from MQTT broker"""
        if self.client:
            await self.client.__aexit__(None, None, None)
            print("❌ Disconnected from MQTT broker")
    
    async def subscribe_car_counts(self, callback: Callable):
        """Subscribe to car count topic
        
        Expected payload format:
        {
            "junction_id": "uuid",
            "lane_id": "uuid",
            "vehicle_count": 15,
            "epc_ids": ["EPC123456", "EPC789012", ...],
            "timestamp": "2026-02-10T14:30:00Z"
        }
        """
        async with self.client.messages() as messages:
            await self.client.subscribe("flextraff/+/+/car-counts")
            
            async for message in messages:
                try:
                    payload = json.loads(message.payload.decode())
                    
                    # Validate payload has required fields
                    if not all(k in payload for k in ['junction_id', 'lane_id', 'vehicle_count', 'epc_ids']):
                        print(f"Invalid car count payload: {payload}")
                        continue
                    
                    await callback(payload)
                except Exception as e:
                    print(f"Error processing car count: {e}")
    
    async def publish_green_times(self, junction_id: str, lane_times: list):
        """Publish green times to MQTT"""
        topic = f"flextraff/{junction_id}/green-time"
        payload = json.dumps({
            "junction_id": junction_id,
            "lane_times": lane_times,  # [N, S, E, W]
            "timestamp": datetime.utcnow().isoformat()
        })
        
        await self.client.publish(topic, payload)

# Global MQTT client
mqtt_client = FlextraffMQTT()
```

**Important Notes on EPC ID Storage:**
- Raspberry Pi RFID readers should send the actual EPC tag IDs in the `epc_ids` array
- The backend stores these as PostgreSQL TEXT[] for querying and analytics
- This enables vehicle tracking, fraud detection, and traffic pattern analysis
- Example: If 5 vehicles pass, send `"epc_ids": ["EPC001", "EPC002", "EPC003", "EPC004", "EPC005"]`

### 2.9 Main Application (`main.py`)
```python
# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import connect_db, disconnect_db
from mqtt_client import mqtt_client
from routes import users, junctions

app = FastAPI(
    title="Flextraff API",
    description="Dynamic Traffic Management System",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(users.router)
app.include_router(junctions.router)

@app.on_event("startup")
async def startup():
    """Startup tasks"""
    await connect_db()
    await mqtt_client.connect()
    # TODO: Start MQTT subscriber task

@app.on_event("shutdown")
async def shutdown():
    """Shutdown tasks"""
    await disconnect_db()
    await mqtt_client.disconnect()

@app.get("/")
async def root():
    return {"message": "Flextraff API v1.0", "status": "online"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "database": "connected", "mqtt": "connected"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
```

---

## Step 3: Run the Application

```bash
# Start the FastAPI server
python main.py

# Or with uvicorn
uvicorn main:app --reload

# API will be available at:
# http://localhost:8000
# Docs: http://localhost:8000/docs
```

---

## Step 4: Test the API

### 4.1 Register Admin User
```bash
curl -X POST "http://localhost:8000/api/users/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "email": "admin@flextraff.com",
    "password": "securepassword123",
    "full_name": "System Admin",
    "is_admin": true
  }'
```

### 4.2 Login
```bash
curl -X POST "http://localhost:8000/api/users/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=securepassword123"

# Returns: {"access_token": "eyJ...", "token_type": "bearer"}
```

### 4.3 Create Junction
```bash
curl -X POST "http://localhost:8000/api/junctions/" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "junction_name": "Main Street & Oak Ave",
    "city": "Mumbai",
    "latitude": 19.0760,
    "longitude": 72.8777,
    "min_cycle_time": 30,
    "max_cycle_time": 120,
    "base_cycle_time": 60
  }'
```

---

## Step 5: Next Steps

1. **Frontend Development**
   - Build React dashboard
   - Implement WebSocket for real-time updates
   - Create user management UI

2. **Raspberry Pi Integration**
   - Install MQTT client on Raspberry Pis
   - Configure RFID readers
   - Set up GPIO for traffic lights

3. **Algorithm Development**
   - Implement traffic optimization algorithm
   - Test with simulated data
   - Tune parameters

4. **Testing & Deployment**
   - Unit tests for API endpoints
   - Integration tests for MQTT
   - Deploy to production (AWS/Azure/GCP)

---

## Troubleshooting

### Database Connection Issues
```python
# Check connection
import asyncpg
conn = await asyncpg.connect('postgresql://user:pass@host:5432/flextraff')
print(await conn.fetchval('SELECT 1'))
```

### MQTT Connection Issues
```bash
# Test MQTT broker
mosquitto_sub -h localhost -t 'flextraff/#' -v

# Publish test message
mosquitto_pub -h localhost -t 'flextraff/test' -m 'Hello'
```

---

## Production Checklist

- [ ] Change SECRET_KEY to strong random value
- [ ] Enable SSL/TLS for database
- [ ] Enable MQTT over TLS
- [ ] Set up database backups
- [ ] Configure logging (Sentry, CloudWatch)
- [ ] Set up monitoring (Prometheus, Grafana)
- [ ] Enable rate limiting
- [ ] Set up CI/CD pipeline
- [ ] Configure environment variables properly
- [ ] Enable HTTPS (Let's Encrypt)

---

**Version:** 1.0  
**Last Updated:** February 10, 2026