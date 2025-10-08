import os
from flask import Flask, jsonify, request
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
import json

app = Flask(__name__)

class JudgmentAPI:
    def __init__(self):
        self.driver = None
        self.setup_driver()
    
    def setup_driver(self):
        """設置瀏覽器驅動 - Heroku 兼容版本"""
        try:
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
                chrome_options.binary_location = os.environ.get('GOOGLE_CHROME_BIN')
                service = Service(executable_path=os.environ.get('CHROMEDRIVER_PATH'))
            else:
                service = Service(ChromeDriverManager().install())
            
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.set_page_load_timeout(15)
            print("✅ 瀏覽器驅動初始化成功")
        except Exception as e:
            print(f"❌ 瀏覽器驅動初始化失敗: {e}")
            self.driver = None
    
    def search_judgments(self, name):
        """
        搜索判決書主函數
        """
        if not self.driver:
            return self.create_error_response("DRIVER_NOT_READY", "瀏覽器驅動未就緒")
        
        try:
            print(f"🔍 開始搜索: {name}")
            
            # 訪問網站
            self.driver.get("https://judgment.judicial.gov.tw/LAW_Mobile_FJUD/FJUD/default.aspx")
            time.sleep(2)
            
            # 輸入姓名
            name_input = self.driver.find_element(By.XPATH, "/html/body/form/div[5]/div[1]/div[1]/input")
            name_input.clear()
            name_input.send_keys(name)
            
            # 點擊查詢
            search_button = self.driver.find_element(By.XPATH, "/html/body/form/div[5]/div[1]/div[2]/input[1]")
            search_button.click()
            time.sleep(3)
            
            # 抓取表格文字
            table = self.driver.find_element(By.TAG_NAME, "table")
            table_text = table.text
            
            # 解析前六筆資料
            judgments = self.parse_judgments(table_text)
            
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
            return self.create_error_response("SEARCH_FAILED", str(e))
    
    def parse_judgments(self, table_text):
        """
        解析判決書文字為JSON格式
        """
        judgments = []
        lines = table_text.split('\n')
        current_judgment = {}
        count = 0
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # 只取前六筆
            if count >= 6:
                break
                
            # 判斷是否是編號行
            if line[0].isdigit() and '.' in line:
                if current_judgment and 'header' in current_judgment:
                    judgments.append(current_judgment)
                    count += 1
                    if count >= 6:
                        break
                
                # 清理格式
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
        
        # 添加最後一個
        if current_judgment and 'header' in current_judgment and count < 6:
            judgments.append(current_judgment)
        
        return judgments
    
    def create_error_response(self, error_code, error_message):
        """創建錯誤回應"""
        return {
            "api_version": "1.0",
            "status": "error",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "request": {
                "name": "未知",
                "search_type": "姓名搜索"
            },
            "error": {
                "code": error_code,
                "message": error_message
            },
            "response": {
                "total_found": 0,
                "judgments": []
            }
        }
    
    def close(self):
        """關閉瀏覽器"""
        if self.driver:
            self.driver.quit()

# 創建API實例
judgment_api = JudgmentAPI()

@app.route('/api/search', methods=['POST'])
def api_search():
    """
    主要API端點 - 搜索判決書
    """
    try:
        if not request.is_json:
            return jsonify({
                "api_version": "1.0",
                "status": "error",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "request": {"name": "未知", "search_type": "姓名搜索"},
                "error": {"code": "INVALID_FORMAT", "message": "請求必須是JSON格式"},
                "response": {"total_found": 0, "judgments": []}
            }), 400
        
        data = request.get_json()
        
        if not data or 'name' not in data:
            return jsonify({
                "api_version": "1.0",
                "status": "error",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "request": {"name": "未知", "search_type": "姓名搜索"},
                "error": {"code": "MISSING_PARAMETER", "message": "缺少必要參數: name"},
                "response": {"total_found": 0, "judgments": []}
            }), 400
        
        name = data['name'].strip()
        if not name:
            return jsonify({
                "api_version": "1.0",
                "status": "error",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "request": {"name": "空值", "search_type": "姓名搜索"},
                "error": {"code": "EMPTY_NAME", "message": "姓名不能為空"},
                "response": {"total_found": 0, "judgments": []}
            }), 400
        
        # 執行搜索
        result = judgment_api.search_judgments(name)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "api_version": "1.0",
            "status": "error",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "request": {"name": "未知", "search_type": "姓名搜索"},
            "error": {"code": "SERVER_ERROR", "message": f"伺服器錯誤: {str(e)}"},
            "response": {"total_found": 0, "judgments": []}
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """健康檢查端點"""
    return jsonify({
        "api_version": "1.0",
        "status": "healthy",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "service": "司法院判決書搜索API"
    })

@app.route('/api/info', methods=['GET'])
def api_info():
    """API資訊端點"""
    return jsonify({
        "api_version": "1.0",
        "name": "司法院判決書搜索API",
        "description": "根據姓名搜索司法院判決書",
        "endpoints": {
            "POST /api/search": "搜索判決書",
            "GET /api/health": "健康檢查",
            "GET /api/info": "API資訊"
        },
        "usage": {
            "search": {
                "method": "POST",
                "url": "/api/search",
                "body": {"name": "姓名"}
            }
        }
    })

@app.route('/')
def home():
    """根目錄"""
    return jsonify({
        "message": "司法院判決書搜索API",
        "version": "1.0",
        "documentation": "請訪問 /api/info 查看使用說明",
        "deployed_on": "Heroku"
    })

# 應用程式關閉時清理資源
import atexit
@atexit.register
def cleanup():
    judgment_api.close()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, threaded=True)