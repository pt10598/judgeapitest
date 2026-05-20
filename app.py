# app.py (裁判書 API v3)

import os
import time
import threading
from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

app = Flask(__name__)

# 全域線程鎖，確保多人同時查詢時會排隊
search_lock = threading.Lock()

def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    # 偽裝成真實瀏覽器
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(options=chrome_options)
    return driver

def search_judgments(name):
    driver = get_driver()
    judgments = []
    try:
        print(f"🔍 開始搜尋 (含連結): {name}")
        # 法院官網
        driver.get("https://judgment.judicial.gov.tw/LAW_Mobile_Search/JudSearch.aspx")
        
        # 等待搜尋輸入框出現
        wait = WebDriverWait(driver, 15)
        try:
            search_input = wait.until(EC.presence_of_element_located((By.ID, "txtKW")))
            search_input.send_keys(name)
        except TimeoutException:
            print("❌ 錯誤: 找不到搜尋輸入框")
            return []

        # 點擊搜尋按鈕
        try:
            btn_search = driver.find_element(By.ID, "btnSearch")
            btn_search.click()
        except NoSuchElementException:
            print("❌ 錯誤: 找不到搜尋按鈕")
            return []

        # 等待搜尋結果表格出現
        try:
            wait.until(EC.presence_of_element_located((By.ID, "gv")))
        except TimeoutException:
            print(f"ℹ️ 提示: {name} 可能查無裁判紀錄")
            return []

        # 抓取表格行與連結
        # 我們抓取前 12 行 (約 6 筆資料)
        rows = driver.find_elements(By.CSS_SELECTOR, "#gv tr")
        
        for i, row in enumerate(rows[1:13]): # 跳過標題行
            try:
                # 嘗試抓取內容文字
                content = row.text.strip()
                # 嘗試抓取該行內的連結
                link_element = None
                try:
                    link_element = row.find_element(By.TAG_NAME, "a")
                    link = link_element.get_attribute("href")
                except:
                    link = ""
                
                if content:
                    judgments.append({
                        "id": i + 1,
                        "content": content,
                        "link": link
                    })
            except Exception as e:
                print(f"⚠️ 解析第 {i} 行時發生錯誤: {e}")
                continue

        print(f"✅ 成功抓取 {len(judgments)} 筆原始資料片段")
        return judgments

    except Exception as e:
        print(f"❌ 搜尋失敗: {e}")
        import traceback
        traceback.print_exc()
        return []
    finally:
        driver.quit()

@app.route("/api/search", methods=["POST"])
def api_search():
    data = request.json
    name = data.get("name")
    
    if not name:
        return jsonify({"status": "error", "message": "Missing name"}), 400
    
    # 使用鎖進行排隊
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
