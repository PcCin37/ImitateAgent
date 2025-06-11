import os
import json
import base64
from openai import OpenAI

# 你的API KEY和base_url
client = OpenAI(
    api_key="sk-k8H2334c64655f76c985327626e94aff66ac02a11f9m1iRg",  # 替换为你的 key
    base_url="https://api.gptsapi.net/v1"  # 如果使用代理服务请替换为对应 base_url
)

HISTORY_JSONL_PATH = "history.jsonl"

def encode_image_to_base64(img_path):
    with open(img_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def append_entry_to_jsonl(file_path, entry: dict):
    with open(file_path, "a", encoding="utf-8") as f:
        json.dump({"history_entry": entry}, f, ensure_ascii=False)
        f.write("\n")

def evaluate_task_success(before_img, after_img, response_json):
    # 读取response_json
    with open(response_json, "r", encoding="utf-8") as f:
        data = json.load(f)
    # 只取第一个任务
    task_info = data[0] if isinstance(data, list) and len(data) > 0 else {}

    # 编码图片
    before_b64 = encode_image_to_base64(before_img)
    after_b64 = encode_image_to_base64(after_img)

    # 构造prompt
    prompt = f"""
你是一个UI自动化执行结果判定助手。
下面是本次子任务的描述和操作参数：
{json.dumps(task_info, ensure_ascii=False, indent=2)}

请对比“操作前截图”和“操作后截图”，判断本次子任务是否执行成功，并简要说明理由。
请严格按照如下JSON格式输出：
{{
  "success": true/false,
  "reason": "简要说明"
}}
"""

    # 发送到大模型
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "user", "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{before_b64}"}},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{after_b64}"}}
            ]}
        ]
    )
    content = response.choices[0].message.content.strip()
    # 尝试提取JSON
    import re
    match = re.search(r'(\{[\s\S]*\})', content)
    if match:
        result = json.loads(match.group(1))
    else:
        result = {"success": None, "reason": content}

    return result

def main():
    before_img = input("请输入操作前截图路径: ").strip()
    after_img = input("请输入操作后截图路径: ").strip()
    response_json = input("请输入本轮response_json路径: ").strip()

    result = evaluate_task_success(before_img, after_img, response_json)
    print("判定结果：", result)

    # 写入history
    entry = {
        "before_img": before_img,
        "after_img": after_img,
        "response_json": response_json,
        "success": result.get("success"),
        "reason": result.get("reason")
    }
    append_entry_to_jsonl(HISTORY_JSONL_PATH, entry)
    print("已写入history.jsonl")

if __name__ == "__main__":
    main()