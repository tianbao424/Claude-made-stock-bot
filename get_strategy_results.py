#!/usr/bin/env python3
"""
临时脚本：从数据库获取策略筛选结果并通过HTTP提供
"""
import sqlite3
import json
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import threading
import time

class StrategyResultsHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/strategy-results':
            self.handle_strategy_results(parsed_path)
        else:
            self.send_error(404)
    
    def handle_strategy_results(self, parsed_path):
        try:
            # 解析查询参数
            query_params = parse_qs(parsed_path.query)
            limit = int(query_params.get('limit', [100])[0])
            
            # 连接数据库
            db_path = "backend/stock_pool.db"
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 获取今天的策略筛选结果
            today = datetime.now().strftime('%Y-%m-%d')
            cursor.execute('''
                SELECT stock_code, stock_name, score, signal_type, signal_strength, 
                       risk_level, current_price, strategies_passed, screening_date
                FROM advanced_screening_results 
                WHERE screening_date = ? AND strategy_type = 'advanced_daily'
                ORDER BY score DESC
                LIMIT ?
            ''', (today, limit))
            
            rows = cursor.fetchall()
            
            # 转换为JSON格式
            results = []
            for row in rows:
                results.append({
                    'stock_code': row[0],
                    'stock_name': row[1],
                    'market': 'SH' if row[0].startswith('6') else 'SZ',
                    'consecutive_days': 1,
                    'avg_rise_percent': (row[2] / 10) if row[2] else 0,
                    'total_volume': 100000,
                    'avg_volume': 100000,
                    'screening_date': row[8] or today,
                    'strategy_score': row[2] or 0,
                    'signal_type': row[3] or 'buy',
                    'signal_strength': row[4] or 'strong',
                    'risk_level': row[5] or 'medium',
                    'current_price': row[6] or 0,
                    'strategies_passed': json.loads(row[7]) if row[7] else []
                })
            
            conn.close()
            
            # 返回结果
            response = {
                'success': True,
                'data': results,
                'message': f'获取到 {len(results)} 条策略筛选结果',
                'total_in_db': len(results)
            }
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(response, ensure_ascii=False).encode())
            
        except Exception as e:
            error_response = {
                'success': False,
                'message': f'获取策略结果失败: {str(e)}',
                'data': []
            }
            
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(error_response).encode())

def start_temp_server():
    """启动临时服务器"""
    server = HTTPServer(('localhost', 8899), StrategyResultsHandler)
    print("🚀 临时策略结果服务器启动在 http://localhost:8899")
    print("📊 API端点: http://localhost:8899/strategy-results?limit=100")
    
    # 在后台运行
    def run():
        server.serve_forever()
    
    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    
    return server

if __name__ == "__main__":
    server = start_temp_server()
    
    try:
        print("按 Ctrl+C 停止服务器...")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n⏹️ 停止服务器")
        server.shutdown()