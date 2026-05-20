# app.py (原版架構強化版 v3)

import os
import time
from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

app = Flask(__name__)

def search_judgments(name):
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    # 加入偽裝，減少被攔截機率
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(options=chrome_options)
    judgments = []
    
    try:
        print(f"🔍 [v3] 開始搜尋: {name}")
        driver.get("https://judgment.judicial.gov.tw/LAW_Mobile_Search/JudSearch.aspx")
        
        # 等待輸入框
        wait = WebDriverWait(driver, 15)
        search_input = wait.until(EC.presence_of_element_located((By.ID, "txtKW")))
        search_input.send_keys(name)
        
        btn_search = driver.find_element(By.ID, "btnSearch")
        btn_search.click()
        print("🖱️ 已點擊搜尋，等待結果...")
        
        # 等待表格出現
        try:
            wait.until(EC.presence_of_element_located((By.ID, "gv")))
            time.sleep(2) # 穩定的等待
        except:
            print("⚠️ 等待表格逾時，目前的網頁標題是:", driver.title)
        
        # 抓取表格行
        rows = driver.find_elements(By.CSS_SELECTOR, "#gv tr")
        print(f"📊 總共抓取到 {len(rows)} 行資料")
        
        # 跳過標題行
        for i, row in enumerate(rows[1:13]):
            try:
                content = row.text.strip()
                link = ""
                try:
                    link_element = row.find_element(By.TAG_NAME, "a")
                    link = link_element.get_attribute("href")
                except:
                    pass
                
                if content:
                    judgments.append({
                        "id": i + 1,
                        "content": content,
                        "link": link
                    })
            except:
                continue
        
        print(f"✅ 成功處理 {len(judgments)} 筆紀錄")
                
    except Exception as e:
        print(f"❌ 發生錯誤: {e}")
    finally:
        driver.quit()
        
    return judgments

@app.route("/api/search", methods=["POST"])
def api_search():
    data = request.json
    name = data.get("name")
    if not name:
        return jsonify({"status": "error", "message": "Missing name"}), 400
        
    results = search_judgments(name)
    return jsonify({
        "status": "success",
        "judgments": results
    })

@app.route("/")
def index():
    return "Judgment API v3 is running."

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
