import requests
import time
import threading
import os
from flask import Flask
from pymongo import MongoClient

# --- 設定區域 ---
MONGO_URI = os.environ.get("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client["msw_bot"]
collection = db["message_ids"] 
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1508579382262894674/nsuyDSWdCBpIIys7otJmgEM_FwSKG1Ea-F6p2mDxVAk43JtHP1WmsHXq88niTX2m4uyI"
CHECK_INTERVAL = 15 
API_URL_TEMPLATE = "https://mverse-api.nexon.com/social/v1/profile/{}"

PLAYER_MAP = {
    "20372100008741142": {"name": "m4s4", "image": "https://mod-file.dn.nexoncdn.co.kr/profile/581/1774372787770.png"}
}

last_known_data = {pid: {"is_online": None, "world_name": None} for pid in PLAYER_MAP.keys()}
app = Flask('')

@app.route('/')
def home(): return "MSW Bot is Running!"

def delete_old_msg(pid):
    doc = collection.find_one({"pid": pid})
    if doc and "msg_id" in doc:
        try:
            requests.delete(f"{DISCORD_WEBHOOK_URL}/messages/{doc['msg_id']}", timeout=5)
        except: pass
        collection.delete_one({"pid": pid})

def save_new_msg(pid, msg_id):
    collection.update_one({"pid": pid}, {"$set": {"msg_id": msg_id}}, upsert=True)

def send_notification(entry, is_online):
    ppsn = str(entry["ppsn"])
    delete_old_msg(ppsn)
    
    clean_name = entry["profileName"].replace('【', '').replace('】', '')
    icon = "🟢" if is_online else "🔴"
    status_str = "上線了！" if is_online else "下線了。"
    
    fields = [
        {"name": "代碼", "value": f"`{entry['profileCode']}`", "inline": True},
        {"name": "狀態", "value": f"{icon} {status_str}", "inline": True},
    ]
    if is_online and entry.get("worldName"):
        fields.append({"name": "目前位置", "value": f"`{entry['worldName']}`", "inline": True})

    embed = {
        "color": 3066993 if is_online else 15158332,
        "title": f"{icon} 【{clean_name}】 {icon} {status_str}",
        "fields": fields,
        "footer": {"text": f"PPSN: {ppsn}"},
        "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        "thumbnail": {"url": entry.get("profileImageUrl", "")}
    }
    
    try:
        r = requests.post(DISCORD_WEBHOOK_URL + "?wait=true", json={"embeds": [embed]}, timeout=10)
        if r.status_code == 200:
            save_new_msg(ppsn, r.json()["id"])
    except Exception as e:
        print(f"❌ Discord 發送失敗: {e}")

def check_players():
    for pid, info in PLAYER_MAP.items():
        time.sleep(1.0)
        try:
            r = requests.get(API_URL_TEMPLATE.format(pid), timeout=10)
            if r.status_code != 200: 
                print(f"⚠️ API 回傳錯誤 {r.status_code} 對象: {pid}")
                continue
            
            data = r.json().get('data', {})
            # 這裡加入 DEBUG 資訊，觀察 API 實際回傳什麼
            is_online = data.get('isOnline') == 1 or data.get('isOnline') is True
            world_name = data.get('worldName')
            p_code = data.get('profileCode', '未知')
            print(f"🔍 DEBUG: 玩家 {info['name']} 狀態: {'線上' if is_online else '離線'}, 地點: {world_name}")

            prev = last_known_data[pid]
            # 強制條件：如果上次狀態是 None (剛啟動)，直接記錄當前狀態，但不發通知 (除非你想讓他開機就噴通知)
            if prev["is_online"] is None:
                last_known_data[pid] = {"is_online": is_online, "world_name": world_name}
                print(f"✅ 玩家 {info['name']} 初始狀態已設定為: {'線上' if is_online else '離線'}")
                continue

            # 狀態改變才觸發
            if prev["is_online"] != is_online or (is_online and prev["world_name"] != world_name):
                print(f"🔔 狀態變更！玩家 {info['name']} 準備發送通知...")
                send_notification({
                    "ppsn": pid, "profileName": info["name"],
                    "profileCode": p_code, "profileImageUrl": info["image"], 
                    "worldName": world_name
                }, is_online)
                last_known_data[pid] = {"is_online": is_online, "world_name": world_name}
        except Exception as e:
            print(f"❌ 檢查 {pid} 錯誤: {e}")

def main_loop():
    print("📡 監控循環已啟動...")
    while True:
        check_players()
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    threading.Thread(target=main_loop, daemon=True).start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
