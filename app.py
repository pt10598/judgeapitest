import os
import time
import json
from flask import Flask, jsonify, request
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

app = Flask(__name__)

def init_driver():
    """簡單的驅動初始化 - 恢復原本可工作的版本"""
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    
    # 簡單初始化，讓 Selenium 自動處理路徑
    driver = webdriver.Chrome(options=chrome_options)
    return driver

def search_judgments(name):
    """搜索判決書主函數"""
    driver = None
    try:
        driver = init_driver()
        print(f"🔍 開始搜索: {name}")
        
        # 訪問網站
        driver.get("https://judgment.judicial.gov.tw/LAW_Mobile_FJUD/FJUD/default.aspx")
        time.sleep(2)
        
        # 輸入姓名
        name_input = driver.find_element(By.XPATH, "/html/body/form/div[5]/div[1]/div[1]/input")
        name_input.clear()
        name_input.send_keys(name)
        
        # 點擊查詢
        search_button = driver.find_element(By.XPATH, "/html/body/form/div[5]/div[1]/div[2]/input[1]")
        search_button.click()
        time.sleep(3)
        
        # 抓取表格文字
        table = driver.find_element(By.TAG_NAME, "table")
        table_text = table.text
        
        # 解析前六筆資料
        judgments = parse_judgments(table_text)
        
        print(f"✅ 搜索完成，找到 {len(judgments)} 筆資料")
        
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

def parse_judgments(table_text):
    """解析判決書文字"""
    judgments = []
    lines = table_text.split('\n')
    
    for i, line in enumerate(lines[:6]):  # 只取前6行
        line = line.strip()
        if line:
            judgments.append({
                "id": i + 1,
                "content": line
            })
    
    return judgments

@app.route('/api/search', methods=['POST'])
def api_search():
    """搜索判決書 API - 簡化版本"""
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
            "message": f"伺服器錯誤: {str(e)}"
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
