const puppeteer = require('puppeteer');

(async () => {
  console.log('🚀 启动Puppeteer浏览器测试...');
  
  const browser = await puppeteer.launch({
    headless: false, // 显示浏览器窗口
    defaultViewport: { width: 1200, height: 800 }
  });
  
  try {
    const page = await browser.newPage();
    
    console.log('📱 访问股票助手页面...');
    await page.goto('http://localhost:8001', { 
      waitUntil: 'networkidle2',
      timeout: 10000 
    });
    
    // 等待页面加载
    await page.waitForTimeout(2000);
    
    console.log('📊 测试聊天功能...');
    // 点击聊天输入框并输入消息
    await page.click('#messageInput');
    await page.type('#messageInput', '茅台现在多少钱');
    
    // 点击发送按钮
    await page.click('button[onclick="sendMessage()"]');
    
    // 等待响应
    await page.waitForTimeout(3000);
    
    console.log('🔄 测试标签切换...');
    // 点击股票池标签
    await page.evaluate(() => {
      const poolTab = Array.from(document.querySelectorAll('.tab')).find(tab => 
        tab.textContent.includes('股票池')
      );
      if (poolTab) poolTab.click();
    });
    
    await page.waitForTimeout(1000);
    
    console.log('➕ 测试添加股票功能...');
    // 在股票池中添加股票
    await page.type('#stockCode', '600519');
    await page.type('#stockName', '贵州茅台');
    await page.click('button[onclick="addStock()"]');
    
    await page.waitForTimeout(2000);
    
    // 截图
    console.log('📸 保存界面截图...');
    await page.screenshot({ 
      path: '/Users/quxiaomeng/工作/code/Claude made stock bot/screenshot.png',
      fullPage: true 
    });
    
    // 获取页面信息
    const title = await page.title();
    const url = await page.url();
    const pageContent = await page.evaluate(() => {
      return {
        chatMessages: document.getElementById('messages')?.children.length || 0,
        stockListItems: document.getElementById('stockList')?.children.length || 0,
        activeTab: document.querySelector('.tab.active')?.textContent?.trim() || '未知'
      };
    });
    
    console.log('📋 页面信息:');
    console.log(`标题: ${title}`);
    console.log(`URL: ${url}`);
    console.log(`聊天消息数: ${pageContent.chatMessages}`);
    console.log(`股票列表项: ${pageContent.stockListItems}`);
    console.log(`当前激活标签: ${pageContent.activeTab}`);
    
    // 检查控制台错误
    const logs = [];
    page.on('console', msg => {
      logs.push(`${msg.type()}: ${msg.text()}`);
    });
    
    page.on('pageerror', error => {
      console.log('❌ 页面错误:', error.message);
    });
    
    console.log('✅ 测试完成！截图已保存到 screenshot.png');
    
  } catch (error) {
    console.error('❌ 测试过程中出现错误:', error.message);
  } finally {
    await browser.close();
  }
})();