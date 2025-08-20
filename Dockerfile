# 使用官方 Python 映像檔作為基礎
FROM python:3.11-slim

# 設定工作目錄
WORKDIR /app

# 將你的 requirements.txt 複製到容器中
COPY requirements.txt .

# 安裝所有 Python 函式庫
RUN pip install --no-cache-dir -r requirements.txt

# 將你的所有程式碼檔案複製到容器中
COPY . .

# 定義容器啟動時的命令
CMD ["python", "main.py"]