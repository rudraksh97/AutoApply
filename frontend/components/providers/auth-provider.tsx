"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { jwtDecode } from "jwt-decode";
import axios from "axios";

interface User {
    id: string;
    username: string;
    roles: string[];
}

interface AuthContextType {
    user: User | null;
    loading: boolean;
    login: (token: string) => void;
    logout: () => void;
    hasRole: (role: string) => boolean;
}

const AuthContext = createContext<AuthContextType>({
    user: null,
    loading: true,
    login: () => { },
    logout: () => { },
    hasRole: () => false,
});

export const useAuth = () => useContext(AuthContext);

export function AuthProvider({ children }: { children: React.ReactNode }) {
    const [user, setUser] = useState<User | null>(null);
    const [loading, setLoading] = useState(true);
    const router = useRouter();
    const pathname = usePathname();

    useEffect(() => {
        // Check for token on mount
        const token = localStorage.getItem("token");
        if (token) {
            try {
                const decoded: any = jwtDecode(token);
                // Ensure roles is an array
                const roles = Array.isArray(decoded.roles) ? decoded.roles : [decoded.roles];
                setUser({
                    id: decoded.id,
                    username: decoded.sub,
                    roles
                });

                // Setup axios interceptor
                axios.defaults.headers.common["Authorization"] = `Bearer ${token}`;
            } catch (e) {
                console.error("Invalid token", e);
                localStorage.removeItem("token");
            }
        }
        setLoading(false);
    }, []);

    const login = (token: string) => {
        localStorage.setItem("token", token);
        const decoded: any = jwtDecode(token);
        const roles = Array.isArray(decoded.roles) ? decoded.roles : [decoded.roles];
        const isBasic = roles.includes("admin") || roles.includes("basic");
        setUser({
            id: decoded.id,
            username: decoded.sub,
            roles
        });
        axios.defaults.headers.common["Authorization"] = `Bearer ${token}`;
        // Everyone lands on /dashboard (Jobs History) by default
        router.push("/dashboard");
    };

    const logout = () => {
        localStorage.removeItem("token");
        setUser(null);
        delete axios.defaults.headers.common["Authorization"];
        router.push("/login"); // Force redirect to login
    };

    const hasRole = (role: string) => {
        if (!user) return false;
        if (user.roles.includes("admin")) return true; // Admin has all access
        return user.roles.includes(role);
    };

    // Protected Routes Logic
    useEffect(() => {
        if (loading) return;

        const publicRoutes = ["/login", "/register"];

        if (!user && !publicRoutes.includes(pathname)) {
            router.push("/login");
            return;
        }

        if (user && publicRoutes.includes(pathname)) {
            router.push("/dashboard");
            return;
        }

        // Customer-only route guard: restrict to /jobs only
        if (user) {
            const isAdmin = user.roles.includes("admin");
            const isBasic = user.roles.includes("basic") || isAdmin;
            const isCustomerOnly = !isBasic && user.roles.includes("customer");
            const CUSTOMER_ALLOWED = ["/dashboard", "/feeds"];
            if (isCustomerOnly && !CUSTOMER_ALLOWED.includes(pathname)) {
                router.push("/dashboard");
            }
        }
    }, [user, loading, pathname, router]);

    if (loading) {
        // Simple loading spinner or verify layout doesn't break
        return <div className="flex h-screen items-center justify-center">Loading...</div>;
    }

    return (
        <AuthContext.Provider value={{ user, loading, login, logout, hasRole }}>
            {children}
        </AuthContext.Provider>
    );
}
