import { X } from 'lucide-react';

interface JobJsonModalProps {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  job: any;
  onClose: () => void;
}

export function JobJsonModal({ job, onClose }: JobJsonModalProps) {
  // Use the job object directly if no specific format mapping is needed yet,
  // or default to showing the whole object.
  const jsonData = job;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50 animate-in fade-in duration-200">
      <div className="bg-white rounded-lg w-full max-w-3xl max-h-[80vh] flex flex-col shadow-2xl">
        <div className="flex items-center justify-between p-6 border-b border-[#629FAD]/30">
          <h2 className="text-xl font-semibold text-[#0C2C55]">Job Data</h2>
          <button
            onClick={onClose}
            className="p-2 text-[#629FAD] hover:text-[#0C2C55] rounded-lg hover:bg-[#E8E2DB]/50 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        
        <div className="flex-1 overflow-auto p-6">
          <pre className="bg-[#0C2C55] text-[#E8E2DB] p-4 rounded-lg overflow-auto text-sm font-mono whitespace-pre-wrap">
            {JSON.stringify(jsonData, null, 2)}
          </pre>
        </div>

        <div className="p-6 border-t border-[#629FAD]/30">
          <button
            onClick={onClose}
            className="w-full px-4 py-2 bg-[#0C2C55] text-[#E8E2DB] rounded-lg hover:bg-[#0C2C55]/90 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
