"use client";
import { useState } from 'react';
import { RotateCcw, Save } from 'lucide-react';

const defaultScoringPrompt = `You are an ATS (Applicant Tracking System) scoring assistant. Analyze the candidate's resume against the job description.

Variables:
- {{job_description}}: The full text of the job posting
- {{resume_content}}: The candidate's resume text
- {{required_skills}}: List of required skills from the job

Return a JSON object with:
{
  "overall_score": 0-100,
  "skill_match": 0-100,
  "experience_match": 0-100,
  "education_match": 0-100,
  "reasoning": "Brief explanation"
}`;

const defaultTailoringPrompt = `You are a resume tailoring assistant. Rewrite the candidate's LaTeX resume to better match the job description while maintaining truthfulness.

Variables:
- {{job_description}}: The target job posting
- {{latex_template}}: The original LaTeX resume template
- {{profile_data}}: Structured candidate information

Guidelines:
1. Keep all information factual
2. Emphasize relevant experience
3. Adjust keyword density for ATS optimization
4. Maintain professional formatting

Return the complete LaTeX document.`;

const scoringOutputFormat = {
  overall_score: 85,
  skill_match: 90,
  experience_match: 82,
  education_match: 88,
  reasoning: "Strong match for senior frontend position with React expertise"
};

const tailoringOutputFormat = `\\documentclass{article}
\\begin{document}
% Tailored resume content here
\\end{document}`;

export function AtsConfigPage() {
  const [scoringPrompt, setScoringPrompt] = useState(defaultScoringPrompt);
  const [tailoringPrompt, setTailoringPrompt] = useState(defaultTailoringPrompt);

  const insertVariable = (variable: string, isScoring: boolean) => {
    if (isScoring) {
      setScoringPrompt(prev => prev + `\n{{${variable}}}`);
    } else {
      setTailoringPrompt(prev => prev + `\n{{${variable}}}`);
    }
  };

  const resetToDefaults = () => {
    setScoringPrompt(defaultScoringPrompt);
    setTailoringPrompt(defaultTailoringPrompt);
  };

  const handleSave = () => {
    console.log('Saving ATS configuration...');
  };

  return (
    <div className="p-8">
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <h1 className="text-3xl font-semibold text-[#0C2C55]">ATS Configuration</h1>
          <div className="flex gap-3">
            <button
              onClick={resetToDefaults}
              className="flex items-center gap-2 px-4 py-2 bg-white text-[#0C2C55] border border-[#629FAD]/30 rounded-lg hover:bg-[#E8E2DB]/50 transition-colors"
            >
              <RotateCcw className="w-4 h-4" />
              Reset to Defaults
            </button>
            <button
              onClick={handleSave}
              className="flex items-center gap-2 px-4 py-2 bg-[#0C2C55] text-[#E8E2DB] rounded-lg hover:bg-[#0C2C55]/90 transition-colors"
            >
              <Save className="w-4 h-4" />
              Save Configuration
            </button>
          </div>
        </div>

        {/* Scoring Prompt Editor */}
        <div className="bg-white rounded-lg border border-[#629FAD]/30 p-6 mb-6 shadow-sm">
          <h2 className="text-lg font-semibold text-[#0C2C55] mb-4">Resume Scoring Prompt</h2>
          <p className="text-sm text-[#296374] mb-4">
            This prompt is used by the AI to score how well a resume matches a job description.
          </p>
          
          <div className="mb-4">
            <div className="flex gap-2 mb-2">
              <button
                onClick={() => insertVariable('job_description', true)}
                className="px-3 py-1.5 text-sm bg-[#629FAD]/20 text-[#296374] rounded-lg hover:bg-[#629FAD]/30 transition-colors"
              >
                Insert {'{{job_description}}'}
              </button>
              <button
                onClick={() => insertVariable('resume_content', true)}
                className="px-3 py-1.5 text-sm bg-[#629FAD]/20 text-[#296374] rounded-lg hover:bg-[#629FAD]/30 transition-colors"
              >
                Insert {'{{resume_content}}'}
              </button>
              <button
                onClick={() => insertVariable('required_skills', true)}
                className="px-3 py-1.5 text-sm bg-[#629FAD]/20 text-[#296374] rounded-lg hover:bg-[#629FAD]/30 transition-colors"
              >
                Insert {'{{required_skills}}'}
              </button>
            </div>
            <textarea
              value={scoringPrompt}
              onChange={(e) => setScoringPrompt(e.target.value)}
              rows={12}
              className="w-full px-4 py-3 border border-[#629FAD]/30 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#296374] font-mono text-sm"
            />
          </div>

          <div>
            <h3 className="font-medium text-[#0C2C55] mb-2">Expected Output Format</h3>
            <pre className="bg-[#0C2C55] text-[#E8E2DB] p-4 rounded-lg overflow-auto text-sm">
              {JSON.stringify(scoringOutputFormat, null, 2)}
            </pre>
          </div>
        </div>

        {/* Tailoring Prompt Editor */}
        <div className="bg-white rounded-lg border border-[#629FAD]/30 p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-[#0C2C55] mb-4">Resume Tailoring Prompt</h2>
          <p className="text-sm text-[#296374] mb-4">
            This prompt instructs the AI on how to rewrite the LaTeX resume template for each specific job.
          </p>
          
          <div className="mb-4">
            <div className="flex gap-2 mb-2">
              <button
                onClick={() => insertVariable('job_description', false)}
                className="px-3 py-1.5 text-sm bg-[#629FAD]/20 text-[#296374] rounded-lg hover:bg-[#629FAD]/30 transition-colors"
              >
                Insert {'{{job_description}}'}
              </button>
              <button
                onClick={() => insertVariable('latex_template', false)}
                className="px-3 py-1.5 text-sm bg-[#629FAD]/20 text-[#296374] rounded-lg hover:bg-[#629FAD]/30 transition-colors"
              >
                Insert {'{{latex_template}}'}
              </button>
              <button
                onClick={() => insertVariable('profile_data', false)}
                className="px-3 py-1.5 text-sm bg-[#629FAD]/20 text-[#296374] rounded-lg hover:bg-[#629FAD]/30 transition-colors"
              >
                Insert {'{{profile_data}}'}
              </button>
            </div>
            <textarea
              value={tailoringPrompt}
              onChange={(e) => setTailoringPrompt(e.target.value)}
              rows={14}
              className="w-full px-4 py-3 border border-[#629FAD]/30 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#296374] font-mono text-sm"
            />
          </div>

          <div>
            <h3 className="font-medium text-[#0C2C55] mb-2">Expected Output Format</h3>
            <pre className="bg-[#0C2C55] text-[#E8E2DB] p-4 rounded-lg overflow-auto text-sm">
              {tailoringOutputFormat}
            </pre>
          </div>
        </div>
      </div>
    </div>
  );
}