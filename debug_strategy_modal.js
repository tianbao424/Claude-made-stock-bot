// 调试脚本：在浏览器控制台中运行，模拟策略应用成功后的数据

// 模拟后端返回的数据
const mockResult = {
    success: true,
    data: {
        results: Array(625).fill(null).map((_, i) => ({
            stock_code: `00${1000 + i}`,
            stock_name: `股票${i}`,
            weighted_score: 70 + Math.random() * 30
        })),
        screening_date: "2025-10-20",
        summary: {
            total_found: 625,  // 候选股票总数
            after_strategy_filter: 625,  // 通过策略筛选的数量
            strategies_used: 2,  // 使用的策略数量
            filter_efficiency: 1.0  // 筛选效率
        }
    }
};

// 在控制台输出，用于调试
console.log('🔍 模拟后端返回数据：');
console.log('成功状态:', mockResult.success);
console.log('结果数量:', mockResult.data.results.length);
console.log('总分析数:', mockResult.data.summary.total_found);
console.log('策略筛选后:', mockResult.data.summary.after_strategy_filter);
console.log('使用策略数:', mockResult.data.summary.strategies_used);

// 测试前端逻辑
const resultCount = mockResult.data?.results?.length || 0;
const totalAnalyzed = mockResult.data?.summary?.total_found || 0;

console.log('\n📊 前端解析结果：');
console.log('resultCount:', resultCount);
console.log('totalAnalyzed:', totalAnalyzed);

// 如果 resultCount 和 totalAnalyzed 都是 625，说明数据正确
if (resultCount === 625 && totalAnalyzed === 625) {
    console.log('✅ 数据解析正确，应该显示模态框');
    console.log(`提示内容: 分析了 ${totalAnalyzed} 只股票，找到 ${resultCount} 只符合条件的股票`);
} else {
    console.log('❌ 数据解析有问题');
}

// 保存到 sessionStorage 测试
sessionStorage.setItem('latest_screening_result', JSON.stringify(mockResult));
console.log('\n💾 数据已保存到 sessionStorage');
console.log('可以刷新股票甄选页面查看是否能加载策略结果');