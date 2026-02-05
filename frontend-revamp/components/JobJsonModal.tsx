/* eslint-disable @typescript-eslint/no-explicit-any */
import { X } from 'lucide-react';

interface JobJsonModalProps {
  job: any;
  onClose: () => void;
}

export function JobJsonModal({ job, onClose }: JobJsonModalProps) {
  const jsonData = {
    jobId: job.id,
    formData: job.formData || {
      personalInfo: {
        name: 'John Doe',
        email: 'john@example.com',
        phone: '+1 (555) 123-4567'
      },
      workExperience: [
        {
          company: 'Previous Company',
          role: 'Software Engineer',
          duration: '2020-2023'
        }
      ],
      education: [
        {
          degree: 'BS Computer Science',
          university: 'Tech University'
        }
      ]
    },
    confidenceScores: {
      overall: 0.95,
      personalInfo: 0.98,
      workExperience: 0.92,
      education: 0.96
    },
    validation: {
      requiredFieldsFilled: true,
      emailValid: true,
      phoneValid: true
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg w-full max-w-3xl max-h-[80vh] flex flex-col shadow-2xl">
        <div className="flex items-center justify-between p-6 border-b border-[#629FAD]/30">
          <h2 className="text-xl font-semibold text-[#0C2C55]">Form Data & Validation</h2>
          <button
            onClick={onClose}
            className="p-2 text-[#629FAD] hover:text-[#0C2C55] rounded-lg hover:bg-[#EDEDCE]/50 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        
        <div className="flex-1 overflow-auto p-6">
          <pre className="bg-[#0C2C55] text-[#EDEDCE] p-4 rounded-lg overflow-auto text-sm">
            {JSON.stringify(jsonData, null, 2)}
          </pre>
        </div>

        <div className="p-6 border-t border-[#629FAD]/30">
          <button
            onClick={onClose}
            className="w-full px-4 py-2 bg-[#0C2C55] text-[#EDEDCE] rounded-lg hover:bg-[#0C2C55]/90 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}