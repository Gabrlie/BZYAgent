import { request } from '@umijs/max';
import type { LoginResponse, User } from './typings';

const API_BASE = 'http://localhost:8000';

/**
 * 用户登录
 */
export async function login(username: string, password: string): Promise<LoginResponse> {
    const response = await request<LoginResponse>(`${API_BASE}/api/auth/login`, {
        method: 'POST',
        data: {
            username,
            password,
        },
    });

    // 保存 token 到 localStorage
    if (response.access_token) {
        localStorage.setItem('token', response.access_token);
    }

    return response;
}

/**
 * 获取当前用户信息
 */
export async function getCurrentUser(): Promise<User> {
    return request<User>(`${API_BASE}/api/auth/me`, {
        method: 'GET',
    });
}

/**
 * 登出
 */
export function logout(): void {
    localStorage.removeItem('token');
}

/**
 * 检查是否已登录
 */
export function isAuthenticated(): boolean {
    return !!localStorage.getItem('token');
}

/**
 * 修改密码
 */
export async function changePassword(
    oldPassword: string,
    newPassword: string
): Promise<{ message: string }> {
    return request<{ message: string }>(`${API_BASE}/api/auth/change-password`, {
        method: 'POST',
        data: {
            old_password: oldPassword,
            new_password: newPassword,
        },
    });
}

/**
 * 修改用户名
 */
export async function changeUsername(
    newUsername: string
): Promise<{ message: string; access_token: string; token_type: string }> {
    return request<{ message: string; access_token: string; token_type: string }>(
        `${API_BASE}/api/auth/username`,
        {
            method: 'PUT',
            data: {
                new_username: newUsername,
            },
        }
    );
}

/**
 * 更新用户设置（AI 配置）
 */
export async function updateUserSettings(settings: {
    ai_api_key?: string;
    ai_base_url?: string;
    ai_model_name?: string;
}): Promise<{ message: string }> {
    return request<{ message: string }>(`${API_BASE}/api/auth/settings`, {
        method: 'PUT',
        data: settings,
    });
}

/**
 * 获取可用的 AI 模型列表
 */
export async function getAvailableModels(config: {
    ai_api_key?: string;  // 可选，如果不提供则使用已保存的
    ai_base_url: string;
}): Promise<{ models: Array<{ id: string; name: string }>; error?: string }> {
    return request<{ models: Array<{ id: string; name: string }>; error?: string }>(
        `${API_BASE}/api/auth/models`,
        {
            method: 'POST',
            data: config,
        }
    );
}
