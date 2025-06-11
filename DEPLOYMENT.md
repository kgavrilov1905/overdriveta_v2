# Deployment Guide

## Current Live System

**Status**: ✅ Fully Operational  
**Frontend**: https://overdriveta-v2.vercel.app  
**Backend**: https://overdrivetav2-production-1980.up.railway.app

## Environment Configuration

### Backend (Railway)
```bash
GEMINI_API_KEY=[your_google_api_key]
SUPABASE_URL=[your_supabase_url] 
SUPABASE_KEY=[your_supabase_service_key]
ENVIRONMENT=production
```

### Frontend (Vercel)
```bash
NEXT_PUBLIC_API_URL=[your_backend_url]
```

## Deployment Commands

### Backend to Railway
```bash
cd backend
railway login
railway up --detach
```

### Frontend to Vercel
```bash
cd frontend
vercel login
vercel deploy --prod
```

## Verification Steps

### 1. Backend Health Check
```bash
curl https://overdrivetav2-production-1980.up.railway.app/health
```
**Expected**: `{"status": "healthy", "message": "All systems operational"}`

### 2. Test Query Processing
```bash
curl -X POST "https://overdrivetav2-production-1980.up.railway.app/query/" \
  -H "Content-Type: application/json" \
  -d '{"query": "What are Alberta economic priorities?"}'
```
**Expected**: JSON response with `response`, `sources`, `confidence_score`

### 3. Frontend Connectivity
```bash
curl -I https://overdriveta-v2.vercel.app
```
**Expected**: `200 OK` status

## Troubleshooting

### Backend Issues
- **Environment variables**: Check Railway dashboard settings
- **Logs**: `railway logs` to see startup errors
- **Health**: `/health` endpoint shows service status

### Frontend Issues
- **Build errors**: Check Vercel build logs
- **API connection**: Verify `NEXT_PUBLIC_API_URL` environment variable
- **CORS**: Backend allows specific origins only

### Database Issues
- **Supabase connection**: Check URL and key validity
- **Vector search**: Requires pgvector extension enabled
- **RLS policies**: Ensure proper table permissions

## Production Monitoring

### Health Endpoints
- Backend health: `/health`
- Security status: `/security/status`
- Real-time metrics: `/advanced/analytics/real-time`

### Performance Targets
- Query response time: < 3 seconds
- Uptime: > 99.9%
- Error rate: < 1%

## Rollback Procedure

### Backend Rollback
```bash
railway rollback [deployment-id]
```

### Frontend Rollback
```bash
vercel rollback [deployment-url]
```

## Scaling Considerations

### Current Limits
- Rate limiting: 100 requests/hour per IP
- File upload: 50MB max per file
- Batch processing: 50 documents max

### Database Optimization
- Vector index tuning for large document sets
- Connection pooling for high concurrency
- Read replicas for analytics queries 