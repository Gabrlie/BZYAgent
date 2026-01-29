import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

// 创建 axios 实例
const apiClient = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

// 请求拦截器 - 自动添加 Authorization header
apiClient.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem('token');
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    (error) => {
        return Promise.reject(error);
    }
);

// 响应拦截器 - 拦截 401 错误
apiClient.interceptors.response.use(
    (response) => {
        return response;
    },
    (error) => {
        if (error.response && error.response.status === 401) {
            // 清除 token
            localStorage.removeItem('token');
            // 跳转到登录页面
            window.location.href = '/';
        }
        return Promise.reject(error);
    }
);

export default apiClient;
