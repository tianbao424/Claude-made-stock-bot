import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi, describe, test, expect, beforeEach } from 'vitest';
import StockPoolManager from '../../../frontend/src/components/StockPoolManager';
import * as api from '../../../frontend/src/services/api';

// Mock API calls
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
    tags: ['银行', '金融'],
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

describe('StockPoolManager', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (api.stockPoolAPI.getAll as any).mockResolvedValue({
      success: true,
      data: mockStockPools
    });
  });

  test('renders stock pool manager correctly', async () => {
    render(<StockPoolManager />);
    
    expect(screen.getByText('股票池管理')).toBeInTheDocument();
    
    // 等待数据加载
    await waitFor(() => {
      expect(screen.getByText('平安银行')).toBeInTheDocument();
      expect(screen.getByText('万科A')).toBeInTheDocument();
    });
  });

  test('displays stock pools in correct format', async () => {
    render(<StockPoolManager />);
    
    await waitFor(() => {
      // 检查持仓股票
      expect(screen.getByText('000001')).toBeInTheDocument();
      expect(screen.getByText('平安银行')).toBeInTheDocument();
      expect(screen.getByText('1000')).toBeInTheDocument(); // shares
      expect(screen.getByText('¥12.50')).toBeInTheDocument(); // avg_cost
      expect(screen.getByText('¥13.20')).toBeInTheDocument(); // current_price
      
      // 检查潜在股票
      expect(screen.getByText('000002')).toBeInTheDocument();
      expect(screen.getByText('万科A')).toBeInTheDocument();
      expect(screen.getByText('¥22.50')).toBeInTheDocument();
    });
  });

  test('filters stock pools by type', async () => {
    render(<StockPoolManager />);
    
    await waitFor(() => {
      expect(screen.getByText('平安银行')).toBeInTheDocument();
      expect(screen.getByText('万科A')).toBeInTheDocument();
    });
    
    // 切换到持仓标签
    fireEvent.click(screen.getByText('持仓'));
    
    expect(screen.getByText('平安银行')).toBeInTheDocument();
    expect(screen.queryByText('万科A')).not.toBeInTheDocument();
    
    // 切换到潜在标签
    fireEvent.click(screen.getByText('潜在'));
    
    expect(screen.queryByText('平安银行')).not.toBeInTheDocument();
    expect(screen.getByText('万科A')).toBeInTheDocument();
  });

  test('opens add stock form when clicking add button', async () => {
    render(<StockPoolManager />);
    
    const addButton = screen.getByText('添加股票');
    fireEvent.click(addButton);
    
    // 应该显示股票表单
    await waitFor(() => {
      expect(screen.getByText('添加股票到池中')).toBeInTheDocument();
    });
  });

  test('creates new stock pool successfully', async () => {
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
      notes: '新增持仓',
      created_at: '2023-01-02T00:00:00Z',
      updated_at: '2023-01-02T00:00:00Z'
    };

    (api.stockPoolAPI.create as any).mockResolvedValue({
      success: true,
      data: newStock
    });

    render(<StockPoolManager />);
    
    // 点击添加按钮
    fireEvent.click(screen.getByText('添加股票'));
    
    await waitFor(() => {
      expect(screen.getByText('添加股票到池中')).toBeInTheDocument();
    });
    
    // 填写表单
    fireEvent.change(screen.getByLabelText('股票代码'), {
      target: { value: '600036' }
    });
    fireEvent.change(screen.getByLabelText('股票名称'), {
      target: { value: '招商银行' }
    });
    fireEvent.change(screen.getByLabelText('持股数量'), {
      target: { value: '500' }
    });
    fireEvent.change(screen.getByLabelText('平均成本'), {
      target: { value: '42.50' }
    });
    
    // 提交表单
    fireEvent.click(screen.getByText('确认添加'));
    
    await waitFor(() => {
      expect(api.stockPoolAPI.create).toHaveBeenCalledWith({
        stock_code: '600036',
        stock_name: '招商银行',
        pool_type: 'holding',
        shares: 500,
        avg_cost: 42.50,
        current_price: 0,
        tags: [],
        notes: ''
      });
    });
  });

  test('updates existing stock pool', async () => {
    const updatedStock = { ...mockStockPools[0], shares: 1200, notes: '已增仓' };
    (api.stockPoolAPI.update as any).mockResolvedValue({
      success: true,
      data: updatedStock
    });

    render(<StockPoolManager />);
    
    await waitFor(() => {
      expect(screen.getByText('平安银行')).toBeInTheDocument();
    });
    
    // 点击编辑按钮
    const editButtons = screen.getAllByText('编辑');
    fireEvent.click(editButtons[0]);
    
    await waitFor(() => {
      expect(screen.getByText('编辑股票信息')).toBeInTheDocument();
    });
    
    // 修改持股数量
    const sharesInput = screen.getByDisplayValue('1000');
    fireEvent.change(sharesInput, { target: { value: '1200' } });
    
    // 提交更新
    fireEvent.click(screen.getByText('确认更新'));
    
    await waitFor(() => {
      expect(api.stockPoolAPI.update).toHaveBeenCalledWith(1, expect.objectContaining({
        shares: 1200
      }));
    });
  });

  test('deletes stock pool with confirmation', async () => {
    (api.stockPoolAPI.delete as any).mockResolvedValue({
      success: true
    });

    // Mock window.confirm
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true);

    render(<StockPoolManager />);
    
    await waitFor(() => {
      expect(screen.getByText('平安银行')).toBeInTheDocument();
    });
    
    // 点击删除按钮
    const deleteButtons = screen.getAllByText('删除');
    fireEvent.click(deleteButtons[0]);
    
    expect(confirmSpy).toHaveBeenCalledWith('确定要删除股票"平安银行"吗？');
    
    await waitFor(() => {
      expect(api.stockPoolAPI.delete).toHaveBeenCalledWith(1);
    });

    confirmSpy.mockRestore();
  });

  test('handles API error gracefully', async () => {
    (api.stockPoolAPI.getAll as any).mockRejectedValue(new Error('Network error'));
    
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    
    render(<StockPoolManager />);
    
    await waitFor(() => {
      expect(consoleSpy).toHaveBeenCalledWith('获取股票池失败:', expect.any(Error));
    });
    
    // 应该显示错误状态
    expect(screen.getByText('获取数据失败')).toBeInTheDocument();
    
    consoleSpy.mockRestore();
  });

  test('calculates profit/loss correctly', async () => {
    render(<StockPoolManager />);
    
    await waitFor(() => {
      // 平安银行: (13.20 - 12.50) / 12.50 * 100 = 5.6%
      expect(screen.getByText('+5.60%')).toBeInTheDocument();
      expect(screen.getByText('+¥700.00')).toBeInTheDocument(); // (13.20 - 12.50) * 1000
    });
  });

  test('searches stocks correctly', async () => {
    render(<StockPoolManager />);
    
    await waitFor(() => {
      expect(screen.getByText('平安银行')).toBeInTheDocument();
      expect(screen.getByText('万科A')).toBeInTheDocument();
    });
    
    // 输入搜索关键词
    const searchInput = screen.getByPlaceholderText('搜索股票代码或名称...');
    fireEvent.change(searchInput, { target: { value: '平安' } });
    
    await waitFor(() => {
      expect(screen.getByText('平安银行')).toBeInTheDocument();
      expect(screen.queryByText('万科A')).not.toBeInTheDocument();
    });
  });

  test('handles empty stock pool list', async () => {
    (api.stockPoolAPI.getAll as any).mockResolvedValue({
      success: true,
      data: []
    });

    render(<StockPoolManager />);
    
    await waitFor(() => {
      expect(screen.getByText('暂无股票数据')).toBeInTheDocument();
      expect(screen.getByText('点击"添加股票"按钮开始添加股票到池中')).toBeInTheDocument();
    });
  });
});