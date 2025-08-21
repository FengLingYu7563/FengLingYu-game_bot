import os
import json
import threading
import firebase_admin
from firebase_admin import credentials, firestore

# 從環境變數中讀取服務帳戶金鑰
cred_json_str = os.getenv("FIREBASE_ADMIN_CREDENTIALS")
if cred_json_str:
    cred_obj = json.loads(cred_json_str)
    cred = credentials.Certificate(cred_obj)
    firebase_admin.initialize_app(cred)
    print("✅ Firebase 已成功初始化")
    db = firestore.client()
else:
    raise Exception("找不到 Firebase 服務帳戶金鑰")

# 這裡我們使用一個字典來快取使用者資料，避免頻繁讀取資料庫
user_cache = {}
# 使用 Lock 來確保多執行緒環境下的資料同步
cache_lock = threading.Lock()

def get_user_profile(user_id):
    """從 Firestore 或快取中獲取使用者資料"""
    with cache_lock:
        if user_id in user_cache:
            return user_cache[user_id]

    doc_ref = db.collection('user_profiles').document(str(user_id))
    doc = doc_ref.get()
    
    if doc.exists:
        profile = doc.to_dict()
        with cache_lock:
            user_cache[user_id] = profile
        return profile
    else:
        # 如果找不到資料，回傳一個空的字典
        return {}

def update_user_profile(user_id, profile_data):
    """更新 Firestore 中的使用者資料，並同步更新快取"""
    doc_ref = db.collection('user_profiles').document(str(user_id))
    doc_ref.set(profile_data, merge=True)
    
    with cache_lock:
        # 確保快取與資料庫同步
        user_cache[user_id] = profile_data