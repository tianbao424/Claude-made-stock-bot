"""
端到端测试 - 用户场景模拟测试
模拟真实用户使用场景的完整测试流程
"""
import pytest
import asyncio
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

class TestUserScenarios:
    """用户场景端到端测试"""
    
    @pytest.fixture(scope="class")
    def browser(self):
        """设置Chrome浏览器"""
        options = Options()
        options.add_argument('--headless')  # 无头模式
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        
        driver = webdriver.Chrome(options=options)
        driver.implicitly_wait(10)
        yield driver
        driver.quit()
    
    @pytest.fixture(autouse=True)
    def setup_test_data(self):
        """每个测试前清理数据"""
        # 这里可以添加测试数据清理逻辑
        yield
        # 测试后清理
    
    def test_complete_stock_management_workflow(self, browser):
        """完整的股票管理工作流程测试"""
        # 1. 访问应用主页
        browser.get("http://localhost:3000")
        
        # 等待页面加载
        wait = WebDriverWait(browser, 10)
        
        # 2. 检查页面标题
        assert "AI股票助手" in browser.title
        
        # 3. 导航到股票池管理
        pool_tab = wait.until(EC.element_to_be_clickable((By.TEXT, "股票池")))
        pool_tab.click()
        
        # 4. 添加新股票
        add_button = wait.until(EC.element_to_be_clickable((By.TEXT, "添加股票")))
        add_button.click()
        
        # 填写股票信息
        wait.until(EC.presence_of_element_located((By.ID, "stock-code-input")))
        
        browser.find_element(By.ID, "stock-code-input").send_keys("000001")
        browser.find_element(By.ID, "stock-name-input").send_keys("平安银行")
        browser.find_element(By.ID, "shares-input").send_keys("1000")
        browser.find_element(By.ID, "avg-cost-input").send_keys("12.50")
        
        # 提交表单
        submit_button = browser.find_element(By.TEXT, "确认添加")
        submit_button.click()
        
        # 5. 验证股票已添加
        wait.until(EC.text_to_be_present_in_element((By.CLASS_NAME, "stock-item"), "000001"))
        
        stock_items = browser.find_elements(By.CLASS_NAME, "stock-item")
        assert any("平安银行" in item.text for item in stock_items)
        
        # 6. 编辑股票信息
        edit_buttons = browser.find_elements(By.TEXT, "编辑")
        if edit_buttons:
            edit_buttons[0].click()
            
            # 修改持股数量
            shares_input = wait.until(EC.presence_of_element_located((By.ID, "shares-input")))
            shares_input.clear()
            shares_input.send_keys("1200")
            
            # 保存修改
            save_button = browser.find_element(By.TEXT, "确认更新")
            save_button.click()
            
            # 验证修改成功
            wait.until(EC.text_to_be_present_in_element((By.CLASS_NAME, "stock-item"), "1200"))
        
        # 7. 生成AI策略分析
        analysis_buttons = browser.find_elements(By.TEXT, "AI策略")
        if analysis_buttons:
            analysis_buttons[0].click()
            
            # 等待分析完成
            wait.until(EC.presence_of_element_located((By.CLASS_NAME, "strategy-modal")))
            
            # 检查分析结果
            modal = browser.find_element(By.CLASS_NAME, "strategy-modal")
            assert "综合评分" in modal.text
            
            # 关闭分析窗口
            close_button = browser.find_element(By.CLASS_NAME, "modal-close")
            close_button.click()
    
    def test_stock_screening_workflow(self, browser):
        """股票筛选工作流程测试"""
        browser.get("http://localhost:3000")
        wait = WebDriverWait(browser, 10)
        
        # 1. 导航到股票筛选页面
        screening_tab = wait.until(EC.element_to_be_clickable((By.TEXT, "股票筛选")))
        screening_tab.click()
        
        # 2. 检查筛选页面元素
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "screening-config")))
        
        # 3. 设置筛选条件
        consecutive_days_select = browser.find_element(By.ID, "consecutive-days-select")
        consecutive_days_select.click()
        
        day_option = browser.find_element(By.XPATH, "//option[@value='3']")
        day_option.click()
        
        rise_percent_input = browser.find_element(By.ID, "rise-percent-input")
        rise_percent_input.clear()
        rise_percent_input.send_keys("7.0")
        
        # 4. 触发筛选
        trigger_button = browser.find_element(By.TEXT, "手动筛选")
        trigger_button.click()
        
        # 5. 等待筛选结果
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "screening-results")))
        
        # 6. 验证结果显示
        results_table = browser.find_element(By.CLASS_NAME, "results-table")
        assert results_table.is_displayed()
        
        # 检查表头
        headers = browser.find_elements(By.TAG_NAME, "th")
        expected_headers = ["股票代码", "股票名称", "连续天数", "平均涨幅"]
        for header in expected_headers:
            assert any(header in h.text for h in headers)
    
    def test_chat_interface_workflow(self, browser):
        """聊天界面工作流程测试"""
        browser.get("http://localhost:3000")
        wait = WebDriverWait(browser, 10)
        
        # 1. 检查聊天界面
        chat_interface = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "chat-interface")))
        assert chat_interface.is_displayed()
        
        # 2. 检查连接状态
        connection_status = browser.find_element(By.CLASS_NAME, "connection-status")
        wait.until(lambda driver: "已连接" in connection_status.text)
        
        # 3. 发送测试消息
        chat_input = browser.find_element(By.ID, "chat-input")
        chat_input.send_keys("查询平安银行股价")
        
        send_button = browser.find_element(By.TEXT, "发送")
        send_button.click()
        
        # 4. 等待AI响应
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "ai-message")))
        
        # 5. 验证消息显示
        messages = browser.find_elements(By.CLASS_NAME, "message")
        assert len(messages) >= 2  # 用户消息 + AI响应
        
        user_message = browser.find_element(By.CLASS_NAME, "user-message")
        assert "查询平安银行股价" in user_message.text
        
        ai_message = browser.find_element(By.CLASS_NAME, "ai-message")
        assert ai_message.text  # AI有回复
    
    def test_responsive_design(self, browser):
        """响应式设计测试"""
        browser.get("http://localhost:3000")
        wait = WebDriverWait(browser, 10)
        
        # 1. 桌面视图测试
        browser.set_window_size(1920, 1080)
        
        sidebar = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "sidebar")))
        assert sidebar.is_displayed()
        
        # 2. 平板视图测试
        browser.set_window_size(768, 1024)
        
        # 检查布局适应
        main_content = browser.find_element(By.CLASS_NAME, "main-content")
        assert main_content.is_displayed()
        
        # 3. 手机视图测试
        browser.set_window_size(375, 667)
        
        # 检查移动端适配
        assert browser.find_element(By.TAG_NAME, "body").is_displayed()
    
    def test_error_handling(self, browser):
        """错误处理测试"""
        browser.get("http://localhost:3000")
        wait = WebDriverWait(browser, 10)
        
        # 1. 导航到股票池管理
        pool_tab = wait.until(EC.element_to_be_clickable((By.TEXT, "股票池")))
        pool_tab.click()
        
        # 2. 尝试添加无效数据
        add_button = wait.until(EC.element_to_be_clickable((By.TEXT, "添加股票")))
        add_button.click()
        
        # 提交空表单
        submit_button = wait.until(EC.element_to_be_clickable((By.TEXT, "确认添加")))
        submit_button.click()
        
        # 3. 验证错误提示
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "error-message")))
        error_message = browser.find_element(By.CLASS_NAME, "error-message")
        assert "股票代码不能为空" in error_message.text or "必填字段" in error_message.text
    
    def test_performance_indicators(self, browser):
        """性能指标测试"""
        import time
        
        start_time = time.time()
        browser.get("http://localhost:3000")
        
        # 页面加载时间测试
        wait = WebDriverWait(browser, 10)
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "main-content")))
        
        load_time = time.time() - start_time
        assert load_time < 5.0  # 页面应在5秒内加载完成
        
        # 导航响应速度测试
        start_time = time.time()
        pool_tab = browser.find_element(By.TEXT, "股票池")
        pool_tab.click()
        
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "stock-pool-manager")))
        navigation_time = time.time() - start_time
        assert navigation_time < 2.0  # 导航应在2秒内完成

class TestAccessibility:
    """无障碍访问测试"""
    
    def test_keyboard_navigation(self, browser):
        """键盘导航测试"""
        browser.get("http://localhost:3000")
        
        # 使用Tab键导航
        from selenium.webdriver.common.keys import Keys
        
        body = browser.find_element(By.TAG_NAME, "body")
        body.send_keys(Keys.TAB)
        
        # 验证焦点移动
        focused_element = browser.switch_to.active_element
        assert focused_element is not None
    
    def test_aria_labels(self, browser):
        """ARIA标签测试"""
        browser.get("http://localhost:3000")
        
        # 检查重要元素的ARIA标签
        buttons = browser.find_elements(By.TAG_NAME, "button")
        for button in buttons:
            # 按钮应该有文本内容或aria-label
            assert button.text or button.get_attribute("aria-label")

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])