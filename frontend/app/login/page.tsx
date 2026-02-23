"use client";

import { useState } from "react";
import { useAuth } from "@/components/providers/auth-provider";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { toast } from "sonner";
import axios from "axios";
import { API_URL } from "@/lib/api";

export default function LoginPage() {
    const [username, setUsername] = useState("");
    const [password, setPassword] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const { login } = useAuth();
    const router = useRouter();

    const handleLogin = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsLoading(true);

        try {
            // Use relative URL - next.config.js or proxy should handle /api
            // But based on previous context, we might need full URL if not proxied
            // Let's assume /api proxy is set up or use env var

            const response = await axios.post(`${API_URL}/auth/token`,
                new URLSearchParams({
                    username: username,
                    password: password,
                }),
                {
                    headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
                }
            );

            const { access_token } = response.data;
            login(access_token);
            toast.success("Logged in successfully");
        } catch (error: unknown) {
            console.error(error);
            if (axios.isAxiosError(error)) {
                toast.error(error.response?.data?.detail || "Login failed");
            } else {
                toast.error("An unexpected error occurred");
            }
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="flex items-center justify-center min-h-[80vh]">
            <Card className="w-full max-w-md">
                <CardHeader>
                    <CardTitle className="text-2xl font-bold text-center">Welcome Back</CardTitle>
                    <CardDescription className="text-center">
                        Enter your credentials to access your account
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <form onSubmit={handleLogin} className="space-y-4">
                        <div className="space-y-2">
                            <Label htmlFor="username">Username</Label>
                            <Input
                                id="username"
                                type="text"
                                placeholder="jdoe"
                                value={username}
                                onChange={(e) => setUsername(e.target.value)}
                                required
                            />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="password">Password</Label>
                            <Input
                                id="password"
                                type="password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                required
                            />
                        </div>
                        <Button type="submit" className="w-full" disabled={isLoading}>
                            {isLoading ? "Logging in..." : "Login"}
                        </Button>
                    </form>
                </CardContent>
                <CardFooter className="flex flex-col space-y-4">
                    <div className="pt-4 border-t w-full">
                        <p className="text-xs text-center text-slate-500 uppercase font-bold tracking-wider mb-3">Test Access</p>
                        <div className="flex flex-col gap-2">
                            <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 flex items-center justify-between">
                                <div className="text-sm">
                                    <span className="font-semibold text-slate-700">Username:</span> testuser<br />
                                    <span className="font-semibold text-slate-700">Password:</span> password123
                                </div>
                                <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={() => {
                                        setUsername("testuser");
                                        setPassword("password123");
                                    }}
                                    className="text-xs"
                                >
                                    Auto-fill
                                </Button>
                            </div>
                        </div>
                    </div>
                    <p className="text-sm text-gray-500">
                        Don't have an account?{" "}
                        <Link href="/register" className="text-blue-600 hover:underline">
                            Register
                        </Link>
                    </p>
                </CardFooter>
            </Card>
        </div>
    );
}
