import { request } from '@umijs/max';

export interface Message {
    id: number;
    role: 'user' | 'assistant';
    content: string;
    created_at: string;
}

const API_BASE = 'http://localhost:8000';

/**
 * 发送消息（流式）
 */
export async function sendMessage(
    content: string,
    onChunk: (chunk: string) => void,
    onError?: (error: string) => void
): Promise<void> {
    try {
        const response = await fetch(`${API_BASE}/api/chat/send`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('token')}`,
            },
            body: JSON.stringify({ content }),
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || '发送失败');
        }

        const reader = response.body?.getReader();
        const decoder = new TextDecoder();

        while (true) {
            const { done, value } = await reader!.read();
            if (done) break;

            const chunk = decoder.decode(value);
            onChunk(chunk);
        }
    } catch (error: any) {
        if (onError) {
            onError(error.message || '网络错误');
        }
        throw error;
    }
}

/**
 * 获取聊天历史
 */
export async function getChatHistory(): Promise<{ messages: Message[] }> {
    return request(`${API_BASE}/api/chat/history`);
}

/**
 * 清除聊天历史
 */
export async function clearChatHistory(): Promise<{ message: string }> {
    return request(`${API_BASE}/api/chat/clear`, {
        method: 'DELETE',
    });
}
