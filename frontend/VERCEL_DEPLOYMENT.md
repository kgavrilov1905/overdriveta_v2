# Vercel Deployment Guide

## Environment Variables Required

Set these in Vercel's environment variables section:

```
NEXT_PUBLIC_API_URL=https://your-backend.railway.app
```

## Deployment Steps

1. **Go to [Vercel.com](https://vercel.com)** and sign up with your GitHub account

2. **Import your project:**
   - Click "New Project"
   - Select your GitHub repository
   - Select the **frontend** folder as the root directory

3. **Configure build settings:**
   - Framework Preset: Next.js
   - Root Directory: `frontend`
   - Build Command: `npm run build` (auto-detected)
   - Output Directory: `.next` (auto-detected)

4. **Set environment variables:**
   - Go to Project Settings → Environment Variables
   - Add: `NEXT_PUBLIC_API_URL` with value `https://your-backend.railway.app`

5. **Deploy:** Click "Deploy" and Vercel will build and deploy your frontend!

## Post-Deployment

1. **Update CORS in Railway:**
   - Go to your Railway project
   - Update the `CORS_ORIGINS` environment variable to include your Vercel URL:
   ```
   CORS_ORIGINS=["https://your-frontend.vercel.app"]
   ```

2. **Test your deployment:**
   - Visit your Vercel URL
   - Try sending a query to verify the connection

## Custom Domain (Optional)

1. In Vercel project settings → Domains
2. Add your custom domain
3. Update Railway CORS_ORIGINS accordingly 