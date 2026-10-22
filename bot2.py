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
    "20372100005802883": {"name": "paka2", "image": "https://mod-file.dn.nexoncdn.co.kr/shop/389/1777320374327.png"},    
    "20372100007012493": {"name": "newpaka", "image": "https://mod-file.dn.nexoncdn.co.kr/shop/104/1783450974975.png"},
    "20372100004902236": {"name": "黑兔死亡頭paka", "image": "https://mod-file.dn.nexoncdn.co.kr/shop/860/1785678726583.png"},
    "20372100000224266": {"name": "內衣paka", "image": "https://mod-file.dn.nexoncdn.co.kr/shop/800/1720733179821.png"}
}

DEFAULT_IMAGE = "https://example.com/default.png"
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

CHECK_INTERVAL = 10
API_URL_TEMPLATE = "https://mverse-api.nexon.com/social/v1/profile/{}"

last_known_data = {pid: {"is_online": None, "world_name": None} for pid in PLAYER_MAP.keys()}

def send_discord_webhook(url, payload):
    """安全發送 Discord Webhook，每次遇到 429 時都會明確印出 Log 並暫停 10 分鐘 (600秒)"""
    for attempt in range(5):
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            
            if response.status_code == 429:
                print(f"[{time.strftime('%H:%M:%S')}] ⚠️ 觸發 Discord 429 Rate Limit！進入冷卻模式：暫停 10 分鐘...")
                time.sleep(600)  # 強制暫停 10 分鐘
                continue         # 10分鐘後重新嘗試
            elif response.status_code in [200, 204]:
                return True
            else:
                print(f"[{time.strftime('%H:%M:%S')}] ❌ Discord 回傳非預期狀態碼: {response.status_code}")
                return False
        except Exception as e:
            print(f"[{time.strftime('%H:%M:%S')}] 發送 Discord 請求發生異常: {e}")
            time.sleep(2)
    return False

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
    send_discord_webhook(DISCORD_WEBHOOK_URL, payload)

def check_players():
    global last_known_data
    print(f"[{time.strftime('%H:%M:%S')}] 啟動掃描...")

    for pid, info in PLAYER_MAP.items():
        time.sleep(0.8) # 分散請求，降低被鎖機率
        try:
            name = info["name"]
            custom_image = info.get("image", DEFAULT_IMAGE)
            url = API_URL_TEMPLATE.format(pid)
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code != 200:
                print(f"❌ 擷取 {name} 失敗，狀態碼: {response.status_code}")
                if response.status_code in [429, 403, 1015]:
                    send_ip_blocked_warning(response.status_code)
                    print("😴 進入冷卻模式，暫停打擾 Nexon 10 分鐘...")
                    time.sleep(600)  # 暫停 10 分鐘
                    return           
                continue
                
            data_root = response.json().get('data', {})
            raw_online = data_root.get('isOnline')
            is_online = (raw_online == 1 or raw_online is True)
            
            world_name = data_root.get('worldName') 
            p_code = data_root.get('profileCode', '未知')
            
            prev = last_known_data[pid]

            if prev["is_online"] is None:
                last_known_data[pid] = {"is_online": is_online, "world_name": world_name}
                print(f"📌 [初始化紀錄] {name} -> 線上: {is_online}, 世界: {world_name}")
                continue

            should_notify = False
            status_msg = ""
            
            print(f"    [比對-{name}] 歷史: {prev['is_online']}({prev['world_name']}) ➡️ 最新: {is_online}({world_name})")

            if prev["is_online"] != is_online:
                should_notify = True
                status_msg = "🟢 上線了！" if is_online else "🔴 下線了。"
            elif is_online and prev["world_name"] != world_name:
                should_notify = True
                status_msg = f"切換世界"
            
            if should_notify:
                last_known_data[pid] = {"is_online": is_online, "world_name": world_name}
                current_world = world_name if world_name else "大廳或選單中"
                
                if is_online:
                    if "切換世界" in status_msg:
                        color = 16776960  # 純黃色
                        title_icon = "🔄"
                    else:
                        color = 65280     # 純綠色
                        title_icon = "🟢"
                else:
                    color = 16185856      # 純紅色
                    title_icon = "🔴"
                
                description = f"代碼：`{p_code}`\n狀態：**{status_msg}**"
                if is_online:
                    description += f"\n目前位置：`{current_world}`"

                payload = {
                    "embeds": [{
                        "title": f"{title_icon} 【{name}】{status_msg}",  
                        "description": description,
                        "thumbnail": {"url": custom_image}, 
                        "color": color,                                            
                        "footer": {"text": f"PPSN: {pid}"},
                        "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
                    }]
                }
                
                send_discord_webhook(DISCORD_WEBHOOK_URL, payload)
                print(f"📣 [Discord已發送] 通知玩家: {name} {status_msg}")

        except Exception as e:
            print(f"❌ 檢查 {pid} ({info.get('name', '未知')}) 出錯: {e}")

def main_loop():
    while True:
        check_players()
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    print("--- 正在嘗試發送啟動訊號到 Discord ---")
    
    # 💡 這裡改用統一的安全發送函數，確保開機發送如果遇到 429 也能完整印出 Log 並冷卻
    startup_payload = {"content": "🤖 PAKA，自己掰開！"}
    if send_discord_webhook(DISCORD_WEBHOOK_URL, startup_payload):
        print(f"✅ Discord 啟動訊號發送成功！")
    else:
        print(f"⚠️ Discord 啟動訊號發送未成功（可能遭遇 429 限制已自動暫停）")

    monitor_thread = threading.Thread(target=main_loop, daemon=True)
    monitor_thread.start()
    print("📡 後台監控線程已啟動，開始循環掃描。")

    print("🌐 正在啟動 Flask Web 服務...")
    run_web()
