"""Configuration for Telly Chat features"""

import os
from typing import Dict, Any

# Feature flags from environment
ENABLE_MEMORY = os.getenv("ENABLE_MEMORY", "false").lower() == "true"
ENABLE_WORKFLOWS = os.getenv("ENABLE_WORKFLOWS", "false").lower() == "true"
ENABLE_THREADS = os.getenv("ENABLE_THREADS", "false").lower() == "true"

# Memory configuration
MEMORY_CONFIG = {
    "short_term_capacity": int(os.getenv("MEMORY_SHORT_TERM_CAPACITY", "200")),
    "vector_store_type": os.getenv("MEMORY_VECTOR_STORE", "faiss"),
    "embedding_provider": os.getenv("MEMORY_EMBEDDING_PROVIDER", "openai"),
    "persist_directory": os.getenv("MEMORY_PERSIST_DIR", "./data/memory"),
    "episode_dir": os.getenv("MEMORY_EPISODE_DIR", "./data/memory/episodes"),
    "transcript_dir": os.getenv("MEMORY_TRANSCRIPT_DIR", "./data/memory/transcripts"),
    "consolidation_threshold": int(os.getenv("MEMORY_CONSOLIDATION_THRESHOLD", "3"))
}

# Workflow configuration
WORKFLOW_CONFIG = {
    "max_concurrent": int(os.getenv("WORKFLOW_MAX_CONCURRENT", "10")),
    "queue_size": int(os.getenv("WORKFLOW_QUEUE_SIZE", "100"))
}

# Thread configuration
THREAD_CONFIG = {
    "max_active_threads": int(os.getenv("THREAD_MAX_ACTIVE", "10")),
    "auto_archive_hours": int(os.getenv("THREAD_AUTO_ARCHIVE_HOURS", "24"))
}


def get_agent_config() -> Dict[str, Any]:
    """Get configuration for the chat agent"""
    return {
        "enable_memory": True,  # Always initialize with memory support (can toggle on/off at runtime)
        "enable_workflows": ENABLE_WORKFLOWS,
        "enable_threads": ENABLE_THREADS,
        "memory_config": MEMORY_CONFIG  # Always provide config
    }


def print_config():
    """Print current configuration"""
    print("=== Telly Chat Configuration ===")
    print(f"Memory Enabled: {ENABLE_MEMORY}")
    print(f"Workflows Enabled: {ENABLE_WORKFLOWS}")
    print(f"Threads Enabled: {ENABLE_THREADS}")
    
    if ENABLE_MEMORY:
        print("\nMemory Configuration:")
        print(f"  Short-term capacity: {MEMORY_CONFIG['short_term_capacity']}")
        print(f"  Vector store: {MEMORY_CONFIG['vector_store_type']}")
        print(f"  Persist directory: {MEMORY_CONFIG['persist_directory']}")
    
    print("================================")