import React, { createContext, useContext, useState, useEffect, ReactNode, useCallback } from 'react';
import { documentProcessingAPI } from '../services/api';
import { ProcessingJob } from '../services/api.types';
import { useAuth } from './AuthContext.v2';
import { Icons } from '../components/icons';
import { X, CheckCircle, ChevronUp } from 'lucide-react';

interface JobContextType {
    jobs: ProcessingJob[];
    addJob: (jobId: string, filename: string, kbName: string) => void;
    removeJob: (jobId: string) => void;
}

const JobContext = createContext<JobContextType | undefined>(undefined);

export const useJobs = () => {
    const context = useContext(JobContext);
    if (!context) throw new Error('useJobs must be used within a JobProvider');
    return context;
};

export const JobProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
    const { isAuthenticated } = useAuth();
    const [jobs, setJobs] = useState<ProcessingJob[]>([]);

    // Periodically poll active jobs
    useEffect(() => {
        if (!isAuthenticated) return;

        let timeoutId: ReturnType<typeof setTimeout>;

        const pollJobs = async () => {
            // Find all active jobs directly from context state
            setJobs(currentJobs => {
                const activeJobs = currentJobs.filter(j => j.status === 'pending' || j.status === 'in_progress');

                if (activeJobs.length > 0) {
                    activeJobs.forEach(async (job) => {
                        try {
                            const status = await documentProcessingAPI.getProcessingStatus(job.job_id) as ProcessingJob;
                            setJobs(prev => prev.map(j => j.job_id === job.job_id ? { ...j, ...status } : j));
                        } catch (error) {
                            console.error(`Failed to poll job ${job.job_id}`, error);
                        }
                    });
                }

                return currentJobs;
            });

            timeoutId = setTimeout(pollJobs, 2000);
        };

        pollJobs();

        return () => clearTimeout(timeoutId);
    }, [isAuthenticated]);

    const addJob = useCallback((jobId: string, filename: string, kbName: string) => {
        setJobs(prev => {
            if (prev.some(j => j.job_id === jobId)) return prev;
            return [...prev, {
                job_id: jobId,
                file_path: filename,
                collection_name: kbName,
                status: 'in_progress',
                progress_message: 'Initializing...',
                created_at: new Date().toISOString()
            }];
        });
    }, []);

    const removeJob = useCallback((jobId: string) => {
        setJobs(prev => prev.filter(j => j.job_id !== jobId));
    }, []);

    return (
        <JobContext.Provider value={{ jobs, addJob, removeJob }}>
            {children}
            <JobTracker />
        </JobContext.Provider>
    );
};

const JobTracker = () => {
    const { jobs, removeJob } = useJobs();
    const [isExpanded, setIsExpanded] = useState(false);

    // Auto-expand when a new job starts processing, and optionally auto-dismiss
    useEffect(() => {
        const inProgress = jobs.filter(j => j.status === 'pending' || j.status === 'in_progress');
        if (inProgress.length > 0 && !isExpanded) {
            // Optional: Auto-expand on new job: setIsExpanded(true); 
            // Keeping it collapsed by default might be less intrusive based on user request.
        }

        // Removed auto-dismissing to continuously show job status. User can manually dismiss them.
    }, [jobs, isExpanded, removeJob]);

    if (jobs.length === 0) return null;

    const inProgress = jobs.filter(j => j.status === 'pending' || j.status === 'in_progress');
    const hasActive = inProgress.length > 0;

    return (
        <div className="fixed bottom-6 right-6 z-50 flex flex-col items-end gap-2 text-text">
            {isExpanded ? (
                <div className="bg-surface border border-border rounded-xl shadow-2xl p-4 w-80 max-h-96 flex flex-col overflow-hidden animate-in fade-in slide-in-from-bottom-2">
                    <div className="flex justify-between items-center border-b border-border/50 pb-3 mb-3">
                        <h3 className="text-sm font-bold flex items-center gap-2">
                            {hasActive ? <Icons.Spinner className="w-4 h-4 animate-spin text-primary" /> : <CheckCircle className="w-4 h-4 text-success" />}
                            Uploads ({jobs.length})
                        </h3>
                        <button onClick={() => setIsExpanded(false)} className="text-text-secondary hover:text-text p-1 translate-x-1">
                            <X className="w-4 h-4" />
                        </button>
                    </div>

                    <div className="overflow-y-auto space-y-3 custom-scrollbar pr-1 flex-1">
                        {jobs.map(job => (
                            <div key={job.job_id} className="flex flex-col gap-1 p-2 bg-background rounded-lg border border-border/50">
                                <div className="flex justify-between items-start text-sm">
                                    <span className="font-medium truncate pr-2 flex-1 text-xs" title={job.file_path}>
                                        {job.file_path?.split('/').pop() || job.file_path}
                                    </span>
                                    {job.status === 'pending' || job.status === 'in_progress' ? (
                                        <Icons.Spinner className="w-3.5 h-3.5 text-primary animate-spin shrink-0 mt-0.5" />
                                    ) : job.status === 'completed' ? (
                                        <CheckCircle className="w-3.5 h-3.5 text-success shrink-0 mt-0.5" />
                                    ) : (
                                        <button onClick={() => removeJob(job.job_id)} className="text-text-secondary hover:text-text shrink-0">
                                            <X className="w-3.5 h-3.5 mt-0.5" />
                                        </button>
                                    )}
                                </div>
                                <div className="text-[10px] text-text-secondary line-clamp-2">
                                    {job.status === 'completed' ? 'Processing finished successfully' :
                                        job.status === 'failed' ? (
                                            <span className="text-error">{job.error_message || job.error || 'Processing failed'}</span>
                                        ) :
                                            (job.progress_message || 'Processing...')}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            ) : (
                <button
                    onClick={() => setIsExpanded(true)}
                    className="bg-surface hover:bg-surface-hover border border-border rounded-full shadow-lg px-4 py-2 flex items-center gap-3 transition-colors group animate-in slide-in-from-bottom-5"
                >
                    {hasActive ? (
                        <Icons.Spinner className="w-4 h-4 text-primary animate-spin" />
                    ) : (
                        <CheckCircle className="w-4 h-4 text-success" />
                    )}
                    <span className="text-sm font-medium">
                        {hasActive
                            ? `Processing ${inProgress.length} file${inProgress.length !== 1 ? 's' : ''}...`
                            : `Uploads complete`}
                    </span>
                    <ChevronUp className="w-4 h-4 opacity-50 group-hover:opacity-100 transition-opacity" />
                </button>
            )}
        </div>
    );
};
