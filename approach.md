# Technical Approach - Alberta Economic Research RAG System

## System Overview
RAG system for Alberta economic research documents with AI-powered chat interface.

**Live URLs:**
- Frontend: https://overdriveta-v2.vercel.app
- Backend: https://overdrivetav2-production-1980.up.railway.app

## Architecture

```
Frontend (Vercel)     Backend (Railway)      External Services
Next.js 15         ←→ FastAPI + Python   ←→ Google Gemini 2.0
Tailwind CSS           RAG Pipeline          Supabase Vector DB
iOS Messages UI        Document Processing   pgvector
```

## Technology Stack

### Backend
- **FastAPI**: High-performance async API framework
- **Railway**: Container deployment platform
- **Python 3.11**: Runtime environment
- **Supabase**: PostgreSQL with vector extensions

### Frontend  
- **Next.js 15**: React framework with App Router
- **Vercel**: Deployment and hosting
- **Tailwind CSS v3**: Utility-first styling
- **TypeScript**: Type-safe development

### AI/ML
- **Google Gemini 2.0 Flash**: LLM for response generation
- **sentence-transformers**: Text embeddings
- **pgvector**: Vector similarity search

## Implementation Details

### Document Processing
1. **Upload**: Validates .pdf/.pptx files (50MB max)
2. **Extract**: Text extraction preserving page structure
3. **Chunk**: Semantic chunking (500-1000 chars)
4. **Embed**: Generate 384-dimension vectors
5. **Store**: Save to Supabase with metadata

### Query Pipeline
1. **Embed**: Convert query to vector
2. **Search**: Find similar chunks (cosine similarity)
3. **Context**: Assemble relevant content
4. **Generate**: LLM response with sources
5. **Return**: Structured response with metadata

### Key Features Implemented

**High Priority (Production Ready):**
- ✅ API key validation and security middleware
- ✅ Enhanced error handling with circuit breakers  
- ✅ LLM safety configuration and content filtering
- ✅ Input validation and sanitization
- ✅ Advanced query prompting for Alberta context
- ✅ Document validation and preprocessing

**Medium Priority (Deployed):**
- ✅ Document deduplication system
- ✅ Real-time analytics dashboard
- ✅ Advanced search with faceted filtering
- ✅ Batch document processing
- ✅ Business intelligence reporting

## API Endpoints

### Core Features
- `POST /query/` - Process user queries
- `POST /documents/upload` - Upload documents
- `GET /health` - System health check

### Advanced Features  
- `GET /advanced/analytics/dashboard` - Analytics data
- `POST /advanced/search` - Advanced search
- `POST /advanced/deduplication/check` - Duplicate detection
- `GET /advanced/business/insights` - Business metrics

## Database Schema

```sql
-- Documents table
documents (id, file_name, content_type, file_size, 
          processing_status, metadata, created_at)

-- Text chunks
chunks (id, document_id, content, page_number, 
       embedding vector(384), metadata)

-- Vector search index
CREATE INDEX ON chunks USING ivfflat (embedding vector_cosine_ops);
```

## Security & Performance

### Security
- Rate limiting (100 req/hour per IP)
- Input sanitization and XSS protection
- API key validation
- Content safety filtering
- CORS restriction to specific domains

### Performance
- Async processing with background tasks
- Vector similarity search optimization
- Response caching strategies
- Circuit breaker for database failures

## Business Value

### Cost Optimization
- Document deduplication prevents redundant storage
- Batch processing reduces overhead
- Analytics identify optimization opportunities

### User Experience
- Sub-3-second response times
- iOS Messages-style interface
- Advanced search with filtering
- Query suggestions and auto-complete

### Analytics & Insights
- Real-time usage metrics
- Business intelligence reporting
- ROI calculation and time savings
- Performance monitoring

## Deployment

### Backend (Railway)
```bash
railway up --detach
```

### Frontend (Vercel)
```bash
vercel deploy --prod
```

### Environment Variables
```bash
# Backend
GEMINI_API_KEY=AIzaSyBMo6D7Iiv1pWWPPZzLNf57ijwbkwVnB5s
SUPABASE_URL=https://aaegatfojqyfronbkpgn.supabase.co
SUPABASE_KEY=[jwt_token]

# Frontend  
NEXT_PUBLIC_API_URL=https://overdrivetav2-production-1980.up.railway.app
```

## Current Status
- **Backend**: Fully operational with advanced features
- **Frontend**: iOS Messages UI, responsive design
- **Database**: 3 sample documents loaded and indexed
- **AI Pipeline**: End-to-end RAG working with high confidence
- **Analytics**: Real-time metrics and business reporting
- **Security**: Production-grade validation and protection
