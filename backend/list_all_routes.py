#!/usr/bin/env python3
"""List all routes from the OpenAPI schema"""

import requests
import json

r = requests.get("http://localhost:8000/openapi.json")
if r.status_code == 200:
    schema = r.json()
    paths = schema.get("paths", {})
    
    print(f"Total routes: {len(paths)}\n")
    
    # Group by prefix
    groups = {}
    for path in sorted(paths.keys()):
        prefix = path.split('/')[1] if '/' in path[1:] else path[1:]
        if prefix not in groups:
            groups[prefix] = []
        groups[prefix].append(path)
    
    # Print grouped
    for prefix, routes in sorted(groups.items()):
        print(f"\n{prefix.upper()} endpoints:")
        for route in routes:
            methods = list(paths[route].keys())
            print(f"  {route:<40} {', '.join(methods).upper()}")
            
    # Check specifically for episodes
    episode_routes = [p for p in paths if 'episode' in p]
    print(f"\n\nEpisode-related routes: {len(episode_routes)}")
    
    # Check for transcripts
    transcript_routes = [p for p in paths if 'transcript' in p]
    print(f"Transcript-related routes: {len(transcript_routes)}")
    for route in transcript_routes:
        print(f"  - {route}")