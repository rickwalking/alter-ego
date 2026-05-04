import json

with open("/app/seed_data.json") as f:
    projects = json.load(f)

for p in projects:
    for key, val in p.items():
        if isinstance(val, str) and len(val) > 500:
            print(f"{p['id']} - {key}: {len(val)} chars")
            print(f"  {val[:100]}...")
