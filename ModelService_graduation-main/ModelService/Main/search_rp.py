import re

with open(r"D:\ModelService_graduation-main\ModelService_graduation-main\ModelService\Main\app\main.py", "r", encoding="utf-8") as f:
    content = f.read()

lines = content.split("\n")
for i, line in enumerate(lines):
    if "route_planning" in line.lower() and ("import" in line or "from" in line):
        print(f"{i+1}: {line.strip()}")




