#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Web搜索助手前端生成器
生成HTML文件供浏览器使用
"""

import os
import sys
from pathlib import Path

def generate_html_content():
    """生成HTML内容"""
    return '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Web搜索助手</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(180deg, #f7f7f8 0%, #ffffff 100%);
            height: 100vh;
            display: flex;
        }

        /* 侧边栏 */
        .sidebar {
            width: 260px;
            background: #202123;
            color: #fff;
            display: flex;
            flex-direction: column;
            transition: margin-left 0.3s;
        }

        .sidebar-header {
            padding: 20px;
            border-bottom: 1px solid #353740;
        }

        .new-chat-btn {
            width: 100%;
            padding: 12px;
            background: transparent;
            border: 1px solid #565869;
            color: #fff;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            transition: background 0.2s;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
        }

        .new-chat-btn:hover {
            background: #353740;
        }

        .session-list {
            flex: 1;
            overflow-y: auto;
            padding: 10px;
        }

        .session-item {
            padding: 12px 16px;
            margin: 4px 0;
            background: transparent;
            border-radius: 6px;
            cursor: pointer;
            transition: background 0.2s;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 14px;
        }

        .session-item:hover {
            background: #353740;
        }

        .session-item.active {
            background: #353740;
        }

        .session-delete {
            opacity: 0;
            color: #999;
            cursor: pointer;
            padding: 4px;
        }

        .session-item:hover .session-delete {
            opacity: 1;
        }

        /* 设置面板 */
        .settings-panel {
            padding: 20px;
            border-top: 1px solid #353740;
        }

        .setting-group {
            margin-bottom: 15px;
        }

        .setting-label {
            font-size: 12px;
            color: #999;
            margin-bottom: 8px;
            display: block;
        }

        .setting-control {
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .toggle-switch {
            position: relative;
            width: 42px;
            height: 24px;
            background: #565869;
            border-radius: 12px;
            cursor: pointer;
            transition: background 0.3s;
        }

        .toggle-switch.active {
            background: #10a37f;
        }

        .toggle-switch::after {
            content: '';
            position: absolute;
            top: 3px;
            left: 3px;
            width: 18px;
            height: 18px;
            background: #fff;
            border-radius: 50%;
            transition: transform 0.3s;
        }

        .toggle-switch.active::after {
            transform: translateX(18px);
        }

        .select-control {
            width: 100%;
            padding: 8px;
            background: #40414f;
            border: 1px solid #565869;
            color: #fff;
            border-radius: 4px;
            font-size: 14px;
            cursor: pointer;
        }

        .number-input {
            width: 60px;
            padding: 8px;
            background: #40414f;
            border: 1px solid #565869;
            color: #fff;
            border-radius: 4px;
            font-size: 14px;
            text-align: center;
        }

        /* 主聊天区域 */
        .main-content {
            flex: 1;
            display: flex;
            flex-direction: column;
        }

        .chat-header {
            padding: 20px;
            background: #fff;
            border-bottom: 1px solid #e5e5e7;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .header-title {
            font-size: 18px;
            font-weight: 600;
            color: #202123;
        }

        .header-info {
            display: flex;
            gap: 15px;
            font-size: 12px;
            color: #999;
        }

        .status-indicator {
            display: flex;
            align-items: center;
            gap: 5px;
        }

        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #10a37f;
        }

        .chat-messages {
            flex: 1;
            overflow-y: auto;
            padding: 20px 0;
        }

        .message {
            padding: 20px;
            display: flex;
            gap: 20px;
            max-width: 900px;
            margin: 0 auto;
            width: 100%;
            position: relative;

        }
        

        .message.user {
            background: #fff;
        }

        .message.assistant {
            background: #f7f7f8;
        }

        .message-avatar {
            width: 36px;
            height: 36px;
            border-radius: 6px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            color: #fff;
            flex-shrink: 0;
        }

        .message.user .message-avatar {
            background: #5436da;
        }

        .message.assistant .message-avatar {
            background: #10a37f;
        }

        .message-content {
            flex: 1;
            color: #202123;
            line-height: 1.6;
            font-size: 15px;
        }

        .message-content pre {
            background: #f6f6f6;
            padding: 12px;
            border-radius: 6px;
            overflow-x: auto;
            margin: 10px 0;
        }

        .message-content code {
            background: #f6f6f6;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 14px;
        }

        .tool-call-indicator {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 6px 12px;
            background: #e8f4fd;
            border: 1px solid #bee3f8;
            border-radius: 6px;
            color: #2563eb;
            font-size: 13px;
            margin: 10px 0;
        }

        .message-actions {
            position: absolute;
            top: 10px;
            right: 10px;
            display: none;
            gap: 8px;
        }

        .message:hover .message-actions {
            display: flex;
        }

        .action-btn {
            padding: 4px 8px;
            background: rgba(0, 0, 0, 0.1);
            border: none;
            border-radius: 4px;
            color: #666;
            cursor: pointer;
            font-size: 12px;
            transition: background 0.2s;
        }

        .action-btn:hover {
            background: rgba(0, 0, 0, 0.2);
        }

        .typing-indicator {
            display: flex;
            gap: 4px;
            padding: 20px;
            max-width: 900px;
            margin: 0 auto;
            width: 100%;
        }

        .typing-dot {
            width: 8px;
            height: 8px;
            background: #999;
            border-radius: 50%;
            animation: typing 1.4s infinite;
        }

        .typing-dot:nth-child(2) {
            animation-delay: 0.2s;
        }

        .typing-dot:nth-child(3) {
            animation-delay: 0.4s;
        }

        @keyframes typing {
            0%, 60%, 100% {
                opacity: 0.3;
            }
            30% {
                opacity: 1;
            }
        }

        /* 输入区域 */
        .chat-input-container {
            padding: 20px;
            background: #fff;
            border-top: 1px solid #e5e5e7;
        }

        .chat-input-wrapper {
            max-width: 900px;
            margin: 0 auto;
            position: relative;
        }

        .chat-input {
            width: 100%;
            padding: 12px 50px 12px 16px;
            border: 1px solid #e5e5e7;
            border-radius: 8px;
            font-size: 15px;
            resize: none;
            outline: none;
            transition: border-color 0.2s;
            min-height: 52px;
            max-height: 200px;
        }

        .chat-input:focus {
            border-color: #10a37f;
        }

        .send-button {
            position: absolute;
            right: 8px;
            bottom: 8px;
            width: 36px;
            height: 36px;
            background: #10a37f;
            border: none;
            border-radius: 6px;
            color: #fff;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: background 0.2s;
        }

        .send-button:hover {
            background: #0e8c6a;
        }

        .send-button:disabled {
            background: #d1d5db;
            cursor: not-allowed;
        }

        /* 模态框 */
        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.5);
            z-index: 1000;
            align-items: center;
            justify-content: center;
        }

        .modal.active {
            display: flex;
        }

        .modal-content {
            background: #fff;
            padding: 32px;
            border-radius: 12px;
            width: 90%;
            max-width: 480px;
        }

        .modal-title {
            font-size: 20px;
            font-weight: 600;
            margin-bottom: 20px;
            color: #202123;
        }

        .modal-input {
            width: 100%;
            padding: 12px;
            border: 1px solid #e5e5e7;
            border-radius: 6px;
            font-size: 14px;
            margin-bottom: 20px;
        }

        .modal-buttons {
            display: flex;
            gap: 12px;
            justify-content: flex-end;
        }

        .modal-button {
            padding: 10px 20px;
            border: none;
            border-radius: 6px;
            font-size: 14px;
            cursor: pointer;
            transition: opacity 0.2s;
        }

        .modal-button.primary {
            background: #10a37f;
            color: #fff;
        }

        .modal-button.secondary {
            background: #f0f0f0;
            color: #202123;
        }

        .modal-button:hover {
            opacity: 0.9;
        }

        /* 通知提示 */
        .toast {
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 12px 20px;
            border-radius: 6px;
            color: #fff;
            font-size: 14px;
            z-index: 1001;
            animation: slideIn 0.3s ease;
        }

        .toast-success {
            background: #10a37f;
        }

        .toast-error {
            background: #dc2626;
        }

        .toast-warning {
            background: #f59e0b;
        }

        @keyframes slideIn {
            from {
                transform: translateX(100%);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }

        /* 加载状态 */
        .loading-state {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 20px;
            max-width: 900px;
            margin: 0 auto;
            width: 100%;
            color: #666;
            font-size: 14px;
        }

        .loading-spinner {
            width: 16px;
            height: 16px;
            border: 2px solid #f3f3f3;
            border-top: 2px solid #10a37f;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        /* 移动端响应式 */
        @media (max-width: 768px) {
            .sidebar {
                position: fixed;
                left: -260px;
                height: 100%;
                z-index: 100;
                transform: translateX(-100%);
                transition: transform 0.3s ease;
            }

            .sidebar.mobile-open {
                transform: translateX(0);
            }

            .mobile-menu-btn {
                display: block;
            }

            .chat-input {
                font-size: 16px;
            }

            .message {
                padding: 15px;
                margin: 0 10px;
            }

            .message-actions {
                position: static;
                display: flex;
                margin-top: 10px;
            }
        }

        .mobile-menu-btn {
            display: none;
            background: none;
            border: none;
            color: #202123;
            font-size: 24px;
            cursor: pointer;
        }

        /* 主题切换 */
        .theme-toggle {
            position: fixed;
            bottom: 20px;
            right: 20px;
            width: 50px;
            height: 50px;
            border-radius: 50%;
            background: #10a37f;
            border: none;
            color: #fff;
            cursor: pointer;
            font-size: 20px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            transition: transform 0.2s;
        }

        .theme-toggle:hover {
            transform: scale(1.1);
        }
    </style>
</head>
<body>
    <!-- 侧边栏 -->
    <div class="sidebar" id="sidebar">
        <div class="sidebar-header">
            <button class="new-chat-btn" onclick="app.createNewSession()">
                <span>➕</span>
                <span>新对话</span>
            </button>
        </div>
        
        <div class="session-list" id="sessionList">
            <!-- 会话列表动态生成 -->
        </div>
        
        <div class="settings-panel">
            <div class="setting-group">
                <label class="setting-label">工具模式</label>
                <select class="select-control" id="toolMode" onchange="app.updateToolMode()">
                    <option value="auto">自动决定</option>
                    <option value="always">始终使用</option>
                    <option value="never">从不使用</option>
                </select>
            </div>
            
            <div class="setting-group">
                <label class="setting-label">流式输出</label>
                <div class="setting-control">
                    <div class="toggle-switch active" id="streamToggle" onclick="app.toggleStream()"></div>
                    <span style="font-size: 12px; color: #999;">实时显示</span>
                </div>
            </div>
            
            <div class="setting-group">
                <label class="setting-label">最大搜索次数</label>
                <div class="setting-control">
                    <input type="number" class="number-input" id="maxToolCalls" value="3" min="1" max="10" onchange="app.updateMaxToolCalls()">
                    <span style="font-size: 12px; color: #999;">次</span>
                </div>
            </div>
            
            <div class="setting-group">
                <label class="setting-label">温度 (创造性)</label>
                <div class="setting-control">
                    <input type="range" id="temperature" min="0" max="20" value="7" style="flex: 1;" onchange="app.updateTemperature()">
                    <span id="tempValue" style="font-size: 12px; color: #999; width: 30px;">0.7</span>
                </div>
            </div>
        </div>
    </div>
    
    <!-- 主聊天区域 -->
    <div class="main-content">
        <div class="chat-header">
            <button class="mobile-menu-btn" onclick="app.toggleSidebar()">☰</button>
            <div class="header-title">Web搜索助手</div>
            <div class="header-info">
                <div class="status-indicator">
                    <span class="status-dot"></span>
                    <span id="connectionStatus">已连接</span>
                </div>
                <span id="messageCount">消息: 0</span>
                <span id="toolCallCount">搜索: 0</span>
            </div>
        </div>
        
        <div class="chat-messages" id="chatMessages">
            <div class="message assistant">
                <div class="message-avatar">AI</div>
                <div class="message-content">
                    你好！我是Web搜索助手，可以帮你搜索最新的互联网信息。有什么可以帮助你的吗？
                </div>
            </div>
        </div>
        
        <div class="chat-input-container">
            <div class="chat-input-wrapper">
                <textarea 
                    class="chat-input" 
                    id="chatInput"
                    placeholder="输入消息... (Shift+Enter换行，Enter发送)"
                    onkeydown="app.handleInputKeydown(event)"
                ></textarea>
                <button class="send-button" id="sendButton" onclick="app.sendMessage()">
                    ➤
                </button>
            </div>
        </div>
    </div>
    
    <!-- API Key 模态框 -->
    <div class="modal active" id="apiKeyModal">
        <div class="modal-content">
            <div class="modal-title">请输入 DeepSeek API Key</div>
            <input 
                type="password" 
                class="modal-input" 
                id="apiKeyInput"
                placeholder="sk-..."
                onkeydown="if(event.key === 'Enter') app.saveApiKey()"
            >
            <div class="modal-buttons">
                <button class="modal-button primary" onclick="app.saveApiKey()">确认</button>
            </div>
        </div>
    </div>

    <!-- 主题切换按钮 -->
    <button class="theme-toggle" onclick="app.toggleTheme()" title="切换主题">🌙</button>
    
    <script>
        // 应用主类
        class ChatApp {
            constructor() {
                this.API_BASE_URL = 'http://localhost:8000';
                this.currentSessionId = null;
                this.apiKey = this.getSecureApiKey();
                this.ws = null;
                this.messageCount = 0;
                this.totalToolCalls = 0;
                this.reconnectAttempts = 0;
                this.maxReconnectAttempts = 5;
                this.isDarkTheme = false;
                
                this.init();
            }

            // 初始化应用
            async init() {
                if (this.apiKey) {
                    document.getElementById('apiKeyModal').classList.remove('active');
                    await this.initializeApp();
                }
            }

            // 安全存储API Key
            getSecureApiKey() {
                try {
                    const encrypted = sessionStorage.getItem('encryptedApiKey');
                    if (encrypted) {
                        return this.decrypt(encrypted);
                    }
                    return localStorage.getItem('apiKey') || '';
                } catch (error) {
                    console.error('获取API Key失败:', error);
                    return '';
                }
            }

            setSecureApiKey(apiKey) {
                try {
                    const encrypted = this.encrypt(apiKey);
                    sessionStorage.setItem('encryptedApiKey', encrypted);
                    localStorage.removeItem('apiKey'); // 清除旧存储
                } catch (error) {
                    console.error('存储API Key失败:', error);
                    localStorage.setItem('apiKey', apiKey); // 降级到localStorage
                }
            }

            // 简单的加密/解密（生产环境应使用更安全的方法）
            encrypt(text) {
                return btoa(encodeURIComponent(text));
            }

            decrypt(encrypted) {
                return decodeURIComponent(atob(encrypted));
            }

            // 保存API Key
            saveApiKey() {
                const input = document.getElementById('apiKeyInput');
                this.apiKey = input.value.trim();
                
                if (!this.apiKey) {
                    this.showToast('请输入有效的API Key', 'error');
                    return;
                }
                
                this.setSecureApiKey(this.apiKey);
                document.getElementById('apiKeyModal').classList.remove('active');
                this.initializeApp();
            }

            // 初始化应用
            async initializeApp() {
                try {
                    await this.loadSessions();
                    if (!this.currentSessionId) {
                        await this.createNewSession();
                    }
                } catch (error) {
                    this.showToast('初始化失败: ' + error.message, 'error');
                }
            }

            // 创建新会话
            async createNewSession() {
                try {
                    const response = await this.apiRequest('/api/sessions/create', {
                        method: 'POST',
                        body: {
                            config: {
                                api_key: this.apiKey,
                                tool_mode: document.getElementById('toolMode').value,
                                max_tool_calls: parseInt(document.getElementById('maxToolCalls').value),
                                temperature: parseFloat(document.getElementById('temperature').value) / 10,
                                stream: document.getElementById('streamToggle').classList.contains('active')
                            }
                        }
                    });
                    
                    this.currentSessionId = response.session_id;
                    
                    // 重置界面
                    this.messageCount = 0;
                    this.totalToolCalls = 0;
                    this.updateStats();
                    this.clearMessages();
                    this.addSystemMessage();
                    
                    // 刷新会话列表
                    await this.loadSessions();
                    
                    // 连接WebSocket
                    this.connectWebSocket();
                    
                    this.showToast('新会话创建成功', 'success');
                    
                } catch (error) {
                    this.showToast('创建会话失败: ' + error.message, 'error');
                }
            }

            // 加载会话列表
            async loadSessions() {
                try {
                    const sessions = await this.apiRequest('/api/sessions');
                    
                    const sessionList = document.getElementById('sessionList');
                    sessionList.innerHTML = '';
                    
                    sessions.forEach(session => {
                        const item = document.createElement('div');
                        item.className = `session-item ${session.session_id === this.currentSessionId ? 'active' : ''}`;
                        item.innerHTML = `
                            <span onclick="app.switchSession('${session.session_id}')">会话 ${session.session_id.slice(0, 8)}</span>
                            <span class="session-delete" onclick="app.deleteSession('${session.session_id}')">✕</span>
                        `;
                        sessionList.appendChild(item);
                    });
                } catch (error) {
                    console.error('加载会话列表失败:', error);
                }
            }

            // 切换会话
            async switchSession(sessionId) {
                this.currentSessionId = sessionId;
                await this.loadSessions();
                await this.loadHistory();
                this.connectWebSocket();
                this.showToast('已切换到新会话', 'success');
            }

            // 删除会话
            async deleteSession(sessionId) {
                if (sessionId === this.currentSessionId) {
                    this.showToast('不能删除当前会话', 'warning');
                    return;
                }
                
                try {
                    await this.apiRequest(`/api/sessions/${sessionId}`, { method: 'DELETE' });
                    await this.loadSessions();
                    this.showToast('会话已删除', 'success');
                } catch (error) {
                    this.showToast('删除失败: ' + error.message, 'error');
                }
            }

            // 连接WebSocket
            connectWebSocket() {
                if (this.ws) {
                    this.ws.close();
                }
                
                this.ws = new WebSocket(`ws://localhost:8000/api/chat/stream`);
                
                this.ws.onopen = () => {
                    this.ws.send(JSON.stringify({
                        type: 'init',
                        session_id: this.currentSessionId
                    }));
                    this.updateConnectionStatus(true);
                };
                
                this.ws.onmessage = (event) => {
                    const data = JSON.parse(event.data);
                    this.handleWebSocketMessage(data);
                };
                
                this.ws.onclose = () => {
                    this.updateConnectionStatus(false);
                    this.handleReconnect();
                };
                
                this.ws.onerror = (error) => {
                    console.error('WebSocket错误:', error);
                    this.updateConnectionStatus(false);
                };
            }

            // 处理重连
            handleReconnect() {
                if (this.reconnectAttempts < this.maxReconnectAttempts) {
                    setTimeout(() => {
                        this.reconnectAttempts++;
                        this.showToast(`连接断开，正在重连... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`, 'warning');
                        this.connectWebSocket();
                    }, 1000 * Math.pow(2, this.reconnectAttempts));
                } else {
                    this.showToast('连接失败，请刷新页面重试', 'error');
                }
            }

            // 处理WebSocket消息
            handleWebSocketMessage(data) {
                switch (data.type) {
                    case 'init_success':
                        console.log('WebSocket连接成功');
                        this.reconnectAttempts = 0;
                        break;
                    case 'start':
                        this.showLoadingState('thinking');
                        break;
                    case 'complete':
                        this.hideLoadingState();
                        this.addAssistantMessage(data.response);
                        if (data.tool_calls > 0) {
                            this.totalToolCalls += data.tool_calls;
                            this.updateStats();
                        }
                        break;
                    case 'error':
                        this.hideLoadingState();
                        this.showToast('错误: ' + data.message, 'error');
                        break;
                }
            }

            // 发送消息
            async sendMessage() {
                const input = document.getElementById('chatInput');
                const message = input.value.trim();
                
                if (!message) return;
                
                // 清空输入框
                input.value = '';
                
                // 添加用户消息
                this.addUserMessage(message);
                this.messageCount++;
                this.updateStats();
                
                // 禁用发送按钮
                document.getElementById('sendButton').disabled = true;
                
                const useStream = document.getElementById('streamToggle').classList.contains('active');
                
                if (useStream && this.ws && this.ws.readyState === WebSocket.OPEN) {
                    // 使用WebSocket流式传输
                    this.ws.send(JSON.stringify({
                        type: 'message',
                        message: message
                    }));
                } else {
                    // 使用HTTP请求
                    try {
                        this.showLoadingState('thinking');
                        
                        const data = await this.apiRequest('/api/chat', {
                            method: 'POST',
                            body: {
                                session_id: this.currentSessionId,
                                message: message,
                                stream: false
                            }
                        });
                        
                        this.hideLoadingState();
                        
                        if (data.success) {
                            this.addAssistantMessage(data.response);
                            if (data.tool_calls > 0) {
                                this.totalToolCalls += data.tool_calls;
                                this.updateStats();
                            }
                        } else {
                            this.showToast('发送失败: ' + data.error, 'error');
                        }
                    } catch (error) {
                        this.hideLoadingState();
                        this.showToast('发送失败: ' + error.message, 'error');
                    }
                }
                
                // 重新启用发送按钮
                document.getElementById('sendButton').disabled = false;
            }

            // 添加消息到界面
            addUserMessage(content) {
                const messagesDiv = document.getElementById('chatMessages');
                const messageDiv = document.createElement('div');
                messageDiv.className = 'message user';
                messageDiv.innerHTML = `
                    <div class="message-avatar">你</div>
                    <div class="message-content">${this.escapeHtml(content)}</div>
                    <div class="message-actions">
                        <button class="action-btn" onclick="app.copyMessage(this)">复制</button>
                        <button class="action-btn" onclick="app.editMessage(this)">编辑</button>
                    </div>
                `;
                messagesDiv.appendChild(messageDiv);
                messagesDiv.scrollTop = messagesDiv.scrollHeight;
            }

            addAssistantMessage(content) {
                const messagesDiv = document.getElementById('chatMessages');
                const messageDiv = document.createElement('div');
                messageDiv.className = 'message assistant';
                messageDiv.innerHTML = `
                    <div class="message-avatar">AI</div>
                    <div class="message-content">${this.formatMessage(content)}</div>
                    <div class="message-actions">
                        <button class="action-btn" onclick="app.copyMessage(this)">复制</button>
                    </div>
                `;
                messagesDiv.appendChild(messageDiv);
                messagesDiv.scrollTop = messagesDiv.scrollHeight;
            }

            addSystemMessage() {
                const messagesDiv = document.getElementById('chatMessages');
                messagesDiv.innerHTML = `
                    <div class="message assistant">
                        <div class="message-avatar">AI</div>
                        <div class="message-content">
                            你好！我是Web搜索助手，可以帮你搜索最新的互联网信息。有什么可以帮助你的吗？
                        </div>
                    </div>
                `;
            }

            // 显示/隐藏加载状态
            showLoadingState(type) {
                this.hideLoadingState();
                const messagesDiv = document.getElementById('chatMessages');
                const indicator = document.createElement('div');
                indicator.className = 'loading-state';
                indicator.id = 'loadingIndicator';
                
                let text = '';
                switch(type) {
                    case 'searching':
                        text = '🔍 正在搜索...';
                        break;
                    case 'thinking':
                        text = '🤔 正在思考...';
                        break;
                    case 'generating':
                        text = '✍️ 正在生成回答...';
                        break;
                    default:
                        text = '⏳ 处理中...';
                }
                
                indicator.innerHTML = `
                    <div class="loading-spinner"></div>
                    <span>${text}</span>
                `;
                messagesDiv.appendChild(indicator);
                messagesDiv.scrollTop = messagesDiv.scrollHeight;
            }

            hideLoadingState() {
                const indicator = document.getElementById('loadingIndicator');
                if (indicator) {
                    indicator.remove();
                }
            }

            // 清空消息
            clearMessages() {
                document.getElementById('chatMessages').innerHTML = '';
            }

            // 加载历史记录
            async loadHistory() {
                try {
                    const data = await this.apiRequest(`/api/sessions/${this.currentSessionId}/history`);
                    
                    this.clearMessages();
                    
                    data.history.forEach(msg => {
                        if (msg.role === 'user') {
                            this.addUserMessage(msg.content);
                        } else if (msg.role === 'assistant' && msg.content) {
                            this.addAssistantMessage(msg.content);
                        }
                    });
                    
                    this.messageCount = data.total_messages;
                    this.updateStats();
                    
                } catch (error) {
                    console.error('加载历史记录失败:', error);
                }
            }

            // 更新设置
            async updateToolMode() {
                const mode = document.getElementById('toolMode').value;
                await this.updateSessionConfig({ tool_mode: mode });
            }

            async toggleStream() {
                const toggle = document.getElementById('streamToggle');
                toggle.classList.toggle('active');
                const stream = toggle.classList.contains('active');
                await this.updateSessionConfig({ stream: stream });
            }

            async updateMaxToolCalls() {
                const maxCalls = parseInt(document.getElementById('maxToolCalls').value);
                await this.updateSessionConfig({ max_tool_calls: maxCalls });
            }

            async updateTemperature() {
                const temp = parseFloat(document.getElementById('temperature').value) / 10;
                document.getElementById('tempValue').textContent = temp.toFixed(1);
                await this.updateSessionConfig({ temperature: temp });
            }

            async updateSessionConfig(updates) {
                if (!this.currentSessionId) return;
                
                try {
                    await this.apiRequest('/api/sessions/update', {
                        method: 'PATCH',
                        body: {
                            session_id: this.currentSessionId,
                            ...updates
                        }
                    });
                } catch (error) {
                    console.error('更新配置失败:', error);
                    this.showToast('配置更新失败', 'error');
                }
            }

            // 更新统计信息
            updateStats() {
                document.getElementById('messageCount').textContent = `消息: ${this.messageCount}`;
                document.getElementById('toolCallCount').textContent = `搜索: ${this.totalToolCalls}`;
            }

            // 更新连接状态
            updateConnectionStatus(connected) {
                const status = document.getElementById('connectionStatus');
                const dot = document.querySelector('.status-dot');
                
                if (connected) {
                    status.textContent = '已连接';
                    dot.style.background = '#10a37f';
                } else {
                    status.textContent = '未连接';
                    dot.style.background = '#dc2626';
                }
            }

            // 处理输入框快捷键
            handleInputKeydown(event) {
                if (event.key === 'Enter' && !event.shiftKey) {
                    event.preventDefault();
                    this.sendMessage();
                }
            }

            // 切换侧边栏（移动端）
            toggleSidebar() {
                document.getElementById('sidebar').classList.toggle('mobile-open');
            }

            // 切换主题
            toggleTheme() {
                this.isDarkTheme = !this.isDarkTheme;
                document.body.classList.toggle('dark-theme', this.isDarkTheme);
                const themeBtn = document.querySelector('.theme-toggle');
                themeBtn.textContent = this.isDarkTheme ? '☀️' : '🌙';
                themeBtn.title = this.isDarkTheme ? '切换到浅色主题' : '切换到深色主题';
            }

            // 消息操作
            copyMessage(button) {
                const messageContent = button.closest('.message').querySelector('.message-content');
                const text = messageContent.textContent || messageContent.innerText;
                
                navigator.clipboard.writeText(text).then(() => {
                    this.showToast('消息已复制到剪贴板', 'success');
                }).catch(() => {
                    // 降级方案
                    const textArea = document.createElement('textarea');
                    textArea.value = text;
                    document.body.appendChild(textArea);
                    textArea.select();
                    document.execCommand('copy');
                    document.body.removeChild(textArea);
                    this.showToast('消息已复制到剪贴板', 'success');
                });
            }

            editMessage(button) {
                const messageContent = button.closest('.message').querySelector('.message-content');
                const originalText = messageContent.textContent || messageContent.innerText;
                
                const input = document.getElementById('chatInput');
                input.value = originalText;
                input.focus();
                input.setSelectionRange(input.value.length, input.value.length);
                
                this.showToast('消息已加载到输入框，请编辑后重新发送', 'success');
            }

            // 显示通知
            showToast(message, type = 'success') {
                const toast = document.createElement('div');
                toast.className = `toast toast-${type}`;
                toast.textContent = message;
                document.body.appendChild(toast);
                
                setTimeout(() => {
                    toast.style.opacity = '0';
                    setTimeout(() => toast.remove(), 300);
                }, 3000);
            }

            // API请求封装
            async apiRequest(endpoint, options = {}) {
                const url = this.API_BASE_URL + endpoint;
                const config = {
                    headers: {
                        'Content-Type': 'application/json',
                        ...options.headers
                    },
                    ...options
                };

                if (options.body) {
                    config.body = JSON.stringify(options.body);
                }

                try {
                    const response = await fetch(url, config);
                    
                    if (!response.ok) {
                        const errorData = await response.json().catch(() => ({}));
                        throw new Error(errorData.detail || `HTTP ${response.status}`);
                    }
                    
                    return await response.json();
                } catch (error) {
                    if (error.name === 'TypeError' && error.message.includes('fetch')) {
                        throw new Error('网络连接失败，请检查服务器是否启动');
                    }
                    throw error;
                }
            }

            // 工具函数
            escapeHtml(text) {
                const div = document.createElement('div');
                div.textContent = text;
                return div.innerHTML;
            }

            formatMessage(content) {
                // 增强的markdown格式化
                return content
                    .replace(/```(\w+)?\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>')
                    .replace(/`([^`]+)`/g, '<code>$1</code>')
                    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                    .replace(/\*(.*?)\*/g, '<em>$1</em>')
                    .replace(/\n/g, '<br>')
                    .replace(/\[搜索：(.*?)\]/g, '<span class="tool-call-indicator">🔍 搜索：$1</span>')
                    .replace(/\[工具调用：(.*?)\]/g, '<span class="tool-call-indicator">🔧 工具调用：$1</span>');
            }
        }

        // 初始化应用
        let app;
        window.onload = function() {
            app = new ChatApp();
        };
    </script>
</body>
</html>'''

def save_html_file(output_path='front_end.html'):
    """保存HTML文件"""
    try:
        html_content = generate_html_content()
        
        # 确保输出目录存在
        output_dir = Path(output_path).parent
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 保存HTML文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"✅ HTML文件已保存到: {output_path}")
        return True
        
    except Exception as e:
        print(f"❌ 保存HTML文件失败: {e}")
        return False

def serve_html_file(port=3000):
    """启动简单的HTTP服务器来提供HTML文件"""
    try:
        import http.server
        import socketserver
        
        # 确保HTML文件存在
        html_path = 'front_end.html'
        if not os.path.exists(html_path):
            save_html_file(html_path)
        
        # 切换到HTML文件所在目录
        os.chdir(Path(html_path).parent)
        
        # 启动服务器
        Handler = http.server.SimpleHTTPRequestHandler
        with socketserver.TCPServer(("", port), Handler) as httpd:
            print(f"🌐 HTTP服务器已启动: http://localhost:{port}")
            print(f"📄 前端页面: http://localhost:{port}/front_end.html")
            print("按 Ctrl+C 停止服务器")
            httpd.serve_forever()
            
    except KeyboardInterrupt:
        print("\n👋 服务器已停止")
    except Exception as e:
        print(f"❌ 启动服务器失败: {e}")

def main():
    """主函数"""
    print("🚀 Web搜索助手前端生成器")
    print("=" * 50)
    
    # 检查命令行参数
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == 'serve':
            # 启动服务器
            port = int(sys.argv[2]) if len(sys.argv) > 2 else 3000
            serve_html_file(port)
        elif command == 'save':
            # 保存HTML文件
            output_path = sys.argv[2] if len(sys.argv) > 2 else 'front_end.html'
            save_html_file(output_path)
        elif command == 'help':
            print("使用方法:")
            print("  python front_end.py save [output_path]  # 保存HTML文件")
            print("  python front_end.py serve [port]      # 启动HTTP服务器")
            print("  python front_end.py                    # 默认保存HTML文件")
        else:
            print(f"❌ 未知命令: {command}")
            print("使用 'python front_end.py help' 查看帮助")
    else:
        # 默认行为：保存HTML文件
        save_html_file()
        print("\n💡 提示:")
        print("  - 使用 'python front_end.py serve' 启动HTTP服务器")
        print("  - 使用 'python front_end.py help' 查看所有命令")

if __name__ == "__main__":
    main()