# app.py (原版架構強化版 v2)

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
    
    driver = webdriver.Chrome(options=chrome_options)
    judgments = []
    
    try:
        # 使用您原有的穩定路徑
        driver.get("https://judgment.judicial.gov.tw/LAW_Mobile_Search/JudSearch.aspx")
        
        search_input = driver.find_element(By.ID, "txtKW")
        search_input.send_keys(name)
        
        btn_search = driver.find_element(By.ID, "btnSearch")
        btn_search.click()
        
        # --- 新增：確保表格載入的等待邏輯 ---
        wait = WebDriverWait(driver, 15)
        try:
            wait.until(EC.presence_of_element_located((By.ID, "gv")))
            time.sleep(1) # 額外多等一秒確保渲染完成
        except:
            print("Timeout waiting for results table")
        # ----------------------------------
        
        # 修改解析邏輯：抓取 12 行以確保有 6 筆，並同步抓取連結
        rows = driver.find_elements(By.CSS_SELECTOR, "#gv tr")
        print(f"Found {len(rows)} rows")
        
        # 跳過標題行，抓取後續內容
        for i, row in enumerate(rows[1:13]):
            try:
                content = row.text.strip()
                link = ""
                try:
                    # 嘗試抓取該行內的連結
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
