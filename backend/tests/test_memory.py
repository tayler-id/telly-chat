"""Tests for memory system"""

import unittest
from datetime import datetime, timedelta
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from memory.short_term import ShortTermMemory, MemoryPriority, MemoryItem
    from memory.episodic import EpisodicMemory, Episode, EpisodeType
    MEMORY_AVAILABLE = True
except ImportError:
    MEMORY_AVAILABLE = False


@unittest.skipIf(not MEMORY_AVAILABLE, "Memory modules not available")
class TestShortTermMemory(unittest.TestCase):
    """Test short-term memory functionality"""
    
    def setUp(self):
        self.memory = ShortTermMemory(capacity=5)
    
    def test_add_memory(self):
        """Test adding memories"""
        memory_id = self.memory.add("Test memory 1")
        self.assertIsNotNone(memory_id)
        self.assertEqual(len(self.memory._memories), 1)
    
    def test_capacity_limit(self):
        """Test memory capacity and eviction"""
        # Fill memory to capacity
        for i in range(7):
            self.memory.add(f"Memory {i}", priority=MemoryPriority.LOW)
        
        # Should not exceed capacity
        self.assertEqual(len(self.memory._memories), 5)
        
        # Oldest low priority memories should be evicted
        memories = list(self.memory._memories)
        self.assertNotIn("Memory 0", [m.content for m in memories])
        self.assertNotIn("Memory 1", [m.content for m in memories])
    
    def test_priority_retention(self):
        """Test that high priority memories are retained"""
        # Add high priority memory
        high_id = self.memory.add("Important memory", priority=MemoryPriority.CRITICAL)
        
        # Fill with low priority memories
        for i in range(10):
            self.memory.add(f"Low priority {i}", priority=MemoryPriority.LOW)
        
        # High priority should still be there
        high_memory = self.memory.get(high_id)
        self.assertIsNotNone(high_memory)
        self.assertEqual(high_memory.content, "Important memory")
    
    def test_search(self):
        """Test memory search"""
        self.memory.add("Python programming tutorial")
        self.memory.add("JavaScript web development")
        self.memory.add("Python data science")
        
        # Search for Python
        results = self.memory.search("Python")
        self.assertEqual(len(results), 2)
        
        # Search with limit
        results = self.memory.search("Python", limit=1)
        self.assertEqual(len(results), 1)
    
    def test_context_window(self):
        """Test context window management"""
        for i in range(5):
            self.memory.add(f"Message {i}")
        
        context = self.memory.get_context_window()
        self.assertLessEqual(len(context), self.memory._max_context_size)
    
    def test_decay(self):
        """Test time-based decay"""
        # Add old memory
        old_memory = MemoryItem(
            id="old_1",
            content="Old memory",
            timestamp=datetime.now() - timedelta(hours=2),
            priority=MemoryPriority.LOW
        )
        self.memory._memories.append(old_memory)
        self.memory._memory_index[old_memory.id] = old_memory
        
        # Add recent memory
        self.memory.add("Recent memory", priority=MemoryPriority.LOW)
        
        # Apply decay
        self.memory.decay()
        
        # Old memory should be removed
        self.assertIsNone(self.memory.get("old_1"))


@unittest.skipIf(not MEMORY_AVAILABLE, "Memory modules not available")
class TestEpisodicMemory(unittest.TestCase):
    """Test episodic memory functionality"""
    
    def setUp(self):
        self.memory = EpisodicMemory()
    
    def test_episode_lifecycle(self):
        """Test episode creation and completion"""
        # Start episode
        episode_id = self.memory.start_episode(
            title="Test Episode",
            episode_type=EpisodeType.CONVERSATION,
            participants=["user", "assistant"]
        )
        
        self.assertIsNotNone(episode_id)
        self.assertEqual(len(self.memory._active_episodes), 1)
        
        # Add events
        success = self.memory.add_event(
            episode_id,
            event_type="message",
            actor="user",
            action="asked_question",
            data={"question": "What is Python?"}
        )
        self.assertTrue(success)
        
        # End episode
        success = self.memory.end_episode(
            episode_id,
            outcome="completed",
            success_metrics={"satisfaction": 0.9}
        )
        self.assertTrue(success)
        
        # Check episode is no longer active
        self.assertEqual(len(self.memory._active_episodes), 0)
        episode = self.memory.get_episode(episode_id)
        self.assertFalse(episode.is_active)
    
    def test_episode_search(self):
        """Test searching episodes"""
        # Create multiple episodes
        for i in range(3):
            episode_id = self.memory.start_episode(
                title=f"Episode {i}",
                episode_type=EpisodeType.CONVERSATION,
                participants=["user", "assistant"]
            )
            self.memory.end_episode(episode_id, outcome="completed")
        
        # Search all episodes
        results = self.memory.search_episodes()
        self.assertEqual(len(results), 3)
        
        # Search with query
        results = self.memory.search_episodes(query="Episode 1")
        self.assertEqual(len(results), 1)
    
    def test_similar_episodes(self):
        """Test finding similar episodes"""
        # Create episodes with same type
        ep1_id = self.memory.start_episode(
            title="Learning Python",
            episode_type=EpisodeType.LEARNING,
            participants=["user", "assistant"]
        )
        self.memory.end_episode(ep1_id)
        
        ep2_id = self.memory.start_episode(
            title="Learning JavaScript",
            episode_type=EpisodeType.LEARNING,
            participants=["user", "assistant"]
        )
        self.memory.end_episode(ep2_id)
        
        # Find similar
        similar = self.memory.get_similar_episodes(ep1_id)
        self.assertEqual(len(similar), 1)
        self.assertEqual(similar[0].id, ep2_id)


class TestMemoryIntegration(unittest.TestCase):
    """Test memory system integration"""
    
    @unittest.skipIf(not MEMORY_AVAILABLE, "Memory modules not available")
    def test_memory_hierarchy(self):
        """Test integration between memory types"""
        # This would test consolidation from short-term to long-term
        # Requires vector store setup, so keeping simple for now
        stm = ShortTermMemory()
        
        # Add memories with different priorities
        stm.add("Temporary info", priority=MemoryPriority.LOW)
        stm.add("Important fact", priority=MemoryPriority.HIGH)
        
        # Get high priority memories
        high_priority = stm.get_high_priority()
        self.assertEqual(len(high_priority), 1)
        self.assertEqual(high_priority[0].content, "Important fact")


if __name__ == '__main__':
    unittest.main()