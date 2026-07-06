import requests
import time
import threading
from flask import Flask
import os

app = Flask('')

@app.route('/')
def home():
    return "MSW Bot with Custom Images is Alive!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

# --- 設定區域 ---
PLAYER_MAP = {
    "20372100000209378": {"name": "doxx(老PAKA)", "image": "https://mod-file.dn.nexoncdn.co.kr/shop/491/1724686860431.png"},
    "20372100005770592": {"name": "PAKA", "image": "https://mod-file.dn.nexoncdn.co.kr/shop/271/1775588447819.png"},
    "20372100008443475": {"name": "paka1", "image": "https://mod-file.dn.nexoncdn.co.kr/shop/679/1774714211779.png"},
    "20372100005802883": {"name": "paka2", "image": "https://mod-file.dn.nexoncdn.co.kr/shop/389/1777320374327.png"
}


DEFAULT_IMAGE = "https://example.com/default.png"
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1502364012128637039/o9cJHlVQ4sibt4E-YVSki-TsNlaRSwjFH2kDaiqwl5qPnek5_UR4SWDVdZpfBYWRVbS7"

# 建議調到 30 或 60 比較安全，但這邊先保留你原本的 15 試試看
CHECK_INTERVAL = 5 
API_URL_TEMPLATE = "https://mverse-api.nexon.com/social/v1/profile/{}"

last_known_data = {pid: {"is_online": None, "world_name": None} for pid in PLAYER_MAP.keys()}

def send_ip_blocked_warning(status_code):
    """當發現被鎖 IP 時，發送警告到 Discord"""
    print(f"⚠️ [警告] : 維京出現把阿拉擄走 {status_code}。正在發送通知...")
    payload = {
        "embeds": [{
            "title": "⚠️ 阿拉跟隨維京進入到特殊領域 (Error 1015)",
            "description": f"安靜叫不起來了。\n**原因**：阿拉學維京，已被 rate limit。\n**HTTP 狀態碼**：`{status_code}`\n\n倒數機制已啟動：**阿拉被維京關在地下室 10 分鐘**。",
            "color": 16744192,  # 橘色
            "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        }]
    }
    try:
        requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=5)
    except Exception as e:
