import os
import time
from datetime import datetime

# === 新增：导入OpenAI相关依赖 ===
import base64
from openai import OpenAI

# === 新增：初始化OpenAI客户端（请根据实际情况替换key和base_url） ===
client = OpenAI(
    api_key="sk-k8H2334c64655f76c985327626e94aff66ac02a11f9m1iRg",  # 替换为你的 key
    base_url="https://api.gptsapi.net/v1"
)

# === 新增：大模型判断未加载内容的prompt模板 ===
UNLOADED_PROMPT = '''
你是一个UI自动化测试助手。请根据以下三项内容，判断执行完操作后的界面（after_img）是否存在未加载出的内容（如骨架屏、加载动画、空白区域、明显的"加载中"等）。

1. 操作前截图（current_img）
2. 操作后截图（after_img）
3. 操作response内容（response_txt）

请严格按照如下格式输出：
{"unloaded": true/false, "reason": "简要说明理由"}
如果界面存在未加载内容，请返回true，否则返回false。
'''

def capture_screenshot(adb_device_id, save_path):
    import subprocess
    try:
        subprocess.run(
            ['adb', '-s', adb_device_id, 'shell', 'screencap', '-p', '/sdcard/screenshot.png'],
            check=True
        )
        subprocess.run(
            ['adb', '-s', adb_device_id, 'pull', '/sdcard/screenshot.png', save_path],
            check=True
        )
        print(f"截图已保存至: {save_path}")
        return save_path
    except subprocess.CalledProcessError as e:
        print(f"ADB 截图失败: {e}")
        return None

# === 修改：用大模型判断界面是否存在未加载内容 ===
def is_content_unloaded(current_img, after_img, response_txt):
    """
    调用大模型API，判断after_img界面是否存在未加载内容。
    返回True表示有未加载内容，False表示无。
    """
    # 读取图片并转base64
    def img2b64(img_path):
        with open(img_path, "rb") as f:
            return base64.b64encode(f.read()).decode('utf-8')
    current_img_b64 = img2b64(current_img)
    after_img_b64 = img2b64(after_img)
    # 构造消息
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": UNLOADED_PROMPT},
                {"type": "text", "text": "操作前截图（current_img）："},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{current_img_b64}"}},
                {"type": "text", "text": "操作后截图（after_img）："},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{after_img_b64}"}},
                {"type": "text", "text": "操作response内容（response_txt）：\n" + response_txt}
            ]
        }
    ]
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages
        )
        content = response.choices[0].message.content.strip()
        import re, json
        match = re.search(r'\{[\s\S]*\}', content)
        if match:
            json_block = match.group(0)
            result = json.loads(json_block)
            print("[大模型判定]", result)
            return bool(result.get("unloaded", False))
        else:
            print("[大模型判定] 未找到JSON，原始输出：", content)
            return False
    except Exception as e:
        print("[大模型API异常]", e)
        return False

def check_and_handle_unloaded_content(current_img_path, after_img_path, response_json_path, adb_device_id, img_folder, step_count):
    """
    上传当前界面截图、操作后截图和 response.json 文件，让模型判断界面是否存在未加载出的内容。
    如果存在未加载内容，则等待5秒后再次截图，并返回新截图路径作为下一步输入。
    否则，返回 after_img_path。
    """
    if not os.path.exists(response_json_path):
        print(f"未找到 response.json: {response_json_path}")
        return after_img_path
    # 读取json并格式化为字符串
    import json
    with open(response_json_path, 'r', encoding='utf-8') as f:
        try:
            response_obj = json.load(f)
            response_txt = json.dumps(response_obj, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"读取response.json失败: {e}")
            response_txt = f.read()
    has_unloaded = is_content_unloaded(current_img_path, after_img_path, response_txt)
    if has_unloaded:
        print("检测到界面存在未加载内容，等待5秒后重新截图...")
        time.sleep(5)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        new_screenshot_path = os.path.join(img_folder, f"screenshot_step{step_count}_reload_{timestamp}.png")
        new_screenshot = capture_screenshot(adb_device_id, new_screenshot_path)
        if new_screenshot:
            print(f"重新截图已保存: {new_screenshot}")
            return new_screenshot
        else:
            print("重新截图失败，仍使用原截图")
            return after_img_path
    else:
        print("界面内容已全部加载，无需重新截图")
        return after_img_path

if __name__ == "__main__":
    # 示例用法：请根据实际情况替换参数
    current_img_path = "screenshots/img/screenshot_step1_20240601_120000.png"
    after_img_path = "screenshots/img/screenshot_step2_20240601_120010.png"
    response_json_path = "screenshots/outputs/step1/step1_response.json"
    adb_device_id = "设备ID"
    img_folder = "screenshots/img"
    step_count = 2
    result_img = check_and_handle_unloaded_content(current_img_path, after_img_path, response_json_path, adb_device_id, img_folder, step_count)
    print("下一步输入截图路径:", result_img) 