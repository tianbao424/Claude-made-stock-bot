import { useState, useEffect, useRef } from 'react';
import { WebSocketMessage, ChatMessage } from '../types';

export const useWebSocket = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  const connect = () => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const wsUrl = `ws://localhost:8001/ws`;
    wsRef.current = new WebSocket(wsUrl);

    wsRef.current.onopen = () => {
      setIsConnected(true);
      console.log('WebSocket连接已建立');
    };

    wsRef.current.onmessage = (event) => {
      try {
        const message: WebSocketMessage = JSON.parse(event.data);
        
        if (message.type === 'response') {
          setMessages(prev => [...prev, {
            id: Date.now().toString(),
            type: 'assistant',
            content: message.content,
            timestamp: new Date().toISOString(),
          }]);
          setIsLoading(false);
        }
      } catch (error) {
        console.error('解析WebSocket消息失败:', error);
        setIsLoading(false);
      }
    };

    wsRef.current.onclose = () => {
      setIsConnected(false);
      setIsLoading(false);
      console.log('WebSocket连接已关闭');
    };

    wsRef.current.onerror = (error) => {
      console.error('WebSocket错误:', error);
      setIsLoading(false);
    };
  };

  const sendMessage = (content: string) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      console.error('WebSocket未连接');
      return;
    }

    // 添加用户消息
    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      type: 'user',
      content,
      timestamp: new Date().toISOString(),
    };
    
    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);

    // 发送消息到服务器
    const wsMessage: WebSocketMessage = {
      type: 'query',
      content,
      timestamp: new Date().toISOString(),
    };

    wsRef.current.send(JSON.stringify(wsMessage));
  };

  const disconnect = () => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  };

  const clearMessages = () => {
    setMessages([]);
  };

  useEffect(() => {
    connect();
    
    return () => {
      disconnect();
    };
  }, []);

  return {
    messages,
    isConnected,
    isLoading,
    sendMessage,
    clearMessages,
    connect,
    disconnect,
  };
};