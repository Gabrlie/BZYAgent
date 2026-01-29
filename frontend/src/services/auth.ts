import apiClient from './api';
import type { LoginResponse, User } from '../types/auth';

/**
 * 用户登录
 */
export const login = async (username: string, password: string): Promise<LoginResponse> => {
    const response = await apiClient.post<LoginResponse>('/api/auth/login', {
        username,
        password,
    });

    // 保存 token 到 localStorage
    localStorage.setItem('token', response.data.access_token);

    return response.data;
};

/**
 * 获取当前用户信息
 */
export const getCurrentUser = async (): Promise<User> => {
    const response = await apiClient.get<User>('/api/auth/me');
    return response.data;
};

/**
 * 登出
 */
export const logout = (): void => {
    localStorage.removeItem('token');
};

/**
 * 检查是否已登录
 */
export const isAuthenticated = (): boolean => {
    return !!localStorage.getItem('token');
};
