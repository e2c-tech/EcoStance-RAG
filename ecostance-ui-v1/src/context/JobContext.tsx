import React, { createContext, useContext, useState, useEffect, ReactNode, useCallback } from 'react';
import { documentProcessingAPI } from '../services/api';
import { ProcessingJob } from '../services/api.types';
import { useAuth } from './AuthContext.v2';
import { Icons } from '../components/icons';
import { X, CheckCircle, AlertCircle } from 'lucide-react';

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

    if (jobs.length === 0) return null;

    return (
        <div className="fixed bottom-6 right-6 z-50 flex flex-col gap-2 max-w-sm w-full">
            {jobs.map(job => (
                <div key={job.job_id} className="bg-surface border border-border rounded-lg shadow-lg p-3 flex items-start gap-3 w-full">
                    <div className="pt-0.5">
                        {job.status === 'pending' || job.status === 'in_progress' ? (
                            <Icons.Spinner className="w-5 h-5 text-primary animate-spin" />
                        ) : job.status === 'completed' ? (
                            <CheckCircle className="w-5 h-5 text-success" />
                        ) : (
                            <AlertCircle className="w-5 h-5 text-error" />
                        )}
                    </div>
                    <div className="flex-1 min-w-0">
                        <div className="flex justify-between items-start">
                            <p className="text-sm font-medium text-text truncate pr-2" title={job.file_path}>
                                {job.file_path?.split('/').pop() || job.file_path}
                            </p>
                            {(job.status === 'completed' || job.status === 'failed') && (
                                <button onClick={() => removeJob(job.job_id)} className="text-text-secondary hover:text-text shrink-0">
                                    <X className="w-4 h-4" />
                                </button>
                            )}
                        </div>
                        <p className="text-xs text-text-secondary line-clamp-2 mt-0.5">
                            {job.status === 'completed' ? 'Processing finished successfully' :
                                job.status === 'failed' ? (job.error_message || job.error || 'Processing failed') :
                                    (job.progress_message || 'Processing...')}
                        </p>
                    </div>
                </div>
            ))}
        </div>
    );
};
