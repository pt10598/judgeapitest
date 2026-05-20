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
        
        # 5. 抓取文字 (回歸您最穩定的方式)
        gv_element = driver.find_element(By.ID, "gv")
        full_text = gv_element.text
        lines = [line.strip() for line in full_text.split("\n") if line.strip()]
        
        # 6. 抓取連結 (獨立抓取以防干擾文字)
        links = driver.find_elements(By.TAG_NAME, "a")
        urls = []
        for link in links:
            href = link.get_attribute("href")
            if href and "JudDetail" in href:
                urls.append(href)
        
        # 7. 組合成結果 (取前 12 行，約 6 筆)
        # 通常 2 行文字對應 1 個連結
        for i in range(min(len(lines), 12)):
            url_index = i // 2 # 每兩行對應一個詳情連結
            judgments.append({
                "id": i + 1,
                "content": lines[i],
                "link": urls[url_index] if url_index < len(urls) else ""
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
