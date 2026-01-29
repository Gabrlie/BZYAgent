export interface User {
    id: number;
    username: string;
    created_at: string;
}

export interface LoginResponse {
    access_token: string;
    token_type: string;
}
