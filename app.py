import os
import time
import json
from flask import Flask, jsonify, request

app = Flask(__name__)

# 延遲導入 Selenium 以避免啟動問題
def init_driver():
    try:
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-images')
        
        # Heroku 環境設置
        if 'DYNO' in os.environ:
            chrome_options.binary_location = os.environ.get('GOOGLE_CHROME_BIN', '/app/.apt/usr/bin/google-chrome')
            service = Service(executable_path=os.environ.get('CHROMEDRIVER_PATH', '/app/.chromedriver/bin/chromedriver'))
        else:
            from webdriver_manager.chrome import ChromeDriverManager
            service = Service(ChromeDriverManager().install())
        
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.set_page_load_timeout(15)
        return driver
    except Exception as e:
        print(f"❌ 驅動初始化失敗: {e}")
        return None

def search_judgments(name):
    """搜索判決書主函數"""
    driver = None
    try:
        driver = init_driver()
        if not driver:
            return {
                "status": "error",
                "message": "瀏覽器驅動初始化失敗"
            }
        
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
            "api_version": "1.0",
            "status": "success",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "request": {
                "name": name,
                "search_type": "姓名搜索"
            },
            "response": {
                "total_found": len(judgments),
                "judgments": judgments
            }
        }
        
    except Exception as e:
        print(f"❌ 搜索失敗: {e}")
        return {
            "api_version": "1.0",
            "status": "error",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "request": {
                "name": name,
                "search_type": "姓名搜索"
            },
            "error": {
                "code": "SEARCH_FAILED",
                "message": str(e)
            },
            "response": {
                "total_found": 0,
                "judgments": []
            }
        }
    finally:
        if driver:
            driver.quit()

def parse_judgments(table_text):
    """解析判決書文字"""
    judgments = []
    lines = table_text.split('\n')
    current_judgment = {}
    count = 0
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        if count >= 6:
            break
            
        if line[0].isdigit() and '.' in line:
            if current_judgment and 'header' in current_judgment:
                judgments.append(current_judgment)
                count += 1
                if count >= 6:
                    break
            
            cleaned_line = line.replace('（1K）', '').replace('（1k）', '').replace('(1K)', '').strip()
            current_judgment = {
                "id": count + 1,
                "header": cleaned_line
            }
        else:
            if current_judgment and 'header' in current_judgment:
                current_judgment["case_type"] = line
                judgments.append(current_judgment)
                count += 1
                current_judgment = {}
                if count >= 6:
                    break
    
    if current_judgment and 'header' in current_judgment and count < 6:
        judgments.append(current_judgment)
    
    return judgments

@app.route('/api/search', methods=['POST'])
def api_search():
    """搜索判決書 API"""
    try:
        if not request.is_json:
            return jsonify({
                "api_version": "1.0",
                "status": "error",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "error": {"code": "INVALID_FORMAT", "message": "請求必須是JSON格式"},
                "response": {"total_found": 0, "judgments": []}
            }), 400
        
        data = request.get_json()
        name = data.get('name', '').strip()
        
        if not name:
            return jsonify({
                "api_version": "1.0",
                "status": "error",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "error": {"code": "EMPTY_NAME", "message": "姓名不能為空"},
                "response": {"total_found": 0, "judgments": []}
            }), 400
        
        result = search_judgments(name)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "api_version": "1.0",
            "status": "error",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "error": {"code": "SERVER_ERROR", "message": f"伺服器錯誤: {str(e)}"},
            "response": {"total_found": 0, "judgments": []}
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        "api_version": "1.0",
        "status": "healthy",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "service": "司法院判決書搜索API"
    })

@app.route('/api/info', methods=['GET'])
def api_info():
    return jsonify({
        "api_version": "1.0",
        "name": "司法院判決書搜索API",
        "description": "根據姓名搜索司法院判決書",
        "endpoints": {
            "POST /api/search": "搜索判決書",
            "GET /api/health": "健康檢查",
            "GET /api/info": "API資訊"
        }
    })

@app.route('/')
def home():
    return jsonify({
        "message": "司法院判決書搜索API",
        "version": "1.0",
        "deployed_on": "Heroku"
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, threaded=True)
