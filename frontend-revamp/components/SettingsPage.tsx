"use client";
import { useState } from 'react';
import { Plus, Trash2, Settings as SettingsIcon, CheckCircle, XCircle, X } from 'lucide-react';
import { AddLlmDialog } from './AddLlmDialog';

interface LLM {
  id: string;
  provider: string;
  model: string;
  name: string;
  apiKey: string;
  dailyLimit: number;
  used: number;
}

interface WorkflowTask {
  id: string;
  name: string;
  assignedLLMs: string[];
}

export function SettingsPage() {
  const [showAddLlm, setShowAddLlm] = useState(false);
  const [llms, setLlms] = useState<LLM[]>([
    {
      id: '1',
      provider: 'OpenAI',
      model: 'gpt-4',
      name: 'Primary GPT-4',
      apiKey: 'sk-...abc123',
      dailyLimit: 1000000,
      used: 245000
    },
    {
      id: '2',
      provider: 'Anthropic',
      model: 'claude-3-opus',
      name: 'Claude Opus',
      apiKey: 'sk-...xyz789',
      dailyLimit: 500000,
      used: 120000
    }
  ]);

  const [workflowTasks, setWorkflowTasks] = useState<WorkflowTask[]>([
    { id: '1', name: 'Score Resume', assignedLLMs: ['1'] },
    { id: '2', name: 'Tailor Resume', assignedLLMs: ['1', '2'] },
    { id: '3', name: 'Extract Job Details', assignedLLMs: ['2'] },
    { id: '4', name: 'Fill Application Form', assignedLLMs: ['1'] }
  ]);

  const [extensionConnected, setExtensionConnected] = useState(true);

  const deleteLLM = (id: string) => {
    setLlms(llms.filter(llm => llm.id !== id));
  };

  const toggleLLMForTask = (taskId: string, llmId: string) => {
    setWorkflowTasks(workflowTasks.map(task => {
      if (task.id === taskId) {
        const assigned = task.assignedLLMs.includes(llmId)
          ? task.assignedLLMs.filter(id => id !== llmId)
          : [...task.assignedLLMs, llmId];
        return { ...task, assignedLLMs: assigned };
      }
      return task;
    }));
  };

  const addLLMToTask = (taskId: string, llmId: string) => {
    if (!llmId) return;
    setWorkflowTasks(workflowTasks.map(task => {
      if (task.id === taskId && !task.assignedLLMs.includes(llmId)) {
        return { ...task, assignedLLMs: [...task.assignedLLMs, llmId] };
      }
      return task;
    }));
  };

  const removeLLMFromTask = (taskId: string, llmId: string) => {
    setWorkflowTasks(workflowTasks.map(task => {
      if (task.id === taskId) {
        return { ...task, assignedLLMs: task.assignedLLMs.filter(id => id !== llmId) };
      }
      return task;
    }));
  };

  const getLLMName = (id: string) => {
    return llms.find(llm => llm.id === id)?.name || 'Unknown';
  };

  const getLLM = (id: string) => {
    return llms.find(llm => llm.id === id);
  };

  return (
    <div className="p-8">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <h1 className="text-3xl font-semibold text-[#0C2C55] mb-8">Settings</h1>

        {/* Extension Status */}
        <div className="bg-[#629FAD]/10 border border-[#629FAD]/30 rounded-lg p-6 mb-6">
          <div className="flex items-start justify-between">
            <div className="flex items-start gap-4">
              <div className={`p-3 rounded-lg ${
                extensionConnected ? 'bg-[#629FAD]/20' : 'bg-red-200/50'
              }`}>
                {extensionConnected ? (
                  <CheckCircle className="w-6 h-6 text-[#296374]" />
                ) : (
                  <XCircle className="w-6 h-6 text-red-600" />
                )}
              </div>
              <div>
                <h3 className="font-semibold text-[#0C2C55]">
                  {extensionConnected ? 'Extension Connected' : 'Extension Disconnected'}
                </h3>
                <p className="text-sm text-[#296374] mt-1">
                  {extensionConnected 
                    ? 'Chrome extension is communicating successfully' 
                    : 'Please install or enable the Chrome extension'
                  }
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* LLM Inventory */}
        <div className="bg-white rounded-lg border border-[#629FAD]/30 p-6 mb-6 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-[#0C2C55]">LLM Inventory</h2>
            <button
              onClick={() => setShowAddLlm(true)}
              className="flex items-center gap-2 px-4 py-2 bg-[#0C2C55] text-[#E8E2DB] rounded-lg hover:bg-[#0C2C55]/90 transition-colors"
            >
              <Plus className="w-4 h-4" />
              Add LLM
            </button>
          </div>

          <div className="space-y-4">
            {llms.map((llm) => {
              const usagePercent = (llm.used / llm.dailyLimit) * 100;
              return (
                <div key={llm.id} className="border border-[#629FAD]/30 rounded-lg p-4">
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <h3 className="font-semibold text-[#0C2C55]">{llm.name}</h3>
                      <p className="text-sm text-[#296374]">{llm.provider} - {llm.model}</p>
                      <p className="text-xs text-[#629FAD] mt-1 font-mono">{llm.apiKey}</p>
                    </div>
                    <button
                      onClick={() => deleteLLM(llm.id)}
                      className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                  
                  <div>
                    <div className="flex items-center justify-between text-sm mb-1">
                      <span className="text-[#296374]">Daily Token Usage</span>
                      <span className="font-medium text-[#0C2C55]">
                        {llm.used.toLocaleString()} / {llm.dailyLimit.toLocaleString()}
                      </span>
                    </div>
                    <div className="w-full bg-[#E8E2DB]/50 rounded-full h-2">
                      <div
                        className={`h-2 rounded-full transition-all ${
                          usagePercent > 90 ? 'bg-red-600' : usagePercent > 70 ? 'bg-[#629FAD]' : 'bg-[#0C2C55]'
                        }`}
                        style={{ width: `${Math.min(usagePercent, 100)}%` }}
                      />
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Workflow Configuration */}
        <div className="bg-white rounded-lg border border-[#629FAD]/30 p-6 shadow-sm">
          <div className="flex items-center gap-2 mb-4">
            <SettingsIcon className="w-5 h-5 text-[#296374]" />
            <h2 className="text-lg font-semibold text-[#0C2C55]">Workflow Configuration</h2>
          </div>
          <p className="text-sm text-[#296374] mb-6">
            Assign LLM models to specific workflow tasks. Multiple LLMs can be assigned for load balancing.
          </p>

          <div className="space-y-4">
            {workflowTasks.map((task) => {
              const availableLLMs = llms.filter(llm => !task.assignedLLMs.includes(llm.id));
              
              return (
                <div key={task.id} className="border border-[#629FAD]/30 rounded-lg p-4">
                  <h3 className="font-medium text-[#0C2C55] mb-3">{task.name}</h3>
                  
                  {/* Dropdown to add LLMs */}
                  <div className="mb-3">
                    <select
                      onChange={(e) => {
                        addLLMToTask(task.id, e.target.value);
                        e.target.value = ''; // Reset dropdown
                      }}
                      className="w-full px-4 py-2 border border-[#629FAD]/30 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#296374] bg-white"
                      defaultValue=""
                    >
                      <option value="" disabled>
                        {availableLLMs.length > 0 ? 'Select model to add...' : 'All models assigned'}
                      </option>
                      {availableLLMs.map((llm) => (
                        <option key={llm.id} value={llm.id}>
                          {llm.name} ({llm.provider} - {llm.model})
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Assigned LLMs as Cards/Chips */}
                  {task.assignedLLMs.length > 0 ? (
                    <div className="space-y-2">
                      <p className="text-xs font-medium text-[#296374] mb-2">Assigned Models:</p>
                      <div className="flex flex-wrap gap-2">
                        {task.assignedLLMs.map((llmId) => {
                          const llm = getLLM(llmId);
                          if (!llm) return null;
                          
                          return (
                            <div
                              key={llmId}
                              className="flex items-center gap-2 px-3 py-2 bg-[#0C2C55]/10 border border-[#0C2C55]/20 rounded-lg group hover:bg-[#0C2C55]/20 transition-colors"
                            >
                              <div className="flex-1">
                                <div className="text-sm font-medium text-[#0C2C55]">{llm.name}</div>
                                <div className="text-xs text-[#296374]">{llm.provider} - {llm.model}</div>
                              </div>
                              <button
                                onClick={() => removeLLMFromTask(task.id, llmId)}
                                className="p-1 text-[#296374] hover:text-red-600 hover:bg-red-50 rounded transition-colors"
                                title="Remove model"
                              >
                                <X className="w-4 h-4" />
                              </button>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  ) : (
                    <div className="text-center py-4 text-sm text-[#629FAD] bg-[#E8E2DB]/30 rounded-lg border border-[#629FAD]/30 border-dashed">
                      No models assigned. Select a model from the dropdown above.
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Add LLM Dialog */}
      {showAddLlm && (
        <AddLlmDialog
          onClose={() => setShowAddLlm(false)}
          onAdd={(newLlm) => {
            setLlms([...llms, { ...newLlm, id: Date.now().toString(), used: 0 }]);
            setShowAddLlm(false);
          }}
        />
      )}
    </div>
  );
}