import os
import json
import threading
import firebase_admin
from firebase_admin import credentials, firestore

db = None
user_cache = {}
cache_lock = threading.Lock()

def initialize_database():
    """初始化 Firebase Admin SDK"""
    global db
    cred_json_str = os.getenv("FIREBASE_ADMIN_CREDENTIALS")
    if cred_json_str:
        try:
            cred_obj = json.loads(cred_json_str)
            cred = credentials.Certificate(cred_obj)
            firebase_admin.initialize_app(cred)
            db = firestore.client()
            print("✅ Firebase 已成功初始化")
        except Exception as e:
            print(f"❌ Firebase 初始化失敗: {e}")
            raise Exception("Firebase 初始化失敗")
    else:
        raise Exception("找不到 Firebase 服務帳戶金鑰")

def get_user_profile(user_id):
    """從 Firestore 或快取中獲取使用者資料"""
    if db is None:
        return {}
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
        return {}

def update_user_profile(user_id, profile_data):
    """更新 Firestore 中的使用者資料，並同步更新快取"""
    if db is None:
        return
    doc_ref = db.collection('user_profiles').document(str(user_id))
    doc_ref.set(profile_data, merge=True)
    
    with cache_lock:
        user_cache[user_id] = profile_data
