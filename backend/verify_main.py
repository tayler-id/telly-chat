#!/usr/bin/env python3
"""Verify main.py has all endpoints"""

import ast
import os

# Read main.py
with open('main.py', 'r') as f:
    content = f.read()

# Parse the AST
tree = ast.parse(content)

# Find all route decorators
routes = []
for node in ast.walk(tree):
    if isinstance(node, ast.FunctionDef):
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute):
                if hasattr(decorator.func.value, 'id') and decorator.func.value.id == 'app':
                    if decorator.func.attr in ['get', 'post', 'put', 'delete']:
                        # Get the path from the decorator
                        if decorator.args:
                            path = ast.literal_eval(decorator.args[0])
                            routes.append((decorator.func.attr.upper(), path, node.name))

# Print all routes
print(f"Total routes found: {len(routes)}\n")

# Group by category
categories = {}
for method, path, func_name in sorted(routes):
    category = path.split('/')[1] if '/' in path[1:] else 'root'
    if category not in categories:
        categories[category] = []
    categories[category].append((method, path, func_name))

# Print by category
for category, items in sorted(categories.items()):
    print(f"\n{category.upper()}:")
    for method, path, func_name in items:
        print(f"  {method:6} {path:40} -> {func_name}()")

# Check for specific endpoints
episode_routes = [r for r in routes if 'episode' in r[1]]
transcript_routes = [r for r in routes if 'transcript' in r[1]]

print(f"\n\nEpisode routes: {len(episode_routes)}")
for method, path, func in episode_routes:
    print(f"  {method} {path}")

print(f"\nTranscript routes: {len(transcript_routes)}")
for method, path, func in transcript_routes:
    print(f"  {method} {path}")

# Check file stats
stat = os.stat('main.py')
print(f"\n\nFile info:")
print(f"  Size: {stat.st_size} bytes")
print(f"  Modified: {os.path.getmtime('main.py')}")

# Check if running in venv
import sys
print(f"\n  Python: {sys.executable}")
print(f"  In venv: {'venv' in sys.executable}")