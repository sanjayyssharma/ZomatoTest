# Deployment Guide

This guide outlines the process for deploying the AI Restaurant Recommender's decoupled architecture:
1. **Backend** (FastAPI) on **Railway**
2. **Frontend** (HTML/CSS/JS) on **Vercel**

---

## 1. Backend Deployment (Railway)

We use Railway to host the FastAPI application because it natively supports Python and easily handles environment variables and automatic builds via Nixpacks.

### Prerequisites
- A Railway account linked to your GitHub.
- The `requirements.txt` must contain all backend dependencies (e.g., `fastapi`, `uvicorn`, `groq`).

### Steps
1. **Create a New Project**:
   - Go to the [Railway Dashboard](https://railway.app/dashboard).
   - Click **New Project** > **Deploy from GitHub repo**.
   - Select the `basicRepository` repository.

2. **Configure the Service**:
   - Railway will automatically detect the `railway.toml` file in the root directory.
   - This file configures the build process and sets the start command (`uvicorn phase6.backend.api:app --host 0.0.0.0 --port $PORT`).
   - *No manual configuration of the start command is needed.*

3. **Environment Variables**:
   - Navigate to the **Variables** tab for the service.
   - Add the necessary environment variables:
     - `GROQ_API_KEY`: Your Groq API token.
     - `ENVIRONMENT`: `production` (optional, if your app uses it).

4. **Generate Public URL**:
   - Go to the **Settings** tab.
   - Under **Environment** > **Domains**, click **Generate Domain** to get a public URL for your backend (e.g., `https://my-backend-app.up.railway.app`).
   - Copy this URL. You will need it for the Frontend deployment.

---

## 2. Frontend Deployment (Vercel)

We use Vercel for the frontend to seamlessly host the static files and to proxy API requests to our Railway backend, resolving any CORS issues smoothly.

### Prerequisites
- A Vercel account linked to your GitHub.
- The Railway backend URL obtained in the previous step.

### Steps
1. **Create a New Project**:
   - Go to the [Vercel Dashboard](https://vercel.com/dashboard).
   - Click **Add New** > **Project**.
   - Import the `basicRepository` repository.

2. **Configure the Project Build**:
   - In the **Configure Project** step, open the **Root Directory** section.
   - Click **Edit** and select the `phase6/frontend` directory.
   - Ensure the Framework Preset is set to **Other** (since we are deploying raw HTML/JS).
   - *No Build Command or Output Directory overrides are needed.*

3. **Configure Environment Variables**:
   - Expand the **Environment Variables** section.
   - Add a new variable to define your backend API:
     - **Name**: `RAILWAY_BACKEND_URL`
     - **Value**: The URL you generated in Railway (e.g., `https://my-backend-app.up.railway.app`). Ensure there is **no trailing slash**.
   - *Note: The `vercel.json` rewrite configuration will automatically use this URL to proxy requests.*

4. **Deploy**:
   - Click **Deploy**. Vercel will build and assign a domain.
   - Once complete, visit the domain to interact with your production application.

---

## Architecture Summary
- **Client Request**: User visits the Vercel app and makes a search.
- **Frontend Fetch**: The browser sends a `POST` request to `/api/recommend`.
- **Vercel Rewrite**: Vercel acts as a reverse proxy, intercepting `/api/*` and securely forwarding it to `https://<RAILWAY_BACKEND_URL>/api/*`.
- **Backend Processing**: The Railway FastAPI app receives the request, calls Groq, processes the database, and returns the JSON payload.
