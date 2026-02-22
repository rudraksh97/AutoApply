export interface Job {
    id: string;
    user_id: string;
    feed_id?: string;
    company: string;
    role: string;
    status: string; // APPLIED, PENDING, FAILED
    url: string;
    created_at: string;

    // Legacy/Parity
    pdf_path?: string;
    details?: string;
    error_message?: string;
    sent?: boolean;
    retry_count?: number;
    apply_link?: string;
}
