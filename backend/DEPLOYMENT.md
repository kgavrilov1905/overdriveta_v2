# Railway Deployment Guide

## Environment Variables Required

Set these in Railway's environment variables section:

```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_anon_key
GOOGLE_API_KEY=your_google_api_key
CORS_ORIGINS=["https://your-frontend-domain.vercel.app"]
ENVIRONMENT=production
DEBUG=false
```

## Deployment Steps

1. Create Railway account at https://railway.app
2. Connect your GitHub repository
3. Select the backend folder as the root directory
4. Set environment variables above
5. Railway will automatically build using the Dockerfile
6. Your API will be available at: https://your-app.railway.app

## Health Check

Once deployed, verify with:
- Health endpoint: `https://your-app.railway.app/health`
- API docs: `https://your-app.railway.app/docs` 