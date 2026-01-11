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
        <div className="space-y-12 pb-20">
            <header className="flex items-center justify-between gap-4">
                <div className="flex flex-col gap-2">
                    <h1 className="text-3xl font-bold tracking-tight font-serif text-foreground">My Profile</h1>
                    <p className="text-muted-foreground">Manage your personal information and application preferences.</p>
                </div>
                <Button
                    onClick={saveProfile}
                    size="lg"
                    className="px-8 shadow-sm"
                >
                    Save Changes
                </Button>
            </header>

            <div className="flex flex-col gap-10">
                {/* Basics Section */}
                <section className="space-y-6">
                    <div className="flex flex-col gap-1">
                        <h2 className="text-xl font-semibold text-foreground">Personal Details</h2>
                        <p className="text-sm text-muted-foreground">Standard information used for your applications.</p>
                    </div>
                    <Card className="shadow-sm border-border/60">
                        <CardContent className="p-8 space-y-8">
                            <div className="grid gap-8 sm:grid-cols-2">
                                <div className="space-y-2.5">
                                    <Label className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground/80">First Name</Label>
                                    <Input className="h-11 bg-muted/20 border-transparent focus:border-accent/30 transition-all" value={profile.basics.first_name} onChange={(e) => handleChange('basics', 'first_name', e.target.value)} />
                                </div>
                                <div className="space-y-2.5">
                                    <Label className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground/80">Last Name</Label>
                                    <Input className="h-11 bg-muted/20 border-transparent focus:border-accent/30 transition-all" value={profile.basics.last_name} onChange={(e) => handleChange('basics', 'last_name', e.target.value)} />
                                </div>
                            </div>
                            <div className="grid gap-8 sm:grid-cols-2">
                                <div className="space-y-2.5">
                                    <Label className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground/80">Email Address</Label>
                                    <Input className="h-11 bg-muted/20 border-transparent focus:border-accent/30 transition-all" value={profile.basics.email} onChange={(e) => handleChange('basics', 'email', e.target.value)} />
                                </div>
                                <div className="space-y-2.5">
                                    <Label className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground/80">Phone Number</Label>
                                    <Input className="h-11 bg-muted/20 border-transparent focus:border-accent/30 transition-all" value={profile.basics.phone} onChange={(e) => handleChange('basics', 'phone', e.target.value)} />
                                </div>
                            </div>
                            <div className="space-y-2.5">
                                <Label className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground/80">Current Location</Label>
                                <Input className="h-11 bg-muted/20 border-transparent focus:border-accent/30 transition-all" value={profile.basics.location} onChange={(e) => handleChange('basics', 'location', e.target.value)} />
                            </div>
                        </CardContent>
                    </Card>
                </section>

                <div className="grid gap-10 lg:grid-cols-2">
                    {/* Links Section */}
                    <section className="space-y-6">
                        <div className="flex flex-col gap-1">
                            <h2 className="text-xl font-semibold text-foreground">Online Presence</h2>
                            <p className="text-sm text-muted-foreground">Links to your professional profiles.</p>
                        </div>
                        <Card className="shadow-sm border-border/60 h-full">
                            <CardContent className="p-8 space-y-8">
                                <div className="space-y-2.5">
                                    <Label className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground/80">LinkedIn URL</Label>
                                    <Input className="h-11 bg-muted/20 border-transparent focus:border-accent/30 transition-all" value={profile.urls.linkedin} onChange={(e) => handleChange('urls', 'linkedin', e.target.value)} />
                                </div>
                                <div className="space-y-2.5">
                                    <Label className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground/80">GitHub URL</Label>
                                    <Input className="h-11 bg-muted/20 border-transparent focus:border-accent/30 transition-all" value={profile.urls.github} onChange={(e) => handleChange('urls', 'github', e.target.value)} />
                                </div>
                                <div className="space-y-2.5">
                                    <Label className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground/80">Portfolio URL</Label>
                                    <Input className="h-11 bg-muted/20 border-transparent focus:border-accent/30 transition-all" value={profile.urls.portfolio} onChange={(e) => handleChange('urls', 'portfolio', e.target.value)} />
                                </div>
                            </CardContent>
                        </Card>
                    </section>

                    {/* Education Section */}
                    <section className="space-y-6">
                        <div className="flex flex-col gap-1">
                            <h2 className="text-xl font-semibold text-foreground">Education</h2>
                            <p className="text-sm text-muted-foreground">Your highest level of academic achievement.</p>
                        </div>
                        <Card className="shadow-sm border-border/60 h-full">
                            <CardContent className="p-8 space-y-8">
                                <div className="grid gap-8 sm:grid-cols-2">
                                    <div className="space-y-2.5">
                                        <Label className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground/80">Degree</Label>
                                        <Input className="h-11 bg-muted/20 border-transparent focus:border-accent/30 transition-all" value={profile.education.degree} onChange={(e) => handleChange('education', 'degree', e.target.value)} />
                                    </div>
                                    <div className="space-y-2.5">
                                        <Label className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground/80">Graduation Year</Label>
                                        <Input className="h-11 bg-muted/20 border-transparent focus:border-accent/30 transition-all" value={profile.education.graduation_year} onChange={(e) => handleChange('education', 'graduation_year', e.target.value)} />
                                    </div>
                                </div>
                                <div className="space-y-2.5">
                                    <Label className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground/80">Field of Study</Label>
                                    <Input className="h-11 bg-muted/20 border-transparent focus:border-accent/30 transition-all" value={profile.education.field_of_study} onChange={(e) => handleChange('education', 'field_of_study', e.target.value)} />
                                </div>
                                <div className="space-y-2.5">
                                    <Label className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground/80">University Name</Label>
                                    <Input className="h-11 bg-muted/20 border-transparent focus:border-accent/30 transition-all" value={profile.education.university} onChange={(e) => handleChange('education', 'university', e.target.value)} />
                                </div>
                            </CardContent>
                        </Card>
                    </section>
                </div>
            </div>
        </div>
    );
}
