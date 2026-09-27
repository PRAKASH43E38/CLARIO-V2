from pathlib import Path

files = [
    Path(r"C:\clario\CLARIO-V2\backend\app\orchestrator\adaptive_policy.py"),
    Path(r"C:\clario\CLARIO-V2\backend\app\orchestrator\nova.py"),
]

for p in files:
    content = p.read_text(encoding="utf-8")
    content = content.replace('\\"""', '"""')
    content = content.replace('\\"', '"')
    p.write_text(content, encoding="utf-8")
    print(f"Cleaned {p.name}")
