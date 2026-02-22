"use client";

import { useEffect, useState } from "react";
import { fetchWithAuth } from "@/lib/api";
import { User } from "@/types/auth";
import { toast } from "sonner";
import { useAuth } from "@/components/providers/auth-provider";
import { useRouter } from "next/navigation";

export default function UsersPage() {
    const [users, setUsers] = useState<User[]>([]);
    const [loading, setLoading] = useState(true);

    const { user, loading: authLoading, hasRole } = useAuth();
    const router = useRouter();

    useEffect(() => {
        if (!authLoading) {
            if (!hasRole("admin")) {
                toast.error("Unauthorized access");
                router.push("/dashboard");
                return;
            }
            loadUsers();
        }
    }, [authLoading, user, hasRole, router]);

    const loadUsers = async () => {
        try {
            const res = await fetchWithAuth("/admin/users");
            if (res.ok) {
                const data = await res.json();
                setUsers(data);
            } else {
                toast.error("Failed to load users");
            }
        } catch (err) {
            toast.error("Error loading users");
        } finally {
            setLoading(false);
        }
    };

    const handleRoleChange = async (userId: string, role: string, checked: boolean) => {
        // Optimistic update? No, let's just wait.
        const user = users.find((u) => u.id === userId);
        if (!user) return;

        let newRoles = [...user.roles];
        if (checked) {
            if (!newRoles.includes(role)) newRoles.push(role);
        } else {
            newRoles = newRoles.filter((r) => r !== role);
        }

        // Call API
        try {
            const res = await fetchWithAuth(`/admin/users/${userId}/roles`, {
                method: "PUT",
                body: JSON.stringify({ roles: newRoles }),
            });

            if (res.ok) {
                const updatedUser = await res.json();
                setUsers((prev) => prev.map((u) => (u.id === userId ? updatedUser : u)));
                toast.success("Roles updated");
            } else {
                toast.error("Failed to update roles");
            }
        } catch (err: unknown) {
            console.error("Failed to update role", err);
            toast.error("Error updating roles");
        }
    };

    if (loading) return <div>Loading users...</div>;

    return (
        <div>
            <h1 className="text-2xl font-bold mb-6">User Management</h1>
            <div className="bg-card rounded-lg border text-card-foreground shadow-sm">
                <div className="relative w-full overflow-auto">
                    <table className="w-full caption-bottom text-sm">
                        <thead className="[&_tr]:border-b">
                            <tr className="border-b transition-colors hover:bg-muted/50 data-[state=selected]:bg-muted">
                                <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground">Username</th>
                                <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground">Email</th>
                                <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground">Roles</th>
                                <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground">Actions</th>
                            </tr>
                        </thead>
                        <tbody className="[&_tr:last-child]:border-0">
                            {users.map((user) => (
                                <tr key={user.id} className="border-b transition-colors hover:bg-muted/50">
                                    <td className="p-4 align-middle font-medium">{user.username}</td>
                                    <td className="p-4 align-middle">{user.email}</td>
                                    <td className="p-4 align-middle">
                                        <div className="flex gap-1 flex-wrap">
                                            {user.roles.map((r) => (
                                                <span key={r} className="inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80">
                                                    {r}
                                                </span>
                                            ))}
                                        </div>
                                    </td>
                                    <td className="p-4 align-middle">
                                        <div className="flex gap-4">
                                            {["customer", "basic", "admin"].map((role) => (
                                                <label key={role} className="flex items-center space-x-2">
                                                    <input
                                                        type="checkbox"
                                                        checked={user.roles.includes(role)}
                                                        onChange={(e) => handleRoleChange(user.id, role, e.target.checked)}
                                                        className="h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-600"
                                                    />
                                                    <span className="text-xs uppercase">{role}</span>
                                                </label>
                                            ))}
                                        </div>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}
