import requests
import time
import threading
import os
from flask import Flask
from pymongo import MongoClient

# --- MongoDB 設定 ---
# 請記得在 Render 環境變數設定 MONGO_URI
MONGO_URI = os.environ.get("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client["msw_bot"]
collection = db["message_ids"] # 儲存 {pid: msg_id}

app = Flask('')

@app.route('/')
def home():
    return "MSW Bot with Custom Images is Alive!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

# --- 訊息清理與記錄函式 ---
def delete_old_msg(pid):
    """從資料庫查詢並刪除舊訊息"""
    doc = collection.find_one({"pid": pid})
    if doc and "msg_id" in doc:
        try:
            # 刪除 Discord 上的舊訊息
            delete_url = f"{DISCORD_WEBHOOK_URL}/messages/{doc['msg_id']}"
            requests.delete(delete_url, timeout=5)
        except Exception as e:
            print(f"刪除舊訊息失敗: {e}")
        # 從資料庫移除紀錄
        collection.delete_one({"pid": pid})

def save_new_msg(pid, msg_id):
    """將新訊息 ID 寫入資料庫"""
    collection.update_one({"pid": pid}, {"$set": {"msg_id": msg_id}}, upsert=True)

# --- 設定區域 ---
PLAYER_MAP = {
    "20372100007473992": {"name": "蕾米&芙蘭", "image": "https://mod-file.dn.nexoncdn.co.kr/shop/792/1753813913624.png"},
    "20372100004981518": {"name": "AWAWA", "image": "https://mod-file.dn.nexoncdn.co.kr/shop/706/1749651958133.png"},
    "20372100003328034": {"name": "Coya奇術", "image": "https://mod-file.dn.nexoncdn.co.kr/profile/949/1778243422289.png"},
    "20372001057320745": {"name": "MIKA", "image": "https://mod-file.dn.nexoncdn.co.kr/shop/854/1766070535501.png"},
    "20372100005833987": {"name": "菲特", "image": "https://mod-file.dn.nexoncdn.co.kr/shop/440/1757093677010.png"},
    "20372100005779084": {"name": "簡&卡媽", "image": "https://mod-file.dn.nexoncdn.co.kr/profile/951/1770739129110.png"},
    "20372100007840052": {"name": "惡魔狐", "image": "https://mod-file.dn.nexoncdn.co.kr/shop/982/1757623973159.png"},
    "20372100007791322": {"name": "奶鱈", "image": "https://mod-file.dn.nexoncdn.co.kr/shop/773/1758903318897.png"},
    "20372100008359961": {"name": "沖田作者", "image": "https://mod-file.dn.nexoncdn.co.kr/shop/18/1777724572613.png"},
    "20372100002553986": {"name": "殺手兔作者", "image": "https://mod-file.dn.nexoncdn.co.kr/shop/610/1777201020468.png"},
    "20372100009098159": {"name": "哥倫比雅作者", "image": "https://mod-file.dn.nexoncdn.co.kr/shop/123/1777628265094.png"},
    "20372100009382026": {"name": "JOON", "image": "https://mod-file.dn.nexoncdn.co.kr/profile/315/1778431919948.png"},
    "20372100003462156": {"name": "ㄋㄍ奧米加", "image": "https://mod-file.dn.nexoncdn.co.kr/shop/987/1778554167572.png"},
    "20372100001585009": {"name": "打手槍王", "image": "https://mod-file.dn.nexoncdn.co.kr/shop/982/1744040914954.png"},
    "20372100007118040": {"name": "多路", "image": "https://mod-file.dn.nexoncdn.co.kr/profile/430/1778724875211.png"},
    "20372100005885364": {"name": "DCwaiting", "image": "https://mod-file.dn.nexoncdn.co.kr/profile/506/1778862090312.png"},
    "20372100004194770": {"name": "阿丞", "image": "https://mod-file.dn.nexoncdn.co.kr/profile/21/1778951712386.png"},
    "20372100000737301": {"name": "HEE SABER", "image": "https://mod-file.dn.nexoncdn.co.kr/profile/826/1747487981598.png"},
    "20372100008741142": {"name": "m4s4", "image": "https://mod-file.dn.nexoncdn.co.kr/profile/581/1774372787770.png"}
}
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1508579382262894674/nsuyDSWdCBpIIys7otJmgEM_FwSKG1Ea-F6p2mDxVAk43JtHP1WmsHXq88niTX2m4uyI"
CHECK_INTERVAL = 15 
API_URL_TEMPLATE = "https://mverse-api.nexon.com/social/v1/profile/{}"

last_known_data = {pid: {"is_online": None, "world_name": None} for pid in PLAYER_MAP.keys()}

def check_players():
    global last_known_data
    for pid, info in PLAYER_MAP.items():
        time.sleep(0.6)
        try:
            # ... (取得 API 資料 is_online, world_name, p_code 的邏輯) ...

            prev = last_known_data[pid]
            
            # 狀態改變才觸發
            if prev["is_online"] != is_online or (is_online and prev["world_name"] != world_name):
                last_known_data[pid] = {"is_online": is_online, "world_name": world_name}
                
                # 準備資料字典
                entry = {
                    "ppsn": pid,
                    "profileName": info["name"],
                    "profileCode": p_code,
                    "profileImageUrl": info.get("image", ""),
                    "worldName": world_name
                }
                
                # 統一由這個函數處理：清理舊的 -> 發送新的 -> 存入新的 ID
                send_notification(entry, is_online)

        except Exception as e:
            print(f"❌ 檢查 {pid} 出錯: {e}")

def send_notification(entry: dict, is_online: bool) -> None:
    ppsn = str(entry.get("ppsn", "?"))
    
    # 1. 執行清理：刪除舊訊息 (這裡執行一次就夠了)
    delete_old_msg(ppsn)
    
    # 2. 準備排版資料
    custom_info = PLAYER_MAP.get(ppsn)
    raw_name = custom_info.get("name", entry.get("profileName", "?")) if custom_info else entry.get("profileName", "?")
    clean_name = raw_name.replace('【', '').replace('】', '')
    
    code = entry.get("profileCode", "?")
    image = custom_info.get("image", entry.get("profileImageUrl", "")) if custom_info else entry.get("profileImageUrl", "")
    world = entry.get("worldName")

    color = 3066993 if is_online else 15158332
    icon = "🟢" if is_online else "🔴"
    status_str = "上線了！" if is_online else "下線了。"
    title_str = f"{icon} 【{clean_name}】 {icon} {status_str}"

    fields = [
        {"name": "代碼", "value": f"`{code}`", "inline": True},
        {"name": "狀態", "value": f"{icon} {status_str}", "inline": True},
    ]
    if is_online and world:
        fields.append({"name": "目前位置", "value": f"`{world}`", "inline": True})

    embed = {
        "color": color,
        "title": title_str,
        "fields": fields,
        "footer": {"text": f"PPSN: {ppsn}"},
        "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
    }
    if image:
        embed["thumbnail"] = {"url": image}

    # 3. 發送新訊息
    try:
        # 使用 ?wait=true 確保能拿到 msg_id
        r = requests.post(DISCORD_WEBHOOK_URL + "?wait=true", json={"embeds": [embed]}, timeout=10)
        if r.status_code == 200:
            new_id = r.json().get("id")
            # 存入 MongoDB 以供下次刪除使用
            save_new_msg(ppsn, new_id)
            print(f"📣 [Discord已發送] 通知玩家: {clean_name} {status_str}")
        else:
            print(f"❌ Discord 發送失敗，狀態碼: {r.status_code}")
    except Exception as e:
        print(f"❌ Discord 通知異常: {e}")
        
def main_loop():
    while True:
        check_players()
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    print("--- 正在嘗試發送啟動訊號到 Discord ---")
    try:
        response = requests.post(
            DISCORD_WEBHOOK_URL, 
            json={"content": "🤖 安靜晚安！"},
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

