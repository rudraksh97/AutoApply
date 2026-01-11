"use client"
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Plus, Trash2 } from "lucide-react";

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

                {/* Demographics Section */}
                <section className="space-y-6">
                    <div className="flex flex-col gap-1">
                        <h2 className="text-xl font-semibold text-foreground">Demographics</h2>
                        <p className="text-sm text-muted-foreground">Voluntary self-identification information.</p>
                    </div>
                    <Card className="shadow-sm border-border/60">
                        <CardContent className="p-8 space-y-8">
                            <div className="grid gap-8 sm:grid-cols-2">
                                <div className="space-y-2.5">
                                    <Label className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground/80">Gender</Label>
                                    <select
                                        className="flex h-11 w-full rounded-md border border-input bg-muted/20 px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                                        value={profile.demographics.gender}
                                        onChange={(e) => handleChange('demographics', 'gender', e.target.value)}
                                    >
                                        <option value="Male">Male</option>
                                        <option value="Female">Female</option>
                                        <option value="Non-binary">Non-binary</option>
                                        <option value="Prefer not to say">Prefer not to say</option>
                                    </select>
                                </div>
                                <div className="space-y-2.5">
                                    <Label className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground/80">Nationality</Label>
                                    <Input className="h-11 bg-muted/20 border-transparent focus:border-accent/30 transition-all" value={profile.demographics.nationality} onChange={(e) => handleChange('demographics', 'nationality', e.target.value)} />
                                </div>
                            </div>
                            <div className="grid gap-8 sm:grid-cols-2">
                                <div className="space-y-2.5">
                                    <Label className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground/80">Veteran Status</Label>
                                    <select
                                        className="flex h-11 w-full rounded-md border border-input bg-muted/20 px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                                        value={profile.demographics.veteran}
                                        onChange={(e) => handleChange('demographics', 'veteran', e.target.value)}
                                    >
                                        <option value="I am not a protected veteran">I am not a protected veteran</option>
                                        <option value="I am a protected veteran">I am a protected veteran</option>
                                        <option value="Prefer not to say">Prefer not to say</option>
                                    </select>
                                </div>
                                <div className="space-y-2.5">
                                    <Label className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground/80">Disability Status</Label>
                                    <select
                                        className="flex h-11 w-full rounded-md border border-input bg-muted/20 px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                                        value={profile.demographics.disability}
                                        onChange={(e) => handleChange('demographics', 'disability', e.target.value)}
                                    >
                                        <option value="I do not have a disability">I do not have a disability</option>
                                        <option value="I have a disability">I have a disability</option>
                                        <option value="Prefer not to say">Prefer not to say</option>
                                    </select>
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                </section>

                {/* Work Authorization Section */}
                <section className="space-y-6">
                    <div className="flex flex-col gap-1">
                        <h2 className="text-xl font-semibold text-foreground">Work Authorization</h2>
                        <p className="text-sm text-muted-foreground">Legal authorization to work in the target country.</p>
                    </div>
                    <Card className="shadow-sm border-border/60">
                        <CardContent className="p-8 space-y-4">
                            <div className="flex items-center space-x-3 p-4 border rounded-lg bg-slate-50/50">
                                <input
                                    type="checkbox"
                                    id="auth_us"
                                    className="h-5 w-5 rounded border-gray-300 text-primary focus:ring-primary"
                                    checked={profile.work_auth.authorized_in_us}
                                    onChange={(e) => handleChange('work_auth', 'authorized_in_us', e.target.checked)}
                                />
                                <Label htmlFor="auth_us" className="text-sm font-medium cursor-pointer">Authorized to work in the US</Label>
                            </div>
                            <div className="flex items-center space-x-3 p-4 border rounded-lg bg-slate-50/50">
                                <input
                                    type="checkbox"
                                    id="req_sponsorship"
                                    className="h-5 w-5 rounded border-gray-300 text-primary focus:ring-primary"
                                    checked={profile.work_auth.requires_sponsorship}
                                    onChange={(e) => handleChange('work_auth', 'requires_sponsorship', e.target.checked)}
                                />
                                <Label htmlFor="req_sponsorship" className="text-sm font-medium cursor-pointer">Requires Sponsorship</Label>
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
                            <div className="flex items-center justify-between">
                                <div>
                                    <h2 className="text-xl font-semibold text-foreground">Education</h2>
                                    <p className="text-sm text-muted-foreground">Academic background and qualifications.</p>
                                </div>
                                <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={() => setProfile((prev: any) => ({
                                        ...prev,
                                        education: [...prev.education, { degree: "", university: "", field_of_study: "", graduation_year: "" }]
                                    }))}
                                >
                                    <Plus className="h-4 w-4 mr-2" /> Add
                                </Button>
                            </div>
                        </div>

                        {profile.education.map((edu: any, index: number) => (
                            <Card key={index} className="shadow-sm border-border/60">
                                <CardHeader className="flex flex-row items-center justify-between py-4">
                                    <CardTitle className="text-base font-medium">Education #{index + 1}</CardTitle>
                                    <Button
                                        variant="ghost"
                                        size="icon"
                                        className="h-8 w-8 text-muted-foreground hover:text-red-500"
                                        onClick={() => {
                                            const newEdu = [...profile.education];
                                            newEdu.splice(index, 1);
                                            setProfile((prev: any) => ({ ...prev, education: newEdu }));
                                        }}
                                    >
                                        <Trash2 className="h-4 w-4" />
                                    </Button>
                                </CardHeader>
                                <CardContent className="p-8 pt-0 space-y-8">
                                    <div className="grid gap-8 sm:grid-cols-2">
                                        <div className="space-y-2.5">
                                            <Label className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground/80">Degree</Label>
                                            <Input
                                                className="h-11 bg-muted/20 border-transparent focus:border-accent/30 transition-all"
                                                value={edu.degree}
                                                onChange={(e) => {
                                                    const newEdu = [...profile.education];
                                                    newEdu[index].degree = e.target.value;
                                                    setProfile((prev: any) => ({ ...prev, education: newEdu }));
                                                }}
                                            />
                                        </div>
                                        <div className="space-y-2.5">
                                            <Label className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground/80">Graduation Year</Label>
                                            <Input
                                                className="h-11 bg-muted/20 border-transparent focus:border-accent/30 transition-all"
                                                value={edu.graduation_year}
                                                onChange={(e) => {
                                                    const newEdu = [...profile.education];
                                                    newEdu[index].graduation_year = e.target.value;
                                                    setProfile((prev: any) => ({ ...prev, education: newEdu }));
                                                }}
                                            />
                                        </div>
                                    </div>
                                    <div className="space-y-2.5">
                                        <Label className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground/80">Field of Study</Label>
                                        <Input
                                            className="h-11 bg-muted/20 border-transparent focus:border-accent/30 transition-all"
                                            value={edu.field_of_study}
                                            onChange={(e) => {
                                                const newEdu = [...profile.education];
                                                newEdu[index].field_of_study = e.target.value;
                                                setProfile((prev: any) => ({ ...prev, education: newEdu }));
                                            }}
                                        />
                                    </div>
                                    <div className="space-y-2.5">
                                        <Label className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground/80">University Name</Label>
                                        <Input
                                            className="h-11 bg-muted/20 border-transparent focus:border-accent/30 transition-all"
                                            value={edu.university}
                                            onChange={(e) => {
                                                const newEdu = [...profile.education];
                                                newEdu[index].university = e.target.value;
                                                setProfile((prev: any) => ({ ...prev, education: newEdu }));
                                            }}
                                        />
                                    </div>
                                </CardContent>
                            </Card>
                        ))}
                    </section>
                </div>

                {/* Experience Section */}
                <section className="space-y-6">
                    <div className="flex flex-col gap-1">
                        <div className="flex items-center justify-between">
                            <div>
                                <h2 className="text-xl font-semibold text-foreground">Work Experience</h2>
                                <p className="text-sm text-muted-foreground">Professional history and roles.</p>
                            </div>
                            <Button
                                variant="outline"
                                size="sm"
                                onClick={() => setProfile((prev: any) => ({
                                    ...prev,
                                    experience: [...(prev.experience || []), { company: "", role: "", start_date: "", end_date: "", description: "" }]
                                }))}
                            >
                                <Plus className="h-4 w-4 mr-2" /> Add
                            </Button>
                        </div>
                    </div>

                    {(profile.experience || []).map((exp: any, index: number) => (
                        <Card key={index} className="shadow-sm border-border/60">
                            <CardHeader className="flex flex-row items-center justify-between py-4">
                                <CardTitle className="text-base font-medium">Position #{index + 1}</CardTitle>
                                <Button
                                    variant="ghost"
                                    size="icon"
                                    className="h-8 w-8 text-muted-foreground hover:text-red-500"
                                    onClick={() => {
                                        const newExp = [...profile.experience];
                                        newExp.splice(index, 1);
                                        setProfile((prev: any) => ({ ...prev, experience: newExp }));
                                    }}
                                >
                                    <Trash2 className="h-4 w-4" />
                                </Button>
                            </CardHeader>
                            <CardContent className="p-8 pt-0 space-y-8">
                                <div className="grid gap-8 sm:grid-cols-2">
                                    <div className="space-y-2.5">
                                        <Label className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground/80">Company</Label>
                                        <Input
                                            className="h-11 bg-muted/20 border-transparent focus:border-accent/30 transition-all"
                                            value={exp.company}
                                            onChange={(e) => {
                                                const newExp = [...profile.experience];
                                                newExp[index].company = e.target.value;
                                                setProfile((prev: any) => ({ ...prev, experience: newExp }));
                                            }}
                                        />
                                    </div>
                                    <div className="space-y-2.5">
                                        <Label className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground/80">Role / Title</Label>
                                        <Input
                                            className="h-11 bg-muted/20 border-transparent focus:border-accent/30 transition-all"
                                            value={exp.role}
                                            onChange={(e) => {
                                                const newExp = [...profile.experience];
                                                newExp[index].role = e.target.value;
                                                setProfile((prev: any) => ({ ...prev, experience: newExp }));
                                            }}
                                        />
                                    </div>
                                </div>
                                <div className="grid gap-8 sm:grid-cols-2">
                                    <div className="space-y-2.5">
                                        <Label className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground/80">Start Date</Label>
                                        <Input
                                            className="h-11 bg-muted/20 border-transparent focus:border-accent/30 transition-all"
                                            placeholder="MM/YYYY"
                                            value={exp.start_date}
                                            onChange={(e) => {
                                                const newExp = [...profile.experience];
                                                newExp[index].start_date = e.target.value;
                                                setProfile((prev: any) => ({ ...prev, experience: newExp }));
                                            }}
                                        />
                                    </div>
                                    <div className="space-y-2.5">
                                        <Label className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground/80">End Date</Label>
                                        <Input
                                            className="h-11 bg-muted/20 border-transparent focus:border-accent/30 transition-all"
                                            placeholder="MM/YYYY or Present"
                                            value={exp.end_date}
                                            onChange={(e) => {
                                                const newExp = [...profile.experience];
                                                newExp[index].end_date = e.target.value;
                                                setProfile((prev: any) => ({ ...prev, experience: newExp }));
                                            }}
                                        />
                                    </div>
                                </div>
                                <div className="space-y-2.5">
                                    <Label className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground/80">Description</Label>
                                    <textarea
                                        className="flex min-h-[120px] w-full rounded-md border border-input bg-muted/20 px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                                        value={exp.description}
                                        onChange={(e) => {
                                            const newExp = [...profile.experience];
                                            newExp[index].description = e.target.value;
                                            setProfile((prev: any) => ({ ...prev, experience: newExp }));
                                        }}
                                    />
                                </div>
                            </CardContent>
                        </Card>
                    ))}
                </section>

                {/* Strategy Section */}
                <section className="space-y-6">
                    <div className="flex flex-col gap-1">
                        <h2 className="text-xl font-semibold text-foreground">Application Strategy</h2>
                        <p className="text-sm text-muted-foreground">Custom content for cover letters and "Why us?" questions.</p>
                    </div>

                    <Card className="shadow-sm border-border/60">
                        <CardHeader className="pb-4">
                            <CardTitle className="text-base font-medium">Your Pitch</CardTitle>
                            <CardDescription>Why are you a great fit?</CardDescription>
                        </CardHeader>
                        <CardContent className="p-8 pt-0">
                            <textarea
                                className="flex min-h-[150px] w-full rounded-md border border-input bg-muted/20 px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                                placeholder="I am a software engineer with 5 years of experience..."
                                value={profile.great_fit_pitch || ""}
                                onChange={(e) => setProfile((prev: any) => ({ ...prev, great_fit_pitch: e.target.value }))}
                            />
                        </CardContent>
                    </Card>

                    <Card className="shadow-sm border-border/60">
                        <CardHeader className="pb-4">
                            <CardTitle className="text-base font-medium">Cover Letter Template</CardTitle>
                            <CardDescription>Use placeholder {"{{company}}"} to dynamically insert the company name.</CardDescription>
                        </CardHeader>
                        <CardContent className="p-8 pt-0">
                            <textarea
                                className="flex min-h-[200px] w-full rounded-md border border-input bg-muted/20 px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                                value={profile.cover_letter_template || ""}
                                onChange={(e) => setProfile((prev: any) => ({ ...prev, cover_letter_template: e.target.value }))}
                            />
                        </CardContent>
                    </Card>

                    <Card className="shadow-sm border-border/60">
                        <CardHeader className="pb-4">
                            <CardTitle className="text-base font-medium">"Why do you want to join us?" Template</CardTitle>
                            <CardDescription>Generic template for "Why Us?". Use {"{{company}}"} placeholder.</CardDescription>
                        </CardHeader>
                        <CardContent className="p-8 pt-0">
                            <textarea
                                className="flex min-h-[150px] w-full rounded-md border border-input bg-muted/20 px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                                placeholder="I've always admired {{company}}'s commitment to..."
                                value={profile.why_us || ""}
                                onChange={(e) => setProfile((prev: any) => ({ ...prev, why_us: e.target.value }))}
                            />
                        </CardContent>
                    </Card>

                    <Card className="shadow-sm border-border/60">
                        <CardHeader className="pb-4">
                            <CardTitle className="text-base font-medium">Challenging Project</CardTitle>
                            <CardDescription>Tell me about a challenging project loop.</CardDescription>
                        </CardHeader>
                        <CardContent className="p-8 pt-0">
                            <textarea
                                className="flex min-h-[200px] w-full rounded-md border border-input bg-muted/20 px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                                placeholder="One of the most challenging projects I worked on was..."
                                value={profile.challenging_project || ""}
                                onChange={(e) => setProfile((prev: any) => ({ ...prev, challenging_project: e.target.value }))}
                            />
                        </CardContent>
                    </Card>
                </section>
            </div>
        </div>
    );
}
