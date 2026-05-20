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

# 建立線程鎖，確保同一時間只有一個爬蟲在執行，避免多人併發導致的資源衝突
search_lock = threading.Lock()

def init_driver():
    """初始化瀏覽器驅動"""
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    
    # 增加穩定性參數
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    
    driver = webdriver.Chrome(options=chrome_options)
    # 設定隱式等待
    driver.implicitly_wait(10)
    return driver

def search_judgments(name):
    """搜索判決書主函數"""
    driver = None
    # 使用 lock 確保排隊執行
    with search_lock:
        try:
            driver = init_driver()
            print(f"🔍 開始搜索: {name}")
            
            # 訪問網站 (維持原版路徑)
            driver.get("https://judgment.judicial.gov.tw/LAW_Mobile_FJUD/FJUD/default.aspx")
            
            # 等待輸入框出現 (維持原版 XPATH)
            wait = WebDriverWait(driver, 15)
            name_input = wait.until(EC.presence_of_element_located((By.XPATH, "/html/body/form/div[5]/div[1]/div[1]/input")))
            
            name_input.clear()
            name_input.send_keys(name)
            
            # 點擊查詢 (維持原版 XPATH)
            search_button = driver.find_element(By.XPATH, "/html/body/form/div[5]/div[1]/div[2]/input[1]")
            search_button.click()
            
            # 等待結果表格出現
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))
            time.sleep(1) # 額外等待確保渲染完成
            
            # 抓取表格與連結
            table = driver.find_element(By.TAG_NAME, "table")
            rows = table.find_elements(By.TAG_NAME, "tr")
            
            judgments = []
            # 從第一行(跳過標題)開始解析
            for row in rows[1:]:
                row_text = row.text.strip()
                if not row_text:
                    continue
                
                # 獲取該行的超連結
                link = ""
                try:
                    a_tag = row.find_element(By.TAG_NAME, "a")
                    link = a_tag.get_attribute("href")
                except:
                    pass
                
                # 按照您原本的邏輯，將每一行拆開，但為同一筆紀錄的行附上相同的連結
                for line in row_text.split('\n'):
                    line = line.strip()
                    if line:
                        judgments.append({
                            "id": len(judgments) + 1,
                            "content": line,
                            "link": link
                        })
                        if len(judgments) >= 12: # 維持原本取 12 行的設定
                            break
                if len(judgments) >= 12:
                    break
            
            print(f"✅ 搜索完成，找到 {len(judgments)} 行資料")
            
            return {
                "status": "success",
                "total_found": len(judgments),
                "judgments": judgments
            }
            
        except Exception as e:
            print(f"❌ 搜索失敗: {e}")
            return {
                "status": "error",
                "message": f"查詢過程出錯: {str(e)}",
                "total_found": 0,
                "judgments": []
            }
        finally:
            if driver:
                driver.quit()

@app.route('/api/search', methods=['POST'])
def api_search():
    """搜索判決書 API"""
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        
        if not name:
            return jsonify({
                "status": "error",
                "message": "姓名不能為空"
            }), 400
        
        result = search_judgments(name)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"伺服器內部錯誤: {str(e)}"
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, threaded=True)
