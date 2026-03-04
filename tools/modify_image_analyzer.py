from __future__ import annotations

import re
from pathlib import Path


TARGET = Path(r"D:\ModelService_graduation-main\ModelService_graduation-main\ModelService\Main\app\utils\image_analyzer.py")


def main() -> None:
    if not TARGET.exists():
        raise SystemExit(f"Target not found: {TARGET}")

    text = TARGET.read_text(encoding="utf-8")
    newline = "\r\n" if "\r\n" in text else "\n"

    def norm(s: str) -> str:
        return s.replace("\n", newline)

    original = text

    # 1) requests 注释 + 删除 OpenAI import 块
    text = text.replace(
        "import requests  # 替换 OpenAI 客户端，使用 requests 直接调用 API",
        "import requests  # 调用本地 Ollama（Qwen3-VL）",
    )

    text, n = re.subn(
        r"\ntry:\r?\n\s+from openai import OpenAI\r?\nexcept ImportError:\r?\n\s+print\([^\n]*\)\r?\n\s+OpenAI = None\r?\n",
        "\n",
        text,
        count=1,
        flags=re.MULTILINE,
    )
    if n != 1:
        raise SystemExit(f"Expected to remove 1 OpenAI import block, removed={n}")

    # 2) __init__：移除 DASHSCOPE api_key 逻辑，替换为 Ollama 配置
    init_repl = norm(
        """

        # 本地 Ollama（Qwen3-VL）配置
        # - OLLAMA_BASE_URL: 默认 http://localhost:11434
        # - OLLAMA_QWEN_VL_MODEL: 默认 qwen3-vl:8b
        self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
        self.ollama_model_name = os.getenv("OLLAMA_QWEN_VL_MODEL", "qwen3-vl:8b")
        try:
            self.ollama_timeout_s = int(os.getenv("OLLAMA_TIMEOUT_S", "120"))
        except Exception:
            self.ollama_timeout_s = 120
        logger.info(
            f"本地增强分析配置：OLLAMA_BASE_URL={self.ollama_base_url}, "
            f"OLLAMA_QWEN_VL_MODEL={self.ollama_model_name}, timeout={self.ollama_timeout_s}s"
        )

        self.load_models()
"""
    ).lstrip("\n")

    # 用一个相对稳定的标记区间替换：从 “# 修改 API key 的获取逻辑” 到 “self.load_models()”
    text, n = re.subn(
        r"\n\s*# 修改 API key 的获取逻辑[\s\S]*?\n\s*self\.load_models\(\)\r?\n",
        "\n" + init_repl,
        text,
        count=1,
        flags=re.MULTILINE,
    )
    if n != 1:
        raise SystemExit(f"Expected to replace __init__ api_key block once, replaced={n}")

    # 3) analyze_with_qwen：替换为本地 Ollama /api/chat 调用
    new_analyze_with_qwen = norm(
        """
    def analyze_with_qwen(self, image_path: str) -> Dict:
        \"\"\"使用本地 Ollama 中的 Qwen3-VL 模型分析图片（增强分析模式）\"\"\"
        try:
            # 读取并编码图片
            try:
                with open(image_path, "rb") as image_file:
                    base64_image = base64.b64encode(image_file.read()).decode("utf-8")
                logger.info("成功读取并编码图片（用于本地 Qwen3-VL）")
            except Exception as e:
                logger.error(f"图片编码失败: {str(e)}")
                return {"error": "图片编码失败"}

            prompt = \"\"\"请分析图像中的人物信息，并按照以下JSON格式返回结果：
{
    "detected": 人物数量,
    "persons": [
        {
            "gender": "male/female",
            "gender_confidence": 0.95,
            "age": 25,
            "age_confidence": 0.85,
            "upper_color": "red/blue/green/...",
            "upper_color_confidence": 0.8,
            "lower_color": "red/blue/green/...",
            "lower_color_confidence": 0.8,
            "bbox": [x1, y1, x2, y2]
        }
    ],
    "success": true
}
请严格只输出一个 JSON，不要输出任何额外说明文本。\"\"\"

            url = f"{self.ollama_base_url}/api/chat"
            payload = {
                "model": self.ollama_model_name,
                "stream": False,
                "messages": [
                    {"role": "system", "content": "你是一个严谨的图像分析助手，只能输出有效 JSON。"},
                    {"role": "user", "content": prompt, "images": [base64_image]},
                ],
            }

            logger.info(f"发送本地 Qwen3-VL 请求: url={url}, model={self.ollama_model_name}")
            try:
                resp = requests.post(url, json=payload, timeout=self.ollama_timeout_s)
            except Exception as e:
                logger.error(f"请求本地 Ollama 失败: {str(e)}")
                return {"error": f"Ollama调用失败: {str(e)}"}

            if resp.status_code != 200:
                logger.error(f"Ollama 返回非200: {resp.status_code}, body={resp.text[:500]}")
                return {"error": f"Ollama状态码: {resp.status_code}", "raw_text": resp.text}

            try:
                resp_json = resp.json()
            except Exception as e:
                logger.error(f"解析 Ollama 响应失败: {str(e)}, body={resp.text[:500]}")
                return {"error": "解析Ollama响应失败", "raw_text": resp.text}

            result_text = ""
            if isinstance(resp_json, dict) and "message" in resp_json:
                msg = resp_json.get("message") or {}
                result_text = msg.get("content", "") or ""
            if not result_text:
                result_text = json.dumps(resp_json, ensure_ascii=False)

            logger.info(f"本地 Qwen3-VL 返回原始结果: {result_text[:800]}")

            # 提取 JSON 部分
            json_start = result_text.find('{')
            json_end = result_text.rfind('}') + 1

            if json_start >= 0 and json_end > json_start:
                try:
                    json_text = result_text[json_start:json_end]
                    json_text = json_text.replace('\\n', ' ').replace('\\r', ' ')
                    json_text = ' '.join(json_text.split())
                    parsed_result = json.loads(json_text)
                    logger.info(f"成功解析 Qwen3-VL 返回结果: {json.dumps(parsed_result, ensure_ascii=False, indent=2)}")

                    standardized_result = {
                        "detected": parsed_result.get("detected", 0),
                        "persons": [],
                        "success": True
                    }

                    for person in parsed_result.get("persons", []):
                        standardized_person = {
                            "gender": person.get("gender", "unknown"),
                            "gender_confidence": person.get("gender_confidence", 0.0),
                            "age": person.get("age", 0),
                            "age_confidence": person.get("age_confidence", 0.0),
                            "upper_color": person.get("upper_color", "unknown"),
                            "upper_color_confidence": person.get("upper_color_confidence", 0.0),
                            "lower_color": person.get("lower_color", "unknown"),
                            "lower_color_confidence": person.get("lower_color_confidence", 0.0),
                            "bbox": person.get("bbox", [0, 0, 0, 0])
                        }
                        standardized_result["persons"].append(standardized_person)

                    logger.info(f"标准化后的结果: {json.dumps(standardized_result, ensure_ascii=False, indent=2)}")
                    return standardized_result

                except json.JSONDecodeError as e:
                    logger.error(f"JSON解析失败: {str(e)}")
                    return {"error": "JSON解析失败", "raw_text": result_text}
            else:
                logger.error(f"无法从响应中提取JSON结果: {result_text}")
                return {"error": "无法解析返回结果", "raw_text": result_text}

        except Exception as e:
            logger.error(f"本地 Qwen3-VL 分析失败: {str(e)}")
            return {"error": str(e)}
"""
    ).strip("\n")

    # 用 def analyze_with_qwen ... def merge_results 之间整体替换
    text, n = re.subn(
        r"\n\s*def analyze_with_qwen\(self, image_path: str\) -> Dict:[\s\S]*?\n\s*def merge_results\(",
        "\n" + new_analyze_with_qwen + "\n\n    def merge_results(",
        text,
        count=1,
        flags=re.MULTILINE,
    )
    if n != 1:
        raise SystemExit(f"Expected to replace analyze_with_qwen once, replaced={n}")

    # 4) merge_results 默认权重 + 融合方式（权重*置信度选择 / 数值加权）
    text, n = re.subn(
        r"def merge_results\(self, local_result: Dict, qwen_result: Dict, local_weight: float = 0\.01, qwen_weight: float = 0\.99\) -> Dict:",
        "def merge_results(self, local_result: Dict, qwen_result: Dict, local_weight: float = 0.3, qwen_weight: float = 0.7) -> Dict:",
        text,
        count=1,
    )
    if n != 1:
        raise SystemExit(f"Expected to update merge_results signature once, updated={n}")

    # 在 _low_conf 定义后插入 helper（若已插入则跳过）
    if "_pick_by_weighted_conf" not in text:
        helper_block = norm(
            """

            def _pick_by_weighted_conf(local_val, local_conf, qwen_val, qwen_conf):
                \"\"\"两侧都非 unknown 时，按 (weight * confidence) 选更可信的值。\"\"\"
                if _is_unknown(local_val) and _is_unknown(qwen_val):
                    return "unknown", 0.0
                if _is_unknown(local_val):
                    return qwen_val, float(qwen_conf or 0.0)
                if _is_unknown(qwen_val):
                    return local_val, float(local_conf or 0.0)

                try:
                    lc = float(local_conf or 0.0)
                except Exception:
                    lc = 0.0
                try:
                    qc = float(qwen_conf or 0.0)
                except Exception:
                    qc = 0.0

                if (qwen_weight * qc) > (local_weight * lc):
                    return qwen_val, qc
                return local_val, lc

            def _blend_number(local_num, local_conf, qwen_num, qwen_conf):
                \"\"\"数值字段加权融合：两个都有效则按权重算均值，否则取有效的一侧。\"\"\"
                def _valid(v):
                    return v not in (None, 0, 0.0, "0")

                l_ok = _valid(local_num)
                q_ok = _valid(qwen_num)

                try:
                    l_num = float(local_num) if l_ok else 0.0
                except Exception:
                    l_ok = False
                    l_num = 0.0
                try:
                    q_num = float(qwen_num) if q_ok else 0.0
                except Exception:
                    q_ok = False
                    q_num = 0.0

                try:
                    l_c = float(local_conf or 0.0)
                except Exception:
                    l_c = 0.0
                try:
                    q_c = float(qwen_conf or 0.0)
                except Exception:
                    q_c = 0.0

                if l_ok and q_ok:
                    return (local_weight * l_num + qwen_weight * q_num), (local_weight * l_c + qwen_weight * q_c)
                if q_ok:
                    return q_num, q_c
                if l_ok:
                    return l_num, l_c
                return 0.0, 0.0
"""
        ).strip("\n")

        text, n = re.subn(
            r"(def _low_conf\(v, threshold: float = 0\.4\) -> bool:[\s\S]*?\n\s*return True\r?\n)",
            r"\1" + newline + helper_block + newline,
            text,
            count=1,
            flags=re.MULTILINE,
        )
        if n != 1:
            raise SystemExit(f"Expected to insert helper block once, inserted={n}")

    # 替换 “用Qwen补齐...” 块为真正加权融合逻辑
    fusion_block = norm(
        """
                # 用权重做字段融合（不改 bbox；检测框仍以本地为准）
                if qwen_person is not None:
                    g, g_conf = _pick_by_weighted_conf(
                        person_data.get("gender", "unknown"),
                        person_data.get("gender_confidence", 0.0),
                        qwen_person.get("gender", "unknown"),
                        qwen_person.get("gender_confidence", 0.0),
                    )
                    person_data["gender"] = g
                    person_data["gender_confidence"] = float(g_conf or 0.0)

                    age, age_conf = _blend_number(
                        person_data.get("age", 0),
                        person_data.get("age_confidence", 0.0),
                        qwen_person.get("age", 0),
                        qwen_person.get("age_confidence", 0.0),
                    )
                    try:
                        person_data["age"] = int(round(float(age)))
                    except Exception:
                        person_data["age"] = 0
                    person_data["age_confidence"] = float(age_conf or 0.0)

                    uc, uc_conf = _pick_by_weighted_conf(
                        person_data.get("upper_color", "unknown"),
                        person_data.get("upper_color_confidence", 0.0),
                        qwen_person.get("upper_color", "unknown"),
                        qwen_person.get("upper_color_confidence", 0.0),
                    )
                    person_data["upper_color"] = uc
                    person_data["upper_color_confidence"] = float(uc_conf or 0.0)

                    lc, lc_conf = _pick_by_weighted_conf(
                        person_data.get("lower_color", "unknown"),
                        person_data.get("lower_color_confidence", 0.0),
                        qwen_person.get("lower_color", "unknown"),
                        qwen_person.get("lower_color_confidence", 0.0),
                    )
                    person_data["lower_color"] = lc
                    person_data["lower_color_confidence"] = float(lc_conf or 0.0)
"""
    ).strip("\n")

    text, n = re.subn(
        r"\n\s*# 用Qwen补齐“unknown/低置信度”的语义字段（不改bbox）[\s\S]*?\n\s*merged_result\[\"persons\"\]\.append\(person_data\)",
        "\n" + fusion_block + "\n\n                merged_result[\"persons\"].append(person_data)",
        text,
        count=1,
        flags=re.MULTILINE,
    )
    if n != 1:
        raise SystemExit(f"Expected to replace fusion block once, replaced={n}")

    # 5) analyze_image enhanced 权重改为 0.3/0.7
    text = text.replace(
        "local_weight=0.01,  # 修改权重为 1%",
        "local_weight=0.3,  # 本地模型 30%",
    )
    text = text.replace(
        "qwen_weight=0.99    # 修改权重为 99%",
        "qwen_weight=0.7    # 大模型 70%",
    )

    # 6) 不允许残留 DASHSCOPE/OpenAI 逻辑
    banned = ["DASHSCOPE_API_KEY", "dashscope.aliyuncs.com", "OpenAI("]
    leftover = [b for b in banned if b in text]
    if leftover:
        raise SystemExit(f"Leftover banned strings: {leftover}")

    if text == original:
        raise SystemExit("No changes made (unexpected)")

    TARGET.write_text(text, encoding="utf-8", newline="")  # 保留字符串内换行
    print("OK: modified", TARGET)


if __name__ == "__main__":
    main()

