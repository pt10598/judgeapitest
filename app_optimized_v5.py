# app.py (裁判書 API v5 - 防攔截加強版)

import os
import time
import random
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
    
    # 強力偽裝，隱藏 Selenium 特徵
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    
    driver = webdriver.Chrome(options=chrome_options)
    # 執行 JavaScript 移除 webdriver 標記
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    driver.set_page_load_timeout(30)
    return driver

def search_judgments(name):
    driver = get_driver()
    judgments = []
    try:
        print(f"🔍 [v5] 開始防攔截搜尋: {name}")
        
        # 步驟 1: 先進首頁取得 Cookie
        driver.get("https://judgment.judicial.gov.tw/FJUD/default.aspx")
        time.sleep(random.uniform(1, 3)) # 隨機等待
        
        # 步驟 2: 跳轉到搜尋頁面
        driver.get("https://judgment.judicial.gov.tw/LAW_Mobile_Search/JudSearch.aspx")
        time.sleep(1)
        
        # 檢查是否被攔截
        if "系統訊息" in driver.title:
            print("⚠️ 偵測到系統訊息攔截，嘗試重新載入...")
            driver.get("https://judgment.judicial.gov.tw/LAW_Mobile_Search/JudSearch.aspx")
            time.sleep(2)

        wait = WebDriverWait(driver, 20)
        
        # 尋找搜尋框
        try:
            search_input = wait.until(EC.presence_of_element_located((By.ID, "txtKW")))
        except TimeoutException:
            print(f"❌ 錯誤: 在頁面 {driver.title} 找不到搜尋框 (可能被攔截)")
            return []

        search_input.clear()
        # 模擬真人輸入
        for char in name:
            search_input.send_keys(char)
            time.sleep(random.uniform(0.1, 0.3))
        
        time.sleep(0.5)

        # 尋找並點擊搜尋按鈕
        try:
            btn_search = driver.find_element(By.ID, "btnSearch")
            btn_search.click()
        except NoSuchElementException:
            print("❌ 錯誤: 找不到搜尋按鈕")
            return []

        print("🖱️ 已點擊搜尋按鈕，等待結果...")

        # 等待結果表格出現
        try:
            wait.until(EC.presence_of_element_located((By.ID, "gv")))
            print("✅ 找到結果表格")
        except TimeoutException:
            print(f"ℹ️ 提示: {name} 查無裁判紀錄或載入逾時")
            return []

        # 抓取前 6 筆裁判紀錄連結
        links = driver.find_elements(By.CSS_SELECTOR, "#gv tr a")
        print(f"🔗 找到 {len(links)} 個連結")
        
        count = 0
        for link_element in links:
            if count >= 6: break
            try:
                content = link_element.text.strip()
                href = link_element.get_attribute("href")
                
                if content and href and "JudDetail" in href:
                    judgments.append({
                        "id": count + 1,
                        "content": content,
                        "link": href
                    })
                    count += 1
            except: continue

        print(f"✅ [v5] 成功抓取 {len(judgments)} 筆裁判紀錄")
        return judgments

    except Exception as e:
        print(f"❌ [v5] 搜尋失敗: {e}")
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
    return "Judgment API v5 (Anti-Bot) is running."

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
