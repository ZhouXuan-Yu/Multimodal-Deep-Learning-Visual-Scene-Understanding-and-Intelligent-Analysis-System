import re

with open(r"D:\ModelService_graduation-main\ModelService_graduation-main\ModelService\Main\app\main.py", "r", encoding="utf-8") as f:
    content = f.read()

lines = content.split("\n")
count = 0
for i, line in enumerate(lines):
    if "route_planning" in line:
        count += 1
        print(f"{i+1}: {line}")
        if count > 30:
            break




