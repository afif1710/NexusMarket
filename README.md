# NexusMarket — E-commerce Web Application

An ecommerce webapp built with React (CRACO), FastAPI, and MongoDB, featuring product management, authentication, cart/checkout, seller dashboard, and admin panel.

## Tech Stack

Frontend:

- React + Create React App (CRACO)
- Tailwind CSS + Radix UI
- React Router, Axios, React Hook Form, Zod

Backend:

- FastAPI (Python) + Uvicorn
- MongoDB (Motor async driver)
- JWT auth (+ OAuth support)

## Features

- User authentication (email/password + OAuth)
- Product browsing (categories + search)
- Shopping cart + wishlist
- Checkout + order history
- Seller dashboard
- Admin panel

---

## Local Setup (Windows CMD)

### Folder structure

This README assumes the project is located at:

- %USERPROFILE%\Desktop\ecommerce_webapp

And contains:

- backend\
- frontend\

If yours is different, adjust the `cd` commands.

### Prerequisites (install once)

- Node.js (includes npm)
- Python 3.x
- MongoDB Community Server + mongosh

### Do NOT commit these (recommended .gitignore)

Create a file named `.gitignore` in the project root and add:

node*modules/
build/
venv/
.venv/
**pycache**/
*.py[cod]
.env
.env.\_
_.pem
_.key
.vscode/
.DS_Store
Thumbs.db

---

## Environment Variables

Create these files locally (do not commit them):

### frontend\.env

REACT_APP_BACKEND_URL=http://127.0.0.1:8000
WDS_SOCKET_PORT=0

### backend\.env (example)

MONGO_URL="mongodb://localhost:27017"
DB_NAME="test_database"
CORS_ORIGINS="http://localhost:3000"
JWT_SECRET_KEY=change_me
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

---

## Run the project (daily)

### 1) Start MongoDB (service)

Open CMD and run:

sc query MongoDB
net start MongoDB

(Optional) test DB connection:

mongosh

### 2) Start Backend (Terminal 1)

Open a new CMD and run:

cd %USERPROFILE%\Desktop\ecommerce_webapp\backend

REM Create venv once (safe to re-run; it will just say it exists)
python -m venv venv

REM Activate venv (must do this each new terminal)
venv\Scripts\activate

REM Install deps (run again only when requirements.txt changes)
pip install -r requirements.txt

REM Start FastAPI (dev mode)
uvicorn server:app --reload --port 8000

Backend API docs:

- http://127.0.0.1:8000/docs

Note: If you see logs like GET / 404 or GET /favicon.ico 404, that’s usually harmless.

### 3) Start Frontend (Terminal 2)

Open a new CMD and run:

cd %USERPROFILE%\Desktop\ecommerce_webapp\frontend

REM Enable yarn via corepack (first time only)
corepack enable

REM Install deps (run again only when package.json changes)
yarn install

REM Start React dev server
yarn start

Frontend URL:

- http://localhost:3000

---

## Stop servers

In the terminal windows where frontend/backend are running, press:

Ctrl + C

---

## Common fixes

### Yarn install timeout (slow network)

yarn config set network-timeout 600000 -g
yarn install --network-timeout 600000

### Change ports

If backend port 8000 is busy:
uvicorn server:app --reload --port 8001

Then update `frontend\.env`:
REACT_APP_BACKEND_URL=http://127.0.0.1:8001

---
