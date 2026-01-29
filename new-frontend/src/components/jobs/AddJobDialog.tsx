import { useState } from 'react';
import { X } from 'lucide-react';

interface AddJobDialogProps {
  onClose: () => void;
  onAdd: (url: string) => void;
}

export function AddJobDialog({ onClose, onAdd }: AddJobDialogProps) {
  const [url, setUrl] = useState('');

  const handleSubmit = () => {
    if (url.trim()) {
      onAdd(url);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50 animate-in fade-in duration-200">
      <div className="bg-white rounded-lg w-full max-w-md shadow-2xl">
        <div className="flex items-center justify-between p-6 border-b border-[#629FAD]/30">
          <h2 className="text-xl font-semibold text-[#0C2C55]">Add Job Manually</h2>
          <button
            onClick={onClose}
            className="p-2 text-[#629FAD] hover:text-[#0C2C55] rounded-lg hover:bg-[#E8E2DB]/50 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        
        <div className="p-6">
          <label className="block text-sm font-medium text-[#0C2C55] mb-2">
            Job URL
          </label>
          <input
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://example.com/job-posting"
            className="w-full px-4 py-2 border border-[#629FAD]/30 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#296374]"
            autoFocus
          />
        </div>

        <div className="flex gap-3 p-6 border-t border-[#629FAD]/30">
          <button
            onClick={onClose}
            className="flex-1 px-4 py-2 bg-white text-[#0C2C55] border border-[#629FAD]/30 rounded-lg hover:bg-[#E8E2DB]/50 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={!url.trim()}
            className="flex-1 px-4 py-2 bg-[#0C2C55] text-[#E8E2DB] rounded-lg hover:bg-[#0C2C55]/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Add Job
          </button>
        </div>
      </div>
    </div>
  );
}
