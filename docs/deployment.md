# Deployment Guide

This document outlines the deployment strategy for the AI Restaurant Recommender system. The application is decoupled into a vanilla frontend and a FastAPI backend. We deploy the frontend to **Vercel** and the backend to **Render**.

## Backend Deployment (Render)

The backend is a FastAPI application that serves the AI recommendations and manages the database.

### Prerequisites
- A Render account (https://render.com)
- Your GitHub repository linked to Render

### Steps

1. **Create a New Web Service:**
   - Log in to your Render dashboard.
   - Click **New +** and select **Web Service**.
   - Connect your GitHub repository.

2. **Configure the Service:**
   - **Name:** Choose a descriptive name (e.g., `restaurant-recommender-api`).
   - **Environment:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn phase6.backend.api:app --host 0.0.0.0 --port $PORT`
   
3. **Environment Variables:**
   Under the **Environment** tab, add the necessary environment variables required for the backend to function:
   - `GROQ_API_KEY`: Your Groq API key for LLM generation.
   - `HF_TOKEN`: Your Hugging Face token (if required for data or models).
   - Any other variables present in your local `.env`.

4. **Deploy:**
   - Click **Create Web Service**. 
   - Render will build and deploy the application.
   - Once deployed, note the **external URL** (e.g., `https://restaurant-recommender-api.onrender.com`). You will need this for the frontend configuration.

---

## Frontend Deployment (Vercel)

The frontend is a vanilla HTML/CSS/JS application located in the `phase6/frontend` directory.

### Prerequisites
- A Vercel account (https://vercel.com)
- Vercel CLI (optional, but recommended for easy local configuration)
- The deployed backend URL from Render.

### Frontend Configuration Update

Before deploying, ensure your frontend JavaScript (`phase6/frontend/index.html` or any extracted JS file) points to the correct Render backend URL. 

*If your frontend currently points to `http://localhost:8000`, you should update it to point to your new Render URL.*

### Steps (Using Vercel Dashboard)

1. **Import Project:**
   - Go to your Vercel dashboard and click **Add New... > Project**.
   - Import your GitHub repository.

2. **Configure Project:**
   - **Project Name:** Choose a name (e.g., `restaurant-recommender-ui`).
   - **Framework Preset:** `Other`
   - **Root Directory:** Click **Edit** and select `phase6/frontend` as the root directory.

3. **Build and Output Settings:**
   - **Build Command:** Leave empty (or override and leave blank), as this is a vanilla frontend with no build step required.
   - **Output Directory:** Leave empty or set to the default.

4. **Deploy:**
   - Click **Deploy**. Vercel will process the static files and provide a live URL.

### Local Development vs Production Note

> [!WARNING]
> Remember to handle CORS. Ensure that your FastAPI backend on Render includes the deployed Vercel frontend URL in its list of allowed origins.

```python
# In phase6/backend/api.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "https://your-vercel-frontend-url.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```
