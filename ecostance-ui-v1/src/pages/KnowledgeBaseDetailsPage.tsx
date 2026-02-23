import React, { useState } from 'react';
import { useParams } from 'react-router-dom';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Card } from '../components/ui/Card';
import { Icons } from '../components/icons';
import { Badge } from '../components/ui/Badge';
import { Link } from 'react-router-dom';
import { DocumentsTable, Document } from '../components/DocumentsTable';
import { useKnowledgeBase } from '../hooks/useKnowledgeBase';
import { filesAPI, documentProcessingAPI } from '../services/api';
import { ProcessingJob } from '../services/api.types';

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

  const fetchKBData = React.useCallback(async (force = false) => {
    setIsLoading(true);
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
    fetchKBData();
  }, [fetchKBData]);

  React.useEffect(() => {
    if (knowledgeBase) {
      setKbName(knowledgeBase.name);
    }
  }, [knowledgeBase]);

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
    setProgressMessage("Uploading file...");

    try {
      // Unified call - upload and trigger processing immediately
      const res = await filesAPI.upload(file, true, kbId!) as any;

      if (res.job_id) {
        // Start polling the new status endpoint
        const pollStatus = async () => {
          try {
            const status = await documentProcessingAPI.getProcessingStatus(res.job_id) as ProcessingJob;
            setProgressMessage(status.progress_message || "Processing...");

            if (status.status === 'completed') {
              setIsUploading(false);
              setProgressMessage("");
              fetchKBData(true); // Reload the list
            } else if (status.status === 'failed') {
              setUploadError(status.error_message || status.error || "Processing failed");
              setIsUploading(false);
              setProgressMessage("");
            } else {
              setTimeout(pollStatus, 1000); // Poll every second
            }
          } catch (err) {
            console.error('Polling error:', err);
            setUploadError("Failed to get processing status");
            setIsUploading(false);
            setProgressMessage("");
          }
        };
        pollStatus();
      } else {
        // Fallback for when job_id is not returned (old backend behavior)
        setIsUploading(false);
        fetchKBData(true);
      }

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
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4" role="alert">
          <span className="block sm:inline">{uploadError}</span>
        </div>
      )}

      {isUploading && (
        <div className="bg-blue-50 border border-blue-200 text-blue-700 px-4 py-3 rounded mb-4" role="alert">
          <div className="flex items-center">
            <Icons.Spinner className="h-4 w-4 animate-spin mr-2" />
            <span>{progressMessage || "Uploading and processing document..."}</span>
          </div>
        </div>
      )}

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
