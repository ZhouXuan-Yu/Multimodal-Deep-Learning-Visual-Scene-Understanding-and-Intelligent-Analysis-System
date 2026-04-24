import requests, json, base64, time, io
from PIL import Image

# Create test images
img_red = Image.new('RGB', (200, 200), color='red')
img_blue = Image.new('RGB', (200, 200), color='blue')
img_people = Image.new('RGB', (640, 480), color=(180, 140, 120))

# Save as PNG
buf_red = io.BytesIO()
img_red.save(buf_red, format='PNG')
png_red_b64 = base64.b64encode(buf_red.getvalue()).decode()

buf_blue = io.BytesIO()
img_blue.save(buf_blue, format='PNG')
png_blue_b64 = base64.b64encode(buf_blue.getvalue()).decode()

print(f"Test PNG (red): {len(buf_red.getvalue())} bytes")

# Test 1: requests library + PNG image to Ollama
print("\n=== Test 1: requests + PNG image to Ollama ===")
payload = {
    "model": "qwen3-vl:8b",
    "stream": False,
    "messages": [
        {"role": "user", "content": "Describe what you see in this image briefly.", "images": [png_red_b64]},
    ],
    "options": {"temperature": 0.1, "num_predict": 256},
}
start = time.time()
try:
    resp = requests.post(
        "http://localhost:11434/api/chat",
        json=payload,
        timeout=60
    )
    elapsed = time.time() - start
    result = resp.json()
    content = result.get("message", {}).get("content", "")
    print(f"OK in {elapsed:.1f}s")
    print(f"Content: {content[:300]}")
except Exception as e:
    elapsed = time.time() - start
    print(f"FAIL after {elapsed:.1f}s: {e}")

# Test 2: requests library + real JSON structured output
print("\n=== Test 2: Structured JSON with image ===")
payload = {
    "model": "qwen3-vl:8b",
    "stream": False,
    "messages": [
        {"role": "user", "content": "Return JSON: {\"detected\": N, \"persons\": [{\"gender\": \"male\", \"age\": 25, \"bbox\": [x1,y1,x2,y2]}]}. Just JSON.", "images": [png_red_b64]},
    ],
    "options": {"temperature": 0.1, "num_predict": 512},
}
start = time.time()
try:
    resp = requests.post(
        "http://localhost:11434/api/chat",
        json=payload,
        timeout=60
    )
    elapsed = time.time() - start
    result = resp.json()
    content = result.get("message", {}).get("content", "")
    print(f"OK in {elapsed:.1f}s")
    print(f"Content: {content[:500]}")
    # Try parsing JSON
    j_start = content.find("{")
    j_end = content.rfind("}") + 1
    if j_start >= 0:
        try:
            parsed = json.loads(content[j_start:j_end])
            print(f"Parsed JSON: {json.dumps(parsed)}")
        except Exception as je:
            print(f"JSON parse failed: {je}")
except Exception as e:
    elapsed = time.time() - start
    print(f"FAIL after {elapsed:.1f}s: {e}")

# Test 3: Backend /analyze endpoint (needs restart first)
print("\n=== Test 3: Backend /analyze ===")
files = {"file": ("test.png", buf_red.getvalue(), "image/png")}
data = {"mode": "normal"}
start = time.time()
try:
    resp = requests.post(
        "http://localhost:8082/api/image-recognition/analyze",
        files=files,
        data=data,
        timeout=180
    )
    elapsed = time.time() - start
    result = resp.json()
    print(f"Backend responded in {elapsed:.1f}s!")
    print(json.dumps(result, ensure_ascii=False, indent=2)[:2000])
except Exception as e:
    elapsed = time.time() - start
    print(f"Backend FAIL after {elapsed:.1f}s: {e}")
