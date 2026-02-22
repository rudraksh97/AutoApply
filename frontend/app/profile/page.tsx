"use client";

import { useEffect, useState, useRef } from "react";
import { fetchWithAuth } from "@/lib/api";
import { toast } from "sonner";
import { useAuth } from "@/components/providers/auth-provider";
import { Plus, Trash2, Upload, FileText, CheckCircle } from "lucide-react";

// ─── Types ────────────────────────────────────────────────────────────

interface KBEntry {
    id: string;
    question: string;
    answer: string;
}

interface Education {
    degree: string;
    university: string;
    field_of_study: string;
    graduation_year: string;
}

interface Experience {
    company: string;
    role: string;
    start_date: string;
    end_date: string;
    description: string;
}

interface ResumeInfo {
    id: string;
    filename: string;
    path: string;
    created_at: string;
}

interface ProfileData {
    basics: { first_name: string; last_name: string; email: string; phone: string; location: string; };
    urls: { linkedin: string; github: string; portfolio: string; };
    demographics: { gender: string; race: string; nationality: string; veteran: string; disability: string; };
    work_auth: { authorized_in_us: boolean; requires_sponsorship: boolean; };
    education: Education[];
    experience: Experience[];
    skills: string;
    cover_letter_template: string;
    knowledge_base: KBEntry[];
    pdf_resumes: ResumeInfo[];
    text_resumes: ResumeInfo[];
    current_pdf_resume_id: string | null;
    current_text_resume_id: string | null;
    resume_generation_mode: string;
    use_uploaded_resume: boolean;
}

const EMPTY_EDU: Education = { degree: "", university: "", field_of_study: "", graduation_year: "" };
const EMPTY_EXP: Experience = { company: "", role: "", start_date: "", end_date: "", description: "" };

const DEFAULT_PROFILE: ProfileData = {
    basics: { first_name: "", last_name: "", email: "", phone: "", location: "" },
    urls: { linkedin: "", github: "", portfolio: "" },
    demographics: { gender: "", race: "Prefer not to say", nationality: "", veteran: "I am not a protected veteran", disability: "I do not have a disability" },
    work_auth: { authorized_in_us: true, requires_sponsorship: false },
    education: [{ ...EMPTY_EDU }],
    experience: [{ ...EMPTY_EXP }],
    skills: "",
    cover_letter_template: "",
    knowledge_base: [],
    pdf_resumes: [],
    text_resumes: [],
    current_pdf_resume_id: null,
    current_text_resume_id: null,
    resume_generation_mode: "ats_generated",
    use_uploaded_resume: false,
};

// ─── Shared UI ────────────────────────────────────────────────────────

function Field({ label, children }: { label: string; children: React.ReactNode }) {
    return (
        <div>
            <label className="block text-sm font-medium mb-1 text-foreground">{label}</label>
            {children}
        </div>
    );
}

const inputClass = "w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring";
const selectClass = `${inputClass} cursor-pointer`;

function SectionCard({ title, children }: { title: string; children: React.ReactNode }) {
    return (
        <div className="bg-card p-6 border-x border-b shadow-sm">
            <h2 className="text-lg font-semibold mb-4">{title}</h2>
            {children}
        </div>
    );
}

// ─── Main Page ────────────────────────────────────────────────────────

export default function ProfilePage() {
    const { user } = useAuth();
    const [profile, setProfile] = useState<ProfileData>(DEFAULT_PROFILE);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [uploading, setUploading] = useState<"pdf" | "tex" | null>(null);
    const [autofilling, setAutofilling] = useState<string | null>(null); // resume_id being autofilled
    const pdfRef = useRef<HTMLInputElement>(null);
    const texRef = useRef<HTMLInputElement>(null);

    // New Q&A entry state
    const [newQ, setNewQ] = useState("");
    const [newA, setNewA] = useState("");

    useEffect(() => {
        // Load profile + resume list in parallel
        Promise.all([
            fetchWithAuth("/profile").then(r => r.json()),
            fetchWithAuth("/profile/resumes").then(r => r.json()).catch(() => ({ pdf_resumes: [], tex_resumes: [] })),
        ])
            .then(([profileData, resumeData]) => {
                setProfile({
                    ...DEFAULT_PROFILE,
                    ...profileData,
                    education: profileData.education?.length ? profileData.education : [{ ...EMPTY_EDU }],
                    experience: profileData.experience?.length ? profileData.experience : [{ ...EMPTY_EXP }],
                    knowledge_base: profileData.knowledge_base || [],
                    pdf_resumes: resumeData.pdf_resumes || [],
                    text_resumes: resumeData.tex_resumes || [],
                });
            })
            .catch(() => toast.error("Failed to load profile"))
            .finally(() => setLoading(false));
    }, []);

    const handleSave = async (e: React.FormEvent) => {
        e.preventDefault();
        setSaving(true);
        try {
            const { pdf_resumes, text_resumes, ...payload } = profile;
            const res = await fetchWithAuth("/profile", {
                method: "POST",
                body: JSON.stringify(payload),
            });
            if (res.ok) {
                toast.success("Profile saved");
            } else {
                const err = await res.json().catch(() => ({}));
                toast.error(err.detail || "Save failed");
            }
        } catch {
            toast.error("Error saving profile");
        } finally {
            setSaving(false);
        }
    };

    const handleUpload = async (file: File, type: "pdf" | "tex") => {
        setUploading(type);
        const form = new FormData();
        form.append("file", file);
        try {
            const res = await fetchWithAuth("/profile/resumes", { method: "POST", body: form });
            if (res.ok) {
                const { resume } = await res.json();
                setProfile(p => ({
                    ...p,
                    pdf_resumes: type === "pdf" ? [...p.pdf_resumes, resume] : p.pdf_resumes,
                    text_resumes: type === "tex" ? [...p.text_resumes, resume] : p.text_resumes,
                }));
                toast.success(`${type.toUpperCase()} uploaded`);
            } else {
                toast.error("Upload failed");
            }
        } catch {
            toast.error("Upload error");
        } finally {
            setUploading(null);
        }
    };

    const handleSelectResume = async (id: string) => {
        const res = await fetchWithAuth(`/profile/resumes/${id}/select`, { method: "POST" });
        if (res.ok) {
            const isPdf = profile.pdf_resumes.some(r => r.id === id);
            setProfile(p => ({
                ...p,
                current_pdf_resume_id: isPdf ? id : p.current_pdf_resume_id,
                current_text_resume_id: !isPdf ? id : p.current_text_resume_id,
            }));
            toast.success("Active resume updated");
        }
    };

    const handleDeleteResume = async (id: string) => {
        if (!confirm("Delete this resume?")) return;
        const res = await fetchWithAuth(`/profile/resumes/${id}`, { method: "DELETE" });
        if (res.ok) {
            setProfile(p => ({
                ...p,
                pdf_resumes: p.pdf_resumes.filter(r => r.id !== id),
                text_resumes: p.text_resumes.filter(r => r.id !== id),
                current_pdf_resume_id: p.current_pdf_resume_id === id ? null : p.current_pdf_resume_id,
                current_text_resume_id: p.current_text_resume_id === id ? null : p.current_text_resume_id,
            }));
            toast.success("Resume deleted");
        }
    };

    const handleAutofill = async (resumeId: string, filename: string) => {
        setAutofilling(resumeId);
        try {
            const res = await fetchWithAuth(`/profile/resumes/${resumeId}/autofill`, { method: "POST" });
            if (!res.ok) {
                const err = await res.json().catch(() => ({}));
                toast.error(err.detail || "Autofill failed");
                return;
            }
            const { extracted } = await res.json();
            // Merge extracted data — user still needs to hit Save to persist
            setProfile(p => ({
                ...p,
                basics: { ...p.basics, ...(extracted.basics || {}) },
                urls: { ...p.urls, ...(extracted.urls || {}) },
                education: extracted.education?.length ? extracted.education : p.education,
                experience: extracted.experience?.length ? extracted.experience : p.experience,
                skills: extracted.skills || p.skills,
            }));
            toast.success(`Form filled from "${filename}" — review and save when ready`);
        } catch {
            toast.error("Autofill error");
        } finally {
            setAutofilling(null);
        }
    };

    const addKBEntry = () => {
        if (!newQ.trim() || !newA.trim()) { toast.error("Both question and answer are required"); return; }
        const entry: KBEntry = { id: crypto.randomUUID(), question: newQ.trim(), answer: newA.trim() };
        setProfile(p => ({ ...p, knowledge_base: [...p.knowledge_base, entry] }));
        setNewQ(""); setNewA("");
    };

    const removeKBEntry = (id: string) =>
        setProfile(p => ({ ...p, knowledge_base: p.knowledge_base.filter(e => e.id !== id) }));

    const updateEdu = (idx: number, key: keyof Education, val: string) =>
        setProfile(p => { const e = [...p.education]; e[idx] = { ...e[idx], [key]: val }; return { ...p, education: e }; });

    const updateExp = (idx: number, key: keyof Experience, val: string) =>
        setProfile(p => { const e = [...p.experience]; e[idx] = { ...e[idx], [key]: val }; return { ...p, experience: e }; });

    if (loading) return <div className="flex h-screen items-center justify-center text-muted-foreground">Loading profile…</div>;

    const ResumeList = ({ resumes, type }: { resumes: ResumeInfo[]; type: "pdf" | "tex" }) => (
        <div className="space-y-2">
            {resumes.length === 0 && (
                <p className="text-xs text-muted-foreground italic">No resumes uploaded yet.</p>
            )}
            {resumes.map(r => {
                const isActive = type === "pdf" ? profile.current_pdf_resume_id === r.id : profile.current_text_resume_id === r.id;
                const isAutofilling = autofilling === r.id;
                return (
                    <div key={r.id} className={`flex items-center gap-2 p-2 rounded-md border text-sm ${isActive ? "border-primary bg-primary/5" : "border-border"}`}>
                        <FileText className="h-4 w-4 shrink-0 text-muted-foreground" />
                        <span className="flex-1 truncate">{r.filename}</span>
                        {isActive && <CheckCircle className="h-4 w-4 text-primary shrink-0" />}
                        <button type="button" onClick={() => handleAutofill(r.id, r.filename)}
                            disabled={isAutofilling || !!autofilling}
                            className="text-xs text-amber-600 hover:underline shrink-0 disabled:opacity-50">
                            {isAutofilling ? "Autofilling…" : "Autofill"}
                        </button>
                        <button type="button" onClick={() => handleSelectResume(r.id)}
                            className="text-xs text-primary hover:underline shrink-0">
                            {isActive ? "Active" : "Set Active"}
                        </button>
                        <button type="button" onClick={() => handleDeleteResume(r.id)}
                            className="text-muted-foreground hover:text-destructive shrink-0">
                            <Trash2 className="h-3.5 w-3.5" />
                        </button>
                    </div>
                );
            })}
        </div>
    );

    return (
        <div className="max-w-3xl mx-auto py-8 px-4">
            <div className="mb-6">
                <h1 className="text-2xl font-bold">My Profile</h1>
                <p className="text-sm text-muted-foreground">Keep your profile up-to-date for the best autofill results.</p>
            </div>

            <form onSubmit={handleSave}>
                {/* ─────────────────────────────────────────────────────────────────── */}
                {/* 1. Resume Upload + Toggle  (TOP)                                    */}
                {/* ─────────────────────────────────────────────────────────────────── */}
                <div className="bg-card p-6 border rounded-t shadow-sm">
                    <h2 className="text-lg font-semibold mb-1">Resumes</h2>
                    <p className="text-sm text-muted-foreground mb-4">Upload your PDF and/or LaTeX resume. Set one as active for each type.</p>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-4">
                        {/* PDF */}
                        <div>
                            <p className="text-sm font-medium mb-2">PDF Resume</p>
                            <button type="button" onClick={() => pdfRef.current?.click()}
                                disabled={uploading === "pdf"}
                                className="flex items-center gap-2 text-sm border border-dashed rounded-md px-4 py-2 hover:bg-muted transition-colors disabled:opacity-50 w-full justify-center">
                                <Upload className="h-4 w-4" />
                                {uploading === "pdf" ? "Uploading…" : "Upload PDF"}
                            </button>
                            <input ref={pdfRef} type="file" accept=".pdf" className="hidden"
                                onChange={e => e.target.files?.[0] && handleUpload(e.target.files[0], "pdf")} />
                            <div className="mt-2">
                                <ResumeList resumes={profile.pdf_resumes} type="pdf" />
                            </div>
                        </div>
                        {/* LaTeX */}
                        <div>
                            <p className="text-sm font-medium mb-2">LaTeX Resume (.tex)</p>
                            <button type="button" onClick={() => texRef.current?.click()}
                                disabled={uploading === "tex"}
                                className="flex items-center gap-2 text-sm border border-dashed rounded-md px-4 py-2 hover:bg-muted transition-colors disabled:opacity-50 w-full justify-center">
                                <Upload className="h-4 w-4" />
                                {uploading === "tex" ? "Uploading…" : "Upload .tex"}
                            </button>
                            <input ref={texRef} type="file" accept=".tex" className="hidden"
                                onChange={e => e.target.files?.[0] && handleUpload(e.target.files[0], "tex")} />
                            <div className="mt-2">
                                <ResumeList resumes={profile.text_resumes} type="tex" />
                            </div>
                        </div>
                    </div>

                    {/* Toggle */}
                    <label className="flex items-center gap-3 cursor-pointer border-t pt-4">
                        <input type="checkbox" className="h-4 w-4 rounded border-input"
                            checked={profile.use_uploaded_resume}
                            onChange={e => setProfile(p => ({ ...p, use_uploaded_resume: e.target.checked }))} />
                        <div>
                            <span className="text-sm font-medium">Use uploaded resume instead of AI-generated</span>
                            <p className="text-xs text-muted-foreground">When checked, your active PDF will be submitted directly</p>
                        </div>
                    </label>
                </div>

                {/* ─────────────────────────────────────────────────────────────────── */}
                {/* 2. Cover Letter Template                                            */}
                {/* ─────────────────────────────────────────────────────────────────── */}
                <SectionCard title="Cover Letter Template">
                    <p className="text-xs text-muted-foreground mb-3">Use <code className="bg-muted px-1 rounded">{"{{company}}"}</code> as a placeholder for the company name.</p>
                    <textarea
                        className={inputClass + " min-h-[120px] resize-y"}
                        placeholder={"Dear {{company}} team,\n\nI am excited to apply..."}
                        value={profile.cover_letter_template}
                        onChange={e => setProfile(p => ({ ...p, cover_letter_template: e.target.value }))}
                    />
                </SectionCard>

                {/* ─────────────────────────────────────────────────────────────────── */}
                {/* 3. Basic Info                                                       */}
                {/* ─────────────────────────────────────────────────────────────────── */}
                <SectionCard title="Basic Information">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <Field label="First Name"><input className={inputClass} value={profile.basics.first_name} onChange={e => setProfile(p => ({ ...p, basics: { ...p.basics, first_name: e.target.value } }))} placeholder="Jane" /></Field>
                        <Field label="Last Name"><input className={inputClass} value={profile.basics.last_name} onChange={e => setProfile(p => ({ ...p, basics: { ...p.basics, last_name: e.target.value } }))} placeholder="Doe" /></Field>
                        <Field label="Email"><input type="email" className={inputClass} value={profile.basics.email} onChange={e => setProfile(p => ({ ...p, basics: { ...p.basics, email: e.target.value } }))} placeholder="jane@example.com" /></Field>
                        <Field label="Phone"><input className={inputClass} value={profile.basics.phone} onChange={e => setProfile(p => ({ ...p, basics: { ...p.basics, phone: e.target.value } }))} placeholder="+1 555 0100" /></Field>
                        <Field label="Location" ><input className={inputClass} value={profile.basics.location} onChange={e => setProfile(p => ({ ...p, basics: { ...p.basics, location: e.target.value } }))} placeholder="San Francisco, CA" /></Field>
                    </div>
                </SectionCard>

                {/* ─────────────────────────────────────────────────────────────────── */}
                {/* 4. Professional Links                                               */}
                {/* ─────────────────────────────────────────────────────────────────── */}
                <SectionCard title="Professional Links">
                    <div className="grid grid-cols-1 gap-4">
                        <Field label="LinkedIn"><input className={inputClass} value={profile.urls.linkedin} onChange={e => setProfile(p => ({ ...p, urls: { ...p.urls, linkedin: e.target.value } }))} placeholder="https://linkedin.com/in/..." /></Field>
                        <Field label="GitHub"><input className={inputClass} value={profile.urls.github} onChange={e => setProfile(p => ({ ...p, urls: { ...p.urls, github: e.target.value } }))} placeholder="https://github.com/..." /></Field>
                        <Field label="Portfolio / Website"><input className={inputClass} value={profile.urls.portfolio} onChange={e => setProfile(p => ({ ...p, urls: { ...p.urls, portfolio: e.target.value } }))} placeholder="https://..." /></Field>
                    </div>
                </SectionCard>

                {/* ─────────────────────────────────────────────────────────────────── */}
                {/* 5. Demographics                                                     */}
                {/* ─────────────────────────────────────────────────────────────────── */}
                <SectionCard title="Demographics">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <Field label="Gender">
                            <select className={selectClass} value={profile.demographics.gender} onChange={e => setProfile(p => ({ ...p, demographics: { ...p.demographics, gender: e.target.value } }))}>
                                <option value="">Prefer not to say</option>
                                <option>Male</option><option>Female</option><option>Non-binary</option><option>Other</option>
                            </select>
                        </Field>
                        <Field label="Race / Ethnicity">
                            <select className={selectClass} value={profile.demographics.race} onChange={e => setProfile(p => ({ ...p, demographics: { ...p.demographics, race: e.target.value } }))}>
                                {["Prefer not to say", "White", "Black or African American", "Asian", "Hispanic or Latino", "Native American", "Pacific Islander", "Two or more races", "Other"].map(o => <option key={o}>{o}</option>)}
                            </select>
                        </Field>
                        <Field label="Nationality"><input className={inputClass} value={profile.demographics.nationality} onChange={e => setProfile(p => ({ ...p, demographics: { ...p.demographics, nationality: e.target.value } }))} placeholder="e.g. American" /></Field>
                        <Field label="Veteran Status">
                            <select className={selectClass} value={profile.demographics.veteran} onChange={e => setProfile(p => ({ ...p, demographics: { ...p.demographics, veteran: e.target.value } }))}>
                                {["I am not a protected veteran", "I am a protected veteran", "I prefer not to say"].map(o => <option key={o}>{o}</option>)}
                            </select>
                        </Field>
                        <Field label="Disability Status">
                            <select className={selectClass} value={profile.demographics.disability} onChange={e => setProfile(p => ({ ...p, demographics: { ...p.demographics, disability: e.target.value } }))}>
                                {["I do not have a disability", "I have a disability", "I prefer not to say"].map(o => <option key={o}>{o}</option>)}
                            </select>
                        </Field>
                    </div>
                </SectionCard>

                {/* ─────────────────────────────────────────────────────────────────── */}
                {/* 6. Work Authorization                                               */}
                {/* ─────────────────────────────────────────────────────────────────── */}
                <SectionCard title="Work Authorization">
                    <div className="space-y-3">
                        <label className="flex items-center gap-3 cursor-pointer">
                            <input type="checkbox" className="h-4 w-4 rounded border-input" checked={profile.work_auth.authorized_in_us} onChange={e => setProfile(p => ({ ...p, work_auth: { ...p.work_auth, authorized_in_us: e.target.checked } }))} />
                            <span className="text-sm">I am authorized to work in the United States</span>
                        </label>
                        <label className="flex items-center gap-3 cursor-pointer">
                            <input type="checkbox" className="h-4 w-4 rounded border-input" checked={profile.work_auth.requires_sponsorship} onChange={e => setProfile(p => ({ ...p, work_auth: { ...p.work_auth, requires_sponsorship: e.target.checked } }))} />
                            <span className="text-sm">I will require visa sponsorship</span>
                        </label>
                    </div>
                </SectionCard>

                {/* ─────────────────────────────────────────────────────────────────── */}
                {/* 7. Education                                                        */}
                {/* ─────────────────────────────────────────────────────────────────── */}
                <div className="bg-card p-6 border-x border-b shadow-sm">
                    <div className="flex items-center justify-between mb-4">
                        <h2 className="text-lg font-semibold">Education</h2>
                        <button type="button" onClick={() => setProfile(p => ({ ...p, education: [...p.education, { ...EMPTY_EDU }] }))}
                            className="flex items-center gap-1 text-sm text-primary hover:underline">
                            <Plus className="h-4 w-4" /> Add
                        </button>
                    </div>
                    <div className="space-y-6">
                        {profile.education.map((edu, i) => (
                            <div key={i} className="relative bg-muted/30 rounded-md p-4 border">
                                {profile.education.length > 1 && (
                                    <button type="button" onClick={() => setProfile(p => ({ ...p, education: p.education.filter((_, j) => j !== i) }))}
                                        className="absolute top-3 right-3 text-muted-foreground hover:text-destructive">
                                        <Trash2 className="h-4 w-4" />
                                    </button>
                                )}
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                    <Field label="Degree"><input className={inputClass} value={edu.degree} onChange={e => updateEdu(i, "degree", e.target.value)} placeholder="BS Computer Science" /></Field>
                                    <Field label="University"><input className={inputClass} value={edu.university} onChange={e => updateEdu(i, "university", e.target.value)} placeholder="MIT" /></Field>
                                    <Field label="Field of Study"><input className={inputClass} value={edu.field_of_study} onChange={e => updateEdu(i, "field_of_study", e.target.value)} placeholder="Computer Science" /></Field>
                                    <Field label="Graduation Year"><input className={inputClass} value={edu.graduation_year} onChange={e => updateEdu(i, "graduation_year", e.target.value)} placeholder="2024" /></Field>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>

                {/* ─────────────────────────────────────────────────────────────────── */}
                {/* 8. Experience                                                       */}
                {/* ─────────────────────────────────────────────────────────────────── */}
                <div className="bg-card p-6 border-x border-b shadow-sm">
                    <div className="flex items-center justify-between mb-4">
                        <h2 className="text-lg font-semibold">Work Experience</h2>
                        <button type="button" onClick={() => setProfile(p => ({ ...p, experience: [...p.experience, { ...EMPTY_EXP }] }))}
                            className="flex items-center gap-1 text-sm text-primary hover:underline">
                            <Plus className="h-4 w-4" /> Add
                        </button>
                    </div>
                    <div className="space-y-6">
                        {profile.experience.map((exp, i) => (
                            <div key={i} className="relative bg-muted/30 rounded-md p-4 border">
                                {profile.experience.length > 1 && (
                                    <button type="button" onClick={() => setProfile(p => ({ ...p, experience: p.experience.filter((_, j) => j !== i) }))}
                                        className="absolute top-3 right-3 text-muted-foreground hover:text-destructive">
                                        <Trash2 className="h-4 w-4" />
                                    </button>
                                )}
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                    <Field label="Company"><input className={inputClass} value={exp.company} onChange={e => updateExp(i, "company", e.target.value)} placeholder="Acme Corp" /></Field>
                                    <Field label="Role / Title"><input className={inputClass} value={exp.role} onChange={e => updateExp(i, "role", e.target.value)} placeholder="Software Engineer" /></Field>
                                    <Field label="Start Date"><input className={inputClass} value={exp.start_date} onChange={e => updateExp(i, "start_date", e.target.value)} placeholder="Jan 2022" /></Field>
                                    <Field label="End Date"><input className={inputClass} value={exp.end_date} onChange={e => updateExp(i, "end_date", e.target.value)} placeholder="Present" /></Field>
                                </div>
                                <div className="mt-3">
                                    <Field label="Description">
                                        <textarea className={inputClass + " min-h-[80px] resize-y"} value={exp.description} onChange={e => updateExp(i, "description", e.target.value)} placeholder="Key responsibilities and achievements…" />
                                    </Field>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>

                {/* ─────────────────────────────────────────────────────────────────── */}
                {/* 9. Skills                                                           */}
                {/* ─────────────────────────────────────────────────────────────────── */}
                <SectionCard title="Skills">
                    <Field label="Skills (comma-separated)">
                        <textarea className={inputClass + " min-h-[80px] resize-y"} value={profile.skills}
                            onChange={e => setProfile(p => ({ ...p, skills: e.target.value }))}
                            placeholder="Python, TypeScript, React, PostgreSQL, Docker…" />
                    </Field>
                </SectionCard>

                {/* ─────────────────────────────────────────────────────────────────── */}
                {/* 10. Q&A Knowledge Base (fully dynamic)                              */}
                {/* ─────────────────────────────────────────────────────────────────── */}
                <div className="bg-card p-6 border-x border-b shadow-sm">
                    <h2 className="text-lg font-semibold mb-1">Questions & Answers</h2>
                    <p className="text-sm text-muted-foreground mb-4">
                        Add questions you commonly encounter on application forms and your preferred answers. Saved with your profile.
                    </p>

                    {/* Existing entries */}
                    {profile.knowledge_base.length > 0 && (
                        <div className="space-y-3 mb-5">
                            {profile.knowledge_base.map(entry => (
                                <div key={entry.id} className="group relative bg-muted/30 rounded-md border p-4">
                                    <button type="button" onClick={() => removeKBEntry(entry.id)}
                                        className="absolute top-3 right-3 opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-destructive transition-opacity">
                                        <Trash2 className="h-4 w-4" />
                                    </button>
                                    <p className="text-sm font-medium text-foreground mb-1">{entry.question}</p>
                                    <p className="text-sm text-muted-foreground whitespace-pre-wrap">{entry.answer}</p>
                                </div>
                            ))}
                        </div>
                    )}

                    {/* Add new entry */}
                    <div className="border rounded-md p-4 bg-background space-y-3">
                        <h3 className="text-sm font-semibold">Add New Entry</h3>
                        <Field label="Question">
                            <input type="text" className={inputClass}
                                placeholder="e.g. Why are you a great fit for this role?"
                                value={newQ} onChange={e => setNewQ(e.target.value)} />
                        </Field>
                        <Field label="Answer">
                            <textarea className={inputClass + " min-h-[80px] resize-y"}
                                placeholder="Your answer…"
                                value={newA} onChange={e => setNewA(e.target.value)} />
                        </Field>
                        <div className="flex justify-end">
                            <button type="button" onClick={addKBEntry}
                                className="flex items-center gap-2 bg-primary text-primary-foreground hover:bg-primary/90 h-9 px-4 rounded-md text-sm font-medium transition-colors">
                                <Plus className="h-4 w-4" /> Add Entry
                            </button>
                        </div>
                    </div>
                </div>

                {/* ─────────────────────────────────────────────────────────────────── */}
                {/* Save button                                                         */}
                {/* ─────────────────────────────────────────────────────────────────── */}
                <div className="flex justify-end pt-6">
                    <button type="submit" disabled={saving}
                        className="bg-primary text-primary-foreground hover:bg-primary/90 h-10 px-8 rounded-md text-sm font-medium transition-colors disabled:opacity-50">
                        {saving ? "Saving…" : "Save Profile"}
                    </button>
                </div>
            </form>
        </div>
    );
}
