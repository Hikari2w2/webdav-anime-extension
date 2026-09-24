import json
import os
import sys

files = []
for root, dirs, filenames in os.walk('.'):
    for f in filenames:
        if f in ['run_mcp.py', 'common.gradle']: continue
        path = os.path.join(root, f)
        if '.git/' in path: continue
        with open(path, 'r', encoding='utf-8') as f_in:
            try:
                content = f_in.read()
                files.append({"path": path[2:], "content": content})
            except:
                pass

print(json.dumps(files))
