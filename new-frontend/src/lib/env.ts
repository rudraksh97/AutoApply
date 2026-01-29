export const getEnv = (key: string): string => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    if (typeof window !== 'undefined' && (window as any)._env_ && (window as any)._env_[key]) {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        return (window as any)._env_[key];
    }
    return import.meta.env[key] || '';
};

export const API_URL = getEnv('NEXT_PUBLIC_API_URL') || "http://localhost:8000";
