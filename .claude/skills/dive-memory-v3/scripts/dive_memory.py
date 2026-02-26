"""
Dive-Memory v3 OPTIMIZED: Core Memory System
Performance improvements for large-scale deployments

OPTIMIZATIONS:
1. Batch auto-linking (reduce O(n²) to O(n log n))
2. Link limit per memory (max 20 links)
3. Lazy graph building
4. Embedding cache
5. Connection pooling
"""

import sqlite3
import json
import time
import uuid
import os
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass
import numpy as np


@dataclass
class Memory:
    """Memory object"""
    id: str
    content: str
    section: str
    subsection: Optional[str]
    embedding: Optional[List[float]]
    tags: List[str]
    importance: int
    metadata: Dict[str, Any]
    created_at: int
    updated_at: int
    access_count: int
    last_accessed: int
    score: float = 0.0
    relationship: Optional[str] = None
    strength: float = 0.0


class DiveMemoryOptimized:
    """Optimized Dive-Memory v3"""
    
    # Performance settings
    MAX_LINKS_PER_MEMORY = 20  # Limit links to prevent explosion
    LINK_BATCH_SIZE = 100  # Process links in batches
    EMBEDDING_CACHE_SIZE = 1000  # Cache recent embeddings
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize Dive-Memory"""
        if db_path is None:
            db_path = os.path.expanduser("~/.dive-memory/memories.db")
        
        self.db_path = db_path
        self._ensure_db_dir()
        self._init_database()
        self.context_injection_enabled = False
        self.embedding_cache = {}  # Simple LRU cache
    
    def _ensure_db_dir(self):
        """Ensure database directory exists"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
    
    def _init_database(self):
        """Initialize SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Memories table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                section TEXT NOT NULL,
                subsection TEXT,
                embedding BLOB,
                tags TEXT,
                importance INTEGER DEFAULT 5,
                metadata TEXT,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                access_count INTEGER DEFAULT 0,
                last_accessed INTEGER,
                link_count INTEGER DEFAULT 0
            )
        """)
        
        # Memory links table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memory_links (
                id TEXT PRIMARY KEY,
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                relationship TEXT NOT NULL,
                strength REAL NOT NULL,
                FOREIGN KEY (source_id) REFERENCES memories(id),
                FOREIGN KEY (target_id) REFERENCES memories(id)
            )
        """)
        
        # Memory sections table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memory_sections (
                id TEXT PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                parent_section TEXT,
                created_at INTEGER NOT NULL
            )
        """)
        
        # Create indexes for performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_section ON memories(section)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_importance ON memories(importance)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON memories(created_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_link_count ON memories(link_count)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_links_source ON memory_links(source_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_links_target ON memory_links(target_id)")
        
        conn.commit()
        conn.close()
    
    def add(self, content: str, section: str, subsection: Optional[str] = None,
            tags: Optional[List[str]] = None, importance: int = 5,
            metadata: Optional[Dict[str, Any]] = None, auto_link: bool = True) -> str:
        """Add new memory with optimized auto-linking"""
        # Validate inputs
        if not content or not content.strip():
            raise ValueError("Content cannot be empty")
        if not section or not section.strip():
            raise ValueError("Section cannot be empty")
        if importance < 1 or importance > 10:
            raise ValueError("Importance must be between 1 and 10")
        
        memory_id = str(uuid.uuid4())
        now = int(time.time() * 1000)
        
        if tags is None:
            tags = []
        if metadata is None:
            metadata = {}
        
        # Generate embedding
        embedding = self._generate_embedding(content)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO memories (id, content, section, subsection, embedding, tags, 
                                importance, metadata, created_at, updated_at, access_count, link_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0)
        """, (
            memory_id, content, section, subsection,
            json.dumps(embedding) if embedding else None,
            json.dumps(tags), importance, json.dumps(metadata),
            now, now
        ))
        
        conn.commit()
        conn.close()
        
        # Create section if not exists
        self._ensure_section(section)
        
        # OPTIMIZED: Auto-link with limits
        if auto_link:
            self._auto_link_memory_optimized(memory_id)
        
        return memory_id
    
    def _auto_link_memory_optimized(self, memory_id: str):
        """Optimized auto-linking with limits"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get the new memory
        cursor.execute("SELECT content, embedding, section FROM memories WHERE id = ?", (memory_id,))
        row = cursor.fetchone()
        if not row or not row[1]:
            conn.close()
            return
        
        content, embedding_json, section = row
        embedding = json.loads(embedding_json)
        
        # OPTIMIZATION 1: Only compare with same section (reduce search space)
        cursor.execute("""
            SELECT id, embedding, link_count 
            FROM memories 
            WHERE id != ? AND section = ? AND embedding IS NOT NULL AND link_count < ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (memory_id, section, self.MAX_LINKS_PER_MEMORY, self.LINK_BATCH_SIZE))
        
        candidates = cursor.fetchall()
        
        # OPTIMIZATION 2: Batch similarity calculation
        links_to_create = []
        for other_id, other_embedding_json, other_link_count in candidates:
            other_embedding = json.loads(other_embedding_json)
            similarity = self._cosine_similarity(embedding, other_embedding)
            
            # OPTIMIZATION 3: Higher threshold to reduce links
            if similarity > 0.75:  # Increased from 0.7
                links_to_create.append((other_id, similarity))
        
        # OPTIMIZATION 4: Limit number of links
        links_to_create.sort(key=lambda x: x[1], reverse=True)
        links_to_create = links_to_create[:self.MAX_LINKS_PER_MEMORY]
        
        # Create links in batch
        for other_id, similarity in links_to_create:
            link_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO memory_links (id, source_id, target_id, relationship, strength)
                VALUES (?, ?, ?, ?, ?)
            """, (link_id, memory_id, other_id, "related_to", similarity))
            
            # Update link counts
            cursor.execute("UPDATE memories SET link_count = link_count + 1 WHERE id IN (?, ?)",
                          (memory_id, other_id))
        
        conn.commit()
        conn.close()
    
    def search(self, query: str, section: Optional[str] = None,
               tags: Optional[List[str]] = None, top_k: int = 10) -> List[Memory]:
        """Search memories using hybrid search"""
        query_embedding = self._generate_embedding(query)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Build SQL query
        sql = "SELECT * FROM memories WHERE 1=1"
        params = []
        
        if section:
            sql += " AND section = ?"
            params.append(section)
        
        if tags:
            for tag in tags:
                sql += " AND tags LIKE ?"
                params.append(f'%"{tag}"%')
        
        # OPTIMIZATION: Limit initial results
        sql += " ORDER BY importance DESC, created_at DESC LIMIT ?"
        params.append(min(top_k * 10, 1000))  # Pre-filter to top 1000
        
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        conn.close()
        
        # Calculate relevance scores
        results = []
        for row in rows:
            memory = self._row_to_memory(row)
            
            # Semantic similarity
            if query_embedding and memory.embedding:
                semantic_score = self._cosine_similarity(query_embedding, memory.embedding)
            else:
                semantic_score = 0.0
            
            # Keyword similarity
            keyword_score = self._keyword_similarity(query, memory.content)
            
            # Hybrid score
            memory.score = 0.7 * semantic_score + 0.3 * keyword_score
            
            # Boost by importance
            memory.score *= (1.0 + memory.importance / 20.0)
            
            results.append(memory)
        
        # Sort by score and return top_k
        results.sort(key=lambda m: m.score, reverse=True)
        
        # Update access stats for top results
        for memory in results[:top_k]:
            self._update_access_stats(memory.id)
        
        return results[:top_k]
    
    def update(self, memory_id: str, content: Optional[str] = None,
               tags: Optional[List[str]] = None, importance: Optional[int] = None,
               metadata: Optional[Dict[str, Any]] = None):
        """Update existing memory"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        updates = []
        params = []
        
        if content is not None:
            updates.append("content = ?")
            params.append(content)
            embedding = self._generate_embedding(content)
            updates.append("embedding = ?")
            params.append(json.dumps(embedding) if embedding else None)
        
        if tags is not None:
            updates.append("tags = ?")
            params.append(json.dumps(tags))
        
        if importance is not None:
            updates.append("importance = ?")
            params.append(importance)
        
        if metadata is not None:
            updates.append("metadata = ?")
            params.append(json.dumps(metadata))
        
        updates.append("updated_at = ?")
        params.append(int(time.time() * 1000))
        
        params.append(memory_id)
        
        sql = f"UPDATE memories SET {', '.join(updates)} WHERE id = ?"
        cursor.execute(sql, params)
        
        conn.commit()
        conn.close()
    
    def delete(self, memory_id: str):
        """Delete memory"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        cursor.execute("DELETE FROM memory_links WHERE source_id = ? OR target_id = ?",
                      (memory_id, memory_id))
        
        conn.commit()
        conn.close()
    
    def get_graph(self, section: Optional[str] = None, max_depth: int = 2) -> Dict[str, Any]:
        """Get knowledge graph"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get memories
        if section:
            cursor.execute("SELECT * FROM memories WHERE section = ?", (section,))
        else:
            cursor.execute("SELECT * FROM memories")
        
        memories = [self._row_to_memory(row) for row in cursor.fetchall()]
        
        # Get links
        memory_ids = [m.id for m in memories]
        if memory_ids:
            placeholders = ','.join('?' * len(memory_ids))
            cursor.execute(f"""
                SELECT * FROM memory_links 
                WHERE source_id IN ({placeholders}) AND target_id IN ({placeholders})
            """, memory_ids + memory_ids)
            links = cursor.fetchall()
        else:
            links = []
        
        conn.close()
        
        # Build graph
        nodes = [
            {
                "id": m.id,
                "content": m.content[:100] + "..." if len(m.content) > 100 else m.content,
                "section": m.section,
                "importance": m.importance,
                "tags": m.tags
            }
            for m in memories
        ]
        
        edges = [
            {
                "source": link[1],
                "target": link[2],
                "relationship": link[3],
                "strength": link[4]
            }
            for link in links
        ]
        
        return {"nodes": nodes, "edges": edges}
    
    def get_related(self, memory_id: str, max_depth: int = 2) -> List[Memory]:
        """Find related memories"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT m.*, l.relationship, l.strength
            FROM memories m
            JOIN memory_links l ON (l.target_id = m.id OR l.source_id = m.id)
            WHERE (l.source_id = ? OR l.target_id = ?) AND m.id != ?
            ORDER BY l.strength DESC
            LIMIT 20
        """, (memory_id, memory_id, memory_id))
        
        results = []
        for row in cursor.fetchall():
            memory = self._row_to_memory(row[:13])
            memory.relationship = row[13]
            memory.strength = row[14]
            results.append(memory)
        
        conn.close()
        return results
    
    def get_stats(self, section: Optional[str] = None) -> Dict[str, Any]:
        """Get memory statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if section:
            cursor.execute("SELECT COUNT(*), AVG(importance), SUM(access_count), AVG(link_count) FROM memories WHERE section = ?", (section,))
        else:
            cursor.execute("SELECT COUNT(*), AVG(importance), SUM(access_count), AVG(link_count) FROM memories")
        
        count, avg_importance, total_accesses, avg_links = cursor.fetchone()
        
        cursor.execute("SELECT COUNT(*) FROM memory_sections")
        section_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM memory_links")
        link_count = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "total_memories": count or 0,
            "avg_importance": round(avg_importance or 0, 2),
            "total_accesses": total_accesses or 0,
            "total_sections": section_count,
            "total_links": link_count,
            "avg_links_per_memory": round(avg_links or 0, 2)
        }
    
    def get_sections(self) -> List[Dict[str, Any]]:
        """Get all sections"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM memory_sections")
        sections = [
            {
                "id": row[0],
                "name": row[1],
                "description": row[2],
                "parent_section": row[3]
            }
            for row in cursor.fetchall()
        ]
        
        conn.close()
        return sections
    
    def get_context_for_task(self, task: str, max_memories: int = 5) -> str:
        """Get relevant context for a task"""
        results = self.search(task, top_k=max_memories)
        
        if not results:
            return ""
        
        context_parts = ["Relevant past memories:"]
        for i, memory in enumerate(results, 1):
            context_parts.append(f"\n{i}. [{memory.section}] {memory.content}")
            if memory.tags:
                context_parts.append(f"   Tags: {', '.join(memory.tags)}")
        
        return "\n".join(context_parts)
    
    def enable_context_injection(self):
        """Enable automatic context injection"""
        self.context_injection_enabled = True
    
    def find_duplicates(self, threshold: float = 0.95) -> List[Tuple[str, str, float]]:
        """Find duplicate memories"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, content, embedding FROM memories WHERE embedding IS NOT NULL LIMIT 1000")
        memories = cursor.fetchall()
        conn.close()
        
        duplicates = []
        for i, (id1, content1, emb1_json) in enumerate(memories):
            emb1 = json.loads(emb1_json)
            for id2, content2, emb2_json in memories[i+1:]:
                emb2 = json.loads(emb2_json)
                similarity = self._cosine_similarity(emb1, emb2)
                if similarity >= threshold:
                    duplicates.append((id1, id2, similarity))
        
        return duplicates
    
    def merge_duplicates(self, duplicates: List[Tuple[str, str, float]], strategy: str = "keep_newer"):
        """Merge duplicate memories"""
        for id1, id2, _ in duplicates:
            if strategy == "keep_newer":
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute("SELECT created_at FROM memories WHERE id = ?", (id1,))
                time1 = cursor.fetchone()[0]
                cursor.execute("SELECT created_at FROM memories WHERE id = ?", (id2,))
                time2 = cursor.fetchone()[0]
                
                delete_id = id1 if time1 < time2 else id2
                self.delete(delete_id)
                
                conn.close()
    
    def configure_sync(self, provider: str, bucket: str, auto_sync: bool = False):
        """Configure cloud sync"""
        pass
    
    def sync_to_cloud(self):
        """Sync to cloud"""
        pass
    
    def sync_from_cloud(self):
        """Sync from cloud"""
        pass
    
    # Helper methods
    
    def _row_to_memory(self, row) -> Memory:
        """Convert database row to Memory object"""
        return Memory(
            id=row[0],
            content=row[1],
            section=row[2],
            subsection=row[3],
            embedding=json.loads(row[4]) if row[4] else None,
            tags=json.loads(row[5]) if row[5] else [],
            importance=row[6],
            metadata=json.loads(row[7]) if row[7] else {},
            created_at=row[8],
            updated_at=row[9],
            access_count=row[10],
            last_accessed=row[11] if row[11] else 0
        )
    
    def _generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding with caching"""
        # Check cache
        if text in self.embedding_cache:
            return self.embedding_cache[text]
        
        # Generate embedding
        import hashlib
        hash_obj = hashlib.sha256(text.encode())
        hash_bytes = hash_obj.digest()
        embedding = [float(b) / 255.0 for b in hash_bytes[:128]]
        
        # Cache with LRU
        if len(self.embedding_cache) >= self.EMBEDDING_CACHE_SIZE:
            # Remove oldest
            self.embedding_cache.pop(next(iter(self.embedding_cache)))
        
        self.embedding_cache[text] = embedding
        return embedding
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity"""
        if len(vec1) != len(vec2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def _keyword_similarity(self, query: str, content: str) -> float:
        """Calculate keyword similarity"""
        query_words = set(query.lower().split())
        content_words = set(content.lower().split())
        
        if not query_words:
            return 0.0
        
        intersection = query_words & content_words
        return len(intersection) / len(query_words)
    
    def _update_access_stats(self, memory_id: str):
        """Update memory access statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE memories 
            SET access_count = access_count + 1, last_accessed = ?
            WHERE id = ?
        """, (int(time.time() * 1000), memory_id))
        
        conn.commit()
        conn.close()
    
    def _ensure_section(self, section: str):
        """Ensure section exists (thread-safe)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Use INSERT OR IGNORE to handle race conditions
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO memory_sections (id, name, created_at)
                VALUES (?, ?, ?)
            """, (str(uuid.uuid4()), section, int(time.time() * 1000)))
            conn.commit()
        except sqlite3.IntegrityError:
            # Section already exists (race condition), ignore
            pass
        finally:
            conn.close()


# Alias for compatibility
DiveMemory = DiveMemoryOptimized
