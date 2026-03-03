"""
修复 main.py 中的 emoji 字符编码问题
"""
import re

# 读取文件
file_path = r"D:\ModelService_graduation-main\ModelService_graduation-main\ModelService\Main\app\main.py"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 替换emoji字符为ASCII兼容的文本
replacements = {
    '✅': '[OK]',
    '❌': '[ERROR]',
    '⚠️': '[WARN]',
    '🔄': '[RETRY]',
    '🔧': '[FIX]',
    '💡': '[INFO]',
    '🚀': '[START]',
    '🛑': '[STOP]',
    '📍': '[LOC]',
    '⭐': '[STAR]',
    '📋': '[LIST]',
}

for emoji, ascii_text in replacements.items():
    content = content.replace(emoji, ascii_text)

# 写回文件
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("SUCCESS: Emoji characters replaced with ASCII-compatible text!")
print("Replacements made:")
for emoji, ascii_text in replacements.items():
    print(f"  {emoji} -> {ascii_text}")




