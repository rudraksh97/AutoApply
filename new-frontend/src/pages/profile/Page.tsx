import { useState, useEffect } from 'react';
import axios from 'axios';
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { Trash2, Sparkles, FileText, LayoutGrid, Database, Upload, Save } from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { API_URL } from '@/lib/env';

// Define comprehensive types matching backend
interface Profile {
    basics: {
        first_name: string;
        last_name: string;
        email: string;
        phone: string;
        location: string;
    };
    education: {
        degree: string;
        university: string;
        field_of_study: string;
        graduation_year: string;
    }[];
    experience: {
        company: string;
        role: string;
        start_date: string;
        end_date: string;
        description: string;
    }[];
    skills: string;
    urls: {
        linkedin: string;
        github: string;
        portfolio: string;
    };
    demographics: {
        gender: string;
        race: string;
        veteran: string;
        disability: string;
        nationality: string;
    };
    work_auth: {
        authorized_in_us: boolean;
        requires_sponsorship: boolean;
    };
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    pdf_resumes: any[];
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    text_resumes: any[];
    current_pdf_resume_id: string;
    current_text_resume_id: string;
    resume_generation_mode: string;
    uploaded_pdf_path?: string;
}

export default function ProfilePage() {
    const [profile, setProfile] = useState<Profile | null>(null);
    const [loading, setLoading] = useState(true);
    const [isProcessing, setIsProcessing] = useState(false);



    const fetchProfile = async () => {
        try {
            const res = await axios.get(`${API_URL}/profile`);
            setProfile(res.data);
        } catch (e) {
            console.error(e);
            toast.error("Failed to load profile");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchProfile();
    }, []);

    const uploadFile = async (file: File, type: 'pdf' | 'tex') => {
        const formData = new FormData();
        formData.append('file', file);

        try {
            setIsProcessing(true);
            const endpoint = type === 'pdf' ? '/upload-resume' : '/upload-template';
            await axios.post(`${API_URL}${endpoint}`, formData, {
                headers: { 'Content-Type': 'multipart/form-data' }
            });
            toast.success(`${type.toUpperCase()} uploaded successfully!`);
            fetchProfile(); // Refresh list
        } catch (err) {
            console.error(err);
            toast.error(`Failed to upload ${type}`);
        } finally {
            setIsProcessing(false);
        }
    };

    const deleteResume = async (resumeId: string) => {
        try {
            setIsProcessing(true);
            await axios.delete(`${API_URL}/profile/resumes/${resumeId}`);
            toast.success("Resume deleted");
            fetchProfile();
        } catch {
            toast.error("Failed to delete resume");
        } finally {
            setIsProcessing(false);
        }
    };

    const selectResume = async (resumeId: string) => {
        try {
            setIsProcessing(true);
            await axios.post(`${API_URL}/profile/resumes/${resumeId}/select`);
            toast.success("Current resume updated");
            fetchProfile();
        } catch {
            toast.error("Failed to select resume");
        } finally {
            setIsProcessing(false);
        }
    };

    const handleParseResume = async (source: 'pdf' | 'tex') => {
        try {
            setIsProcessing(true);
            const endpoint = `/parse-resume?source=${source}`;
            const res = await axios.post(`${API_URL}${endpoint}`);
            const parsed = res.data;

            // Merge parsed data into profile
            setProfile((prev) => {
                if (!prev) return null;
                return {
                    ...prev,
                    basics: { ...prev.basics, ...parsed.basics },
                    urls: { ...prev.urls, ...parsed.urls },
                    education: parsed.education || prev.education,
                    experience: parsed.experience || prev.experience,
                    skills: parsed.skills
                        ? Array.isArray(parsed.skills)
                            ? parsed.skills.join(", ")
                            : parsed.skills
                        : prev.skills
                };
            });

            toast.success(`Profile auto-filled from ${source.toUpperCase()}! Please review changes.`);
        } catch (err) {
            console.error(err);
            toast.error(`Failed to parse ${source}. Ensure one is uploaded.`);
        } finally {
            setIsProcessing(false);
        }
    };

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const handleChange = (section: keyof Profile | 'root', field: string, value: any) => {
        setProfile((prev) => {
            if (!prev) return null;
            if (section === 'root') {
                return { ...prev, [field]: value };
            }
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            const sectionData = prev[section] as any;
            return {
                ...prev,
                [section]: {
                    ...sectionData,
                    [field]: value
                }
            };
        });
    };

    const saveProfile = async () => {
        try {
            await axios.post(`${API_URL}/profile`, profile);
            toast.success("Profile saved!");
        } catch {
            toast.error("Failed to save profile");
        }
    };

    if (loading) return <div className="p-8 text-[#296374]">Loading profile...</div>;
    if (!profile) return <div className="p-8 text-red-600">Error loading profile.</div>;

    return (
        <div className="p-8 max-w-5xl mx-auto space-y-8">
            <header className="flex items-center justify-between gap-4">
                <div className="flex flex-col gap-1">
                    <h1 className="text-3xl font-semibold text-[#0C2C55]">My Profile</h1>
                    <p className="text-[#296374]">Manage your personal information and application preferences.</p>
                </div>
                <Button
                    onClick={saveProfile}
                    className="bg-[#0C2C55] text-[#E8E2DB] hover:bg-[#0C2C55]/90 rounded-lg"
                >
                    <Save className="w-4 h-4 mr-2" />
                    Save Changes
                </Button>
            </header>

            {/* Resume Selection */}
            <section className="space-y-4">
                <h2 className="text-xl font-semibold text-[#0C2C55]">Resume Selection</h2>
                <div className="grid gap-6 md:grid-cols-2">
                    <Card
                        className={cn(
                            "cursor-pointer transition-all duration-200 border-2",
                            profile.resume_generation_mode === "ats_generated"
                                ? "border-[#0C2C55] bg-[#0C2C55]/5 rounded-lg"
                                : "border-transparent hover:border-[#629FAD]/50 rounded-lg"
                        )}
                        onClick={() => handleChange('root', 'resume_generation_mode', 'ats_generated')}
                    >
                        <CardContent className="p-6 space-y-4">
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-3">
                                    <div className="p-2 rounded-full bg-[#E8E2DB]">
                                        <Sparkles className="h-5 w-5 text-[#0C2C55]" />
                                    </div>
                                    <CardTitle className="text-lg text-[#0C2C55]">ATS Generated</CardTitle>
                                </div>
                                <div className={cn(
                                    "h-5 w-5 rounded-full border-2 flex items-center justify-center",
                                    profile.resume_generation_mode === "ats_generated" ? "border-[#0C2C55]" : "border-[#629FAD]/50"
                                )}>
                                    {profile.resume_generation_mode === "ats_generated" && <div className="h-2.5 w-2.5 rounded-full bg-[#0C2C55]" />}
                                </div>
                            </div>
                            <p className="text-sm text-[#296374]">
                                Automatically tailor your resume for every job using AI. Uses your profile data and your uploaded <code>.tex</code> template.
                            </p>
                        </CardContent>
                    </Card>

                    <Card
                        className={cn(
                            "cursor-pointer transition-all duration-200 border-2",
                            profile.resume_generation_mode === "uploaded_pdf"
                                ? "border-[#0C2C55] bg-[#0C2C55]/5 rounded-lg"
                                : "border-transparent hover:border-[#629FAD]/50 rounded-lg"
                        )}
                        onClick={() => {
                            if (profile.uploaded_pdf_path?.toLowerCase().endsWith('.pdf')) {
                                handleChange('root', 'resume_generation_mode', 'uploaded_pdf');
                            } else {
                                toast.error("Please upload a PDF resume first.");
                            }
                        }}
                    >
                        <CardContent className="p-6 space-y-4">
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-3">
                                    <div className="p-2 rounded-full bg-[#E8E2DB]">
                                        <FileText className="h-5 w-5 text-[#0C2C55]" />
                                    </div>
                                    <CardTitle className="text-lg text-[#0C2C55]">Uploaded PDF</CardTitle>
                                </div>
                                <div className={cn(
                                    "h-5 w-5 rounded-full border-2 flex items-center justify-center",
                                    profile.resume_generation_mode === "uploaded_pdf" ? "border-[#0C2C55]" : "border-[#629FAD]/50"
                                )}>
                                    {profile.resume_generation_mode === "uploaded_pdf" && <div className="h-2.5 w-2.5 rounded-full bg-[#0C2C55]" />}
                                </div>
                            </div>
                            <p className="text-sm text-[#296374]">
                                Use your original, pre-made PDF resume for all applications. No AI tailoring will be applied.
                            </p>
                        </CardContent>
                    </Card>
                </div>
            </section>

            {/* Resume Files */}
            <section className="space-y-4">
                 <Card className="border-[#629FAD]/30 shadow-sm bg-white rounded-lg">
                    <CardHeader className="bg-white py-4 border-b border-[#629FAD]/10">
                        <CardTitle className="text-base font-medium text-[#0C2C55]">Resume Files</CardTitle>
                    </CardHeader>
                    <CardContent className="p-8 space-y-8">
                        {/* PDF Upload */}
                        <div className="space-y-4">
                             <div className="flex items-center justify-between">
                                <Label className="text-sm font-semibold flex items-center gap-2 text-[#0C2C55]">
                                    <FileText className="h-4 w-4" /> PDF Resumes
                                </Label>
                                <div className="relative">
                                    <Button variant="outline" size="sm" className="pointer-events-none">
                                        <Upload className="h-4 w-4 mr-2" /> Upload New PDF
                                    </Button>
                                    <Input
                                        type="file"
                                        accept=".pdf"
                                        className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                                        onChange={(e) => {
                                            const file = e.target.files?.[0];
                                            if (file) uploadFile(file, 'pdf');
                                        }}
                                        disabled={isProcessing}
                                    />
                                </div>
                            </div>
                            <div className="grid gap-3">
                                {profile.pdf_resumes.map((r: any) => (
                                    <div key={r.id} className={cn(
                                        "flex items-center gap-4 p-4 rounded-xl border transition-all",
                                        profile.current_pdf_resume_id === r.id ? "bg-[#0C2C55]/5 border-[#0C2C55]/40" : "bg-white border-[#629FAD]/20"
                                    )}>
                                        <span className="text-sm font-medium truncate flex-1 text-[#0C2C55]">{r.filename}</span>
                                        {profile.current_pdf_resume_id === r.id ? (
                                            <span className="text-[10px] font-bold text-[#0C2C55] uppercase bg-[#E8E2DB] px-2 py-0.5 rounded">Current</span>
                                        ) : (
                                            <Button variant="ghost" size="sm" onClick={() => selectResume(r.id)}>Select</Button>
                                        )}
                                        <Button variant="ghost" size="icon" onClick={() => deleteResume(r.id)} className="text-red-500"><Trash2 className="h-4 w-4" /></Button>
                                    </div>
                                ))}
                            </div>
                        </div>
                        
                        <Separator />

                        {/* LaTeX Upload */}
                        <div className="space-y-4">
                             <div className="flex items-center justify-between">
                                <Label className="text-sm font-semibold flex items-center gap-2 text-[#0C2C55]">
                                    <Database className="h-4 w-4" /> LaTeX Templates
                                </Label>
                                <div className="relative">
                                    <Button variant="outline" size="sm" className="pointer-events-none">
                                        <Upload className="h-4 w-4 mr-2" /> Upload New .tex
                                    </Button>
                                    <Input
                                        type="file"
                                        accept=".tex"
                                        className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                                        onChange={(e) => {
                                            const file = e.target.files?.[0];
                                            if (file) uploadFile(file, 'tex');
                                        }}
                                        disabled={isProcessing}
                                    />
                                </div>
                            </div>
                            <div className="grid gap-3">
                                {profile.text_resumes.map((r: any) => (
                                    <div key={r.id} className={cn(
                                        "flex items-center gap-4 p-4 rounded-xl border transition-all",
                                        profile.current_text_resume_id === r.id ? "bg-[#0C2C55]/5 border-[#0C2C55]/40" : "bg-white border-[#629FAD]/20"
                                    )}>
                                        <span className="text-sm font-medium truncate flex-1 text-[#0C2C55]">{r.filename}</span>
                                        {profile.current_text_resume_id === r.id ? (
                                            <span className="text-[10px] font-bold text-[#0C2C55] uppercase bg-[#E8E2DB] px-2 py-0.5 rounded">Current</span>
                                        ) : (
                                            <Button variant="ghost" size="sm" onClick={() => selectResume(r.id)}>Select</Button>
                                        )}
                                        <Button variant="ghost" size="icon" onClick={() => deleteResume(r.id)} className="text-red-500"><Trash2 className="h-4 w-4" /></Button>
                                    </div>
                                ))}
                            </div>
                        </div>
                        
                        <div className="flex gap-4 pt-4">
                            <Button variant="secondary" onClick={() => handleParseResume('pdf')} disabled={isProcessing || !profile.current_pdf_resume_id}>
                                <LayoutGrid className="h-4 w-4 mr-2" /> Auto-fill from PDF
                            </Button>
                             <Button variant="secondary" onClick={() => handleParseResume('tex')} disabled={isProcessing || !profile.current_text_resume_id}>
                                <LayoutGrid className="h-4 w-4 mr-2" /> Auto-fill from .tex
                            </Button>
                        </div>
                    </CardContent>
                 </Card>
            </section>

            {/* Personal Details */}
            <section className="space-y-4">
                <h2 className="text-xl font-semibold text-[#0C2C55]">Personal Details</h2>
                <Card className="shadow-sm border-[#629FAD]/30 bg-white rounded-lg">
                    <CardContent className="p-8 space-y-8">
                        <div className="grid gap-8 sm:grid-cols-2">
                             <div className="space-y-2">
                                <Label className="text-xs uppercase text-[#296374] font-bold">First Name</Label>
                                <Input value={profile.basics.first_name} onChange={(e) => handleChange('basics', 'first_name', e.target.value)} />
                             </div>
                             <div className="space-y-2">
                                <Label className="text-xs uppercase text-[#296374] font-bold">Last Name</Label>
                                <Input value={profile.basics.last_name} onChange={(e) => handleChange('basics', 'last_name', e.target.value)} />
                             </div>
                        </div>
                         <div className="grid gap-8 sm:grid-cols-2">
                             <div className="space-y-2">
                                <Label className="text-xs uppercase text-[#296374] font-bold">Email</Label>
                                <Input value={profile.basics.email} onChange={(e) => handleChange('basics', 'email', e.target.value)} />
                             </div>
                             <div className="space-y-2">
                                <Label className="text-xs uppercase text-[#296374] font-bold">Phone</Label>
                                <Input value={profile.basics.phone} onChange={(e) => handleChange('basics', 'phone', e.target.value)} />
                             </div>
                        </div>
                         <div className="space-y-2">
                            <Label className="text-xs uppercase text-[#296374] font-bold">Location</Label>
                            <Input value={profile.basics.location} onChange={(e) => handleChange('basics', 'location', e.target.value)} />
                         </div>
                    </CardContent>
                </Card>
            </section>

             {/* Demographics */}
            <section className="space-y-4">
                <h2 className="text-xl font-semibold text-[#0C2C55]">Demographics</h2>
                <Card className="shadow-sm border-[#629FAD]/30 bg-white rounded-lg">
                    <CardContent className="p-8 space-y-8">
                        <div className="grid gap-8 sm:grid-cols-2">
                             <div className="space-y-2">
                                <Label className="text-xs uppercase text-[#296374] font-bold">Gender</Label>
                                <select 
                                    className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background disabled:cursor-not-allowed disabled:opacity-50"
                                    value={profile.demographics.gender}
                                    onChange={(e) => handleChange('demographics', 'gender', e.target.value)}
                                >
                                    <option value="Male">Male</option>
                                    <option value="Female">Female</option>
                                    <option value="Non-binary">Non-binary</option>
                                    <option value="Prefer not to say">Prefer not to say</option>
                                </select>
                             </div>
                             <div className="space-y-2">
                                <Label className="text-xs uppercase text-[#296374] font-bold">Ethnicity</Label>
                                <select 
                                    className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background disabled:cursor-not-allowed disabled:opacity-50"
                                    value={profile.demographics.race}
                                    onChange={(e) => handleChange('demographics', 'race', e.target.value)}
                                >
                                    <option value="">Select...</option>
                                    <option value="Asian">Asian</option>
                                    <option value="Black or African American">Black or African American</option>
                                    <option value="Hispanic / Latino">Hispanic / Latino</option>
                                    <option value="White">White</option>
                                    <option value="Prefer not to say">Prefer not to say</option>
                                </select>
                             </div>
                        </div>
                    </CardContent>
                </Card>
            </section>

             {/* Skills */}
            <section className="space-y-4">
                <h2 className="text-xl font-semibold text-[#0C2C55]">Skills</h2>
                <Card className="shadow-sm border-[#629FAD]/30 bg-white rounded-lg">
                    <CardContent className="p-8">
                        <textarea
                            className="flex min-h-[120px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                            placeholder="React, TypeScript, Node.js..."
                            value={profile.skills}
                            onChange={(e) => handleChange('root', 'skills', e.target.value)}
                        />
                    </CardContent>
                </Card>
            </section>
        </div>
    );
}
