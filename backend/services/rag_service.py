# backend/services/rag_service.py
import os
import uuid
import logging
from typing import List, Dict, Any
from pathlib import Path

try:
    import chromadb
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False

class MockEmbeddingFunction:
    def __init__(self):
        self.name = "mock_embedding_fn"
    def __call__(self, input: List[str]) -> List[List[float]]:
        embeddings = []
        for text in input:
            import hashlib
            h = hashlib.sha256(text.encode('utf-8')).hexdigest()
            floats = []
            for idx in range(384):
                val = int(h[idx % len(h)], 16) / 15.0
                floats.append(val)
            embeddings.append(floats)
        return embeddings

logger = logging.getLogger("vyaparai.services.rag_service")

class RAGService:
    def __init__(self):
        self.collection = None
        if not CHROMA_AVAILABLE:
            logger.warning("ChromaDB not available. RAG will be disabled.")
            return

        try:
            # Persistent storage in user home directory to prevent uvicorn reload loop
            db_path = os.path.expanduser("~/.vyapar_chroma_db_mock")
            os.makedirs(db_path, exist_ok=True)
            self.client = chromadb.PersistentClient(path=db_path)
            
            # Using lightweight mock embedding function to avoid sentence-transformers startup hang
            self.embedding_fn = MockEmbeddingFunction()
            
            # Get or create knowledge base collection
            self.collection = self.client.get_or_create_collection(
                name="knowledge_base",
                embedding_function=self.embedding_fn
            )
            logger.info("ChromaDB RAG Service initialized successfully.")
            
            # Auto-ingest system knowledge files if collection is empty in a background thread to prevent blocking startup
            if self.collection.count() == 0:
                import threading
                threading.Thread(target=self.auto_ingest_system_knowledge, daemon=True).start()
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            self.collection = None

    def auto_ingest_system_knowledge(self):
        """Locates the backend/knowledge directory and ingests all markdown files."""
        try:
            knowledge_dir = Path(__file__).resolve().parent.parent / "knowledge"
            if not knowledge_dir.exists():
                logger.warning(f"Knowledge directory {knowledge_dir} does not exist. Skipping auto-ingestion.")
                return
                
            md_files = list(knowledge_dir.glob("*.md"))
            logger.info(f"Found {len(md_files)} system knowledge files to auto-ingest.")
            
            for file_path in md_files:
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        text = f.read()
                    chunks = self.ingest_text(text, source=file_path.name)
                    logger.info(f"Successfully auto-ingested {chunks} chunks from {file_path.name}")
                except Exception as file_err:
                    logger.error(f"Failed to ingest knowledge file {file_path.name}: {file_err}")
        except Exception as e:
            logger.error(f"Error during auto-ingestion of knowledge: {e}")

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
            results = self.collection.get()
            docs = results.get("documents", [])
            metadatas = results.get("metadatas", [])
            if not docs:
                return ""
                
            query_words = set(query.lower().split())
            scored_docs = []
            for doc, meta in zip(docs, metadatas):
                overlap = sum(1 for w in query_words if w in doc.lower())
                scored_docs.append((overlap, doc, meta))
                
            scored_docs.sort(key=lambda x: x[0], reverse=True)
            
            top_results = scored_docs[:top_k]
            
            context_parts = []
            for score, doc, meta in top_results:
                source = meta.get("source", "unknown") if meta else "unknown"
                context_parts.append(f"[KNOWLEDGE LAYER: {source}]\n{doc}")
                
            context = "\n---\n".join(context_parts)
            return context
            
        except Exception as e:
            logger.error(f"RAG Retrieval failed: {e}")
            return ""

rag_svc = RAGService()
