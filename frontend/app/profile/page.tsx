"use client"
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function ProfilePage() {
    const [profile, setProfile] = useState<any>(null);
    const [loading, setLoading] = useState(true);

    const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

    const fetchProfile = async () => {
        try {
            const res = await axios.get(`${API_URL}/profile`);
            setProfile(res.data);
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchProfile();
    }, []);

    const handleChange = (section: string, field: string, value: any) => {
        setProfile((prev: any) => ({
            ...prev,
            [section]: {
                ...prev[section],
                [field]: value
            }
        }));
    };

    const saveProfile = async () => {
        try {
            await axios.post(`${API_URL}/profile`, profile);
            alert("Profile saved!");
        } catch (e) {
            alert("Failed to save profile");
        }
    };

    if (loading) return <div>Loading...</div>;
    if (!profile) return <div>Error loading profile.</div>;

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <h1 className="text-3xl font-bold tracking-tight">My Profile</h1>
                <Button onClick={saveProfile}>Save Changes</Button>
            </div>

            <div className="grid gap-6 grid-cols-1 lg:grid-cols-2">
                <Card className="w-full">
                    <CardHeader><CardTitle>Basics</CardTitle></CardHeader>
                    <CardContent className="space-y-4">
                        <div className="grid gap-4 sm:grid-cols-2">
                            <div className="space-y-2">
                                <Label>First Name</Label>
                                <Input className="w-full" value={profile.basics.first_name} onChange={(e) => handleChange('basics', 'first_name', e.target.value)} />
                            </div>
                            <div className="space-y-2">
                                <Label>Last Name</Label>
                                <Input className="w-full" value={profile.basics.last_name} onChange={(e) => handleChange('basics', 'last_name', e.target.value)} />
                            </div>
                        </div>
                        <div className="grid gap-4 sm:grid-cols-2">
                            <div className="space-y-2">
                                <Label>Email</Label>
                                <Input className="w-full" value={profile.basics.email} onChange={(e) => handleChange('basics', 'email', e.target.value)} />
                            </div>
                            <div className="space-y-2">
                                <Label>Phone</Label>
                                <Input className="w-full" value={profile.basics.phone} onChange={(e) => handleChange('basics', 'phone', e.target.value)} />
                            </div>
                        </div>
                        <div className="space-y-2">
                            <Label>Location</Label>
                            <Input className="w-full" value={profile.basics.location} onChange={(e) => handleChange('basics', 'location', e.target.value)} />
                        </div>
                    </CardContent>
                </Card>

                <Card className="w-full">
                    <CardHeader><CardTitle>Links</CardTitle></CardHeader>
                    <CardContent className="space-y-4">
                        <div className="space-y-2">
                            <Label>LinkedIn</Label>
                            <Input className="w-full" value={profile.urls.linkedin} onChange={(e) => handleChange('urls', 'linkedin', e.target.value)} />
                        </div>
                        <div className="space-y-2">
                            <Label>GitHub</Label>
                            <Input className="w-full" value={profile.urls.github} onChange={(e) => handleChange('urls', 'github', e.target.value)} />
                        </div>
                        <div className="space-y-2">
                            <Label>Portfolio</Label>
                            <Input className="w-full" value={profile.urls.portfolio} onChange={(e) => handleChange('urls', 'portfolio', e.target.value)} />
                        </div>
                    </CardContent>
                </Card>

                <Card className="w-full">
                    <CardHeader><CardTitle>Education</CardTitle></CardHeader>
                    <CardContent className="space-y-4">
                        <div className="space-y-2">
                            <Label>Degree</Label>
                            <Input className="w-full" value={profile.education.degree} onChange={(e) => handleChange('education', 'degree', e.target.value)} />
                        </div>
                        <div className="space-y-2">
                            <Label>Field of Study</Label>
                            <Input className="w-full" value={profile.education.field_of_study} onChange={(e) => handleChange('education', 'field_of_study', e.target.value)} />
                        </div>
                        <div className="space-y-2">
                            <Label>University</Label>
                            <Input className="w-full" value={profile.education.university} onChange={(e) => handleChange('education', 'university', e.target.value)} />
                        </div>
                        <div className="space-y-2">
                            <Label>Graduation Year</Label>
                            <Input className="w-full" value={profile.education.graduation_year} onChange={(e) => handleChange('education', 'graduation_year', e.target.value)} />
                        </div>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
