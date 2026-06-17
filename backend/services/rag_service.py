# backend/services/rag_service.py
import os
import uuid
import logging
from typing import List, Dict, Any
from pathlib import Path

try:
    import chromadb
    from chromadb.utils import embedding_functions
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False

logger = logging.getLogger("vyaparai.services.rag_service")

class RAGService:
    def __init__(self):
        self.collection = None
        if not CHROMA_AVAILABLE:
            logger.warning("ChromaDB not available. RAG will be disabled.")
            return

        try:
            # Persistent storage in backend/database/chroma_db
            db_path = str(Path(__file__).resolve().parent.parent / "database" / "chroma_db")
            os.makedirs(db_path, exist_ok=True)
            self.client = chromadb.PersistentClient(path=db_path)
            
            # Using default sentence-transformers embedding function (all-MiniLM-L6-v2)
            self.embedding_fn = embedding_functions.DefaultEmbeddingFunction()
            
            # Get or create knowledge base collection
            self.collection = self.client.get_or_create_collection(
                name="knowledge_base",
                embedding_function=self.embedding_fn
            )
            logger.info("ChromaDB RAG Service initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            self.collection = None

    def ingest_text(self, text: str, source: str = "upload") -> int:
        """Chunk the document and save to vector store."""
        if not self.collection:
            logger.warning("RAG disabled, cannot ingest text.")
            return 0

        # Simple chunking by paragraphs
        chunks = []
        paragraphs = [p.strip() for p in text.split("\n\n") if len(p.strip()) > 10]
        
        for p in paragraphs:
            if len(p) > 1000:
                words = p.split()
                chunk = []
                chunk_len = 0
                for w in words:
                    if chunk_len + len(w) > 800:
                        chunks.append(" ".join(chunk))
                        chunk = [w]
                        chunk_len = len(w)
                    else:
                        chunk.append(w)
                        chunk_len += len(w) + 1
                if chunk:
                    chunks.append(" ".join(chunk))
            else:
                chunks.append(p)
                
        if not chunks:
            return 0
            
        ids = [f"doc_{uuid.uuid4().hex[:10]}" for _ in chunks]
        metadatas = [{"source": source} for _ in chunks]
        
        self.collection.add(
            documents=chunks,
            metadatas=metadatas,
            ids=ids
        )
        logger.info(f"Ingested {len(chunks)} chunks into vector store.")
        return len(chunks)

    def retrieve(self, query: str, top_k: int = 3) -> str:
        """Search vector database and return formatted context."""
        if not self.collection:
            return ""
            
        if self.collection.count() == 0:
            return ""

        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=top_k
            )
            
            docs = results.get("documents", [[]])[0]
            if not docs:
                return ""
                
            context = "\n---\n".join(docs)
            return context
            
        except Exception as e:
            logger.error(f"RAG Retrieval failed: {e}")
            return ""

rag_svc = RAGService()
