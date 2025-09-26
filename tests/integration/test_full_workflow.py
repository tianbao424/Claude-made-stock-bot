"""
集成测试 - 完整工作流程测试
测试前后端协作和完整业务流程
"""
import pytest
import asyncio
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import DatabaseManager

client = TestClient(app)

class TestFullWorkflow:
    """完整工作流程集成测试"""
    
    def test_complete_stock_pool_lifecycle(self):
        """测试股票池完整生命周期"""
        # 1. 创建股票池
        stock_data = {
            "stock_code": "000001",
            "stock_name": "平安银行",
            "pool_type": "holding",
            "shares": 1000,
            "avg_cost": 12.50,
            "current_price": 13.20,
            "tags": ["银行", "金融"],
            "notes": "集成测试股票"
        }
        
        create_response = client.post("/api/stock-pools", json=stock_data)
        assert create_response.status_code == 200
        create_data = create_response.json()
        assert create_data["success"] is True
        stock_id = create_data["data"]["id"]
        
        # 2. 获取创建的股票池
        get_response = client.get(f"/api/stock-pools/{stock_id}")
        assert get_response.status_code == 200
        get_data = get_response.json()
        assert get_data["success"] is True
        assert get_data["data"]["stock_code"] == "000001"
        assert get_data["data"]["stock_name"] == "平安银行"
        
        # 3. 更新股票池
        update_data = {
            "shares": 1200,
            "current_price": 14.00,
            "notes": "更新后的持仓"
        }
        
        update_response = client.put(f"/api/stock-pools/{stock_id}", json=update_data)
        assert update_response.status_code == 200
        update_result = update_response.json()
        assert update_result["success"] is True
        assert update_result["data"]["shares"] == 1200
        assert update_result["data"]["current_price"] == 14.00
        
        # 4. 生成AI策略分析
        strategy_response = client.post(f"/api/strategy/generate/{stock_id}")
        assert strategy_response.status_code == 200
        strategy_data = strategy_response.json()
        assert strategy_data["success"] is True
        assert "analysis_id" in strategy_data["data"]
        
        # 5. 获取策略分析历史
        history_response = client.get(f"/api/strategy/history/{stock_id}")
        assert history_response.status_code == 200
        history_data = history_response.json()
        assert history_data["success"] is True
        assert len(history_data["data"]) >= 1
        
        # 6. 删除股票池
        delete_response = client.delete(f"/api/stock-pools/{stock_id}")
        assert delete_response.status_code == 200
        delete_data = delete_response.json()
        assert delete_data["success"] is True
        
        # 7. 验证已删除
        verify_response = client.get(f"/api/stock-pools/{stock_id}")
        assert verify_response.status_code == 404
    
    def test_stock_screening_workflow(self):
        """测试股票筛选完整流程"""
        # 1. 触发手动筛选
        criteria = {
            "screening_type": "strong_rise_3d",
            "min_consecutive_days": 3,
            "min_rise_percent": 5.0,
            "min_volume": 1000000,
            "market_filter": ["SH", "SZ"]
        }
        
        trigger_response = client.post("/api/screening/manual-trigger", json=criteria)
        assert trigger_response.status_code == 200
        trigger_data = trigger_response.json()
        assert trigger_data["success"] is True
        
        # 2. 获取最新筛选结果
        results_response = client.get("/api/screening/latest-results")
        assert results_response.status_code == 200
        results_data = results_response.json()
        assert results_data["success"] is True
        assert "data" in results_data
        
        # 3. 获取筛选历史
        history_response = client.get("/api/screening/history")
        assert history_response.status_code == 200
        history_data = history_response.json()
        assert history_data["success"] is True
    
    def test_data_sync_workflow(self):
        """测试数据同步工作流程"""
        # 1. 检查数据源状态
        status_response = client.get("/api/data-sources/status")
        assert status_response.status_code == 200
        status_data = status_response.json()
        assert status_data["success"] is True
        
        # 2. 手动触发数据同步
        sync_data = {
            "sync_type": "daily_data_collection"
        }
        
        sync_response = client.post("/api/data-sources/sync", json=sync_data)
        assert sync_response.status_code == 200
        sync_result = sync_response.json()
        assert sync_result["success"] is True
    
    def test_stock_search_and_info_workflow(self):
        """测试股票搜索和信息查询流程"""
        # 1. 搜索股票
        search_response = client.get("/api/stocks/search?query=平安")
        assert search_response.status_code == 200
        search_data = search_response.json()
        assert search_data["success"] is True
        
        # 2. 获取股票详细信息
        info_response = client.get("/api/stocks/info/000001")
        assert info_response.status_code == 200
        info_data = info_response.json()
        assert info_data["success"] is True
        
        # 3. 获取实时行情
        realtime_response = client.get("/api/stocks/realtime/000001")
        assert realtime_response.status_code == 200
        realtime_data = realtime_response.json()
        assert realtime_data["success"] is True

class TestErrorHandling:
    """错误处理集成测试"""
    
    def test_invalid_stock_creation(self):
        """测试无效股票创建的错误处理"""
        invalid_data = {
            "stock_code": "",  # 空代码
            "stock_name": "",  # 空名称
            "pool_type": "invalid_type"  # 无效类型
        }
        
        response = client.post("/api/stock-pools", json=invalid_data)
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
    
    def test_nonexistent_resource_access(self):
        """测试访问不存在资源的错误处理"""
        # 访问不存在的股票池
        response = client.get("/api/stock-pools/99999")
        assert response.status_code == 404
        
        # 尝试删除不存在的股票池
        response = client.delete("/api/stock-pools/99999")
        assert response.status_code == 404
        
        # 为不存在的股票池生成策略
        response = client.post("/api/strategy/generate/99999")
        assert response.status_code == 404
    
    def test_invalid_screening_criteria(self):
        """测试无效筛选条件的错误处理"""
        invalid_criteria = {
            "min_consecutive_days": -1,  # 负数
            "min_rise_percent": -10,     # 负数
            "market_filter": []          # 空筛选
        }
        
        response = client.post("/api/screening/manual-trigger", json=invalid_criteria)
        assert response.status_code == 400

class TestPerformance:
    """性能相关集成测试"""
    
    def test_bulk_operations_performance(self):
        """测试批量操作性能"""
        import time
        
        # 批量创建股票池
        stock_ids = []
        start_time = time.time()
        
        for i in range(10):
            stock_data = {
                "stock_code": f"00000{i}",
                "stock_name": f"测试股票{i}",
                "pool_type": "holding",
                "shares": 1000 + i * 100,
                "avg_cost": 10.0 + i
            }
            
            response = client.post("/api/stock-pools", json=stock_data)
            assert response.status_code == 200
            stock_ids.append(response.json()["data"]["id"])
        
        creation_time = time.time() - start_time
        assert creation_time < 5.0  # 应该在5秒内完成
        
        # 批量获取
        start_time = time.time()
        for stock_id in stock_ids:
            response = client.get(f"/api/stock-pools/{stock_id}")
            assert response.status_code == 200
        
        retrieval_time = time.time() - start_time
        assert retrieval_time < 2.0  # 应该在2秒内完成
        
        # 清理
        for stock_id in stock_ids:
            client.delete(f"/api/stock-pools/{stock_id}")
    
    def test_concurrent_requests(self):
        """测试并发请求处理"""
        import concurrent.futures
        import threading
        
        def make_request():
            response = client.get("/api/stock-pools")
            return response.status_code == 200
        
        # 并发发送10个请求
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # 所有请求都应该成功
        assert all(results)

class TestWebSocketIntegration:
    """WebSocket集成测试"""
    
    def test_websocket_connection(self):
        """测试WebSocket连接"""
        with client.websocket_connect("/ws") as websocket:
            # 发送测试消息
            test_message = {
                "type": "query",
                "content": "查询平安银行股价",
                "timestamp": "2023-01-01T00:00:00Z"
            }
            
            websocket.send_json(test_message)
            
            # 接收响应
            response = websocket.receive_json()
            
            assert "type" in response
            assert "content" in response
            assert response["type"] in ["response", "error"]

if __name__ == "__main__":
    pytest.main([__file__, "-v"])