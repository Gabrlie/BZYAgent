import React, { useState, useEffect, useRef } from 'react';
import { FloatButton, Drawer, Button, Input, App, Empty, Spin } from 'antd';
import { MessageOutlined, ClearOutlined, SendOutlined } from '@ant-design/icons';

interface Message {
    id: number;
    role: 'user' | 'assistant';
    content: string;
    created_at: string;
}

export const AIChat: React.FC = () => {
    const [visible, setVisible] = useState(false);
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [historyLoading, setHistoryLoading] = useState(false);
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const { message: messageApi, modal } = App.useApp();

    // 加载历史
    const loadHistory = async () => {
        setHistoryLoading(true);
        try {
            const response = await fetch('http://localhost:8000/api/chat/history', {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('token')}`,
                },
            });
            const data = await response.json();
            setMessages(data.messages);
        } catch (error) {
            messageApi.error('加载历史失败');
        } finally {
            setHistoryLoading(false);
        }
    };

    // 打开时加载历史
    useEffect(() => {
        if (visible) {
            loadHistory();
        }
    }, [visible]);

    // 自动滚动
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    // 发送消息
    const handleSend = async () => {
        if (!input.trim()) return;

        const userMessage: Message = {
            id: Date.now(),
            role: 'user',
            content: input.trim(),
            created_at: new Date().toISOString(),
        };

        setMessages((prev) => [...prev, userMessage]);
        setInput('');
        setLoading(true);

        // AI 临时消息
        const aiMessageId = Date.now() + 1;
        const tempAiMessage: Message = {
            id: aiMessageId,
            role: 'assistant',
            content: '',
            created_at: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, tempAiMessage]);

        try {
            const response = await fetch('http://localhost:8000/api/chat/send', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('token')}`,
                },
                body: JSON.stringify({ content: userMessage.content }),
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || '发送失败');
            }

            const reader = response.body?.getReader();
            const decoder = new TextDecoder();

            while (true) {
                const { done, value } = await reader!.read();
                if (done) break;

                const chunk = decoder.decode(value);

                setMessages((prev) =>
                    prev.map((msg) =>
                        msg.id === aiMessageId
                            ? { ...msg, content: msg.content + chunk }
                            : msg
                    )
                );
            }
        } catch (error: any) {
            messageApi.error(error.message || '发送失败');
            setMessages((prev) => prev.filter((msg) => msg.id !== aiMessageId));
        } finally {
            setLoading(false);
        }
    };

    // 清除历史
    const handleClear = () => {
        modal.confirm({
            title: '清除历史',
            content: '确定要清除所有聊天记录吗？',
            okText: '确定',
            cancelText: '取消',
            onOk: async () => {
                try {
                    const response = await fetch('http://localhost:8000/api/chat/clear', {
                        method: 'DELETE',
                        headers: {
                            'Authorization': `Bearer ${localStorage.getItem('token')}`,
                        },
                    });

                    if (response.ok) {
                        setMessages([]);
                        messageApi.success('已清除');
                    }
                } catch (error) {
                    messageApi.error('清除失败');
                }
            },
        });
    };

    return (
        <>
            <FloatButton
                icon={<MessageOutlined />}
                type="primary"
                onClick={() => setVisible(true)}
                tooltip="AI 助手"
            />

            <Drawer
                title="AI 助手"
                placement="right"
                width={450}
                onClose={() => setVisible(false)}
                open={visible}
                extra={
                    <Button
                        type="text"
                        icon={<ClearOutlined />}
                        onClick={handleClear}
                        disabled={messages.length === 0}
                    >
                        清除
                    </Button>
                }
            >
                {/* 消息列表 */}
                <div style={{ height: 'calc(100vh - 200px)', overflowY: 'auto', padding: 16, backgroundColor: '#f5f5f5' }}>
                    {historyLoading ? (
                        <div style={{ textAlign: 'center', paddingTop: 100 }}>
                            <Spin tip="加载中..." />
                        </div>
                    ) : messages.length === 0 ? (
                        <Empty description="开始对话吧" image={Empty.PRESENTED_IMAGE_SIMPLE} style={{ marginTop: 100 }} />
                    ) : (
                        messages.map((msg) => (
                            <div
                                key={msg.id}
                                style={{
                                    marginBottom: 16,
                                    textAlign: msg.role === 'user' ? 'right' : 'left',
                                }}
                            >
                                <div
                                    style={{
                                        display: 'inline-block',
                                        padding: '10px 14px',
                                        borderRadius: 12,
                                        maxWidth: '80%',
                                        wordBreak: 'break-word',
                                        whiteSpace: 'pre-wrap',
                                        backgroundColor: msg.role === 'user' ? '#1677ff' : '#fff',
                                        color: msg.role === 'user' ? '#fff' : '#000',
                                        boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
                                    }}
                                >
                                    {msg.content || <Spin size="small" />}
                                </div>
                                <div style={{ fontSize: 12, color: '#999', marginTop: 4 }}>
                                    {new Date(msg.created_at).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}
                                </div>
                            </div>
                        ))
                    )}
                    <div ref={messagesEndRef} />
                </div>

                {/* 输入区 */}
                <div style={{ padding: 16, borderTop: '1px solid #f0f0f0', display: 'flex', gap: 8 }}>
                    <Input.TextArea
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        placeholder="输入消息 (Ctrl+Enter 发送)"
                        disabled={loading}
                        onPressEnter={(e) => {
                            if (e.ctrlKey) {
                                handleSend();
                            }
                        }}
                        autoSize={{ minRows: 1, maxRows: 4 }}
                        style={{ flex: 1 }}
                    />
                    <Button
                        type="primary"
                        icon={<SendOutlined />}
                        onClick={handleSend}
                        loading={loading}
                        disabled={!input.trim()}
                    >
                        发送
                    </Button>
                </div>
            </Drawer>
        </>
    );
};
