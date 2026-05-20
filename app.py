# app.py (基於您提供的穩定版本進行最小化修改)

import os
import time
import threading
from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

app = Flask(__name__)

# 全域線程鎖
search_lock = threading.Lock()

def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=chrome_options)
    return driver

def search_judgments(name):
    driver = get_driver()
    judgments = []
    try:
        # 1. 進入搜尋頁面
        driver.get("https://judgment.judicial.gov.tw/LAW_Mobile_Search/JudSearch.aspx")
        
        # 2. 輸入姓名
        search_input = driver.find_element(By.ID, "txtKW")
        search_input.send_keys(name)
        
        # 3. 點擊搜尋
        btn_search = driver.find_element(By.ID, "btnSearch")
        btn_search.click()
        
        # 4. 等待載入 (維持您原本的等待時間)
        time.sleep(3)
        
        # 5. 抓取資料與連結 (核心修改處)
        # 先抓取所有的 a 標籤 (裁判詳情連結)
        links = driver.find_elements(By.CSS_SELECTOR, "#gv tr a")
        # 同時抓取文字行
        lines = [link.text.strip() for link in links]
        # 抓取連結網址
        urls = [link.get_attribute("href") for link in links]
        
        # 只取前 12 行資料片段 (對應約 6 筆紀錄)
        for i in range(min(len(lines), 12)):
            if lines[i]:
                judgments.append({
                    "id": i + 1,
                    "content": lines[i],
                    "link": urls[i] if i < len(urls) else ""
                })
                
    except Exception as e:
        print(f"Error: {e}")
    finally:
        driver.quit()
    return judgments

@app.route("/api/search", methods=["POST"])
def api_search():
    data = request.json
    name = data.get("name")
    if not name:
        return jsonify({"status": "error", "message": "Missing name"}), 400
    
    with search_lock:
        results = search_judgments(name)
    
    return jsonify({
        "status": "success",
        "judgments": results
    })

@app.route("/")
def index():
    return "Judgment API is running."

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
