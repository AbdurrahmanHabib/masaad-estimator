#!/usr/bin/env python3
"""
Dive-Memory v3 CLI
Command-line interface for memory management
"""

import argparse
import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from dive_memory import DiveMemory


def cmd_add(args):
    """Add memory command"""
    memory = DiveMemory(args.db)
    
    memory_id = memory.add(
        content=args.content,
        section=args.section,
        subsection=args.subsection,
        tags=args.tags or [],
        importance=args.importance,
        metadata=json.loads(args.metadata) if args.metadata else {}
    )
    
    print(f"✅ Memory added: {memory_id}")


def cmd_search(args):
    """Search memories command"""
    memory = DiveMemory(args.db)
    
    results = memory.search(
        query=args.query,
        section=args.section,
        tags=args.tags,
        top_k=args.top_k
    )
    
    if not results:
        print("No memories found")
        return
    
    print(f"\n📚 Found {len(results)} memories:\n")
    for i, result in enumerate(results, 1):
        print(f"{i}. [{result.section}] {result.content}")
        print(f"   Score: {result.score:.3f} | Importance: {result.importance} | Tags: {', '.join(result.tags)}")
        print()


def cmd_stats(args):
    """Show statistics command"""
    memory = DiveMemory(args.db)
    
    stats = memory.get_stats(section=args.section)
    
    print("\n📊 Memory Statistics:\n")
    print(f"Total Memories: {stats['total_memories']}")
    print(f"Average Importance: {stats['avg_importance']}")
    print(f"Total Accesses: {stats['total_accesses']}")
    print(f"Total Sections: {stats['total_sections']}")
    print(f"Total Links: {stats['total_links']}")


def cmd_graph(args):
    """Show knowledge graph command"""
    memory = DiveMemory(args.db)
    
    graph = memory.get_graph(section=args.section)
    
    print(f"\n🕸️  Knowledge Graph:\n")
    print(f"Nodes: {len(graph['nodes'])}")
    print(f"Edges: {len(graph['edges'])}")
    
    if args.export:
        with open(args.export, 'w') as f:
            json.dump(graph, f, indent=2)
        print(f"\n✅ Exported to: {args.export}")


def cmd_related(args):
    """Find related memories command"""
    memory = DiveMemory(args.db)
    
    related = memory.get_related(args.memory_id, max_depth=args.max_depth)
    
    if not related:
        print("No related memories found")
        return
    
    print(f"\n🔗 Related memories:\n")
    for i, mem in enumerate(related, 1):
        print(f"{i}. [{mem.relationship}] {mem.content}")
        print(f"   Strength: {mem.strength:.3f}")
        print()


def cmd_dedup(args):
    """Find and merge duplicates command"""
    memory = DiveMemory(args.db)
    
    print("🔍 Finding duplicates...")
    duplicates = memory.find_duplicates(threshold=args.threshold)
    
    if not duplicates:
        print("✅ No duplicates found")
        return
    
    print(f"\n⚠️  Found {len(duplicates)} duplicate pairs:\n")
    for id1, id2, similarity in duplicates:
        print(f"Similarity: {similarity:.3f}")
        print(f"  ID1: {id1}")
        print(f"  ID2: {id2}")
        print()
    
    if args.merge:
        print("Merging duplicates...")
        memory.merge_duplicates(duplicates, strategy="keep_newer")
        print("✅ Duplicates merged")


def cmd_delete(args):
    """Delete memory command"""
    memory = DiveMemory(args.db)
    
    if args.confirm or input(f"Delete memory {args.memory_id}? (y/n): ").lower() == 'y':
        memory.delete(args.memory_id)
        print(f"✅ Memory deleted: {args.memory_id}")
    else:
        print("Cancelled")


def cmd_context(args):
    """Get context for task command"""
    memory = DiveMemory(args.db)
    
    context = memory.get_context_for_task(args.task, max_memories=args.max_memories)
    
    if context:
        print("\n📝 Context:\n")
        print(context)
    else:
        print("No relevant context found")


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(description="Dive-Memory v3 CLI")
    parser.add_argument("--db", default=None, help="Database path")
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Add command
    add_parser = subparsers.add_parser("add", help="Add memory")
    add_parser.add_argument("content", help="Memory content")
    add_parser.add_argument("--section", required=True, help="Section")
    add_parser.add_argument("--subsection", help="Subsection")
    add_parser.add_argument("--tags", nargs="+", help="Tags")
    add_parser.add_argument("--importance", type=int, default=5, help="Importance (1-10)")
    add_parser.add_argument("--metadata", help="Metadata (JSON)")
    add_parser.set_defaults(func=cmd_add)
    
    # Search command
    search_parser = subparsers.add_parser("search", help="Search memories")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument("--section", help="Filter by section")
    search_parser.add_argument("--tags", nargs="+", help="Filter by tags")
    search_parser.add_argument("--top-k", type=int, default=10, help="Number of results")
    search_parser.set_defaults(func=cmd_search)
    
    # Stats command
    stats_parser = subparsers.add_parser("stats", help="Show statistics")
    stats_parser.add_argument("--section", help="Filter by section")
    stats_parser.set_defaults(func=cmd_stats)
    
    # Graph command
    graph_parser = subparsers.add_parser("graph", help="Show knowledge graph")
    graph_parser.add_argument("--section", help="Filter by section")
    graph_parser.add_argument("--export", help="Export to JSON file")
    graph_parser.set_defaults(func=cmd_graph)
    
    # Related command
    related_parser = subparsers.add_parser("related", help="Find related memories")
    related_parser.add_argument("memory_id", help="Memory ID")
    related_parser.add_argument("--max-depth", type=int, default=2, help="Max depth")
    related_parser.set_defaults(func=cmd_related)
    
    # Dedup command
    dedup_parser = subparsers.add_parser("dedup", help="Find and merge duplicates")
    dedup_parser.add_argument("--threshold", type=float, default=0.95, help="Similarity threshold")
    dedup_parser.add_argument("--merge", action="store_true", help="Merge duplicates")
    dedup_parser.set_defaults(func=cmd_dedup)
    
    # Delete command
    delete_parser = subparsers.add_parser("delete", help="Delete memory")
    delete_parser.add_argument("memory_id", help="Memory ID")
    delete_parser.add_argument("--confirm", action="store_true", help="Skip confirmation")
    delete_parser.set_defaults(func=cmd_delete)
    
    # Context command
    context_parser = subparsers.add_parser("context", help="Get context for task")
    context_parser.add_argument("task", help="Task description")
    context_parser.add_argument("--max-memories", type=int, default=5, help="Max memories")
    context_parser.set_defaults(func=cmd_context)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    args.func(args)


if __name__ == "__main__":
    main()
