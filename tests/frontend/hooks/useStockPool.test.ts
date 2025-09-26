import { renderHook, act } from '@testing-library/react';
import { vi, describe, test, expect, beforeEach } from 'vitest';
import { useStockPool } from '../../../frontend/src/hooks/useStockPool';
import * as api from '../../../frontend/src/services/api';

// Mock API
vi.mock('../../../frontend/src/services/api', () => ({
  stockPoolAPI: {
    getAll: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    delete: vi.fn()
  }
}));

const mockStockPools = [
  {
    id: 1,
    stock_code: '000001',
    stock_name: '平安银行',
    pool_type: 'holding',
    shares: 1000,
    avg_cost: 12.50,
    current_price: 13.20,
    market_value: 13200,
    tags: ['银行'],
    notes: '持仓股票',
    created_at: '2023-01-01T00:00:00Z',
    updated_at: '2023-01-01T00:00:00Z'
  },
  {
    id: 2,
    stock_code: '000002',
    stock_name: '万科A',
    pool_type: 'potential',
    shares: 0,
    avg_cost: 0,
    current_price: 22.50,
    market_value: 0,
    tags: ['房地产'],
    notes: '潜在股票',
    created_at: '2023-01-01T00:00:00Z',
    updated_at: '2023-01-01T00:00:00Z'
  }
];

describe('useStockPool', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test('initializes with empty state', () => {
    const { result } = renderHook(() => useStockPool());

    expect(result.current.stockPools).toEqual([]);
    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBe(null);
  });

  test('fetches stock pools successfully', async () => {
    (api.stockPoolAPI.getAll as any).mockResolvedValue({
      success: true,
      data: mockStockPools
    });

    const { result } = renderHook(() => useStockPool());

    await act(async () => {
      await result.current.refreshStockPools();
    });

    expect(result.current.stockPools).toEqual(mockStockPools);
    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBe(null);
  });

  test('handles fetch error', async () => {
    const errorMessage = 'Network error';
    (api.stockPoolAPI.getAll as any).mockRejectedValue(new Error(errorMessage));

    const { result } = renderHook(() => useStockPool());

    await act(async () => {
      await result.current.refreshStockPools();
    });

    expect(result.current.stockPools).toEqual([]);
    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBe(errorMessage);
  });

  test('shows loading state while fetching', async () => {
    let resolvePromise: (value: any) => void;
    const promise = new Promise(resolve => {
      resolvePromise = resolve;
    });
    (api.stockPoolAPI.getAll as any).mockReturnValue(promise);

    const { result } = renderHook(() => useStockPool());

    act(() => {
      result.current.refreshStockPools();
    });

    expect(result.current.loading).toBe(true);

    await act(async () => {
      resolvePromise!({
        success: true,
        data: mockStockPools
      });
    });

    expect(result.current.loading).toBe(false);
  });

  test('creates new stock pool', async () => {
    const newStock = {
      id: 3,
      stock_code: '600036',
      stock_name: '招商银行',
      pool_type: 'holding',
      shares: 500,
      avg_cost: 42.50,
      current_price: 45.20,
      market_value: 22600,
      tags: ['银行'],
      notes: '新增股票',
      created_at: '2023-01-02T00:00:00Z',
      updated_at: '2023-01-02T00:00:00Z'
    };

    (api.stockPoolAPI.create as any).mockResolvedValue({
      success: true,
      data: newStock
    });

    const { result } = renderHook(() => useStockPool());

    // 先设置初始数据
    await act(async () => {
      result.current.setStockPools(mockStockPools);
    });

    // 创建新股票
    await act(async () => {
      await result.current.createStockPool({
        stock_code: '600036',
        stock_name: '招商银行',
        pool_type: 'holding',
        shares: 500,
        avg_cost: 42.50,
        current_price: 45.20,
        tags: ['银行'],
        notes: '新增股票'
      });
    });

    expect(result.current.stockPools).toHaveLength(3);
    expect(result.current.stockPools[2]).toEqual(newStock);
    expect(result.current.error).toBe(null);
  });

  test('handles create error', async () => {
    const errorMessage = 'Create failed';
    (api.stockPoolAPI.create as any).mockRejectedValue(new Error(errorMessage));

    const { result } = renderHook(() => useStockPool());

    await act(async () => {
      await result.current.createStockPool({
        stock_code: '600036',
        stock_name: '招商银行',
        pool_type: 'holding'
      });
    });

    expect(result.current.error).toBe(errorMessage);
  });

  test('updates existing stock pool', async () => {
    const updatedStock = {
      ...mockStockPools[0],
      shares: 1200,
      notes: '已增仓'
    };

    (api.stockPoolAPI.update as any).mockResolvedValue({
      success: true,
      data: updatedStock
    });

    const { result } = renderHook(() => useStockPool());

    // 先设置初始数据
    await act(async () => {
      result.current.setStockPools(mockStockPools);
    });

    // 更新股票
    await act(async () => {
      await result.current.updateStockPool(1, {
        shares: 1200,
        notes: '已增仓'
      });
    });

    const updatedStockInState = result.current.stockPools.find(s => s.id === 1);
    expect(updatedStockInState?.shares).toBe(1200);
    expect(updatedStockInState?.notes).toBe('已增仓');
    expect(result.current.error).toBe(null);
  });

  test('handles update error', async () => {
    const errorMessage = 'Update failed';
    (api.stockPoolAPI.update as any).mockRejectedValue(new Error(errorMessage));

    const { result } = renderHook(() => useStockPool());

    // 先设置初始数据
    await act(async () => {
      result.current.setStockPools(mockStockPools);
    });

    await act(async () => {
      await result.current.updateStockPool(1, { shares: 1200 });
    });

    expect(result.current.error).toBe(errorMessage);
  });

  test('deletes stock pool', async () => {
    (api.stockPoolAPI.delete as any).mockResolvedValue({
      success: true
    });

    const { result } = renderHook(() => useStockPool());

    // 先设置初始数据
    await act(async () => {
      result.current.setStockPools(mockStockPools);
    });

    expect(result.current.stockPools).toHaveLength(2);

    // 删除股票
    await act(async () => {
      await result.current.deleteStockPool(1);
    });

    expect(result.current.stockPools).toHaveLength(1);
    expect(result.current.stockPools.find(s => s.id === 1)).toBeUndefined();
    expect(result.current.error).toBe(null);
  });

  test('handles delete error', async () => {
    const errorMessage = 'Delete failed';
    (api.stockPoolAPI.delete as any).mockRejectedValue(new Error(errorMessage));

    const { result } = renderHook(() => useStockPool());

    // 先设置初始数据
    await act(async () => {
      result.current.setStockPools(mockStockPools);
    });

    await act(async () => {
      await result.current.deleteStockPool(1);
    });

    expect(result.current.error).toBe(errorMessage);
    // 删除失败时不应该移除数据
    expect(result.current.stockPools).toHaveLength(2);
  });

  test('filters stock pools by type', async () => {
    const { result } = renderHook(() => useStockPool());

    // 设置初始数据
    await act(async () => {
      result.current.setStockPools(mockStockPools);
    });

    // 筛选持仓股票
    const holdingStocks = result.current.getStocksByType('holding');
    expect(holdingStocks).toHaveLength(1);
    expect(holdingStocks[0].stock_code).toBe('000001');

    // 筛选潜在股票
    const potentialStocks = result.current.getStocksByType('potential');
    expect(potentialStocks).toHaveLength(1);
    expect(potentialStocks[0].stock_code).toBe('000002');
  });

  test('searches stock pools', async () => {
    const { result } = renderHook(() => useStockPool());

    // 设置初始数据
    await act(async () => {
      result.current.setStockPools(mockStockPools);
    });

    // 按代码搜索
    let searchResults = result.current.searchStocks('000001');
    expect(searchResults).toHaveLength(1);
    expect(searchResults[0].stock_code).toBe('000001');

    // 按名称搜索
    searchResults = result.current.searchStocks('平安');
    expect(searchResults).toHaveLength(1);
    expect(searchResults[0].stock_name).toBe('平安银行');

    // 不区分大小写搜索
    searchResults = result.current.searchStocks('万科');
    expect(searchResults).toHaveLength(1);
    expect(searchResults[0].stock_name).toBe('万科A');

    // 无匹配结果
    searchResults = result.current.searchStocks('不存在');
    expect(searchResults).toHaveLength(0);
  });

  test('calculates total market value correctly', async () => {
    const { result } = renderHook(() => useStockPool());

    // 设置初始数据
    await act(async () => {
      result.current.setStockPools(mockStockPools);
    });

    const totalValue = result.current.getTotalMarketValue();
    expect(totalValue).toBe(13200); // 只计算 holding 类型的市值
  });

  test('clears error when operation succeeds', async () => {
    (api.stockPoolAPI.getAll as any)
      .mockRejectedValueOnce(new Error('Network error'))
      .mockResolvedValueOnce({
        success: true,
        data: mockStockPools
      });

    const { result } = renderHook(() => useStockPool());

    // 第一次调用失败
    await act(async () => {
      await result.current.refreshStockPools();
    });
    expect(result.current.error).toBe('Network error');

    // 第二次调用成功
    await act(async () => {
      await result.current.refreshStockPools();
    });
    expect(result.current.error).toBe(null);
    expect(result.current.stockPools).toEqual(mockStockPools);
  });
});