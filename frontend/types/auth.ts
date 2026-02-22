export interface User {
    id: string;
    email: string;
    username: string;
    roles: string[];
    created_at?: string;
}

export interface LoginResponse {
    access_token: string;
    token_type: string;
}
