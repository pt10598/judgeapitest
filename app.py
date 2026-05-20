import os
import time
import json
import threading
from flask import Flask, jsonify, request
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

app = Flask(__name__)

# 建立線程鎖，確保併發安全
search_lock = threading.Lock()

def init_driver():
    """初始化瀏覽器驅動"""
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.implicitly_wait(10)
    return driver

def search_judgments(name):
    """搜索判決書主函數，包含連結抓取"""
    driver = None
    with search_lock:
        try:
            driver = init_driver()
            print(f"🔍 開始搜索 (含連結): {name}")
            
            driver.get("https://judgment.judicial.gov.tw/LAW_Mobile_FJUD/FJUD/default.aspx")
            
            wait = WebDriverWait(driver, 15)
            name_input = wait.until(EC.presence_of_element_located((By.XPATH, "/html/body/form/div[5]/div[1]/div[1]/input")))
            name_input.clear()
            name_input.send_keys(name)
            
            search_button = driver.find_element(By.XPATH, "/html/body/form/div[5]/div[1]/div[2]/input[1]")
            search_button.click()
            
            # 等待結果列表出現
            wait.until(EC.presence_of_element_located((By.ID, "gv_result")))
            time.sleep(1)
            
            judgments = []
            # 抓取表格中的行 (排除標題行)
            rows = driver.find_elements(By.XPATH, "//table[@id='gv_result']//tr[position()>1]")
            
            # 抓取前 6 筆完整紀錄 (通常一筆紀錄佔用 1 或 2 行，我們抓取前 10 行來解析)
            for i, row in enumerate(rows[:10]):
                try:
                    # 嘗試抓取該行中的連結
                    link_element = row.find_element(By.TAG_NAME, "a")
                    link = link_element.get_attribute("href")
                    content = row.text.strip().replace("\n", " ")
                    
                    if content:
                        judgments.append({
                            "id": i + 1,
                            "content": content,
                            "link": link
                        })
                except:
                    # 如果該行沒有連結，則只抓取文字
                    content = row.text.strip().replace("\n", " ")
                    if content:
                        judgments.append({
                            "id": i + 1,
                            "content": content,
                            "link": ""
                        })
            
            print(f"✅ 搜索完成，找到 {len(judgments)} 筆帶連結資料")
            
            return {
                "status": "success",
                "total_found": len(judgments),
                "judgments": judgments
            }
            
        except Exception as e:
            print(f"❌ 搜索失敗: {e}")
            return {
                "status": "error",
                "message": str(e),
                "total_found": 0,
                "judgments": []
            }
        finally:
            if driver:
                driver.quit()

@app.route('/api/search', methods=['POST'])
def api_search():
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        if not name:
            return jsonify({"status": "error", "message": "姓名不能為空"}), 400
        
        result = search_judgments(name)
        return jsonify(result)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, threaded=True)
