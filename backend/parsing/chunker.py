"""Text chunking strategies for optimal processing"""

from typing import List, Dict, Any, Optional, Tuple, Callable
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from enum import Enum
import re
import tiktoken
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from .parser import ParsedDocument


class ChunkingStrategy(Enum):
    """Available chunking strategies"""
    FIXED_SIZE = "fixed_size"
    SENTENCE_BASED = "sentence_based"
    PARAGRAPH_BASED = "paragraph_based"
    SEMANTIC = "semantic"
    RECURSIVE = "recursive"
    SLIDING_WINDOW = "sliding_window"


@dataclass
class TextChunk:
    """Represents a text chunk"""
    id: str
    content: str
    start_idx: int
    end_idx: int
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[np.ndarray] = None
    
    @property
    def length(self) -> int:
        """Get chunk length in characters"""
        return len(self.content)
    
    @property
    def word_count(self) -> int:
        """Get word count"""
        return len(self.content.split())
    
    def overlap_with(self, other: 'TextChunk') -> int:
        """Calculate character overlap with another chunk"""
        if self.end_idx <= other.start_idx or other.end_idx <= self.start_idx:
            return 0
        
        overlap_start = max(self.start_idx, other.start_idx)
        overlap_end = min(self.end_idx, other.end_idx)
        
        return overlap_end - overlap_start
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "content": self.content,
            "start_idx": self.start_idx,
            "end_idx": self.end_idx,
            "length": self.length,
            "word_count": self.word_count,
            "metadata": self.metadata
        }


class BaseChunker(ABC):
    """Abstract base class for text chunkers"""
    
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        tokenizer: Optional[Any] = None
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.tokenizer = tokenizer or tiktoken.get_encoding("cl100k_base")
    
    @abstractmethod
    def chunk(self, text: str, **kwargs) -> List[TextChunk]:
        """Chunk text into smaller pieces"""
        pass
    
    def chunk_document(self, document: ParsedDocument, **kwargs) -> List[TextChunk]:
        """Chunk a parsed document"""
        chunks = self.chunk(document.content, **kwargs)
        
        # Add document metadata to chunks
        for chunk in chunks:
            chunk.metadata.update({
                "source": document.source,
                "document_id": document.id,
                "document_format": document.format
            })
        
        return chunks
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        return len(self.tokenizer.encode(text))


class TextChunker(BaseChunker):
    """
    Simple fixed-size text chunker
    
    Features:
    - Fixed character or token-based chunks
    - Configurable overlap
    - Boundary-aware splitting
    """
    
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        use_tokens: bool = False,
        respect_boundaries: bool = True,
        tokenizer: Optional[Any] = None
    ):
        super().__init__(chunk_size, chunk_overlap, tokenizer)
        self.use_tokens = use_tokens
        self.respect_boundaries = respect_boundaries
        
        # Sentence boundary pattern
        self.sentence_end_pattern = re.compile(r'[.!?]\s+')
    
    def chunk(self, text: str, **kwargs) -> List[TextChunk]:
        """Chunk text into fixed-size pieces"""
        if self.use_tokens:
            return self._chunk_by_tokens(text)
        else:
            return self._chunk_by_characters(text)
    
    def _chunk_by_characters(self, text: str) -> List[TextChunk]:
        """Chunk by character count"""
        chunks = []
        start_idx = 0
        chunk_id = 0
        
        while start_idx < len(text):
            # Calculate end index
            end_idx = min(start_idx + self.chunk_size, len(text))
            
            # Adjust for boundaries if needed
            if self.respect_boundaries and end_idx < len(text):
                # Try to end at sentence boundary
                chunk_text = text[start_idx:end_idx]
                last_sentence = self.sentence_end_pattern.search(chunk_text[::-1])
                
                if last_sentence:
                    # Adjust end_idx to sentence boundary
                    end_idx = start_idx + len(chunk_text) - last_sentence.start()
            
            # Create chunk
            chunk_content = text[start_idx:end_idx].strip()
            
            if chunk_content:
                chunk = TextChunk(
                    id=f"chunk_{chunk_id}",
                    content=chunk_content,
                    start_idx=start_idx,
                    end_idx=end_idx,
                    metadata={
                        "chunk_method": "character",
                        "chunk_size": self.chunk_size
                    }
                )
                chunks.append(chunk)
                chunk_id += 1
            
            # Move to next chunk with overlap
            start_idx = end_idx - self.chunk_overlap
            
            # Ensure progress
            if start_idx >= end_idx - 10:
                start_idx = end_idx
        
        return chunks
    
    def _chunk_by_tokens(self, text: str) -> List[TextChunk]:
        """Chunk by token count"""
        # Tokenize entire text
        tokens = self.tokenizer.encode(text)
        chunks = []
        chunk_id = 0
        
        # Track character positions
        char_positions = self._get_token_char_positions(text, tokens)
        
        start_token_idx = 0
        
        while start_token_idx < len(tokens):
            # Calculate end token index
            end_token_idx = min(start_token_idx + self.chunk_size, len(tokens))
            
            # Get character positions
            start_char_idx = char_positions[start_token_idx]
            end_char_idx = char_positions[end_token_idx] if end_token_idx < len(char_positions) else len(text)
            
            # Extract chunk text
            chunk_content = text[start_char_idx:end_char_idx].strip()
            
            if chunk_content:
                chunk = TextChunk(
                    id=f"chunk_{chunk_id}",
                    content=chunk_content,
                    start_idx=start_char_idx,
                    end_idx=end_char_idx,
                    metadata={
                        "chunk_method": "token",
                        "chunk_size": self.chunk_size,
                        "token_count": end_token_idx - start_token_idx
                    }
                )
                chunks.append(chunk)
                chunk_id += 1
            
            # Move to next chunk with overlap
            start_token_idx = end_token_idx - self.chunk_overlap
            
            # Ensure progress
            if start_token_idx >= end_token_idx - 10:
                start_token_idx = end_token_idx
        
        return chunks
    
    def _get_token_char_positions(self, text: str, tokens: List[int]) -> List[int]:
        """Map token indices to character positions"""
        # Decode tokens one by one to find positions
        positions = []
        current_pos = 0
        
        for i in range(len(tokens)):
            # Decode tokens up to this point
            decoded = self.tokenizer.decode(tokens[:i])
            positions.append(len(decoded))
        
        return positions


class SemanticChunker(BaseChunker):
    """
    Semantic-based text chunker using embeddings
    
    Features:
    - Groups semantically similar sentences
    - Dynamic chunk sizes based on content
    - Maintains semantic coherence
    """
    
    def __init__(
        self,
        embedding_fn: Callable[[str], np.ndarray],
        similarity_threshold: float = 0.7,
        min_chunk_size: int = 100,
        max_chunk_size: int = 1500,
        tokenizer: Optional[Any] = None
    ):
        super().__init__(max_chunk_size, 0, tokenizer)
        self.embedding_fn = embedding_fn
        self.similarity_threshold = similarity_threshold
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        
        # Sentence splitter
        self.sentence_splitter = re.compile(r'(?<=[.!?])\s+')
    
    def chunk(self, text: str, **kwargs) -> List[TextChunk]:
        """Chunk text based on semantic similarity"""
        # Split into sentences
        sentences = self.sentence_splitter.split(text)
        
        if not sentences:
            return []
        
        # Get embeddings for each sentence
        embeddings = []
        for sentence in sentences:
            if sentence.strip():
                embedding = self.embedding_fn(sentence)
                embeddings.append(embedding)
            else:
                embeddings.append(None)
        
        # Group sentences into chunks
        chunks = []
        current_chunk = []
        current_chunk_embedding = None
        chunk_start_idx = 0
        char_position = 0
        chunk_id = 0
        
        for i, (sentence, embedding) in enumerate(zip(sentences, embeddings)):
            if not sentence.strip() or embedding is None:
                char_position += len(sentence) + 1
                continue
            
            # Check if we should start a new chunk
            should_split = False
            
            if not current_chunk:
                # First sentence in chunk
                current_chunk = [sentence]
                current_chunk_embedding = embedding
                chunk_start_idx = char_position
            else:
                # Calculate similarity with current chunk
                chunk_text = " ".join(current_chunk)
                
                # Check size constraints
                if len(chunk_text) + len(sentence) > self.max_chunk_size:
                    should_split = True
                elif len(chunk_text) >= self.min_chunk_size:
                    # Check semantic similarity
                    similarity = cosine_similarity(
                        [current_chunk_embedding],
                        [embedding]
                    )[0][0]
                    
                    if similarity < self.similarity_threshold:
                        should_split = True
                
                if not should_split:
                    # Add to current chunk
                    current_chunk.append(sentence)
                    # Update chunk embedding (average)
                    current_chunk_embedding = (
                        current_chunk_embedding * (len(current_chunk) - 1) + embedding
                    ) / len(current_chunk)
                else:
                    # Save current chunk
                    chunk_content = " ".join(current_chunk)
                    chunk = TextChunk(
                        id=f"chunk_{chunk_id}",
                        content=chunk_content,
                        start_idx=chunk_start_idx,
                        end_idx=char_position,
                        metadata={
                            "chunk_method": "semantic",
                            "sentence_count": len(current_chunk),
                            "similarity_threshold": self.similarity_threshold
                        },
                        embedding=current_chunk_embedding
                    )
                    chunks.append(chunk)
                    chunk_id += 1
                    
                    # Start new chunk
                    current_chunk = [sentence]
                    current_chunk_embedding = embedding
                    chunk_start_idx = char_position
            
            char_position += len(sentence) + 1
        
        # Save final chunk
        if current_chunk:
            chunk_content = " ".join(current_chunk)
            chunk = TextChunk(
                id=f"chunk_{chunk_id}",
                content=chunk_content,
                start_idx=chunk_start_idx,
                end_idx=char_position,
                metadata={
                    "chunk_method": "semantic",
                    "sentence_count": len(current_chunk),
                    "similarity_threshold": self.similarity_threshold
                },
                embedding=current_chunk_embedding
            )
            chunks.append(chunk)
        
        return chunks


class RecursiveChunker(BaseChunker):
    """
    Recursive text chunker that respects document structure
    
    Features:
    - Hierarchical splitting by separators
    - Preserves document structure
    - Adaptable to different formats
    """
    
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        separators: Optional[List[str]] = None,
        tokenizer: Optional[Any] = None
    ):
        super().__init__(chunk_size, chunk_overlap, tokenizer)
        
        # Default separators in order of preference
        self.separators = separators or [
            "\n\n\n",  # Multiple blank lines
            "\n\n",    # Paragraph break
            "\n",      # Line break
            ". ",      # Sentence end
            ", ",      # Clause break
            " ",       # Word break
            ""         # Character level
        ]
    
    def chunk(self, text: str, **kwargs) -> List[TextChunk]:
        """Recursively chunk text using separators"""
        chunks = self._recursive_chunk(text, self.separators)
        
        # Post-process chunks
        final_chunks = []
        chunk_id = 0
        char_position = 0
        
        for chunk_text in chunks:
            if chunk_text.strip():
                chunk = TextChunk(
                    id=f"chunk_{chunk_id}",
                    content=chunk_text.strip(),
                    start_idx=char_position,
                    end_idx=char_position + len(chunk_text),
                    metadata={
                        "chunk_method": "recursive",
                        "chunk_size": self.chunk_size
                    }
                )
                final_chunks.append(chunk)
                chunk_id += 1
            
            char_position += len(chunk_text)
        
        return final_chunks
    
    def _recursive_chunk(
        self,
        text: str,
        separators: List[str],
        **kwargs
    ) -> List[str]:
        """Recursively split text"""
        final_chunks = []
        
        # Use the first separator that works
        separator = separators[0] if separators else ""
        
        # Try to split by separator
        if separator:
            splits = text.split(separator)
        else:
            # Character level splitting
            splits = list(text)
        
        # Process each split
        current_chunk = ""
        
        for split in splits:
            # Check if adding this split exceeds chunk size
            if self._get_size(current_chunk + separator + split) <= self.chunk_size:
                current_chunk += (separator if current_chunk else "") + split
            else:
                # Current chunk is full
                if current_chunk:
                    final_chunks.append(current_chunk)
                
                # Check if split itself is too large
                if self._get_size(split) > self.chunk_size:
                    # Need to split further
                    if len(separators) > 1:
                        # Use next separator
                        sub_chunks = self._recursive_chunk(
                            split,
                            separators[1:],
                            **kwargs
                        )
                        final_chunks.extend(sub_chunks)
                    else:
                        # Force split at chunk size
                        force_chunks = self._force_split(split)
                        final_chunks.extend(force_chunks)
                else:
                    current_chunk = split
        
        # Add final chunk
        if current_chunk:
            final_chunks.append(current_chunk)
        
        # Merge small chunks if needed
        final_chunks = self._merge_chunks(final_chunks)
        
        return final_chunks
    
    def _get_size(self, text: str) -> int:
        """Get size of text (characters or tokens)"""
        return len(text)  # Simple character count
    
    def _force_split(self, text: str) -> List[str]:
        """Force split text at chunk size"""
        chunks = []
        
        for i in range(0, len(text), self.chunk_size - self.chunk_overlap):
            chunk = text[i:i + self.chunk_size]
            if chunk:
                chunks.append(chunk)
        
        return chunks
    
    def _merge_chunks(self, chunks: List[str]) -> List[str]:
        """Merge small chunks to reach minimum size"""
        if not chunks:
            return chunks
        
        merged = []
        current = chunks[0]
        
        for chunk in chunks[1:]:
            # Try to merge with current
            if self._get_size(current + " " + chunk) <= self.chunk_size:
                current += " " + chunk
            else:
                merged.append(current)
                current = chunk
        
        if current:
            merged.append(current)
        
        return merged


def create_chunker(
    strategy: ChunkingStrategy,
    **kwargs
) -> BaseChunker:
    """Factory function to create chunkers"""
    if strategy == ChunkingStrategy.FIXED_SIZE:
        return TextChunker(**kwargs)
    elif strategy == ChunkingStrategy.SEMANTIC:
        if "embedding_fn" not in kwargs:
            raise ValueError("Semantic chunker requires embedding_fn")
        return SemanticChunker(**kwargs)
    elif strategy == ChunkingStrategy.RECURSIVE:
        return RecursiveChunker(**kwargs)
    else:
        raise ValueError(f"Unknown chunking strategy: {strategy}")