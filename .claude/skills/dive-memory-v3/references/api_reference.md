# Dive-Memory v3 API Reference

## Python API

### DiveMemory Class

Main class for memory operations.

```python
from dive_memory import DiveMemory

memory = DiveMemory(db_path="~/.dive-memory/memories.db")
```

#### Methods

##### `add(content, section, subsection=None, tags=None, importance=5, metadata=None) -> str`

Add a new memory.

**Parameters:**
- `content` (str): Memory content
- `section` (str): Memory section (e.g., "solutions", "decisions")
- `subsection` (str, optional): Subsection within section
- `tags` (list, optional): List of tags
- `importance` (int, optional): Importance score 1-10 (default: 5)
- `metadata` (dict, optional): Additional metadata

**Returns:** Memory ID (str)

**Example:**
```python
memory_id = memory.add(
    content="Use tRPC for type-safe APIs",
    section="solutions/api",
    tags=["typescript", "api"],
    importance=9,
    metadata={"framework": "tRPC"}
)
```

##### `search(query, section=None, tags=None, top_k=10) -> List[Memory]`

Search memories using hybrid search (semantic + keyword).

**Parameters:**
- `query` (str): Search query
- `section` (str, optional): Filter by section
- `tags` (list, optional): Filter by tags
- `top_k` (int, optional): Number of results (default: 10)

**Returns:** List of Memory objects with relevance scores

**Example:**
```python
results = memory.search(
    query="How to implement authentication?",
    section="solutions",
    tags=["auth"],
    top_k=5
)

for result in results:
    print(f"[{result.score:.2f}] {result.content}")
```

##### `update(memory_id, content=None, tags=None, importance=None, metadata=None)`

Update existing memory.

**Parameters:**
- `memory_id` (str): Memory ID
- `content` (str, optional): New content
- `tags` (list, optional): New tags
- `importance` (int, optional): New importance
- `metadata` (dict, optional): New metadata

**Example:**
```python
memory.update(
    memory_id="abc123",
    importance=10,
    tags=["critical", "security"]
)
```

##### `delete(memory_id)`

Delete memory and its links.

**Parameters:**
- `memory_id` (str): Memory ID

**Example:**
```python
memory.delete("abc123")
```

##### `get_graph(section=None, max_depth=2) -> Dict`

Get knowledge graph.

**Parameters:**
- `section` (str, optional): Filter by section
- `max_depth` (int, optional): Graph depth (default: 2)

**Returns:** Dict with `nodes` and `edges`

**Example:**
```python
graph = memory.get_graph(section="solutions")
print(f"Nodes: {len(graph['nodes'])}, Edges: {len(graph['edges'])}")
```

##### `get_related(memory_id, max_depth=2) -> List[Memory]`

Find related memories.

**Parameters:**
- `memory_id` (str): Memory ID
- `max_depth` (int, optional): Relationship depth (default: 2)

**Returns:** List of related Memory objects

**Example:**
```python
related = memory.get_related("abc123")
for mem in related:
    print(f"[{mem.relationship}] {mem.content} (strength: {mem.strength:.2f})")
```

##### `get_stats(section=None) -> Dict`

Get memory statistics.

**Parameters:**
- `section` (str, optional): Filter by section

**Returns:** Dict with statistics

**Example:**
```python
stats = memory.get_stats()
print(f"Total memories: {stats['total_memories']}")
print(f"Avg importance: {stats['avg_importance']}")
```

##### `get_sections() -> List[Dict]`

Get all memory sections.

**Returns:** List of section dicts

**Example:**
```python
sections = memory.get_sections()
for section in sections:
    print(section['name'])
```

##### `get_context_for_task(task, max_memories=5) -> str`

Get relevant context for a task.

**Parameters:**
- `task` (str): Task description
- `max_memories` (int, optional): Max memories to include (default: 5)

**Returns:** Formatted context string

**Example:**
```python
context = memory.get_context_for_task("Build authentication system")
print(context)
```

##### `enable_context_injection()`

Enable automatic context injection.

**Example:**
```python
memory.enable_context_injection()
```

##### `find_duplicates(threshold=0.95) -> List[Tuple]`

Find duplicate memories.

**Parameters:**
- `threshold` (float, optional): Similarity threshold (default: 0.95)

**Returns:** List of (id1, id2, similarity) tuples

**Example:**
```python
duplicates = memory.find_duplicates(threshold=0.95)
print(f"Found {len(duplicates)} duplicate pairs")
```

##### `merge_duplicates(duplicates, strategy="keep_newer")`

Merge duplicate memories.

**Parameters:**
- `duplicates` (list): List of duplicate tuples from `find_duplicates()`
- `strategy` (str, optional): Merge strategy (default: "keep_newer")

**Example:**
```python
duplicates = memory.find_duplicates()
memory.merge_duplicates(duplicates, strategy="keep_newer")
```

##### `configure_sync(provider, bucket, auto_sync=False)`

Configure cloud sync.

**Parameters:**
- `provider` (str): Cloud provider ("s3", "r2", "d1")
- `bucket` (str): Bucket name
- `auto_sync` (bool, optional): Enable auto-sync (default: False)

**Example:**
```python
memory.configure_sync(
    provider="s3",
    bucket="dive-memory-sync",
    auto_sync=True
)
```

##### `sync_to_cloud()`

Manually sync to cloud.

**Example:**
```python
memory.sync_to_cloud()
```

##### `sync_from_cloud()`

Manually sync from cloud.

**Example:**
```python
memory.sync_from_cloud()
```

### Memory Object

Returned by search and related methods.

**Attributes:**
- `id` (str): Memory ID
- `content` (str): Memory content
- `section` (str): Section
- `subsection` (str): Subsection
- `embedding` (list): Vector embedding
- `tags` (list): Tags
- `importance` (int): Importance score
- `metadata` (dict): Additional metadata
- `created_at` (int): Creation timestamp (ms)
- `updated_at` (int): Update timestamp (ms)
- `access_count` (int): Access count
- `last_accessed` (int): Last access timestamp (ms)
- `score` (float): Search relevance score
- `relationship` (str): Relationship type (for related memories)
- `strength` (float): Relationship strength (for related memories)

## MCP Tools

### memory_add

Add new memory.

**Input Schema:**
```json
{
  "content": "string (required)",
  "section": "string (required)",
  "subsection": "string (optional)",
  "tags": ["string"] (optional),
  "importance": "integer 1-10 (optional)",
  "metadata": "object (optional)"
}
```

**Returns:**
```json
{
  "success": true,
  "memory_id": "abc123",
  "message": "Memory added successfully"
}
```

### memory_search

Search memories.

**Input Schema:**
```json
{
  "query": "string (required)",
  "section": "string (optional)",
  "tags": ["string"] (optional),
  "top_k": "integer (optional, default: 10)"
}
```

**Returns:**
```json
{
  "success": true,
  "count": 5,
  "results": [
    {
      "id": "abc123",
      "content": "...",
      "section": "solutions",
      "tags": ["auth"],
      "importance": 8,
      "score": 0.95,
      "metadata": {}
    }
  ]
}
```

### memory_update

Update memory.

**Input Schema:**
```json
{
  "memory_id": "string (required)",
  "content": "string (optional)",
  "tags": ["string"] (optional),
  "importance": "integer (optional)",
  "metadata": "object (optional)"
}
```

### memory_delete

Delete memory.

**Input Schema:**
```json
{
  "memory_id": "string (required)"
}
```

### memory_graph

Get knowledge graph.

**Input Schema:**
```json
{
  "section": "string (optional)",
  "max_depth": "integer (optional, default: 2)"
}
```

**Returns:**
```json
{
  "success": true,
  "graph": {
    "nodes": [...],
    "edges": [...]
  }
}
```

### memory_related

Find related memories.

**Input Schema:**
```json
{
  "memory_id": "string (required)",
  "max_depth": "integer (optional, default: 2)"
}
```

### memory_stats

Get statistics.

**Input Schema:**
```json
{
  "section": "string (optional)"
}
```

**Returns:**
```json
{
  "success": true,
  "stats": {
    "total_memories": 150,
    "avg_importance": 6.5,
    "total_accesses": 450,
    "total_sections": 10,
    "total_links": 75
  }
}
```

## CLI Commands

### Add Memory
```bash
python3 memory_cli.py add "Memory content" \
  --section solutions \
  --subsection auth \
  --tags jwt security \
  --importance 8
```

### Search Memories
```bash
python3 memory_cli.py search "authentication" \
  --section solutions \
  --tags auth \
  --top-k 5
```

### Show Statistics
```bash
python3 memory_cli.py stats
python3 memory_cli.py stats --section solutions
```

### Show Knowledge Graph
```bash
python3 memory_cli.py graph
python3 memory_cli.py graph --section solutions --export graph.json
```

### Find Related Memories
```bash
python3 memory_cli.py related abc123 --max-depth 2
```

### Find Duplicates
```bash
python3 memory_cli.py dedup
python3 memory_cli.py dedup --threshold 0.95 --merge
```

### Delete Memory
```bash
python3 memory_cli.py delete abc123
python3 memory_cli.py delete abc123 --confirm
```

### Get Context for Task
```bash
python3 memory_cli.py context "Build authentication system" --max-memories 5
```

## Configuration

Configuration file: `references/config.json`

Key settings:
- `storage.backend`: "sqlite" or "postgresql"
- `storage.path`: Database file path
- `embeddings.provider`: "openai" or "local"
- `search.strategy`: "semantic", "keyword", or "hybrid"
- `deduplication.enabled`: Auto-deduplication
- `graph.auto_link`: Auto-create memory links
- `context_injection.enabled`: Auto-inject context

See `config.json` for full configuration options.
