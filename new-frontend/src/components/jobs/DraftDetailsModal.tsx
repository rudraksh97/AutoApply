import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import { Code, RefreshCw } from "lucide-react";
import { cn } from "@/lib/utils";

export interface DraftField {
    xpath: string;
    field_type: string;
    label: string | null;
    options: string[] | null;
    value: string | null;
    confidence: number;
    required: boolean;
    skipped: boolean;
    skip_reason: string | null;
}

export interface DraftFormState {
    version: string;
    job_url: string;
    page_index: number;
    fields: DraftField[];
    extracted_at: string;
    last_modified: string;
}

export interface FullDraft {
    id: string;
    job_url: string;
    apply_link?: string | null;
    status: string;
    form_state: DraftFormState;
    resume_path: string | null;
    job_details: string | null;
    initial_ats_score: number | null;
    current_ats_score?: number | null;
    created_at: string;
    updated_at: string;
}

interface DraftDetailsModalProps {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    draft: FullDraft | null;
    isOpen: boolean;
    onClose: () => void;
    loading?: boolean;
}

export function DraftDetailsModal({ draft, isOpen, onClose, loading }: DraftDetailsModalProps) {
    return (
        <Dialog open={isOpen} onOpenChange={onClose}>
            <DialogContent className="max-w-6xl max-h-[90vh] flex flex-col bg-white">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2 text-[#0C2C55]">
                        <Code className="h-5 w-5" />
                        Extracted Form Data
                    </DialogTitle>
                </DialogHeader>

                {loading ? (
                    <div className="flex items-center justify-center py-12">
                        <RefreshCw className="h-6 w-6 animate-spin text-[#629FAD]" />
                    </div>
                ) : draft ? (
                    <div className="flex-1 overflow-hidden flex flex-col gap-4">
                        {/* Summary */}
                        <div className="grid grid-cols-4 gap-4 text-sm">
                            <div className="bg-[#E8E2DB]/30 rounded-lg p-3 border border-[#629FAD]/20">
                                <div className="text-[#296374] text-xs uppercase tracking-wide mb-1">Status</div>
                                <div className="font-medium text-[#0C2C55]">{draft.status}</div>
                            </div>
                            <div className="bg-[#E8E2DB]/30 rounded-lg p-3 border border-[#629FAD]/20">
                                <div className="text-[#296374] text-xs uppercase tracking-wide mb-1">Total Fields</div>
                                <div className="font-medium text-[#0C2C55]">{draft.form_state?.fields?.length || 0}</div>
                            </div>
                            <div className="bg-[#E8E2DB]/30 rounded-lg p-3 border border-[#629FAD]/20">
                                <div className="text-[#296374] text-xs uppercase tracking-wide mb-1">Filled Fields</div>
                                <div className="font-medium text-[#0C2C55]">
                                    {draft.form_state?.fields?.filter(f => f.value && !f.skipped).length || 0}
                                </div>
                            </div>
                            <div className="bg-[#E8E2DB]/30 rounded-lg p-3 border border-[#629FAD]/20">
                                <div className="text-[#296374] text-xs uppercase tracking-wide mb-1">Skipped Fields</div>
                                <div className="font-medium text-[#0C2C55]">
                                    {draft.form_state?.fields?.filter(f => f.skipped).length || 0}
                                </div>
                            </div>
                        </div>

                        {/* Fields Table */}
                        {draft.form_state?.fields && draft.form_state.fields.length > 0 && (
                            <div className="flex-1 border border-[#629FAD]/20 rounded-lg overflow-hidden flex flex-col min-h-0 bg-white shadow-sm">
                                <div className="bg-[#E8E2DB]/20 px-4 py-2 text-xs font-semibold uppercase tracking-wide border-b border-[#629FAD]/20 text-[#0C2C55]">
                                    Form Fields
                                </div>
                                <div className="flex-1 overflow-auto">
                                    <table className="w-full text-sm">
                                        <thead className="bg-[#E8E2DB]/40 text-xs sticky top-0 z-10">
                                            <tr>
                                                <th className="px-3 py-2 text-left whitespace-nowrap text-[#296374]">Label</th>
                                                <th className="px-3 py-2 text-left whitespace-nowrap text-[#296374]">Type</th>
                                                <th className="px-3 py-2 text-left whitespace-nowrap text-[#296374]">Value</th>
                                                <th className="px-3 py-2 text-left whitespace-nowrap text-[#296374]">Options</th>
                                                <th className="px-3 py-2 text-center whitespace-nowrap text-[#296374]">Confidence</th>
                                                <th className="px-3 py-2 text-center whitespace-nowrap text-[#296374]">Required</th>
                                                <th className="px-3 py-2 text-center whitespace-nowrap text-[#296374]">Skipped</th>
                                                <th className="px-3 py-2 text-left whitespace-nowrap text-[#296374]">Skip Reason</th>
                                                <th className="px-3 py-2 text-left whitespace-nowrap text-[#296374]">XPath</th>
                                            </tr>
                                        </thead>
                                        <tbody className="divide-y divide-[#629FAD]/10">
                                            {draft.form_state.fields.map((field, i) => (
                                                <tr key={i} className={cn(
                                                    "hover:bg-[#E8E2DB]/20 transition-colors",
                                                    field.skipped && "bg-yellow-50/50"
                                                )}>
                                                    <td className="px-3 py-2 font-medium whitespace-nowrap text-[#0C2C55]">
                                                        {field.label || <span className="text-muted-foreground italic">No label</span>}
                                                    </td>
                                                    <td className="px-3 py-2 text-[#296374] whitespace-nowrap">{field.field_type}</td>
                                                    <td className="px-3 py-2">
                                                        {field.value ? (
                                                            <span className="text-emerald-700 truncate block max-w-[200px]" title={field.value}>
                                                                {field.value}
                                                            </span>
                                                        ) : (
                                                            <span className="text-[#296374]/50 italic">Empty</span>
                                                        )}
                                                    </td>
                                                    <td className="px-3 py-2 text-xs text-[#296374]">
                                                        {field.options && field.options.length > 0 ? (
                                                            <span className="truncate block max-w-[150px]" title={field.options.join(', ')}>
                                                                {field.options.slice(0, 3).join(', ')}{field.options.length > 3 && '...'}
                                                            </span>
                                                        ) : (
                                                            <span className="opacity-40">--</span>
                                                        )}
                                                    </td>
                                                    <td className="px-3 py-2 text-center">
                                                        <span className={cn(
                                                            "text-xs font-medium",
                                                            field.confidence >= 0.8 ? "text-emerald-600" :
                                                                field.confidence >= 0.5 ? "text-yellow-600" : "text-red-600"
                                                        )}>
                                                            {(field.confidence * 100).toFixed(0)}%
                                                        </span>
                                                    </td>
                                                    <td className="px-3 py-2 text-center">
                                                        {field.required ? (
                                                            <span className="text-red-500 font-bold text-xs">Yes</span>
                                                        ) : (
                                                            <span className="opacity-40 text-xs">No</span>
                                                        )}
                                                    </td>
                                                    <td className="px-3 py-2 text-center">
                                                        {field.skipped ? (
                                                            <span className="text-yellow-600 font-bold text-xs">Yes</span>
                                                        ) : (
                                                            <span className="opacity-40 text-xs">No</span>
                                                        )}
                                                    </td>
                                                    <td className="px-3 py-2 text-xs text-yellow-600">
                                                        {field.skip_reason || <span className="opacity-40">--</span>}
                                                    </td>
                                                    <td className="px-3 py-2 text-xs text-[#296374] font-mono truncate max-w-[150px]" title={field.xpath}>
                                                        {field.xpath}
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        )}
                    </div>
                ) : (
                    <div className="text-center py-8 text-[#296374]">
                        No draft data available
                    </div>
                )}
            </DialogContent>
        </Dialog>
    );
}
