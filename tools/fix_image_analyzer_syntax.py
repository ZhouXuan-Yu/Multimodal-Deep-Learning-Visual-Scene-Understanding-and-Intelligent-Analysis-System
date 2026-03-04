from __future__ import annotations

import re
from pathlib import Path


TARGET = Path(r"D:\ModelService_graduation-main\ModelService_graduation-main\ModelService\Main\app\utils\image_analyzer.py")


def main() -> None:
    if not TARGET.exists():
        raise SystemExit(f"Target not found: {TARGET}")

    text = TARGET.read_text(encoding="utf-8")
    original = text

    # 修复错误的 replace('\n', '\r') 代码：之前被写成了跨行字符串，导致 SyntaxError
    # 目标：统一改回源码层面的 '\\n' / '\\r'
    pattern = re.compile(
        r"json_text\s*=\s*json_text\.replace\('\s*:\s*',\s*' '\)\.replace\('\s*:\s*',\s*' '\)",
        flags=re.MULTILINE,
    )
    text, n = pattern.subn(
        r"json_text = json_text.replace('\\n', ' ').replace('\\r', ' ')",
        text,
        count=1,
    )
    if n != 1:
        # 兼容另一种可能的坏形态：replace(' <newline> ', ' ') 之类
        pattern2 = re.compile(
            r"json_text\s*=\s*json_text\.replace\('\s*',\s*' '\)\.replace\('\s*',\s*' '\)",
            flags=re.MULTILINE,
        )
        text, n2 = pattern2.subn(
            r"json_text = json_text.replace('\\n', ' ').replace('\\r', ' ')",
            text,
            count=1,
        )
        if n2 != 1:
            raise SystemExit(f"Failed to locate broken json_text.replace(...) line. replaced={n}, alt_replaced={n2}")

    if text == original:
        raise SystemExit("No changes made (unexpected)")

    TARGET.write_text(text, encoding="utf-8")
    print("OK: fixed syntax in", TARGET)


if __name__ == "__main__":
    main()

