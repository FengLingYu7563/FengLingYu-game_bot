# 使用官方 Python 3.11 作為基礎映像
FROM python:3.11-slim

# 設定工作目錄
WORKDIR /app

# 將 requirements.txt 複製到工作目錄
COPY requirements.txt .

# 安裝所有依賴
RUN pip install --no-cache-dir -r requirements.txt

# 將專案所有檔案複製到工作目錄
COPY . .

# 定義 Flask 應用程式的啟動命令
# 這裡使用 gunicorn 啟動 Flask app
CMD exec gunicorn --bind :$PORT --workers 1 main:app