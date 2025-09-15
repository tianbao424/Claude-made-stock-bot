#!/usr/bin/env python3
"""
完整股票数据导入脚本
将所有A股和港股数据导入到优化的数据表中
"""
import asyncio
import sys
import os
from typing import List, Dict

# 添加backend目录到路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from services.akshare_service import akshare_service
from services.optimized_data_service import get_optimized_data_service

async def import_a_stocks() -> List[Dict]:
    """导入A股数据"""
    print("📡 正在获取A股数据...")
    
    try:
        # 获取上海A股
        print("  🔄 获取上海A股...")
        sh_stocks = await akshare_service.get_a_stock_list()
        sh_count = len([s for s in sh_stocks if s.get('market') == 'SH'])
        
        # 获取深圳A股 (通过直接调用)
        print("  🔄 获取深圳A股...")
        import akshare as ak
        sz_data = ak.stock_info_sz_name_code()
        
        sz_stocks = []
        for _, row in sz_data.iterrows():
            if row.get('A股代码') and row.get('A股简称'):
                stock_data = {
                    'symbol': str(row['A股代码']).zfill(6),
                    'name': str(row['A股简称']).strip(),
                    'short_name': str(row['A股简称']).strip(),
                    'market': 'SZ',
                    'industry': str(row.get('行业大类', '其他')).strip() if row.get('行业大类') else '其他'
                }
                sz_stocks.append(stock_data)
        
        all_a_stocks = sh_stocks + sz_stocks
        print(f"✅ A股数据获取完成: 上海{sh_count}只, 深圳{len(sz_stocks)}只, 总计{len(all_a_stocks)}只")
        
        return all_a_stocks
        
    except Exception as e:
        print(f"❌ A股数据获取失败: {e}")
        return []

async def import_hk_stocks() -> List[Dict]:
    """导入港股数据"""
    print("📡 正在获取港股数据...")
    
    try:
        # 先尝试API获取
        hk_stocks = await akshare_service.get_hk_stock_list()
        if hk_stocks:
            print(f"✅ 港股数据获取完成: {len(hk_stocks)}只")
            return hk_stocks
        else:
            print("⚠️ 港股API获取失败，将使用精选股票列表")
            return []
        
    except Exception as e:
        print(f"❌ 港股数据获取失败: {e}")
        return []

async def create_curated_hk_list() -> List[Dict]:
    """创建精选港股列表"""
    curated_hk_stocks = [
        # 互联网科技
        {'symbol': '00700', 'name': '腾讯控股', 'industry': '互联网科技'},
        {'symbol': '09988', 'name': '阿里巴巴-SW', 'industry': '互联网科技'},
        {'symbol': '03690', 'name': '美团-W', 'industry': '互联网服务'},
        {'symbol': '01810', 'name': '小米集团-W', 'industry': '智能手机'},
        {'symbol': '09618', 'name': '京东集团-SW', 'industry': '电子商务'},
        {'symbol': '01024', 'name': '快手-W', 'industry': '社交媒体'},
        
        # 金融银行
        {'symbol': '00388', 'name': '香港交易所', 'industry': '金融服务'},
        {'symbol': '00939', 'name': '建设银行', 'industry': '银行'},
        {'symbol': '03988', 'name': '中国银行', 'industry': '银行'},
        {'symbol': '01398', 'name': '工商银行', 'industry': '银行'},
        {'symbol': '02318', 'name': '中国平安', 'industry': '保险'},
        {'symbol': '01299', 'name': '友邦保险', 'industry': '保险'},
        
        # 能源石油
        {'symbol': '00857', 'name': '中国石油股份', 'industry': '石油天然气'},
        {'symbol': '00386', 'name': '中国石化', 'industry': '石油化工'},
        {'symbol': '00883', 'name': '中海油', 'industry': '石油天然气'},
        
        # 电信通信
        {'symbol': '00941', 'name': '中国移动', 'industry': '电信服务'},
        {'symbol': '00762', 'name': '中国联通', 'industry': '电信服务'},
        {'symbol': '00728', 'name': '中国电信', 'industry': '电信服务'},
        
        # 汽车制造
        {'symbol': '01211', 'name': '比亚迪股份', 'industry': '汽车制造'},
        {'symbol': '02015', 'name': '理想汽车-W', 'industry': '新能源汽车'},
        {'symbol': '09866', 'name': '蔚来-SW', 'industry': '新能源汽车'},
        {'symbol': '09868', 'name': '小鹏汽车-W', 'industry': '新能源汽车'},
        {'symbol': '00175', 'name': '吉利汽车', 'industry': '汽车制造'},
        
        # 地产
        {'symbol': '00016', 'name': '新鸿基地产', 'industry': '房地产'},
        {'symbol': '01109', 'name': '华润置地', 'industry': '房地产'},
        {'symbol': '01997', 'name': '九龙仓置业', 'industry': '房地产'},
        
        # 公用事业
        {'symbol': '00003', 'name': '香港中华煤气', 'industry': '公用事业'},
        {'symbol': '00002', 'name': '中电控股', 'industry': '电力'},
        {'symbol': '00006', 'name': '电能实业', 'industry': '电力'},
        
        # 医药
        {'symbol': '01093', 'name': '石药集团', 'industry': '医药'},
        {'symbol': '00772', 'name': '阅文集团', 'industry': '数字娱乐'},
        
        # 消费零售
        {'symbol': '06098', 'name': '碧桂园服务', 'industry': '物业管理'},
        {'symbol': '01972', 'name': '太古地产', 'industry': '房地产'},
    ]
    
    formatted_stocks = []
    for stock_data in curated_hk_stocks:
        formatted_stock = {
            'symbol': stock_data['symbol'],
            'name': stock_data['name'],
            'short_name': stock_data['name'],
            'market': 'HK',
            'industry': stock_data['industry']
        }
        formatted_stocks.append(formatted_stock)
    
    print(f"✅ 创建精选港股列表: {len(formatted_stocks)}只")
    return formatted_stocks

async def main():
    """主导入流程"""
    print("🚀 开始完整股票数据导入")
    print("=" * 50)
    
    try:
        # 初始化优化数据服务
        service = get_optimized_data_service()
        
        # 导入A股数据
        print("\n📊 第一阶段: 导入A股数据")
        a_stocks = await import_a_stocks()
        if a_stocks:
            a_count = await service.bulk_import_stocks(a_stocks)
            print(f"✅ A股导入完成: {a_count}只")
        else:
            print("⚠️ A股数据导入失败")
        
        # 导入港股数据
        print("\n📊 第二阶段: 导入港股数据")
        hk_stocks = await import_hk_stocks()
        
        # 如果API获取失败，使用精选列表
        if not hk_stocks:
            hk_stocks = await create_curated_hk_list()
        
        if hk_stocks:
            hk_count = await service.bulk_import_stocks(hk_stocks)
            print(f"✅ 港股导入完成: {hk_count}只")
        else:
            print("⚠️ 港股数据导入失败")
        
        # 显示最终统计
        print("\n📈 第三阶段: 数据统计")
        stats = await service.get_stats()
        print("✅ 导入完成! 最终统计:")
        print(f"  📊 总股票数: {stats['total_stocks']}")
        print(f"  🔥 热门股票: {stats['hot_stocks_count']}")
        print("  📋 市场分布:")
        for market in stats['market_distribution']:
            print(f"    • {market['market']}: {market['count']}只")
        
        # 性能测试
        print("\n⚡ 第四阶段: 性能测试")
        test_queries = ["平安", "茅台", "腾讯", "银行", "000001"]
        
        for query in test_queries:
            import time
            start = time.time()
            results, total = await service.search_stocks(query, limit=5)
            duration = (time.time() - start) * 1000
            
            print(f"🔍 搜索'{query}': {len(results)}条结果, 用时{duration:.1f}ms")
            if results:
                for r in results[:3]:
                    print(f"    • {r['symbol']} - {r['name']} ({r['market']})")
        
        # 缓存统计
        cache_stats = service.get_cache_stats()
        print(f"\n📊 缓存统计:")
        for cache_type, stats in cache_stats.items():
            print(f"  {cache_type}: 命中率{stats['hit_rate']}%, 缓存项{stats['total_items']}个")
        
        print("\n🎉 全部导入和测试完成!")
        
    except Exception as e:
        print(f"\n❌ 导入过程出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())