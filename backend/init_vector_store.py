#!/usr/bin/env python3
"""Initialize vector store for first run"""

import os
import sys
import faiss
import pickle
from langchain_community.docstore.in_memory import InMemoryDocstore

# Create directories
dir_path = "data/memory/transcripts/vectors/faiss_index"
os.makedirs(dir_path, exist_ok=True)

# Create empty FAISS index
index = faiss.IndexFlatL2(1536)  # 1536 is OpenAI embedding dimension
faiss.write_index(index, os.path.join(dir_path, "index.faiss"))

# Create proper docstore and index_to_docstore_id mapping
docstore = InMemoryDocstore({})
index_to_docstore_id = {}

# Save in the format expected by FAISS.load_local
with open(os.path.join(dir_path, "index.pkl"), "wb") as f:
    pickle.dump((docstore, index_to_docstore_id), f)

print(f"Initialized vector store at {dir_path}")
print("Files created:")
print(f"  - {os.path.join(dir_path, 'index.faiss')}")
print(f"  - {os.path.join(dir_path, 'index.pkl')}")