# Ecommerce_webapp (NexusMarket) — Local Setup & Run (Windows CMD)

Project root: %USERPROFILE%\Desktop\Ecommerce_webapp
Frontend: %USERPROFILE%\Desktop\Ecommerce_webapp\frontend (React + CRACO)
Backend: %USERPROFILE%\Desktop\Ecommerce_webapp\backend (FastAPI + Uvicorn)
Database: MongoDB (runs separately, default: mongodb://127.0.0.1:27017)

============================================================ 0) One-time prerequisites (install once)
============================================================

# Check Node & npm

node -v
npm -v

# Enable Yarn using Corepack (recommended; your project expects Yarn 1.22.22)

corepack enable
yarn -v

# MongoDB

# - Install MongoDB Community Server (GUI installer)

# - Install mongosh (Shell)

# Verify mongo shell can connect:

mongosh

============================================================

1. # One-time project setup (run once per fresh download/clone)

---

## A) Backend: install deps

cd %USERPROFILE%\Desktop\Ecommerce_webapp\backend

# Create & activate virtual environment

python -m venv venv
venv\Scripts\activate

# Install Python dependencies

pip install -r requirements.txt

# (Optional) If you have a backend/.env file, make sure it has correct local values, e.g.

# MONGO_URL="mongodb://localhost:27017"

# DB_NAME="test_database"

# CORS_ORIGINS="http://localhost:3000"

---

## B) Frontend: install deps

cd %USERPROFILE%\Desktop\Ecommerce_webapp\frontend

# If yarn install times out on slow networks:

yarn config set network-timeout 600000 -g

# Install node dependencies

yarn install --network-timeout 600000

# (Optional) frontend/.env should point to local backend:

# REACT_APP_BACKEND_URL=http://127.0.0.1:8000

# WDS_SOCKET_PORT=0

============================================================ 2) Daily run commands (every time you start working)
============================================================

---

## A) Start MongoDB (usually automatic)

# Check MongoDB Windows Service:

sc query MongoDB

# If NOT running, start it:

net start MongoDB

---

## B) Start Backend (Terminal 1)

cd %USERPROFILE%\Desktop\Ecommerce_webapp\backend
venv\Scripts\activate

# Start FastAPI backend (dev mode with auto-reload)

uvicorn server:app --reload --port 8000

# Backend docs (Swagger UI):

# http://127.0.0.1:8000/docs

# If you see GET / 404 or GET /favicon.ico 404 in logs, it’s normal.

---

## C) Start Frontend (Terminal 2)

cd %USERPROFILE%\Desktop\Ecommerce_webapp\frontend

# Start React dev server

yarn start

# Frontend URL:

# http://localhost:3000

============================================================ 3) Stop servers
============================================================

# Frontend terminal: press Ctrl + C

# Backend terminal: press Ctrl + C

============================================================ 4) Common fixes
============================================================

# If yarn install shows ESOCKETTIMEDOUT:

yarn config set network-timeout 600000 -g
yarn install --network-timeout 600000

# If you changed frontend .env values:

# Stop & restart frontend (Ctrl+C then yarn start) so CRA reloads env vars.

# If backend port 8000 is busy, use another port:

# uvicorn server:app --reload --port 8001

# then update frontend/.env REACT_APP_BACKEND_URL accordingly.

============================================================
Notes
============================================================

- /docs is the BACKEND API docs (FastAPI Swagger UI), not the database.
- MongoDB is the database server at mongodb://127.0.0.1:27017.
- Keep backend + frontend running in two terminals while developing.

Refs:

- CRA dev server is typically started with npm/yarn start. https://create-react-app.dev/docs/getting-started/ [web:247]
- Uvicorn runs FastAPI with: uvicorn module:app --reload --port 8000. https://fastapi.tiangolo.com/deployment/manually/ [web:306]
