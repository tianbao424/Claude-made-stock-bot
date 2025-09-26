import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi, describe, test, expect, beforeEach } from 'vitest';
import ChatInterface from '../../../frontend/src/components/ChatInterface';

// Mock WebSocket
class MockWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  readyState = MockWebSocket.CONNECTING;
  onopen: ((event: Event) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;

  constructor(public url: string) {
    // 模拟异步连接
    setTimeout(() => {
      this.readyState = MockWebSocket.OPEN;
      if (this.onopen) {
        this.onopen(new Event('open'));
      }
    }, 10);
  }

  send(data: string) {
    // 模拟服务器响应
    setTimeout(() => {
      if (this.onmessage) {
        const response = {
          type: 'response',
          content: `模拟响应: ${JSON.parse(data).content}`,
          timestamp: new Date().toISOString()
        };
        this.onmessage(new MessageEvent('message', { 
          data: JSON.stringify(response) 
        }));
      }
    }, 100);
  }

  close() {
    this.readyState = MockWebSocket.CLOSED;
    if (this.onclose) {
      this.onclose(new CloseEvent('close'));
    }
  }
}

// 设置全局 WebSocket mock
(global as any).WebSocket = MockWebSocket;

describe('ChatInterface', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test('renders chat interface correctly', () => {
    render(<ChatInterface />);
    
    expect(screen.getByText('AI股票助手')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('输入您的股票相关问题...')).toBeInTheDocument();
    expect(screen.getByText('发送')).toBeInTheDocument();
  });

  test('shows connection status', async () => {
    render(<ChatInterface />);
    
    // 初始状态应该是连接中
    expect(screen.getByText('连接中...')).toBeInTheDocument();
    
    // 等待连接建立
    await waitFor(() => {
      expect(screen.getByText('已连接')).toBeInTheDocument();
    }, { timeout: 1000 });
  });

  test('sends message and receives response', async () => {
    render(<ChatInterface />);
    
    // 等待连接建立
    await waitFor(() => {
      expect(screen.getByText('已连接')).toBeInTheDocument();
    });
    
    const input = screen.getByPlaceholderText('输入您的股票相关问题...');
    const sendButton = screen.getByText('发送');
    
    // 输入消息
    fireEvent.change(input, { target: { value: '查询平安银行股价' } });
    fireEvent.click(sendButton);
    
    // 检查用户消息是否显示
    expect(screen.getByText('查询平安银行股价')).toBeInTheDocument();
    
    // 等待AI响应
    await waitFor(() => {
      expect(screen.getByText('模拟响应: 查询平安银行股价')).toBeInTheDocument();
    });
    
    // 输入框应该被清空
    expect(input).toHaveValue('');
  });

  test('handles enter key press', async () => {
    render(<ChatInterface />);
    
    await waitFor(() => {
      expect(screen.getByText('已连接')).toBeInTheDocument();
    });
    
    const input = screen.getByPlaceholderText('输入您的股票相关问题...');
    
    fireEvent.change(input, { target: { value: '测试消息' } });
    fireEvent.keyPress(input, { key: 'Enter', code: 'Enter', charCode: 13 });
    
    expect(screen.getByText('测试消息')).toBeInTheDocument();
  });

  test('disables send button when not connected', () => {
    render(<ChatInterface />);
    
    const sendButton = screen.getByText('发送');
    expect(sendButton).toBeDisabled();
  });

  test('disables send button when input is empty', async () => {
    render(<ChatInterface />);
    
    await waitFor(() => {
      expect(screen.getByText('已连接')).toBeInTheDocument();
    });
    
    const sendButton = screen.getByText('发送');
    expect(sendButton).toBeDisabled();
    
    const input = screen.getByPlaceholderText('输入您的股票相关问题...');
    fireEvent.change(input, { target: { value: 'test' } });
    
    expect(sendButton).not.toBeDisabled();
  });

  test('shows typing indicator when message is being sent', async () => {
    render(<ChatInterface />);
    
    await waitFor(() => {
      expect(screen.getByText('已连接')).toBeInTheDocument();
    });
    
    const input = screen.getByPlaceholderText('输入您的股票相关问题...');
    const sendButton = screen.getByText('发送');
    
    fireEvent.change(input, { target: { value: '查询股票' } });
    fireEvent.click(sendButton);
    
    // 短暂显示加载状态
    expect(screen.getByText('AI正在回复...')).toBeInTheDocument();
  });

  test('displays message timestamps', async () => {
    render(<ChatInterface />);
    
    await waitFor(() => {
      expect(screen.getByText('已连接')).toBeInTheDocument();
    });
    
    const input = screen.getByPlaceholderText('输入您的股票相关问题...');
    const sendButton = screen.getByText('发送');
    
    fireEvent.change(input, { target: { value: '测试时间戳' } });
    fireEvent.click(sendButton);
    
    // 检查是否有时间戳显示
    await waitFor(() => {
      const timeElements = screen.getAllByText(/\d{2}:\d{2}/);
      expect(timeElements.length).toBeGreaterThan(0);
    });
  });

  test('scrolls to bottom when new message arrives', async () => {
    const scrollIntoViewMock = vi.fn();
    Element.prototype.scrollIntoView = scrollIntoViewMock;
    
    render(<ChatInterface />);
    
    await waitFor(() => {
      expect(screen.getByText('已连接')).toBeInTheDocument();
    });
    
    const input = screen.getByPlaceholderText('输入您的股票相关问题...');
    const sendButton = screen.getByText('发送');
    
    fireEvent.change(input, { target: { value: '测试滚动' } });
    fireEvent.click(sendButton);
    
    await waitFor(() => {
      expect(scrollIntoViewMock).toHaveBeenCalled();
    });
  });

  test('handles connection error gracefully', async () => {
    // 修改 Mock WebSocket 以模拟连接错误
    const OriginalWebSocket = (global as any).WebSocket;
    
    class ErrorWebSocket extends MockWebSocket {
      constructor(url: string) {
        super(url);
        setTimeout(() => {
          if (this.onerror) {
            this.onerror(new Event('error'));
          }
        }, 10);
      }
    }
    
    (global as any).WebSocket = ErrorWebSocket;
    
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    
    render(<ChatInterface />);
    
    await waitFor(() => {
      expect(screen.getByText('连接失败')).toBeInTheDocument();
    });
    
    // 恢复原始 WebSocket
    (global as any).WebSocket = OriginalWebSocket;
    consoleSpy.mockRestore();
  });

  test('handles reconnection', async () => {
    render(<ChatInterface />);
    
    await waitFor(() => {
      expect(screen.getByText('已连接')).toBeInTheDocument();
    });
    
    // 模拟连接断开
    const websocket = (global as any).lastWebSocketInstance;
    if (websocket && websocket.onclose) {
      websocket.onclose(new CloseEvent('close'));
    }
    
    await waitFor(() => {
      expect(screen.getByText('连接中...')).toBeInTheDocument();
    });
    
    // 应该自动重连
    await waitFor(() => {
      expect(screen.getByText('已连接')).toBeInTheDocument();
    }, { timeout: 5000 });
  });

  test('displays welcome message on first load', () => {
    render(<ChatInterface />);
    
    expect(screen.getByText(/欢迎使用AI股票助手/)).toBeInTheDocument();
    expect(screen.getByText(/您可以询问股票价格、技术分析、投资建议等问题/)).toBeInTheDocument();
  });

  test('clears chat history', async () => {
    render(<ChatInterface />);
    
    await waitFor(() => {
      expect(screen.getByText('已连接')).toBeInTheDocument();
    });
    
    // 发送一条消息
    const input = screen.getByPlaceholderText('输入您的股票相关问题...');
    const sendButton = screen.getByText('发送');
    
    fireEvent.change(input, { target: { value: '测试消息' } });
    fireEvent.click(sendButton);
    
    expect(screen.getByText('测试消息')).toBeInTheDocument();
    
    // 点击清除历史按钮
    const clearButton = screen.getByText('清除历史');
    fireEvent.click(clearButton);
    
    // 消息应该被清除，只保留欢迎消息
    expect(screen.queryByText('测试消息')).not.toBeInTheDocument();
    expect(screen.getByText(/欢迎使用AI股票助手/)).toBeInTheDocument();
  });
});