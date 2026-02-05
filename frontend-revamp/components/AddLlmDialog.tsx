import { useState } from 'react';
import { X } from 'lucide-react';

interface AddLlmDialogProps {
  onClose: () => void;
  onAdd: (llm: {
    provider: string;
    model: string;
    name: string;
    apiKey: string;
    dailyLimit: number;
  }) => void;
}

export function AddLlmDialog({ onClose, onAdd }: AddLlmDialogProps) {
  const [provider, setProvider] = useState('');
  const [model, setModel] = useState('');
  const [name, setName] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [dailyLimit, setDailyLimit] = useState('1000000');

  const handleSubmit = () => {
    if (provider && model && name && apiKey) {
      onAdd({
        provider,
        model,
        name,
        apiKey,
        dailyLimit: parseInt(dailyLimit)
      });
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg w-full max-w-md shadow-2xl">
        <div className="flex items-center justify-between p-6 border-b border-[#629FAD]/30">
          <h2 className="text-xl font-semibold text-[#0C2C55]">Add LLM Configuration</h2>
          <button
            onClick={onClose}
            className="p-2 text-[#629FAD] hover:text-[#0C2C55] rounded-lg hover:bg-[#EDEDCE]/50 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        
        <div className="p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-[#0C2C55] mb-2">Provider</label>
            <select
              value={provider}
              onChange={(e) => setProvider(e.target.value)}
              className="w-full px-4 py-2 border border-[#629FAD]/30 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#296374]"
            >
              <option value="">Select provider</option>
              <option value="OpenAI">OpenAI</option>
              <option value="Anthropic">Anthropic</option>
              <option value="Google">Google</option>
              <option value="Cohere">Cohere</option>
              <option value="Other">Other</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-[#0C2C55] mb-2">Model</label>
            <input
              type="text"
              value={model}
              onChange={(e) => setModel(e.target.value)}
              placeholder="e.g., gpt-4, claude-3-opus"
              className="w-full px-4 py-2 border border-[#629FAD]/30 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#296374]"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-[#0C2C55] mb-2">Display Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., Primary GPT-4"
              className="w-full px-4 py-2 border border-[#629FAD]/30 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#296374]"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-[#0C2C55] mb-2">API Key</label>
            <input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="sk-..."
              className="w-full px-4 py-2 border border-[#629FAD]/30 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#296374]"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-[#0C2C55] mb-2">Daily Token Limit</label>
            <input
              type="number"
              value={dailyLimit}
              onChange={(e) => setDailyLimit(e.target.value)}
              className="w-full px-4 py-2 border border-[#629FAD]/30 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#296374]"
            />
          </div>
        </div>

        <div className="flex gap-3 p-6 border-t border-[#629FAD]/30">
          <button
            onClick={onClose}
            className="flex-1 px-4 py-2 bg-white text-[#0C2C55] border border-[#629FAD]/30 rounded-lg hover:bg-[#EDEDCE]/50 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={!provider || !model || !name || !apiKey}
            className="flex-1 px-4 py-2 bg-[#0C2C55] text-[#EDEDCE] rounded-lg hover:bg-[#0C2C55]/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Add LLM
          </button>
        </div>
      </div>
    </div>
  );
}