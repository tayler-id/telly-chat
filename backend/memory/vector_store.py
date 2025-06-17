"""Vector store implementation for semantic memory"""

import os
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import numpy as np
from abc import ABC, abstractmethod
import json

# LangChain imports
from langchain.vectorstores import VectorStore as LangChainVectorStore
from langchain.schema import Document
from langchain.embeddings.base import Embeddings
from langchain_openai import OpenAIEmbeddings
from langchain_anthropic import AnthropicEmbeddings

# Vector store implementations
try:
    from langchain_pinecone import PineconeVectorStore
    PINECONE_AVAILABLE = True
except ImportError:
    PINECONE_AVAILABLE = False

try:
    from langchain_chroma import Chroma
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False

try:
    from langchain_community.vectorstores import FAISS
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False


class VectorStoreConfig:
    """Configuration for vector stores"""
    def __init__(
        self,
        store_type: str = "faiss",  # faiss, chroma, pinecone
        embedding_provider: str = "openai",  # openai, anthropic
        embedding_model: Optional[str] = None,
        index_name: Optional[str] = None,
        persist_directory: Optional[str] = None,
        **kwargs
    ):
        self.store_type = store_type
        self.embedding_provider = embedding_provider
        self.embedding_model = embedding_model
        self.index_name = index_name or "telly-chat-memory"
        self.persist_directory = persist_directory or "./vector_stores"
        self.additional_config = kwargs


class VectorStore:
    """Unified interface for vector storage"""
    
    def __init__(self, config: VectorStoreConfig):
        self.config = config
        self.embeddings = self._initialize_embeddings()
        self.store = self._initialize_store()
        
    def _initialize_embeddings(self) -> Embeddings:
        """Initialize embedding model"""
        if self.config.embedding_provider == "openai":
            return OpenAIEmbeddings(
                model=self.config.embedding_model or "text-embedding-3-small"
            )
        elif self.config.embedding_provider == "anthropic":
            # Note: Anthropic doesn't have embeddings yet, using OpenAI as fallback
            print("Warning: Anthropic doesn't provide embeddings, using OpenAI")
            return OpenAIEmbeddings(
                model=self.config.embedding_model or "text-embedding-3-small"
            )
        else:
            raise ValueError(f"Unknown embedding provider: {self.config.embedding_provider}")
    
    def _initialize_store(self) -> LangChainVectorStore:
        """Initialize vector store backend"""
        if self.config.store_type == "faiss" and FAISS_AVAILABLE:
            # Create persist directory if it doesn't exist
            os.makedirs(self.config.persist_directory, exist_ok=True)
            faiss_path = os.path.join(self.config.persist_directory, "faiss_index")
            
            # Try to load existing index
            if os.path.exists(faiss_path):
                return FAISS.load_local(
                    faiss_path, 
                    self.embeddings,
                    allow_dangerous_deserialization=True
                )
            else:
                # Create new index
                return FAISS.from_texts(
                    ["Initial document for index creation"],
                    self.embeddings,
                    metadatas=[{"type": "init", "timestamp": datetime.now().isoformat()}]
                )
                
        elif self.config.store_type == "chroma" and CHROMA_AVAILABLE:
            return Chroma(
                collection_name=self.config.index_name,
                embedding_function=self.embeddings,
                persist_directory=os.path.join(self.config.persist_directory, "chroma")
            )
            
        elif self.config.store_type == "pinecone" and PINECONE_AVAILABLE:
            import pinecone
            # Initialize Pinecone
            pinecone.init(
                api_key=os.getenv("PINECONE_API_KEY"),
                environment=os.getenv("PINECONE_ENV", "us-east-1")
            )
            
            return PineconeVectorStore(
                index_name=self.config.index_name,
                embedding=self.embeddings,
                namespace=self.config.additional_config.get("namespace", "default")
            )
        else:
            available_stores = []
            if FAISS_AVAILABLE:
                available_stores.append("faiss")
            if CHROMA_AVAILABLE:
                available_stores.append("chroma")
            if PINECONE_AVAILABLE:
                available_stores.append("pinecone")
                
            raise ValueError(
                f"Vector store '{self.config.store_type}' not available. "
                f"Available stores: {available_stores}"
            )
    
    def add_memory(
        self, 
        content: str, 
        metadata: Dict[str, Any],
        memory_type: str = "general"
    ) -> str:
        """Add a memory to the vector store"""
        # Enhance metadata
        metadata.update({
            "memory_type": memory_type,
            "timestamp": datetime.now().isoformat(),
            "content_length": len(content)
        })
        
        # Create document
        doc = Document(page_content=content, metadata=metadata)
        
        # Add to store
        ids = self.store.add_documents([doc])
        
        # Persist if using FAISS
        if self.config.store_type == "faiss":
            self.persist()
            
        return ids[0] if ids else None
    
    def search_memories(
        self,
        query: str,
        k: int = 5,
        filter_dict: Optional[Dict[str, Any]] = None,
        memory_type: Optional[str] = None
    ) -> List[Tuple[Document, float]]:
        """Search for relevant memories"""
        # Build filter
        search_filter = filter_dict or {}
        if memory_type:
            search_filter["memory_type"] = memory_type
            
        # Search
        results = self.store.similarity_search_with_score(
            query,
            k=k,
            filter=search_filter if search_filter else None
        )
        
        return results
    
    def get_memory_by_id(self, memory_id: str) -> Optional[Document]:
        """Retrieve a specific memory by ID"""
        # This is store-specific, implementing for FAISS
        if self.config.store_type == "faiss":
            # FAISS doesn't have direct ID lookup, need to search
            # This is a limitation we'll address with a metadata index
            return None
        else:
            # Most vector stores don't support direct ID lookup
            return None
    
    def update_memory(self, memory_id: str, content: str, metadata: Dict[str, Any]) -> bool:
        """Update an existing memory"""
        # Most vector stores don't support updates, need to delete and re-add
        # This is a limitation of current vector stores
        metadata["updated_at"] = datetime.now().isoformat()
        metadata["original_id"] = memory_id
        
        self.add_memory(content, metadata)
        return True
    
    def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory"""
        # Implementation depends on vector store capabilities
        # Most don't support direct deletion by ID
        return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the vector store"""
        stats = {
            "store_type": self.config.store_type,
            "embedding_provider": self.config.embedding_provider,
            "total_memories": 0,  # Store-specific implementation needed
            "index_name": self.config.index_name
        }
        
        return stats
    
    def persist(self):
        """Persist the vector store to disk"""
        if self.config.store_type == "faiss":
            faiss_path = os.path.join(self.config.persist_directory, "faiss_index")
            self.store.save_local(faiss_path)
        elif self.config.store_type == "chroma":
            # Chroma auto-persists
            pass
        elif self.config.store_type == "pinecone":
            # Pinecone is cloud-based, no local persistence needed
            pass
    
    def clear(self):
        """Clear all memories from the store"""
        # Implementation depends on vector store
        if self.config.store_type == "faiss":
            # Recreate empty index
            self.store = FAISS.from_texts(
                ["Initial document for index creation"],
                self.embeddings,
                metadatas=[{"type": "init", "timestamp": datetime.now().isoformat()}]
            )
            self.persist()


class HybridMemorySearch:
    """Hybrid search combining vector similarity and keyword matching"""
    
    def __init__(self, vector_store: VectorStore):
        self.vector_store = vector_store
        
    def search(
        self,
        query: str,
        k: int = 5,
        vector_weight: float = 0.7,
        keyword_weight: float = 0.3,
        filter_dict: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[Document, float]]:
        """Perform hybrid search"""
        # Get vector search results
        vector_results = self.vector_store.search_memories(query, k=k*2, filter_dict=filter_dict)
        
        # Perform keyword matching (simple implementation)
        # In production, use BM25 or similar
        query_words = set(query.lower().split())
        
        # Score and combine results
        scored_results = []
        for doc, vector_score in vector_results:
            # Calculate keyword score
            doc_words = set(doc.page_content.lower().split())
            keyword_score = len(query_words.intersection(doc_words)) / len(query_words)
            
            # Combine scores
            combined_score = (vector_weight * vector_score) + (keyword_weight * keyword_score)
            scored_results.append((doc, combined_score))
        
        # Sort by combined score and return top k
        scored_results.sort(key=lambda x: x[1], reverse=True)
        return scored_results[:k]