# app.py (裁判書 API v4 - 終極相容版)

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
    # 強力偽裝
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(options=chrome_options)
    # 設定頁面載入逾時
    driver.set_page_load_timeout(30)
    return driver

def search_judgments(name):
    driver = get_driver()
    judgments = []
    try:
        print(f"🔍 [v4] 開始搜尋: {name}")
        
        # 嘗試進入行動版搜尋頁面 (通常較快且穩定)
        try:
            driver.get("https://judgment.judicial.gov.tw/LAW_Mobile_Search/JudSearch.aspx")
        except Exception as e:
            print(f"⚠️ 載入行動版失敗，嘗試電腦版: {e}")
            driver.get("https://judgment.judicial.gov.tw/FJUD/default.aspx")

        wait = WebDriverWait(driver, 20)
        
        # 尋找搜尋框 (嘗試多種可能的 ID)
        search_input = None
        for selector in ["txtKW", "q", "kw"]:
            try:
                search_input = driver.find_element(By.ID, selector)
                if search_input: break
            except: continue
        
        if not search_input:
            print(f"❌ 錯誤: 在頁面 {driver.title} 找不到搜尋輸入框")
            return []

        search_input.clear()
        search_input.send_keys(name)
        time.sleep(1) # 稍微等待輸入完成

        # 尋找搜尋按鈕
        btn_search = None
        for selector in ["btnSearch", "btn_search", "submit"]:
            try:
                btn_search = driver.find_element(By.ID, selector)
                if btn_search: break
            except: continue
            
        if not btn_search:
            print("❌ 錯誤: 找不到搜尋按鈕")
            return []

        btn_search.click()
        print("🖱️ 已點擊搜尋按鈕，等待結果...")

        # 等待結果表格出現 (gv 是行動版的 ID, gvJudData 是電腦版的)
        table_found = False
        for selector in ["gv", "gvJudData", "table"]:
            try:
                wait.until(EC.presence_of_element_located((By.ID, selector)))
                table_found = True
                print(f"✅ 找到結果表格: {selector}")
                break
            except: continue
        
        if not table_found:
            print(f"ℹ️ 提示: {name} 查無裁判紀錄或載入逾時")
            return []

        # 抓取表格行與連結
        # 法院網頁結構較複雜，我們直接抓取所有 a 標籤內容
        links = driver.find_elements(By.CSS_SELECTOR, "table tr a")
        print(f"🔗 找到 {len(links)} 個潛在連結")
        
        # 只取前 6 個有效的裁判連結
        count = 0
        for link_element in links:
            if count >= 6: break
            try:
                content = link_element.text.strip()
                href = link_element.get_attribute("href")
                
                # 簡單過濾無效連結
                if content and href and "JudDetail" in href:
                    judgments.append({
                        "id": count + 1,
                        "content": content,
                        "link": href
                    })
                    count += 1
            except: continue

        print(f"✅ [v4] 成功抓取 {len(judgments)} 筆裁判紀錄")
        return judgments

    except Exception as e:
        print(f"❌ [v4] 搜尋失敗: {e}")
        return []
    finally:
        driver.quit()

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
    return "Judgment API v4 is running."

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
