import React, { useState } from 'react';
import { useParams } from 'react-router-dom';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Card } from '../components/ui/Card';
import { Icons } from '../components/icons';
import { Badge } from '../components/ui/Badge';
import { Link } from 'react-router-dom';
import { AlertCircle, CheckCircle, X } from 'lucide-react';
import { DocumentsTable, Document } from '../components/DocumentsTable';
import { useKnowledgeBase } from '../hooks/useKnowledgeBase';
import { useJobs } from '../context/JobContext';
import { filesAPI, documentProcessingAPI } from '../services/api';

interface KnowledgeBase {
  id: string;
  name: string;
  status: "Ready" | "Processing" | "Error";
  lastUpdated: string;
  totalVectors: number;
  documents: number;
  vectorSize: number;
  totalChunks: number;
  documentData: Document[];
}



const mapFileType = (mimeType: string | undefined): any => {
  const type = (mimeType || '').toLowerCase();
  if (type.includes('pdf')) return 'pdf';
  if (type.includes('word') || type.includes('docx') || type.includes('doc')) return 'docx';
  if (type.includes('text') || type.includes('txt')) return 'txt';
  if (type.includes('csv')) return 'csv';
  if (type.includes('json')) return 'json';
  if (type.includes('wav')) return 'wav';
  if (type.includes('mp3')) return 'mp3';
  if (type.includes('m4a')) return 'm4a';
  if (type.includes('ogg')) return 'ogg';
  if (type.includes('audio')) return 'audio';
  if (type.includes('markdown') || type.includes('md')) return 'md';
  return 'unknown';
};

const KnowledgeBaseDetailsPage: React.FC = () => {
  const { kbId } = useParams<{ kbId: string }>();
  const [knowledgeBase, setKnowledgeBase] = useState<KnowledgeBase | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isEditingKbName, setIsEditingKbName] = useState(false);
  const [kbName, setKbName] = useState(knowledgeBase?.name || "");
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [progressMessage, setProgressMessage] = useState<string>("");
  const fileInputRef = React.useRef<HTMLInputElement>(null);

  const { getKBDetails, deleteFileFromKB } = useKnowledgeBase();
  const { addJob, removeJob, jobs } = useJobs();
  const prevJobsRef = React.useRef(jobs);

  const fetchKBData = React.useCallback(async (force = false, silent = false) => {
    if (!silent) setIsLoading(true);
    try {
      const data = await getKBDetails(kbId!, force);
      console.log('KB Details API Response:', data);

      if (data) {
        // Calculate total chunks from all files
        const totalChunks = (data.files || []).reduce((sum: number, file: any) => {
          return sum + (file.chunk_count || 0);
        }, 0);

        console.log('Calculated total chunks:', totalChunks);

        // Transform API response to match our interface
        const transformedKB: KnowledgeBase = {
          id: kbId!,
          name: data.name || kbId!,
          status: 'Ready',
          lastUpdated: new Date().toISOString(),
          totalVectors: data.vectors_count || data.total_points || 0,
          documents: data.files_count || 0,
          vectorSize: data.vector_size || 1536,
          totalChunks: totalChunks,
          documentData: (data.files || []).map((file: any) => ({
            id: file.filename,
            filename: file.filename,
            fileType: mapFileType(file.file_type),
            uploadDate: file.upload_date || new Date().toISOString(),
            chunks: file.chunk_count || 0,
            fileSize: file.file_size_mb || 'Unknown',
            characters: file.total_characters || 0,
            status: 'Indexed',
            filePath: file.filename,
            processingDate: file.processing_date || file.upload_date || new Date().toISOString(),
            chunkSize: 512,
            embeddingModel: 'text-embedding-ada-002',
            processingDuration: '0s',
            firstChunkPreview: '',
          })),
        };
        setKnowledgeBase(transformedKB);
        setKbName(transformedKB.name);
      } else {
        // KB exists but is empty - create a minimal KB object
        setKnowledgeBase({
          id: kbId!,
          name: kbId!,
          status: 'Ready',
          lastUpdated: new Date().toISOString(),
          totalVectors: 0,
          documents: 0,
          vectorSize: 1536,
          totalChunks: 0,
          documentData: [],
        });
        setKbName(kbId!);
      }
    } catch (err) {
      console.error('Error fetching KB data:', err);
      // KB might be newly created and empty - don't show error
      setKnowledgeBase({
        id: kbId!,
        name: kbId!,
        status: 'Ready',
        lastUpdated: new Date().toISOString(),
        totalVectors: 0,
        documents: 0,
        vectorSize: 1536,
        totalChunks: 0,
        documentData: [],
      });
      setKbName(kbId!);
    } finally {
      setIsLoading(false);
    }
  }, [kbId, getKBDetails]);

  React.useEffect(() => {
    fetchKBData(false, false);
  }, [fetchKBData]);

  React.useEffect(() => {
    if (knowledgeBase) {
      setKbName(knowledgeBase.name);
    }
  }, [knowledgeBase]);

  React.useEffect(() => {
    // Check if any job for this KB transitioned to 'completed'
    const newlyCompleted = jobs.some(currentJob => {
      const prevJob = prevJobsRef.current.find(j => j.job_id === currentJob.job_id);
      return currentJob.collection_name === kbId &&
        currentJob.status === 'completed' &&
        (!prevJob || prevJob.status !== 'completed');
    });

    if (newlyCompleted) {
      fetchKBData(true, true); // Use silent refresh to avoid full page flicker
    }
    prevJobsRef.current = jobs;
  }, [jobs, kbId, fetchKBData]);

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-screen w-full">
        <Icons.Spinner className="h-10 w-10 animate-spin text-primary" />
      </div>
    );
  }

  if (!knowledgeBase) {
    return null;
  }

  const handleNameChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setKbName(e.target.value);
  };

  const handleNameBlur = () => {
    setIsEditingKbName(false);
    console.log("KB Name updated to:", kbName);
  };

  const handleNameKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      e.currentTarget.blur();
    }
  };

  const formatNumber = (num: number) => {
    return num.toLocaleString();
  };

  const getStatusBadgeVariant = (status: KnowledgeBase['status']) => {
    switch (status) {
      case "Ready":
        return "default";
      case "Processing":
        return "secondary";
      case "Error":
        return "destructive";
      default:
        return "outline";
    }
  };

  const handleDownload = (doc: Document) => {
    console.log('Downloading document:', doc.filename);
  };

  const handleReindex = (doc: Document) => {
    console.log('Reindexing document:', doc.filename);
  };

  const handleDelete = async (doc: Document) => {
    console.log('Deleting document:', doc.filename);

    if (!confirm(`Are you sure you want to delete "${doc.filename}"?`)) {
      return;
    }

    try {
      setIsUploading(true); // Reuse loading state
      setUploadError(null);

      // Call the delete API
      await deleteFileFromKB(kbId!, doc.filename);

      // Refresh the KB details to update the list
      await fetchKBData(true);
    } catch (error) {
      console.error('Delete failed:', error);
      const errorMessage = error instanceof Error ? error.message : 'Failed to delete document';
      setUploadError(errorMessage);
    } finally {
      setIsUploading(false);
    }
  };

  const handleBulkReindex = (docs: Document[]) => {
    console.log('Bulk reindexing documents:', docs.length);
  };

  const handleBulkDelete = async (docs: Document[]) => {
    console.log('Bulk deleting documents:', docs.length);

    if (!confirm(`Are you sure you want to delete ${docs.length} document(s)?`)) {
      return;
    }

    try {
      setIsUploading(true);
      setUploadError(null);

      // Delete all selected documents
      await Promise.all(
        docs.map(doc => deleteFileFromKB(kbId!, doc.filename))
      );

      // Refresh the KB details to update the list
      await fetchKBData(true);
    } catch (error) {
      console.error('Bulk delete failed:', error);
      const errorMessage = error instanceof Error ? error.message : 'Failed to delete documents';
      setUploadError(errorMessage);
    } finally {
      setIsUploading(false);
    }
  };

  const handleUpload = () => {
    // Trigger file input click
    fileInputRef.current?.click();
  };

  const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    setUploadError(null);
    setProgressMessage(`Uploading ${file.name} to server...`);

    try {
      // 1. Upload the file without triggering processing yet
      const uploadRes = await filesAPI.upload(file, false, kbId!) as any;

      setProgressMessage(`Starting background processing for ${file.name}...`);

      // 2. Trigger processing as a background job
      const processRes = await documentProcessingAPI.processToKnowledgeBase(file.name, kbId!) as any;

      if (processRes && processRes.job_id) {
        addJob(processRes.job_id, file.name, kbId!);
      } else if (uploadRes && uploadRes.job_id) {
        // Fallback if backend still returns it from the upload endpoint
        addJob(uploadRes.job_id, file.name, kbId!);
      } else {
        // Fallback for old backend behavior
        fetchKBData(true);
      }

      // Hide the initial banner - the JobContext will take over polling the status
      setIsUploading(false);
      setProgressMessage("");

      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    } catch (error) {
      console.error('Upload failed:', error);
      const errorMessage = error instanceof Error ? error.message : 'Failed to upload document';
      setUploadError(errorMessage);
      setIsUploading(false);
      setProgressMessage("");
    }
  };

  return (
    <div className="container mx-auto py-8">
      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,.doc,.docx,.txt,.csv,.json,.md,.wav,.mp3,.m4a,.ogg"
        onChange={handleFileChange}
        style={{ display: 'none' }}
      />

      <div className="mb-6">
        <nav className="text-sm text-text-secondary mb-2">
          <Link to="/" className="hover:underline hover:text-text">Home</Link> &gt;
          <Link to="/knowledge-base" className="hover:underline hover:text-text">Knowledge Bases</Link> &gt;
          <span className="text-text">{knowledgeBase.name}</span>
        </nav>
        <div className="flex items-center space-x-3">
          {isEditingKbName ? (
            <Input
              value={kbName}
              onChange={handleNameChange}
              onBlur={handleNameBlur}
              onKeyDown={handleNameKeyDown}
              className="text-3xl font-bold p-1"
              autoFocus
            />
          ) : (
            <h1
              className="text-3xl font-bold text-text cursor-pointer hover:text-primary"
              onClick={() => setIsEditingKbName(true)}
            >
              {knowledgeBase.name}
            </h1>
          )}
          <Badge variant={getStatusBadgeVariant(knowledgeBase.status)}>{knowledgeBase.status}</Badge>
        </div>
        <p className="text-text-secondary text-sm mt-1">
          Last updated: {new Date(knowledgeBase.lastUpdated).toLocaleString()}
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <Card className="p-4 flex items-center justify-between">
          <div>
            <p className="text-sm text-text-secondary">Total Vectors</p>
            <p className="text-2xl font-bold text-text">{formatNumber(knowledgeBase.totalVectors)}</p>
          </div>
          <Icons.Hash className="h-8 w-8 text-text-secondary" />
        </Card>
        <Card className="p-4 flex items-center justify-between">
          <div>
            <p className="text-sm text-text-secondary">Documents</p>
            <p className="text-2xl font-bold text-text">{knowledgeBase.documents}</p>
          </div>
          <Icons.FileStack className="h-8 w-8 text-text-secondary" />
        </Card>
        <Card className="p-4 flex items-center justify-between">
          <div>
            <p className="text-sm text-text-secondary">Vector Size</p>
            <p className="text-2xl font-bold text-text">{knowledgeBase.vectorSize}</p>
          </div>
          <Icons.Maximize className="h-8 w-8 text-text-secondary" />
        </Card>
        <Card className="p-4 flex items-center justify-between">
          <div>
            <p className="text-sm text-text-secondary">Total Chunks</p>
            <p className="text-2xl font-bold text-text">{formatNumber(knowledgeBase.totalChunks)}</p>
          </div>
          <Icons.Blocks className="h-8 w-8 text-text-secondary" />
        </Card>
      </div>

      {uploadError && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4 mt-8" role="alert">
          <div className="flex items-center">
            <AlertCircle className="h-4 w-4 mr-2 shrink-0" />
            <span className="block sm:inline">{uploadError}</span>
          </div>
        </div>
      )}

      {isUploading && (
        <div className="bg-primary/5 border border-primary/20 text-primary px-4 py-3 rounded-lg mb-4 mt-8 flex items-center shadow-sm">
          <Icons.Spinner className="h-4 w-4 animate-spin mr-3 shrink-0" />
          <span className="font-medium text-sm">{progressMessage || "Uploading and processing document... "}</span>
        </div>
      )}

      {/* Show active and completed jobs from backend polling */}
      {jobs.filter(j =>
        j.collection_name?.toLowerCase() === kbId?.toLowerCase() ||
        j.collection_name === knowledgeBase?.name
      ).map(job => (
        <div
          key={job.job_id}
          className={`border px-4 py-3 xl:py-4 rounded-lg mb-4 shadow-sm flex items-center justify-between ${job.status === 'failed' ? 'bg-error/10 border-error/20 text-error' :
            job.status === 'completed' ? 'bg-success/10 border-success/20 text-success' :
              'bg-primary/5 border-primary/20 text-primary'
            }`}
          role="alert"
        >
          <div className="flex items-center flex-1 pr-4">
            {job.status === 'failed' ? (
              <AlertCircle className="h-5 w-5 mr-3 shrink-0" />
            ) : job.status === 'completed' ? (
              <CheckCircle className="h-5 w-5 mr-3 shrink-0" />
            ) : (
              <Icons.Spinner className="h-5 w-5 animate-spin mr-3 shrink-0" />
            )}
            <div className="flex flex-col flex-1">
              <span className="font-bold text-sm mb-0.5">{job.file_path}</span>
              <span className="text-xs opacity-80">
                {job.status === 'failed'
                  ? (job.error_message || job.error || 'Processing failed')
                  : job.status === 'completed'
                    ? 'Processing finished successfully'
                    : (job.progress_message || 'Processing...')}
              </span>
            </div>
          </div>

          <button
            onClick={() => removeJob(job.job_id)}
            className="p-1.5 hover:bg-black/10 rounded-md transition-colors shrink-0"
            title="Dismiss"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      ))}



      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-semibold text-text">Documents</h2>
        <Button onClick={handleUpload} disabled={isUploading}>
          {isUploading ? (
            <>
              <Icons.Spinner className="h-4 w-4 mr-2 animate-spin" />
              Uploading...
            </>
          ) : (
            <>
              <Icons.Upload className="h-4 w-4 mr-2" />
              Upload Document
            </>
          )}
        </Button>
      </div>

      <DocumentsTable
        documents={knowledgeBase.documentData}
        knowledgeBaseName={kbId}
        onDownload={handleDownload}
        onReindex={handleReindex}
        onDelete={handleDelete}
        onBulkReindex={handleBulkReindex}
        onBulkDelete={handleBulkDelete}
        onUpload={handleUpload}
      />
    </div>
  );
};

export default KnowledgeBaseDetailsPage;
