"use client";
import { useState } from 'react';
import { Plus, Trash2, Upload, FileText, Save } from 'lucide-react';

interface Education {
  id: string;
  degree: string;
  university: string;
  year: string;
}

interface WorkExperience {
  id: string;
  company: string;
  role: string;
  duration: string;
  description: string;
}

export function MyProfilePage() {
  const [resumeStrategy, setResumeStrategy] = useState<'ats' | 'pdf'>('ats');
  const [uploadedResumes, setUploadedResumes] = useState<string[]>(['resume-v1.pdf']);
  const [latexTemplates, setLatexTemplates] = useState<string[]>(['template-modern.tex']);
  
  // Personal Details
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [location, setLocation] = useState('');
  
  // Demographics
  const [gender, setGender] = useState('');
  const [ethnicity, setEthnicity] = useState('');
  const [veteran, setVeteran] = useState(false);
  const [disability, setDisability] = useState(false);
  
  // Work Authorization
  const [usAuthorized, setUsAuthorized] = useState(false);
  const [needsSponsorship, setNeedsSponsorship] = useState(false);
  
  // Skills
  const [skills, setSkills] = useState('');
  
  // Online Presence
  const [linkedin, setLinkedin] = useState('');
  const [github, setGithub] = useState('');
  const [portfolio, setPortfolio] = useState('');
  
  // Education
  const [education, setEducation] = useState<Education[]>([
    { id: '1', degree: '', university: '', year: '' }
  ]);
  
  // Work Experience
  const [workExperience, setWorkExperience] = useState<WorkExperience[]>([
    { id: '1', company: '', role: '', duration: '', description: '' }
  ]);

  const addEducation = () => {
    setEducation([...education, { id: Date.now().toString(), degree: '', university: '', year: '' }]);
  };

  const removeEducation = (id: string) => {
    if (education.length > 1) {
      setEducation(education.filter(edu => edu.id !== id));
    }
  };

  const updateEducation = (id: string, field: keyof Education, value: string) => {
    setEducation(education.map(edu => 
      edu.id === id ? { ...edu, [field]: value } : edu
    ));
  };

  const addWorkExperience = () => {
    setWorkExperience([...workExperience, { 
      id: Date.now().toString(), 
      company: '', 
      role: '', 
      duration: '', 
      description: '' 
    }]);
  };

  const removeWorkExperience = (id: string) => {
    if (workExperience.length > 1) {
      setWorkExperience(workExperience.filter(exp => exp.id !== id));
    }
  };

  const updateWorkExperience = (id: string, field: keyof WorkExperience, value: string) => {
    setWorkExperience(workExperience.map(exp => 
      exp.id === id ? { ...exp, [field]: value } : exp
    ));
  };

  const handleSave = () => {
    console.log('Saving profile...');
    // In a real app, this would save to backend/localStorage
  };

  const handleParseResume = () => {
    console.log('Parsing PDF resume to auto-fill fields...');
    // Mock auto-fill from PDF
    setName('John Doe');
    setEmail('john.doe@example.com');
    setPhone('+1 (555) 123-4567');
    setLocation('San Francisco, CA');
  };

  const handleParseLatexResume = () => {
    console.log('Parsing LaTeX resume to auto-fill fields...');
    // Mock auto-fill from LaTeX
    setName('Jane Smith');
    setEmail('jane.smith@example.com');
    setPhone('+1 (555) 987-6543');
    setLocation('New York, NY');
    setSkills('React, TypeScript, Node.js, Python, AWS, Docker');
  };

  return (
    <div className="flex-1 p-8 overflow-auto">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-semibold text-[#0C2C55] mb-8">My Profile</h1>
        
        {/* Resume Management Section */}
        <div className="bg-white rounded-lg shadow-sm p-6 mb-6 border border-[#629FAD]/20">
          <h2 className="font-medium text-[#0C2C55] mb-4">Resume Management</h2>
          
          {/* PDF Resumes */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-[#0C2C55] mb-2">PDF Resumes</label>
            <div className="space-y-2">
              {uploadedResumes.map((resume, index) => (
                <div key={index} className="flex items-center justify-between p-3 bg-[#E8E2DB]/30 rounded-lg">
                  <div className="flex items-center gap-2">
                    <FileText className="w-4 h-4 text-[#296374]" />
                    <span className="text-sm text-[#0C2C55]">{resume}</span>
                  </div>
                  <button
                    onClick={() => setUploadedResumes(uploadedResumes.filter((_, i) => i !== index))}
                    className="text-red-600 hover:text-red-700"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ))}
              <button
                onClick={() => setUploadedResumes([...uploadedResumes, `resume-v${uploadedResumes.length + 1}.pdf`])}
                className="flex items-center gap-2 px-4 py-2 text-sm text-[#296374] hover:bg-[#629FAD]/10 rounded-lg transition-colors"
              >
                <Upload className="w-4 h-4" />
                Upload New Resume
              </button>
            </div>
          </div>

          {/* LaTeX Resumes */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-[#0C2C55] mb-2">LaTeX Resumes</label>
            <div className="space-y-2">
              {latexTemplates.map((template, index) => (
                <div key={index} className="flex items-center justify-between p-3 bg-[#E8E2DB]/30 rounded-lg">
                  <div className="flex items-center gap-2">
                    <FileText className="w-4 h-4 text-[#296374]" />
                    <span className="text-sm text-[#0C2C55]">{template}</span>
                  </div>
                  <button
                    onClick={() => setLatexTemplates(latexTemplates.filter((_, i) => i !== index))}
                    className="text-red-600 hover:text-red-700"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ))}
              <button
                onClick={() => setLatexTemplates([...latexTemplates, `template-${latexTemplates.length + 1}.tex`])}
                className="flex items-center gap-2 px-4 py-2 text-sm text-[#296374] hover:bg-[#629FAD]/10 rounded-lg transition-colors"
              >
                <Upload className="w-4 h-4" />
                Upload New LaTeX Resume
              </button>
            </div>
          </div>

          {/* Auto-Fill */}
          <div className="mt-6 pt-6 border-t border-[#629FAD]/30">
            <h3 className="font-medium text-[#0C2C55] mb-3">Auto-Fill Profile Fields</h3>
            <div className="grid grid-cols-2 gap-3">
              <button
                onClick={handleParseResume}
                className="px-4 py-2 bg-[#0C2C55] text-[#E8E2DB] rounded-lg hover:bg-[#0C2C55]/90 transition-colors"
              >
                Auto-Fill Using PDF Resume
              </button>
              <button
                onClick={handleParseLatexResume}
                className="px-4 py-2 bg-[#0C2C55] text-[#E8E2DB] rounded-lg hover:bg-[#0C2C55]/90 transition-colors"
              >
                Auto-Fill Using LaTeX Resume
              </button>
            </div>
            <p className="text-xs text-[#296374] mt-2">
              Parse your uploaded resume to automatically populate the profile fields below
            </p>
          </div>
        </div>

        {/* Personal Details */}
        <div className="bg-white rounded-lg shadow-sm p-6 mb-6 border border-[#629FAD]/20">
          <h2 className="font-medium text-[#0C2C55] mb-4">Personal Details</h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-[#0C2C55] mb-1">Full Name</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full px-4 py-2 border border-[#629FAD]/30 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#296374]"
                placeholder="John Doe"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-[#0C2C55] mb-1">Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-4 py-2 border border-[#629FAD]/30 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#296374]"
                placeholder="john.doe@example.com"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-[#0C2C55] mb-1">Phone</label>
              <input
                type="tel"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                className="w-full px-4 py-2 border border-[#629FAD]/30 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#296374]"
                placeholder="+1 (555) 123-4567"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-[#0C2C55] mb-1">Location</label>
              <input
                type="text"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                className="w-full px-4 py-2 border border-[#629FAD]/30 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#296374]"
                placeholder="San Francisco, CA"
              />
            </div>
          </div>
        </div>

        {/* Skills */}
        <div className="bg-white rounded-lg shadow-sm p-6 mb-6 border border-[#629FAD]/20">
          <h2 className="font-medium text-[#0C2C55] mb-4">Skills</h2>
          <textarea
            value={skills}
            onChange={(e) => setSkills(e.target.value)}
            className="w-full px-4 py-2 border border-[#629FAD]/30 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#296374]"
            rows={3}
            placeholder="React, TypeScript, Node.js, Python, AWS, Docker..."
          />
        </div>

        {/* Online Presence */}
        <div className="bg-white rounded-lg shadow-sm p-6 mb-6 border border-[#629FAD]/20">
          <h2 className="font-medium text-[#0C2C55] mb-4">Online Presence</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-[#0C2C55] mb-1">LinkedIn</label>
              <input
                type="url"
                value={linkedin}
                onChange={(e) => setLinkedin(e.target.value)}
                className="w-full px-4 py-2 border border-[#629FAD]/30 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#296374]"
                placeholder="https://linkedin.com/in/username"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-[#0C2C55] mb-1">GitHub</label>
              <input
                type="url"
                value={github}
                onChange={(e) => setGithub(e.target.value)}
                className="w-full px-4 py-2 border border-[#629FAD]/30 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#296374]"
                placeholder="https://github.com/username"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-[#0C2C55] mb-1">Portfolio</label>
              <input
                type="url"
                value={portfolio}
                onChange={(e) => setPortfolio(e.target.value)}
                className="w-full px-4 py-2 border border-[#629FAD]/30 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#296374]"
                placeholder="https://yourportfolio.com"
              />
            </div>
          </div>
        </div>

        {/* Education */}
        <div className="bg-white rounded-lg shadow-sm p-6 mb-6 border border-[#629FAD]/20">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-medium text-[#0C2C55]">Education</h2>
            <button
              onClick={addEducation}
              className="flex items-center gap-2 px-3 py-1.5 text-sm text-[#296374] hover:bg-[#629FAD]/10 rounded-lg transition-colors"
            >
              <Plus className="w-4 h-4" />
              Add Education
            </button>
          </div>
          <div className="space-y-4">
            {education.map((edu) => (
              <div key={edu.id} className="p-4 bg-[#E8E2DB]/20 rounded-lg">
                <div className="grid grid-cols-2 gap-4 mb-4">
                  <div>
                    <label className="block text-sm font-medium text-[#0C2C55] mb-1">Degree</label>
                    <input
                      type="text"
                      value={edu.degree}
                      onChange={(e) => updateEducation(edu.id, 'degree', e.target.value)}
                      className="w-full px-4 py-2 border border-[#629FAD]/30 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#296374]"
                      placeholder="B.S. Computer Science"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-[#0C2C55] mb-1">University</label>
                    <input
                      type="text"
                      value={edu.university}
                      onChange={(e) => updateEducation(edu.id, 'university', e.target.value)}
                      className="w-full px-4 py-2 border border-[#629FAD]/30 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#296374]"
                      placeholder="Stanford University"
                    />
                  </div>
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex-1 mr-4">
                    <label className="block text-sm font-medium text-[#0C2C55] mb-1">Year</label>
                    <input
                      type="text"
                      value={edu.year}
                      onChange={(e) => updateEducation(edu.id, 'year', e.target.value)}
                      className="w-full px-4 py-2 border border-[#629FAD]/30 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#296374]"
                      placeholder="2020"
                    />
                  </div>
                  {education.length > 1 && (
                    <button
                      onClick={() => removeEducation(edu.id)}
                      className="text-red-600 hover:text-red-700 mt-6"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Work Experience */}
        <div className="bg-white rounded-lg shadow-sm p-6 mb-6 border border-[#629FAD]/20">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-medium text-[#0C2C55]">Work Experience</h2>
            <button
              onClick={addWorkExperience}
              className="flex items-center gap-2 px-3 py-1.5 text-sm text-[#296374] hover:bg-[#629FAD]/10 rounded-lg transition-colors"
            >
              <Plus className="w-4 h-4" />
              Add Experience
            </button>
          </div>
          <div className="space-y-4">
            {workExperience.map((exp) => (
              <div key={exp.id} className="p-4 bg-[#E8E2DB]/20 rounded-lg">
                <div className="grid grid-cols-2 gap-4 mb-4">
                  <div>
                    <label className="block text-sm font-medium text-[#0C2C55] mb-1">Company</label>
                    <input
                      type="text"
                      value={exp.company}
                      onChange={(e) => updateWorkExperience(exp.id, 'company', e.target.value)}
                      className="w-full px-4 py-2 border border-[#629FAD]/30 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#296374]"
                      placeholder="Google"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-[#0C2C55] mb-1">Role</label>
                    <input
                      type="text"
                      value={exp.role}
                      onChange={(e) => updateWorkExperience(exp.id, 'role', e.target.value)}
                      className="w-full px-4 py-2 border border-[#629FAD]/30 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#296374]"
                      placeholder="Software Engineer"
                    />
                  </div>
                </div>
                <div className="mb-4">
                  <label className="block text-sm font-medium text-[#0C2C55] mb-1">Duration</label>
                  <input
                    type="text"
                    value={exp.duration}
                    onChange={(e) => updateWorkExperience(exp.id, 'duration', e.target.value)}
                    className="w-full px-4 py-2 border border-[#629FAD]/30 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#296374]"
                    placeholder="2020 - 2023"
                  />
                </div>
                <div className="mb-4">
                  <label className="block text-sm font-medium text-[#0C2C55] mb-1">Description</label>
                  <textarea
                    value={exp.description}
                    onChange={(e) => updateWorkExperience(exp.id, 'description', e.target.value)}
                    className="w-full px-4 py-2 border border-[#629FAD]/30 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#296374]"
                    rows={3}
                    placeholder="Describe your role and achievements..."
                  />
                </div>
                {workExperience.length > 1 && (
                  <button
                    onClick={() => removeWorkExperience(exp.id)}
                    className="text-red-600 hover:text-red-700"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Demographics (Optional) */}
        <div className="bg-white rounded-lg shadow-sm p-6 mb-6 border border-[#629FAD]/20">
          <h2 className="font-medium text-[#0C2C55] mb-4">Demographics (Optional)</h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-[#0C2C55] mb-1">Gender</label>
              <select
                value={gender}
                onChange={(e) => setGender(e.target.value)}
                className="w-full px-4 py-2 border border-[#629FAD]/30 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#296374]"
              >
                <option value="">Prefer not to say</option>
                <option value="male">Male</option>
                <option value="female">Female</option>
                <option value="other">Other</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-[#0C2C55] mb-1">Ethnicity</label>
              <select
                value={ethnicity}
                onChange={(e) => setEthnicity(e.target.value)}
                className="w-full px-4 py-2 border border-[#629FAD]/30 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#296374]"
              >
                <option value="">Prefer not to say</option>
                <option value="asian">Asian</option>
                <option value="black">Black or African American</option>
                <option value="hispanic">Hispanic or Latino</option>
                <option value="white">White</option>
                <option value="other">Other</option>
              </select>
            </div>
          </div>
          <div className="mt-4 space-y-2">
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={veteran}
                onChange={(e) => setVeteran(e.target.checked)}
                className="w-4 h-4 text-[#296374]"
              />
              <span className="text-sm text-[#0C2C55]">Veteran Status</span>
            </label>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={disability}
                onChange={(e) => setDisability(e.target.checked)}
                className="w-4 h-4 text-[#296374]"
              />
              <span className="text-sm text-[#0C2C55]">Disability Status</span>
            </label>
          </div>
        </div>

        {/* Work Authorization */}
        <div className="bg-white rounded-lg shadow-sm p-6 mb-6 border border-[#629FAD]/20">
          <h2 className="font-medium text-[#0C2C55] mb-4">Work Authorization</h2>
          <div className="space-y-2">
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={usAuthorized}
                onChange={(e) => setUsAuthorized(e.target.checked)}
                className="w-4 h-4 text-[#296374]"
              />
              <span className="text-sm text-[#0C2C55]">Authorized to work in the US</span>
            </label>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={needsSponsorship}
                onChange={(e) => setNeedsSponsorship(e.target.checked)}
                className="w-4 h-4 text-[#296374]"
              />
              <span className="text-sm text-[#0C2C55]">Requires visa sponsorship</span>
            </label>
          </div>
        </div>

        {/* Save Button */}
        <div className="flex justify-end">
          <button
            onClick={handleSave}
            className="flex items-center gap-2 px-6 py-2.5 bg-[#0C2C55] text-[#E8E2DB] rounded-lg hover:bg-[#0C2C55]/90 transition-colors"
          >
            <Save className="w-4 h-4" />
            Save Profile
          </button>
        </div>
      </div>
    </div>
  );
}