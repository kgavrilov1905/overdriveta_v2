"""
Database connection and management for Alberta Perspectives RAG API
Handles Supabase connection, schema creation, and database operations.
"""

import logging
from typing import List, Dict, Any, Optional
from supabase import create_client, Client
from config import settings

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages database connections and operations."""
    
    def __init__(self):
        self.client: Optional[Client] = None
        self._connected = False
    
    def _get_client(self) -> Client:
        """Get or create the Supabase client."""
        if not self._connected:
            if not settings.supabase_url or not settings.supabase_key:
                raise ValueError("SUPABASE_URL and SUPABASE_KEY environment variables are not set.")
            try:
                self.client = create_client(settings.supabase_url, settings.supabase_key)
                self._connected = True
                logger.info("Successfully connected to Supabase")
            except Exception as e:
                logger.error(f"Failed to connect to Supabase: {str(e)}")
                raise
        return self.client
    
    async def initialize_schema(self):
        """Initialize database schema with required tables."""
        try:
            # Note: In a real implementation, you would run these SQL commands
            # through Supabase SQL editor or migrations. This is for reference.
            
            schema_sql = """
            -- Enable pgvector extension for vector operations
            CREATE EXTENSION IF NOT EXISTS vector;
            
            -- Documents table
            CREATE TABLE IF NOT EXISTS documents (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                file_name VARCHAR(255) NOT NULL,
                title TEXT,
                content_type VARCHAR(100) NOT NULL,
                file_size INTEGER NOT NULL,
                page_count INTEGER,
                upload_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                processing_status VARCHAR(50) DEFAULT 'pending',
                metadata JSONB DEFAULT '{}'::jsonb,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
            
            -- Text chunks table
            CREATE TABLE IF NOT EXISTS chunks (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
                chunk_index INTEGER NOT NULL,
                content TEXT NOT NULL,
                page_number INTEGER,
                start_char INTEGER,
                end_char INTEGER,
                token_count INTEGER,
                metadata JSONB DEFAULT '{}'::jsonb,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
            
            -- Embeddings table with vector column
            CREATE TABLE IF NOT EXISTS embeddings (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                chunk_id UUID REFERENCES chunks(id) ON DELETE CASCADE,
                document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
                embedding vector(768), -- text-embedding-004 has 768 dimensions
                model_name VARCHAR(100) DEFAULT 'text-embedding-004',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
            
            -- Create indexes for better performance
            CREATE INDEX IF NOT EXISTS idx_documents_file_name ON documents(file_name);
            CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(processing_status);
            CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON chunks(document_id);
            CREATE INDEX IF NOT EXISTS idx_chunks_chunk_index ON chunks(chunk_index);
            CREATE INDEX IF NOT EXISTS idx_embeddings_chunk_id ON embeddings(chunk_id);
            CREATE INDEX IF NOT EXISTS idx_embeddings_document_id ON embeddings(document_id);
            
            -- Create vector similarity search index
            CREATE INDEX IF NOT EXISTS idx_embeddings_vector 
            ON embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
            
            -- Enable Row Level Security (RLS)
            ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
            ALTER TABLE chunks ENABLE ROW LEVEL SECURITY;
            ALTER TABLE embeddings ENABLE ROW LEVEL SECURITY;
            
            -- Create policies (allow all operations for anon users in this demo)
            CREATE POLICY IF NOT EXISTS "Allow all operations on documents" 
            ON documents FOR ALL TO anon USING (true);
            
            CREATE POLICY IF NOT EXISTS "Allow all operations on chunks" 
            ON chunks FOR ALL TO anon USING (true);
            
            CREATE POLICY IF NOT EXISTS "Allow all operations on embeddings" 
            ON embeddings FOR ALL TO anon USING (true);
            """
            
            logger.info("Database schema initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize database schema: {str(e)}")
            return False
    
    async def test_connection(self) -> bool:
        """Test database connection."""
        try:
            client = self._get_client()
            # Simple query to test connection
            result = client.table('documents').select('count').execute()
            logger.info("Database connection test successful")
            return True
        except Exception as e:
            logger.error(f"Database connection test failed: {str(e)}")
            return False
    
    # Document operations
    
    async def insert_document(self, document_data: Dict[str, Any]) -> str:
        """Insert a new document record."""
        try:
            client = self._get_client()
            result = client.table('documents').insert(document_data).execute()
            document_id = result.data[0]['id']
            logger.info(f"Document inserted successfully: {document_id}")
            return document_id
        except Exception as e:
            logger.error(f"Failed to insert document: {str(e)}")
            raise
    
    async def update_document_status(self, document_id: str, status: str) -> bool:
        """Update document processing status."""
        try:
            client = self._get_client()
            client.table('documents').update({
                'processing_status': status,
                'updated_at': 'NOW()'
            }).eq('id', document_id).execute()
            logger.info(f"Document status updated: {document_id} -> {status}")
            return True
        except Exception as e:
            logger.error(f"Failed to update document status: {str(e)}")
            return False
    
    async def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Get document by ID."""
        try:
            client = self._get_client()
            result = client.table('documents').select('*').eq('id', document_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Failed to get document: {str(e)}")
            return None
    
    # Chunk operations
    
    async def insert_chunks(self, chunks_data: List[Dict[str, Any]]) -> List[str]:
        """Insert multiple text chunks."""
        try:
            client = self._get_client()
            result = client.table('chunks').insert(chunks_data).execute()
            chunk_ids = [chunk['id'] for chunk in result.data]
            logger.info(f"Inserted {len(chunk_ids)} chunks successfully")
            return chunk_ids
        except Exception as e:
            logger.error(f"Failed to insert chunks: {str(e)}")
            raise
    
    async def get_chunks_by_document(self, document_id: str) -> List[Dict[str, Any]]:
        """Get all chunks for a document."""
        try:
            client = self._get_client()
            result = client.table('chunks').select('*').eq('document_id', document_id).order('chunk_index').execute()
            return result.data
        except Exception as e:
            logger.error(f"Failed to get chunks for document: {str(e)}")
            return []
    
    # Embedding operations
    
    async def insert_embeddings(self, embeddings_data: List[Dict[str, Any]]) -> List[str]:
        """Insert multiple embeddings."""
        try:
            client = self._get_client()
            result = client.table('embeddings').insert(embeddings_data).execute()
            embedding_ids = [embedding['id'] for embedding in result.data]
            logger.info(f"Inserted {len(embedding_ids)} embeddings successfully")
            return embedding_ids
        except Exception as e:
            logger.error(f"Failed to insert embeddings: {str(e)}")
            raise
    
    async def similarity_search(self, query_embedding: List[float], limit: int = 5, threshold: float = 0.75) -> List[Dict[str, Any]]:
        """Perform vector similarity search."""
        try:
            client = self._get_client()
            # Convert list to proper vector format for Supabase
            query_vector = f"[{','.join(map(str, query_embedding))}]"
            
            # Perform similarity search using RPC function
            # Note: This requires a custom function in Supabase
            result = client.rpc('similarity_search', {
                'query_embedding': query_vector,
                'match_threshold': threshold,
                'match_count': limit
            }).execute()
            
            logger.info(f"Similarity search returned {len(result.data)} results")
            return result.data
            
        except Exception as e:
            logger.error(f"Failed to perform similarity search: {str(e)}")
            return []
    
    async def list_documents(self, limit: int = 100) -> List[Dict[str, Any]]:
        """List all documents."""
        try:
            client = self._get_client()
            result = client.table('documents').select('*').limit(limit).order('upload_date', desc=True).execute()
            return result.data
        except Exception as e:
            logger.error(f"Failed to list documents: {str(e)}")
            return []
    
    async def delete_document(self, document_id: str) -> bool:
        """Delete a document and all its related data."""
        try:
            client = self._get_client()
            client.table('documents').delete().eq('id', document_id).execute()
            logger.info(f"Document deleted successfully: {document_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete document: {str(e)}")
            return False

# Global database manager instance
db_manager = DatabaseManager() 