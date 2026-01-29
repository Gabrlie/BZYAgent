export interface User {
    id: number;
    username: string;
    created_at: string;
    ai_base_url?: string;
    ai_model_name?: string;
    has_api_key?: boolean;  // 是否已配置 API Key
}

export interface LoginResponse {
    access_token: string;
    token_type: string;
}
