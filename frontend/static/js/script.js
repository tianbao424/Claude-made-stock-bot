// AI股票聊天助手 - 前端脚本
class StockChatClient {
    constructor() {
        this.ws = null;
        this.isTyping = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 3000;
        
        this.init();
    }
    
    init() {
        this.connectWebSocket();
        this.setupEventListeners();
        this.updateStatus('connecting', '连接中...');
    }
    
    connectWebSocket() {
        try {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            this.ws = new WebSocket(`${protocol}//${window.location.host}/ws`);
            
            this.ws.onopen = (event) => {
                console.log('WebSocket连接已建立');
                this.updateStatus('connected', '已连接');
                this.reconnectAttempts = 0;
            };
            
            this.ws.onmessage = (event) => {
                this.handleMessage(event.data);
            };
            
            this.ws.onclose = (event) => {
                console.log('WebSocket连接已关闭');
                this.updateStatus('disconnected', '连接断开');
                this.handleReconnect();
            };
            
            this.ws.onerror = (error) => {
                console.error('WebSocket错误:', error);
                this.updateStatus('error', '连接错误');
            };
        } catch (error) {
            console.error('WebSocket连接失败:', error);
            this.updateStatus('error', '连接失败');
        }
    }
    
    handleMessage(data) {
        try {
            const message = JSON.parse(data);
            
            switch (message.type) {
                case 'response':
                    this.addMessage(message.content, 'bot');
                    this.setTyping(false);
                    break;
                    
                case 'typing':
                    this.setTyping(true);
                    break;
                    
                case 'error':
                    this.addMessage(`❌ 错误: ${message.content}`, 'bot');
                    this.setTyping(false);
                    break;
                    
                default:
                    console.warn('未知消息类型:', message.type);
            }
        } catch (error) {
            console.error('解析消息失败:', error);
        }
    }
    
    handleReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            this.updateStatus('connecting', `重连中... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
            
            setTimeout(() => {
                console.log(`尝试重连 ${this.reconnectAttempts}/${this.maxReconnectAttempts}`);
                this.connectWebSocket();
            }, this.reconnectDelay);
        } else {
            this.updateStatus('error', '连接失败');
            this.addMessage('❌ 无法连接到服务器，请刷新页面重试', 'bot');
        }
    }
    
    updateStatus(status, text) {
        const statusEl = document.getElementById('status');
        statusEl.className = `status ${status}`;
        statusEl.textContent = text;
    }
    
    setupEventListeners() {
        const messageInput = document.getElementById('messageInput');
        const sendButton = document.getElementById('sendButton');
        
        // 回车发送消息
        messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
        
        // 发送按钮点击
        sendButton.addEventListener('click', () => {
            this.sendMessage();
        });
        
        // 输入框焦点处理
        messageInput.addEventListener('focus', () => {
            messageInput.scrollIntoView({ behavior: 'smooth', block: 'center' });
        });
    }
    
    sendMessage() {
        const input = document.getElementById('messageInput');
        const message = input.value.trim();
        
        if (!message || !this.ws || this.ws.readyState !== WebSocket.OPEN || this.isTyping) {
            return;
        }
        
        // 显示用户消息
        this.addMessage(message, 'user');
        
        // 发送到服务器
        try {
            this.ws.send(JSON.stringify({
                type: 'query',
                content: message,
                timestamp: new Date().toISOString()
            }));
            
            // 清空输入框并显示打字状态
            input.value = '';
            this.setTyping(true);
            
        } catch (error) {
            console.error('发送消息失败:', error);
            this.addMessage('❌ 发送失败，请检查网络连接', 'bot');
        }
    }
    
    addMessage(content, sender) {
        const messages = document.getElementById('messages');
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}`;
        
        // 处理换行和格式化
        const formattedContent = content
            .replace(/\n/g, '<br>')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/`(.*?)`/g, '<code>$1</code>');
            
        messageDiv.innerHTML = formattedContent;
        messages.appendChild(messageDiv);
        
        // 滚动到底部
        this.scrollToBottom();
    }
    
    setTyping(typing) {
        const messages = document.getElementById('messages');
        const existingTyping = messages.querySelector('.typing');
        
        if (typing && !existingTyping) {
            const typingDiv = document.createElement('div');
            typingDiv.className = 'typing';
            typingDiv.textContent = '🤖 AI正在分析...';
            messages.appendChild(typingDiv);
        } else if (!typing && existingTyping) {
            existingTyping.remove();
        }
        
        this.isTyping = typing;
        document.getElementById('sendButton').disabled = typing;
        
        this.scrollToBottom();
    }
    
    scrollToBottom() {
        const messages = document.getElementById('messages');
        setTimeout(() => {
            messages.scrollTop = messages.scrollHeight;
        }, 100);
    }
}

// 全局函数保持向后兼容
let chatClient;

function sendMessage() {
    if (chatClient) {
        chatClient.sendMessage();
    }
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    chatClient = new StockChatClient();
    
    // 添加一些用户友好的提示
    const messageInput = document.getElementById('messageInput');
    const placeholder = messageInput.placeholder;
    
    messageInput.addEventListener('focus', () => {
        if (chatClient.ws && chatClient.ws.readyState !== WebSocket.OPEN) {
            messageInput.placeholder = '正在连接服务器...';
        }
    });
    
    messageInput.addEventListener('blur', () => {
        messageInput.placeholder = placeholder;
    });
});