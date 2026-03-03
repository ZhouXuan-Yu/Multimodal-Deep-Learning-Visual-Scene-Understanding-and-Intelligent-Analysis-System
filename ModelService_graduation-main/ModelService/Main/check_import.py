import re

with open(r'D:\ModelService_graduation-main\ModelService_graduation-main\ModelService\Main\app\main.py', 'r', encoding='utf-8') as f:
    content = f.read()
    
# 找到route_planning相关的导入代码
lines = content.split('\n')
in_route_section = False
count = 0

for i, line in enumerate(lines):
    if 'route_planning' in line.lower() and 'import' in line:
        in_route_section = True
        count = 0
    
    if in_route_section:
        print(f"{i+1}: {line}")
        count += 1
        if count > 20:
            break




