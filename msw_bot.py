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
    "20372100008458134": {"name": "魚人", "image": "https://mod-file.dn.nexoncdn.co.kr/profile/758/1779542741338.png"},
    "20372100000100706": {"name": "康娜作者", "image": "https://mod-file.dn.nexoncdn.co.kr/profile/984/1722308667603.png"},
    "20372100000590354": {"name": "照&露西", "image": "https://mod-file.dn.nexoncdn.co.kr/profile/114/1771410723884.png"},
    "20372100005311821": {"name": "照&露西2", "image": "https://mod-file.dn.nexoncdn.co.kr/shop/949/1774672479562.png"},
    "20372100000684110": {"name": "黑貞", "image": "https://mod-file.dn.nexoncdn.co.kr/shop/49/1721248110286.png"},
    "20372100007023711": {"name": "sansan", "image": "https://mod-file.dn.nexoncdn.co.kr/profile/214/1780392703599.png"},
    "20372100003289343": {"name": "肥倫&奇樹", "image": "https://mod-file.dn.nexoncdn.co.kr/shop/357/1780329461647.png"},
    "20372100000737301": {"name": "HEE SABER", "image": "https://mod-file.dn.nexoncdn.co.kr/shop/521/1728129793932.png"},
    "20372100000535168": {"name": "겐지스", "image": "https://mod-file.dn.nexoncdn.co.kr/shop/212/1781100473061.png"},
    "20372100008590559": {"name": "黑豹女", "image": "https://mod-file.dn.nexoncdn.co.kr/profile/726/1781314436642.png"},
    "20372100005946653": {"name": "詩音", "image": "https://mod-file.dn.nexoncdn.co.kr/shop/556/1748663377570.png"},
    "20372100000104053": {"name": "沖田2", "image": "https://mod-file.dn.nexoncdn.co.kr/profile/704/1781446719047.png"},
    "20372100005252557": {"name": "橘福福雅", "image": "https://mod-file.dn.nexoncdn.co.kr/profile/310/1779852280518.png"},
    "20372100008986248": {"name": "橘福福2?", "image": "https://mod-file.dn.nexoncdn.co.kr/profile/326/1781812989489.png"}
}

DEFAULT_IMAGE = "https://example.com/default.png"
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1519000877241991311/EXzFkOnjb3U2gAIt6j4PIIz32EF-TFHuAgvya5pkY-o7Q559Z5jBaQl3gEB9LUod04PO"

# 建議調到 30 或 60 比較安全，但這邊先保留你原本的 15 試試看
CHECK_INTERVAL = 15 
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
        print(f"發送 IP 被鎖警告至 DC 失敗: {e}")

def check_players():
    global last_known_data
    print(f"[{time.strftime('%H:%M:%S')}] 啟動掃描...")

    for pid, info in PLAYER_MAP.items():
        time.sleep(0.6) # 👈 幫你拉長到 1.0 秒，分散連擊請求，能大大降低再被鎖的機率！
        try:
            name = info["name"]
            custom_image = info.get("image", DEFAULT_IMAGE)
            url = API_URL_TEMPLATE.format(pid)
            
            # 偽裝稍微完整一點的瀏覽器特徵
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            
            # 💡 【新增判斷】如果狀態碼不是 200，先記 LOG；如果是被鎖，就發 DC 通知並休息 10 分鐘
            if response.status_code != 200:
                print(f"❌ 擷取 {name} 失敗，狀態碼: {response.status_code}")
                if response.status_code in [429, 403, 1015]:
                    send_ip_blocked_warning(response.status_code)
                    print("😴 進入冷卻模式，暫停打擾 Nexon 10 分鐘...")
                    time.sleep(600)  # 暫停 10 分鐘
                    return           # 直接中斷這一輪，等 10 分鐘後重新開始
                continue
                
            data_root = response.json().get('data', {})
            
            # 兼容 1/0 或 True/False 的狀態值
            raw_online = data_root.get('isOnline')
            is_online = (raw_online == 1 or raw_online is True)
            
            world_name = data_root.get('worldName') 
            p_code = data_root.get('profileCode', '未知')
            
            prev = last_known_data[pid]

            # 首次啟動：存入資料（洗掉 None 狀態）但不發通知
            if prev["is_online"] is None:
                last_known_data[pid] = {"is_online": is_online, "world_name": world_name}
                print(f"📌 [初始化紀錄] {name} -> 線上: {is_online}, 世界: {world_name}")
                continue

            should_notify = False
            status_msg = ""
            
            # 印出即時比對狀況（方便在 Render 之後 debug 測試帳號）
            print(f"   [比對-{name}] 歷史: {prev['is_online']}({prev['world_name']}) ➡️ 最新: {is_online}({world_name})")

            # 核心狀態改變判斷
            if prev["is_online"] != is_online:
                should_notify = True
                status_msg = "🟢 上線了！" if is_online else "🔴 下線了。"
            elif is_online and prev["world_name"] != world_name:
                should_notify = True
                status_msg = f"切換世界"
            
            if should_notify:
                # 確定要通知後，立即更新歷史資料快取
                last_known_data[pid] = {"is_online": is_online, "world_name": world_name}
                current_world = world_name if world_name else "大廳或選單中"
                
                # 色彩與圖示燈號
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
                
                # 乾淨發送：全部直接走同一個 Webhook
                requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
                print(f"📣 [Discord已發送] 通知玩家: {name} {status_msg}")

        except Exception as e:
            print(f"❌ 檢查 {pid} ({info.get('name', '未知')}) 出錯: {e}")

def main_loop():
    while True:
        check_players()
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    print("--- 正在嘗試發送啟動訊號到 Discord ---")
    try:
        response = requests.post(
            DISCORD_WEBHOOK_URL, 
            json={"content": "🤖 阿拉也默默穿上黑絲！"},
            headers={'User-Agent': 'Mozilla/5.0'},
            timeout=10
        )
        if response.status_code in [200, 204]:
            print(f"✅ Discord 啟動訊號發送成功！")
        else:
            print(f"❌ Discord 拒絕請求，錯誤代碼: {response.status_code}")
            
    except Exception as e:
        print(f"💥 啟動訊號發送過程中發生異常: {e}")

    monitor_thread = threading.Thread(target=main_loop, daemon=True)
    monitor_thread.start()
    print("📡 後台監控線程已啟動，開始循環掃描。")

    print("🌐 正在啟動 Flask Web 服務...")
    run_web()
