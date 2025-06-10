-- Alberta Perspectives RAG Database Schema
-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;

-- Documents table
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
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
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
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
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    chunk_id UUID REFERENCES chunks(id) ON DELETE CASCADE,
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    embedding vector(768), -- text-embedding-004 has 768 dimensions
    model_name VARCHAR(100) DEFAULT 'text-embedding-004',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_documents_file_name ON documents(file_name);
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(processing_status);
CREATE INDEX IF NOT EXISTS idx_documents_created_at ON documents(created_at);
CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_chunks_chunk_index ON chunks(chunk_index);
CREATE INDEX IF NOT EXISTS idx_chunks_page_number ON chunks(page_number);
CREATE INDEX IF NOT EXISTS idx_embeddings_chunk_id ON embeddings(chunk_id);
CREATE INDEX IF NOT EXISTS idx_embeddings_document_id ON embeddings(document_id);

-- Create vector similarity search index
CREATE INDEX IF NOT EXISTS idx_embeddings_vector 
ON embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Drop existing similarity search function if it exists
DROP FUNCTION IF EXISTS similarity_search(vector, double precision, integer);
DROP FUNCTION IF EXISTS similarity_search(vector, float, int);

-- Function for similarity search
CREATE OR REPLACE FUNCTION similarity_search(
    query_embedding vector(768),
    match_threshold float DEFAULT 0.75,
    match_count int DEFAULT 5
)
RETURNS TABLE (
    chunk_id uuid,
    document_id uuid,
    content text,
    similarity_score float,
    document_name text,
    page_number int,
    metadata jsonb
)
LANGUAGE sql
AS $$
    SELECT 
        c.id as chunk_id,
        c.document_id,
        c.content,
        (1 - (e.embedding <=> query_embedding)) as similarity_score,
        d.file_name as document_name,
        c.page_number,
        c.metadata
    FROM embeddings e
    JOIN chunks c ON e.chunk_id = c.id
    JOIN documents d ON c.document_id = d.id
    WHERE (1 - (e.embedding <=> query_embedding)) > match_threshold
    ORDER BY e.embedding <=> query_embedding
    LIMIT match_count;
$$;

-- Function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger for documents table
CREATE TRIGGER update_documents_updated_at
    BEFORE UPDATE ON documents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Enable Row Level Security (RLS)
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE embeddings ENABLE ROW LEVEL SECURITY;

-- Create policies (allow all operations for anon and service role users)
DROP POLICY IF EXISTS "Allow all operations on documents" ON documents;
CREATE POLICY "Allow all operations on documents" 
ON documents FOR ALL TO anon, service_role USING (true);

DROP POLICY IF EXISTS "Allow all operations on chunks" ON chunks;
CREATE POLICY "Allow all operations on chunks" 
ON chunks FOR ALL TO anon, service_role USING (true);

DROP POLICY IF EXISTS "Allow all operations on embeddings" ON embeddings;
CREATE POLICY "Allow all operations on embeddings" 
ON embeddings FOR ALL TO anon, service_role USING (true); 