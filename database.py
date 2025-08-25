import os
import json
import threading
import firebase_admin
from firebase_admin import credentials, firestore

db = None
user_cache = {}
cache_lock = threading.Lock()

# 這裡我們將初始化邏輯放在頂層，以確保它在任何函式被呼叫前執行
cred_json_str = os.getenv("FIREBASE_ADMIN_CREDENTIALS")
if cred_json_str:
    try:
        cred_obj = json.loads(cred_json_str)
        cred = credentials.Certificate(cred_obj)
        firebase_admin.initialize_app(cred)
        print("✅ Firebase 已成功初始化 (模式: 服務帳號憑證)")
        db = firestore.client()
    except Exception as e:
        print(f"❌ Firebase 初始化失敗: {e}")
        db = None
        # 如果初始化失敗，我們不直接拋出錯誤，讓程式繼續運行以便偵錯
else:
    print("警告: 找不到 FIREBASE_ADMIN_CREDENTIALS 環境變數。")
    db = None

def get_user_profile(user_id):
    """從 Firestore 或快取中獲取使用者資料"""
    if db is None:
        raise Exception("資料庫未初始化，無法執行 get_user_profile。")

    with cache_lock:
        if user_id in user_cache:
            return user_cache[user_id]
            
    doc_ref = db.collection('user_profiles').document(str(user_id))
    try:
        doc = doc_ref.get()
        if doc.exists:
            profile = doc.to_dict()
            with cache_lock:
                user_cache[user_id] = profile
            return profile
        else:
            return {
                "current_role": "冒險者",
                "discord_id": str(user_id),
                "gpt_notes": "",
                "keywords": []
            }
    except Exception as e:
        print(f"❌ 從 Firestore 讀取使用者 {user_id} 資料失敗: {e}")
        raise e

def update_user_profile(user_id, profile_data):
    """更新 Firestore 中的使用者資料，並同步更新快取"""
    if db is None:
        raise Exception("資料庫未初始化，無法執行 update_user_profile。")

    doc_ref = db.collection('user_profiles').document(str(user_id))
    try:
        doc_ref.set(profile_data, merge=True)
        with cache_lock:
            user_cache[user_id] = profile_data
        print(f"✅ 使用者 {user_id} 的資料已更新")
    except Exception as e:
        print(f"❌ 更新 Firestore 使用者 {user_id} 資料失敗: {e}")
        raise e