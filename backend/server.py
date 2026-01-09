from fastapi import FastAPI, APIRouter, HTTPException, Depends, Query, WebSocket, WebSocketDisconnect, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
import bcrypt
from jose import jwt, JWTError
import httpx
import json
import asyncio

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT Config
JWT_SECRET = os.environ.get('JWT_SECRET_KEY', 'default_secret')
JWT_ALGORITHM = os.environ.get('JWT_ALGORITHM', 'HS256')
ACCESS_TOKEN_EXPIRE = int(os.environ.get('ACCESS_TOKEN_EXPIRE_MINUTES', 1440))

# OpenAI Config
EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY', '')

# Stripe Config
STRIPE_API_KEY = os.environ.get('STRIPE_API_KEY', '')

# Create the main app
app = FastAPI(title="NexusMarket API", version="1.0.0")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Security
security = HTTPBearer(auto_error=False)

# WebSocket connection manager for real-time inventory
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass

manager = ConnectionManager()

# ============== MODELS ==============

class UserBase(BaseModel):
    email: EmailStr
    name: str
    role: str = "customer"  # customer, seller, admin

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: str = "customer"

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    user_id: str
    email: str
    name: str
    role: str
    picture: Optional[str] = None
    loyalty_points: int = 0
    created_at: datetime

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: User

class Category(BaseModel):
    model_config = ConfigDict(extra="ignore")
    category_id: str
    name: str
    description: Optional[str] = None
    image: Optional[str] = None
    parent_id: Optional[str] = None

class ProductCreate(BaseModel):
    name: str
    description: str
    price: float
    category_id: str
    images: List[str] = []
    stock: int = 0
    tags: List[str] = []

class Product(BaseModel):
    model_config = ConfigDict(extra="ignore")
    product_id: str
    seller_id: str
    name: str
    description: str
    price: float
    category_id: str
    images: List[str] = []
    stock: int = 0
    tags: List[str] = []
    rating: float = 0.0
    review_count: int = 0
    created_at: datetime

class CartItem(BaseModel):
    product_id: str
    quantity: int

class CartUpdate(BaseModel):
    items: List[CartItem]

class ReviewCreate(BaseModel):
    product_id: str
    rating: int = Field(..., ge=1, le=5)
    comment: str

class Review(BaseModel):
    model_config = ConfigDict(extra="ignore")
    review_id: str
    product_id: str
    user_id: str
    user_name: str
    rating: int
    comment: str
    created_at: datetime

class OrderItem(BaseModel):
    product_id: str
    product_name: str
    price: float
    quantity: int
    image: Optional[str] = None

class OrderCreate(BaseModel):
    items: List[OrderItem]
    shipping_address: Dict[str, str]
    payment_method: str  # stripe or paypal

class Order(BaseModel):
    model_config = ConfigDict(extra="ignore")
    order_id: str
    user_id: str
    items: List[OrderItem]
    subtotal: float
    shipping: float = 0.0
    tax: float = 0.0
    total: float
    status: str = "pending"
    payment_status: str = "pending"
    payment_method: str
    shipping_address: Dict[str, str]
    tracking_number: Optional[str] = None
    created_at: datetime

class NewsletterSubscribe(BaseModel):
    email: EmailStr

class CheckoutRequest(BaseModel):
    order_id: str
    origin_url: str

# ============== AUTH HELPERS ==============

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), request: Request = None) -> Optional[User]:
    token = None
    
    # Try to get token from Authorization header
    if credentials:
        token = credentials.credentials
    
    # Try to get token from cookie
    if not token and request:
        token = request.cookies.get("session_token")
    
    if not token:
        return None
    
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            return None
        
        user_doc = await db.users.find_one({"user_id": user_id}, {"_id": 0})
        if not user_doc:
            return None
        
        if isinstance(user_doc.get('created_at'), str):
            user_doc['created_at'] = datetime.fromisoformat(user_doc['created_at'])
        
        return User(**user_doc)
    except JWTError:
        return None

async def require_auth(user: Optional[User] = Depends(get_current_user)) -> User:
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user

async def require_seller(user: User = Depends(require_auth)) -> User:
    if user.role not in ["seller", "admin"]:
        raise HTTPException(status_code=403, detail="Seller access required")
    return user

async def require_admin(user: User = Depends(require_auth)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user

# ============== AUTH ROUTES ==============

@api_router.post("/auth/register", response_model=TokenResponse)
async def register(data: UserCreate):
    existing = await db.users.find_one({"email": data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user_id = f"user_{uuid.uuid4().hex[:12]}"
    user_doc = {
        "user_id": user_id,
        "email": data.email,
        "name": data.name,
        "password_hash": hash_password(data.password),
        "role": data.role,
        "picture": None,
        "loyalty_points": 0,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.users.insert_one(user_doc)
    
    token = create_access_token({"sub": user_id})
    user_doc.pop("password_hash")
    user_doc['created_at'] = datetime.fromisoformat(user_doc['created_at'])
    
    return TokenResponse(access_token=token, user=User(**user_doc))

@api_router.post("/auth/login", response_model=TokenResponse)
async def login(data: UserLogin, response: Response):
    user_doc = await db.users.find_one({"email": data.email}, {"_id": 0})
    if not user_doc:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not verify_password(data.password, user_doc.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_access_token({"sub": user_doc["user_id"]})
    
    # Set cookie
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=ACCESS_TOKEN_EXPIRE * 60
    )
    
    user_doc.pop("password_hash", None)
    if isinstance(user_doc.get('created_at'), str):
        user_doc['created_at'] = datetime.fromisoformat(user_doc['created_at'])
    
    return TokenResponse(access_token=token, user=User(**user_doc))

@api_router.get("/auth/me", response_model=User)
async def get_me(user: User = Depends(require_auth)):
    return user

@api_router.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie("session_token")
    return {"message": "Logged out successfully"}

# Google OAuth session endpoint
@api_router.get("/auth/session")
async def get_session_data(request: Request, response: Response):
    session_id = request.headers.get("X-Session-ID")
    if not session_id:
        raise HTTPException(status_code=400, detail="Session ID required")
    
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
            headers={"X-Session-ID": session_id}
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid session")
        
        data = resp.json()
    
    # Check if user exists
    existing = await db.users.find_one({"email": data["email"]}, {"_id": 0})
    
    if existing:
        user_id = existing["user_id"]
        # Update user info
        await db.users.update_one(
            {"user_id": user_id},
            {"$set": {"name": data["name"], "picture": data.get("picture")}}
        )
    else:
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        await db.users.insert_one({
            "user_id": user_id,
            "email": data["email"],
            "name": data["name"],
            "picture": data.get("picture"),
            "role": "customer",
            "loyalty_points": 0,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
    
    token = create_access_token({"sub": user_id})
    
    # Set cookie
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=ACCESS_TOKEN_EXPIRE * 60
    )
    
    user_doc = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    if isinstance(user_doc.get('created_at'), str):
        user_doc['created_at'] = datetime.fromisoformat(user_doc['created_at'])
    
    return {"user": User(**user_doc), "session_token": token}

# ============== CATEGORY ROUTES ==============

@api_router.get("/categories", response_model=List[Category])
async def get_categories():
    categories = await db.categories.find({}, {"_id": 0}).to_list(100)
    return categories

@api_router.post("/categories", response_model=Category)
async def create_category(data: Category, user: User = Depends(require_admin)):
    data.category_id = f"cat_{uuid.uuid4().hex[:8]}"
    await db.categories.insert_one(data.model_dump())
    return data

# ============== PRODUCT ROUTES ==============

@api_router.get("/products", response_model=List[Product])
async def get_products(
    category: Optional[str] = None,
    search: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    min_rating: Optional[float] = None,
    sort: Optional[str] = "newest",
    limit: int = Query(20, le=100),
    skip: int = 0
):
    query = {}
    
    if category:
        query["category_id"] = category
    
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}},
            {"tags": {"$in": [search.lower()]}}
        ]
    
    if min_price is not None:
        query["price"] = {"$gte": min_price}
    if max_price is not None:
        query.setdefault("price", {})["$lte"] = max_price
    
    if min_rating is not None:
        query["rating"] = {"$gte": min_rating}
    
    sort_field = {"newest": ("created_at", -1), "price_low": ("price", 1), "price_high": ("price", -1), "rating": ("rating", -1)}.get(sort, ("created_at", -1))
    
    products = await db.products.find(query, {"_id": 0}).sort(*sort_field).skip(skip).limit(limit).to_list(limit)
    
    for p in products:
        if isinstance(p.get('created_at'), str):
            p['created_at'] = datetime.fromisoformat(p['created_at'])
    
    return products

@api_router.get("/products/{product_id}", response_model=Product)
async def get_product(product_id: str):
    product = await db.products.find_one({"product_id": product_id}, {"_id": 0})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    if isinstance(product.get('created_at'), str):
        product['created_at'] = datetime.fromisoformat(product['created_at'])
    
    return product

@api_router.post("/products", response_model=Product)
async def create_product(data: ProductCreate, user: User = Depends(require_seller)):
    product_id = f"prod_{uuid.uuid4().hex[:8]}"
    product = {
        "product_id": product_id,
        "seller_id": user.user_id,
        **data.model_dump(),
        "rating": 0.0,
        "review_count": 0,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.products.insert_one(product)
    product['created_at'] = datetime.fromisoformat(product['created_at'])
    
    # Broadcast inventory update
    await manager.broadcast({"type": "product_added", "product_id": product_id, "stock": data.stock})
    
    return product

@api_router.put("/products/{product_id}", response_model=Product)
async def update_product(product_id: str, data: ProductCreate, user: User = Depends(require_seller)):
    product = await db.products.find_one({"product_id": product_id}, {"_id": 0})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    if product["seller_id"] != user.user_id and user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    
    old_stock = product.get("stock", 0)
    
    await db.products.update_one(
        {"product_id": product_id},
        {"$set": data.model_dump()}
    )
    
    updated = await db.products.find_one({"product_id": product_id}, {"_id": 0})
    if isinstance(updated.get('created_at'), str):
        updated['created_at'] = datetime.fromisoformat(updated['created_at'])
    
    # Broadcast inventory update if stock changed
    if data.stock != old_stock:
        await manager.broadcast({"type": "inventory_update", "product_id": product_id, "stock": data.stock})
    
    return updated

@api_router.delete("/products/{product_id}")
async def delete_product(product_id: str, user: User = Depends(require_seller)):
    product = await db.products.find_one({"product_id": product_id})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    if product["seller_id"] != user.user_id and user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    
    await db.products.delete_one({"product_id": product_id})
    await manager.broadcast({"type": "product_deleted", "product_id": product_id})
    
    return {"message": "Product deleted"}

# ============== CART ROUTES ==============

@api_router.get("/cart")
async def get_cart(user: User = Depends(require_auth)):
    cart = await db.carts.find_one({"user_id": user.user_id}, {"_id": 0})
    if not cart:
        return {"items": [], "total": 0}
    
    # Get product details
    items_with_details = []
    total = 0
    
    for item in cart.get("items", []):
        product = await db.products.find_one({"product_id": item["product_id"]}, {"_id": 0})
        if product:
            item_total = product["price"] * item["quantity"]
            total += item_total
            items_with_details.append({
                "product_id": item["product_id"],
                "quantity": item["quantity"],
                "product": {
                    "name": product["name"],
                    "price": product["price"],
                    "image": product["images"][0] if product["images"] else None,
                    "stock": product["stock"]
                }
            })
    
    return {"items": items_with_details, "total": round(total, 2)}

@api_router.post("/cart/add")
async def add_to_cart(item: CartItem, user: User = Depends(require_auth)):
    product = await db.products.find_one({"product_id": item.product_id})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    if product["stock"] < item.quantity:
        raise HTTPException(status_code=400, detail="Insufficient stock")
    
    cart = await db.carts.find_one({"user_id": user.user_id})
    
    if cart:
        # Check if item exists
        existing_item = next((i for i in cart.get("items", []) if i["product_id"] == item.product_id), None)
        if existing_item:
            new_qty = existing_item["quantity"] + item.quantity
            if new_qty > product["stock"]:
                raise HTTPException(status_code=400, detail="Insufficient stock")
            await db.carts.update_one(
                {"user_id": user.user_id, "items.product_id": item.product_id},
                {"$set": {"items.$.quantity": new_qty}}
            )
        else:
            await db.carts.update_one(
                {"user_id": user.user_id},
                {"$push": {"items": item.model_dump()}}
            )
    else:
        await db.carts.insert_one({
            "user_id": user.user_id,
            "items": [item.model_dump()]
        })
    
    return {"message": "Added to cart"}

@api_router.put("/cart/update")
async def update_cart(data: CartUpdate, user: User = Depends(require_auth)):
    await db.carts.update_one(
        {"user_id": user.user_id},
        {"$set": {"items": [i.model_dump() for i in data.items]}},
        upsert=True
    )
    return {"message": "Cart updated"}

@api_router.delete("/cart/item/{product_id}")
async def remove_from_cart(product_id: str, user: User = Depends(require_auth)):
    await db.carts.update_one(
        {"user_id": user.user_id},
        {"$pull": {"items": {"product_id": product_id}}}
    )
    return {"message": "Item removed"}

@api_router.delete("/cart")
async def clear_cart(user: User = Depends(require_auth)):
    await db.carts.delete_one({"user_id": user.user_id})
    return {"message": "Cart cleared"}

# ============== WISHLIST ROUTES ==============

@api_router.get("/wishlist")
async def get_wishlist(user: User = Depends(require_auth)):
    wishlist = await db.wishlists.find_one({"user_id": user.user_id}, {"_id": 0})
    if not wishlist:
        return {"items": []}
    
    products = []
    for pid in wishlist.get("product_ids", []):
        product = await db.products.find_one({"product_id": pid}, {"_id": 0})
        if product:
            if isinstance(product.get('created_at'), str):
                product['created_at'] = datetime.fromisoformat(product['created_at'])
            products.append(product)
    
    return {"items": products}

@api_router.post("/wishlist/{product_id}")
async def add_to_wishlist(product_id: str, user: User = Depends(require_auth)):
    product = await db.products.find_one({"product_id": product_id})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    await db.wishlists.update_one(
        {"user_id": user.user_id},
        {"$addToSet": {"product_ids": product_id}},
        upsert=True
    )
    return {"message": "Added to wishlist"}

@api_router.delete("/wishlist/{product_id}")
async def remove_from_wishlist(product_id: str, user: User = Depends(require_auth)):
    await db.wishlists.update_one(
        {"user_id": user.user_id},
        {"$pull": {"product_ids": product_id}}
    )
    return {"message": "Removed from wishlist"}

# ============== REVIEW ROUTES ==============

@api_router.get("/products/{product_id}/reviews", response_model=List[Review])
async def get_product_reviews(product_id: str):
    reviews = await db.reviews.find({"product_id": product_id}, {"_id": 0}).sort("created_at", -1).to_list(100)
    for r in reviews:
        if isinstance(r.get('created_at'), str):
            r['created_at'] = datetime.fromisoformat(r['created_at'])
    return reviews

@api_router.post("/reviews", response_model=Review)
async def create_review(data: ReviewCreate, user: User = Depends(require_auth)):
    # Check if user already reviewed
    existing = await db.reviews.find_one({"product_id": data.product_id, "user_id": user.user_id})
    if existing:
        raise HTTPException(status_code=400, detail="Already reviewed this product")
    
    review_id = f"rev_{uuid.uuid4().hex[:8]}"
    review = {
        "review_id": review_id,
        "product_id": data.product_id,
        "user_id": user.user_id,
        "user_name": user.name,
        "rating": data.rating,
        "comment": data.comment,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.reviews.insert_one(review)
    
    # Update product rating
    all_reviews = await db.reviews.find({"product_id": data.product_id}).to_list(1000)
    avg_rating = sum(r["rating"] for r in all_reviews) / len(all_reviews)
    await db.products.update_one(
        {"product_id": data.product_id},
        {"$set": {"rating": round(avg_rating, 1), "review_count": len(all_reviews)}}
    )
    
    review['created_at'] = datetime.fromisoformat(review['created_at'])
    return review

# ============== ORDER ROUTES ==============

@api_router.get("/orders", response_model=List[Order])
async def get_orders(user: User = Depends(require_auth)):
    query = {"user_id": user.user_id}
    if user.role == "admin":
        query = {}
    elif user.role == "seller":
        # Get orders containing seller's products
        seller_products = await db.products.find({"seller_id": user.user_id}).to_list(1000)
        product_ids = [p["product_id"] for p in seller_products]
        query = {"items.product_id": {"$in": product_ids}}
    
    orders = await db.orders.find(query, {"_id": 0}).sort("created_at", -1).to_list(100)
    for o in orders:
        if isinstance(o.get('created_at'), str):
            o['created_at'] = datetime.fromisoformat(o['created_at'])
    return orders

@api_router.get("/orders/{order_id}", response_model=Order)
async def get_order(order_id: str, user: User = Depends(require_auth)):
    order = await db.orders.find_one({"order_id": order_id}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order["user_id"] != user.user_id and user.role not in ["admin", "seller"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    if isinstance(order.get('created_at'), str):
        order['created_at'] = datetime.fromisoformat(order['created_at'])
    
    return order

@api_router.post("/orders", response_model=Order)
async def create_order(data: OrderCreate, user: User = Depends(require_auth)):
    # Validate items and calculate totals
    subtotal = 0
    for item in data.items:
        product = await db.products.find_one({"product_id": item.product_id})
        if not product:
            raise HTTPException(status_code=400, detail=f"Product {item.product_id} not found")
        if product["stock"] < item.quantity:
            raise HTTPException(status_code=400, detail=f"Insufficient stock for {product['name']}")
        subtotal += item.price * item.quantity
    
    tax = round(subtotal * 0.1, 2)  # 10% tax
    shipping = 10.00 if subtotal < 100 else 0.00
    total = round(subtotal + tax + shipping, 2)
    
    order_id = f"ord_{uuid.uuid4().hex[:8]}"
    order = {
        "order_id": order_id,
        "user_id": user.user_id,
        "items": [i.model_dump() for i in data.items],
        "subtotal": round(subtotal, 2),
        "tax": tax,
        "shipping": shipping,
        "total": total,
        "status": "pending",
        "payment_status": "pending",
        "payment_method": data.payment_method,
        "shipping_address": data.shipping_address,
        "tracking_number": None,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.orders.insert_one(order)
    order['created_at'] = datetime.fromisoformat(order['created_at'])
    
    return order

@api_router.put("/orders/{order_id}/status")
async def update_order_status(order_id: str, status: str, user: User = Depends(require_admin)):
    valid_statuses = ["pending", "processing", "shipped", "delivered", "cancelled"]
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail="Invalid status")
    
    result = await db.orders.update_one(
        {"order_id": order_id},
        {"$set": {"status": status}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Order not found")
    
    return {"message": "Status updated"}

# ============== PAYMENT ROUTES ==============

@api_router.post("/payments/stripe/create-session")
async def create_stripe_session(data: CheckoutRequest, request: Request, user: User = Depends(require_auth)):
    order = await db.orders.find_one({"order_id": data.order_id, "user_id": user.user_id})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    try:
        # Import Stripe integration
        from emergentintegrations.payments.stripe.checkout import StripeCheckout, CheckoutSessionRequest
        
        host_url = data.origin_url
        webhook_url = f"{request.base_url}api/webhook/stripe"
        
        stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=webhook_url)
        
        checkout_request = CheckoutSessionRequest(
            amount=float(order["total"]),
            currency="usd",
            success_url=f"{host_url}/order-success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{host_url}/checkout",
            metadata={"order_id": data.order_id, "user_id": user.user_id}
        )
        
        session = await stripe_checkout.create_checkout_session(checkout_request)
        
        # Store payment transaction
        await db.payment_transactions.insert_one({
            "transaction_id": f"txn_{uuid.uuid4().hex[:8]}",
            "session_id": session.session_id,
            "order_id": data.order_id,
            "user_id": user.user_id,
            "amount": order["total"],
            "currency": "usd",
            "payment_status": "initiated",
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        return {"url": session.url, "session_id": session.session_id}
    except ImportError:
        # Fallback for when emergentintegrations is not available
        import httpx
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.stripe.com/v1/checkout/sessions",
                auth=(STRIPE_API_KEY, ""),
                data={
                    "payment_method_types[]": "card",
                    "line_items[0][price_data][currency]": "usd",
                    "line_items[0][price_data][unit_amount]": int(order["total"] * 100),
                    "line_items[0][price_data][product_data][name]": f"Order {data.order_id}",
                    "line_items[0][quantity]": "1",
                    "mode": "payment",
                    "success_url": f"{data.origin_url}/order-success?session_id={{CHECKOUT_SESSION_ID}}",
                    "cancel_url": f"{data.origin_url}/checkout",
                    "metadata[order_id]": data.order_id,
                    "metadata[user_id]": user.user_id
                }
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=400, detail="Failed to create checkout session")
            
            session_data = response.json()
            
            # Store payment transaction
            await db.payment_transactions.insert_one({
                "transaction_id": f"txn_{uuid.uuid4().hex[:8]}",
                "session_id": session_data["id"],
                "order_id": data.order_id,
                "user_id": user.user_id,
                "amount": order["total"],
                "currency": "usd",
                "payment_status": "initiated",
                "created_at": datetime.now(timezone.utc).isoformat()
            })
            
            return {"url": session_data["url"], "session_id": session_data["id"]}

@api_router.get("/payments/status/{session_id}")
async def get_payment_status(session_id: str, user: User = Depends(require_auth)):
    transaction = await db.payment_transactions.find_one({"session_id": session_id}, {"_id": 0})
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    try:
        from emergentintegrations.payments.stripe.checkout import StripeCheckout
        
        stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url="")
        status = await stripe_checkout.get_checkout_status(session_id)
        
        if status.payment_status == "paid" and transaction["payment_status"] != "paid":
            # Update transaction and order
            await db.payment_transactions.update_one(
                {"session_id": session_id},
                {"$set": {"payment_status": "paid"}}
            )
            await db.orders.update_one(
                {"order_id": transaction["order_id"]},
                {"$set": {"payment_status": "paid", "status": "processing"}}
            )
            
            # Update inventory
            order = await db.orders.find_one({"order_id": transaction["order_id"]})
            if order:
                for item in order["items"]:
                    await db.products.update_one(
                        {"product_id": item["product_id"]},
                        {"$inc": {"stock": -item["quantity"]}}
                    )
                    # Broadcast inventory update
                    product = await db.products.find_one({"product_id": item["product_id"]})
                    if product:
                        await manager.broadcast({
                            "type": "inventory_update",
                            "product_id": item["product_id"],
                            "stock": product["stock"]
                        })
            
            # Add loyalty points
            points = int(order["total"])
            await db.users.update_one(
                {"user_id": transaction["user_id"]},
                {"$inc": {"loyalty_points": points}}
            )
        
        return {
            "status": status.status,
            "payment_status": status.payment_status,
            "order_id": transaction["order_id"]
        }
    except ImportError:
        # Fallback
        import httpx
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.stripe.com/v1/checkout/sessions/{session_id}",
                auth=(STRIPE_API_KEY, "")
            )
            
            if response.status_code != 200:
                return {"status": "unknown", "payment_status": transaction["payment_status"]}
            
            data = response.json()
            
            if data.get("payment_status") == "paid" and transaction["payment_status"] != "paid":
                await db.payment_transactions.update_one(
                    {"session_id": session_id},
                    {"$set": {"payment_status": "paid"}}
                )
                await db.orders.update_one(
                    {"order_id": transaction["order_id"]},
                    {"$set": {"payment_status": "paid", "status": "processing"}}
                )
                
                # Update inventory
                order = await db.orders.find_one({"order_id": transaction["order_id"]})
                if order:
                    for item in order["items"]:
                        await db.products.update_one(
                            {"product_id": item["product_id"]},
                            {"$inc": {"stock": -item["quantity"]}}
                        )
                    
                    # Add loyalty points
                    points = int(order["total"])
                    await db.users.update_one(
                        {"user_id": transaction["user_id"]},
                        {"$inc": {"loyalty_points": points}}
                    )
            
            return {
                "status": data.get("status"),
                "payment_status": data.get("payment_status"),
                "order_id": transaction["order_id"]
            }

@api_router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    body = await request.body()
    # Handle webhook (simplified)
    try:
        data = json.loads(body)
        if data.get("type") == "checkout.session.completed":
            session = data["data"]["object"]
            session_id = session["id"]
            
            await db.payment_transactions.update_one(
                {"session_id": session_id},
                {"$set": {"payment_status": "paid"}}
            )
            
            transaction = await db.payment_transactions.find_one({"session_id": session_id})
            if transaction:
                await db.orders.update_one(
                    {"order_id": transaction["order_id"]},
                    {"$set": {"payment_status": "paid", "status": "processing"}}
                )
    except:
        pass
    
    return {"received": True}

# ============== AI RECOMMENDATIONS ==============

@api_router.get("/recommendations")
async def get_recommendations(user: Optional[User] = Depends(get_current_user)):
    # Get trending/popular products
    trending = await db.products.find({}, {"_id": 0}).sort("review_count", -1).limit(8).to_list(8)
    
    for p in trending:
        if isinstance(p.get('created_at'), str):
            p['created_at'] = datetime.fromisoformat(p['created_at'])
    
    if not user:
        return {"recommendations": trending, "type": "trending"}
    
    # Get user's order history for personalized recommendations
    orders = await db.orders.find({"user_id": user.user_id}).to_list(10)
    if not orders:
        return {"recommendations": trending, "type": "trending"}
    
    # Get categories from user's purchases
    purchased_products = []
    for order in orders:
        for item in order["items"]:
            purchased_products.append(item["product_id"])
    
    if purchased_products:
        products = await db.products.find({"product_id": {"$in": purchased_products}}).to_list(100)
        categories = list(set(p["category_id"] for p in products))
        
        # Recommend from same categories
        recommendations = await db.products.find(
            {"category_id": {"$in": categories}, "product_id": {"$nin": purchased_products}},
            {"_id": 0}
        ).limit(8).to_list(8)
        
        for p in recommendations:
            if isinstance(p.get('created_at'), str):
                p['created_at'] = datetime.fromisoformat(p['created_at'])
        
        if recommendations:
            return {"recommendations": recommendations, "type": "personalized"}
    
    return {"recommendations": trending, "type": "trending"}

@api_router.get("/recommendations/ai/{product_id}")
async def get_ai_recommendations(product_id: str):
    product = await db.products.find_one({"product_id": product_id}, {"_id": 0})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Get similar products
    similar = await db.products.find(
        {"category_id": product["category_id"], "product_id": {"$ne": product_id}},
        {"_id": 0}
    ).limit(4).to_list(4)
    
    for p in similar:
        if isinstance(p.get('created_at'), str):
            p['created_at'] = datetime.fromisoformat(p['created_at'])
    
    # Use AI for description if available
    ai_description = None
    if EMERGENT_LLM_KEY:
        try:
            from openai import AsyncOpenAI
            
            client = AsyncOpenAI(api_key=EMERGENT_LLM_KEY)
            response = await client.chat.completions.create(
                model="gpt-5.2",
                messages=[
                    {"role": "system", "content": "You are a helpful shopping assistant. Provide a brief recommendation."},
                    {"role": "user", "content": f"Why should someone buy '{product['name']}'? Keep it to 2 sentences."}
                ],
                max_tokens=100
            )
            ai_description = response.choices[0].message.content
        except:
            pass
    
    return {
        "similar_products": similar,
        "ai_recommendation": ai_description
    }

# ============== NEWSLETTER ==============

@api_router.post("/newsletter/subscribe")
async def subscribe_newsletter(data: NewsletterSubscribe):
    existing = await db.newsletter.find_one({"email": data.email})
    if existing:
        return {"message": "Already subscribed"}
    
    await db.newsletter.insert_one({
        "email": data.email,
        "subscribed_at": datetime.now(timezone.utc).isoformat()
    })
    return {"message": "Subscribed successfully"}

# ============== ADMIN ROUTES ==============

@api_router.get("/admin/stats")
async def get_admin_stats(user: User = Depends(require_admin)):
    total_users = await db.users.count_documents({})
    total_products = await db.products.count_documents({})
    total_orders = await db.orders.count_documents({})
    
    # Revenue calculation
    orders = await db.orders.find({"payment_status": "paid"}).to_list(1000)
    total_revenue = sum(o["total"] for o in orders)
    
    # Recent orders
    recent_orders = await db.orders.find({}, {"_id": 0}).sort("created_at", -1).limit(10).to_list(10)
    for o in recent_orders:
        if isinstance(o.get('created_at'), str):
            o['created_at'] = datetime.fromisoformat(o['created_at'])
    
    # Sales by day (last 7 days)
    from datetime import timedelta
    sales_by_day = []
    for i in range(7):
        day = datetime.now(timezone.utc) - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        
        day_orders = await db.orders.find({
            "payment_status": "paid",
            "created_at": {"$gte": day_start.isoformat(), "$lt": day_end.isoformat()}
        }).to_list(1000)
        
        sales_by_day.append({
            "date": day_start.strftime("%Y-%m-%d"),
            "revenue": sum(o["total"] for o in day_orders),
            "orders": len(day_orders)
        })
    
    return {
        "total_users": total_users,
        "total_products": total_products,
        "total_orders": total_orders,
        "total_revenue": round(total_revenue, 2),
        "recent_orders": recent_orders,
        "sales_by_day": list(reversed(sales_by_day))
    }

@api_router.get("/admin/users")
async def get_all_users(user: User = Depends(require_admin)):
    users = await db.users.find({}, {"_id": 0, "password_hash": 0}).to_list(1000)
    for u in users:
        if isinstance(u.get('created_at'), str):
            u['created_at'] = datetime.fromisoformat(u['created_at'])
    return users

@api_router.put("/admin/users/{user_id}/role")
async def update_user_role(user_id: str, role: str, admin: User = Depends(require_admin)):
    if role not in ["customer", "seller", "admin"]:
        raise HTTPException(status_code=400, detail="Invalid role")
    
    await db.users.update_one(
        {"user_id": user_id},
        {"$set": {"role": role}}
    )
    return {"message": "Role updated"}

# ============== SELLER ROUTES ==============

@api_router.get("/seller/products")
async def get_seller_products(user: User = Depends(require_seller)):
    products = await db.products.find({"seller_id": user.user_id}, {"_id": 0}).to_list(100)
    for p in products:
        if isinstance(p.get('created_at'), str):
            p['created_at'] = datetime.fromisoformat(p['created_at'])
    return products

@api_router.get("/seller/stats")
async def get_seller_stats(user: User = Depends(require_seller)):
    products = await db.products.find({"seller_id": user.user_id}).to_list(100)
    product_ids = [p["product_id"] for p in products]
    
    total_products = len(products)
    total_stock = sum(p["stock"] for p in products)
    
    # Orders containing seller's products
    orders = await db.orders.find({"items.product_id": {"$in": product_ids}}).to_list(1000)
    
    total_sales = 0
    for order in orders:
        for item in order["items"]:
            if item["product_id"] in product_ids:
                total_sales += item["price"] * item["quantity"]
    
    return {
        "total_products": total_products,
        "total_stock": total_stock,
        "total_orders": len(orders),
        "total_sales": round(total_sales, 2)
    }

# ============== WEBSOCKET ==============

@app.websocket("/ws/inventory")
async def websocket_inventory(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Echo back or handle commands
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# ============== SEED DATA ==============

@api_router.post("/seed")
async def seed_data():
    # Check if data exists
    existing = await db.categories.count_documents({})
    if existing > 0:
        return {"message": "Data already seeded"}
    
    # Seed categories
    categories = [
        {"category_id": "cat_electronics", "name": "Electronics", "description": "Latest gadgets and devices", "image": "https://images.unsplash.com/photo-1498049794561-7780e7231661?w=500"},
        {"category_id": "cat_fashion", "name": "Fashion", "description": "Trendy clothing and accessories", "image": "https://images.unsplash.com/photo-1445205170230-053b83016050?w=500"},
        {"category_id": "cat_home", "name": "Home & Living", "description": "Furniture and home decor", "image": "https://images.unsplash.com/photo-1484101403633-562f891dc89a?w=500"},
        {"category_id": "cat_sports", "name": "Sports & Outdoors", "description": "Sports equipment and outdoor gear", "image": "https://images.unsplash.com/photo-1461896836934-ffe607ba8211?w=500"},
        {"category_id": "cat_books", "name": "Books", "description": "Books and educational materials", "image": "https://images.unsplash.com/photo-1495446815901-a7297e633e8d?w=500"},
    ]
    await db.categories.insert_many(categories)
    
    # Seed admin user
    admin_id = f"user_{uuid.uuid4().hex[:12]}"
    await db.users.insert_one({
        "user_id": admin_id,
        "email": "admin@nexusmarket.com",
        "name": "Admin User",
        "password_hash": hash_password("admin123"),
        "role": "admin",
        "picture": None,
        "loyalty_points": 0,
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    # Seed seller
    seller_id = f"user_{uuid.uuid4().hex[:12]}"
    await db.users.insert_one({
        "user_id": seller_id,
        "email": "seller@nexusmarket.com",
        "name": "Demo Seller",
        "password_hash": hash_password("seller123"),
        "role": "seller",
        "picture": None,
        "loyalty_points": 0,
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    # Seed products
    products = [
        {"product_id": "prod_001", "seller_id": seller_id, "name": "Wireless Bluetooth Headphones", "description": "Premium noise-cancelling headphones with 30-hour battery life", "price": 199.99, "category_id": "cat_electronics", "images": ["https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=500"], "stock": 50, "tags": ["audio", "bluetooth", "headphones"], "rating": 4.5, "review_count": 128, "created_at": datetime.now(timezone.utc).isoformat()},
        {"product_id": "prod_002", "seller_id": seller_id, "name": "Smart Watch Pro", "description": "Advanced fitness tracking with heart rate monitor and GPS", "price": 299.99, "category_id": "cat_electronics", "images": ["https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=500"], "stock": 30, "tags": ["smartwatch", "fitness", "wearable"], "rating": 4.7, "review_count": 89, "created_at": datetime.now(timezone.utc).isoformat()},
        {"product_id": "prod_003", "seller_id": seller_id, "name": "Premium Leather Jacket", "description": "Genuine leather jacket with vintage styling", "price": 349.99, "category_id": "cat_fashion", "images": ["https://images.unsplash.com/photo-1551028719-00167b16eac5?w=500"], "stock": 20, "tags": ["leather", "jacket", "fashion"], "rating": 4.8, "review_count": 56, "created_at": datetime.now(timezone.utc).isoformat()},
        {"product_id": "prod_004", "seller_id": seller_id, "name": "Modern Desk Lamp", "description": "LED desk lamp with adjustable brightness and color temperature", "price": 79.99, "category_id": "cat_home", "images": ["https://images.unsplash.com/photo-1507473885765-e6ed057f782c?w=500"], "stock": 100, "tags": ["lamp", "led", "office"], "rating": 4.3, "review_count": 234, "created_at": datetime.now(timezone.utc).isoformat()},
        {"product_id": "prod_005", "seller_id": seller_id, "name": "Running Shoes Elite", "description": "Lightweight running shoes with advanced cushioning technology", "price": 149.99, "category_id": "cat_sports", "images": ["https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=500"], "stock": 75, "tags": ["shoes", "running", "sports"], "rating": 4.6, "review_count": 312, "created_at": datetime.now(timezone.utc).isoformat()},
        {"product_id": "prod_006", "seller_id": seller_id, "name": "Minimalist Backpack", "description": "Water-resistant backpack with laptop compartment", "price": 89.99, "category_id": "cat_fashion", "images": ["https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=500"], "stock": 45, "tags": ["backpack", "bag", "travel"], "rating": 4.4, "review_count": 167, "created_at": datetime.now(timezone.utc).isoformat()},
        {"product_id": "prod_007", "seller_id": seller_id, "name": "Wireless Charging Pad", "description": "Fast wireless charger compatible with all Qi-enabled devices", "price": 39.99, "category_id": "cat_electronics", "images": ["https://images.unsplash.com/photo-1586816879360-004f5b0c51e5?w=500"], "stock": 200, "tags": ["charger", "wireless", "accessories"], "rating": 4.2, "review_count": 445, "created_at": datetime.now(timezone.utc).isoformat()},
        {"product_id": "prod_008", "seller_id": seller_id, "name": "Yoga Mat Premium", "description": "Extra thick non-slip yoga mat with carrying strap", "price": 49.99, "category_id": "cat_sports", "images": ["https://images.unsplash.com/photo-1601925260368-ae2f83cf8b7f?w=500"], "stock": 80, "tags": ["yoga", "fitness", "mat"], "rating": 4.5, "review_count": 198, "created_at": datetime.now(timezone.utc).isoformat()},
    ]
    await db.products.insert_many(products)
    
    return {"message": "Data seeded successfully"}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
