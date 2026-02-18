import { useState, useCallback } from 'react';
import { knowledgeBaseAPI, documentProcessingAPI, ragQueryAPI } from '../services/api';
import type { KnowledgeBaseDetails, ProcessingJob, RAGQueryResponse } from '../services/api.types';

export function useKnowledgeBase() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const listKnowledgeBases = useCallback(async (forceRefresh = false) => {
    try {
      setLoading(true);
      setError(null);
      return await knowledgeBaseAPI.list(forceRefresh);
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to list knowledge bases');
      setError(error);
      throw error;
    } finally {
      setLoading(false);
    }
  }, []);

  const getKBDetails = useCallback(async (kbName: string, forceRefresh = false): Promise<KnowledgeBaseDetails | null> => {
    try {
      setLoading(true);
      setError(null);
      return await knowledgeBaseAPI.getDetails(kbName, forceRefresh) as KnowledgeBaseDetails;
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to get KB details');
      setError(error);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const deleteKB = useCallback(async (kbName: string) => {
    try {
      setLoading(true);
      setError(null);
      return await knowledgeBaseAPI.delete(kbName);
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to delete KB');
      setError(error);
      throw error;
    } finally {
      setLoading(false);
    }
  }, []);

  const deleteFileFromKB = useCallback(async (kbName: string, filename: string) => {
    try {
      setLoading(true);
      setError(null);
      return await knowledgeBaseAPI.deleteFile(kbName, filename);
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to delete file');
      setError(error);
      throw error;
    } finally {
      setLoading(false);
    }
  }, []);

  const reindexFile = useCallback(async (kbName: string, filename: string) => {
    try {
      setLoading(true);
      setError(null);
      return await knowledgeBaseAPI.reindexFile(kbName, filename);
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to reindex file');
      setError(error);
      throw error;
    } finally {
      setLoading(false);
    }
  }, []);

  const processFile = useCallback(async (filePath: string, kbName = 'default') => {
    try {
      setLoading(true);
      setError(null);
      return await documentProcessingAPI.processToKnowledgeBase(filePath, kbName);
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to process file');
      setError(error);
      throw error;
    } finally {
      setLoading(false);
    }
  }, []);

  const getProcessingStatus = useCallback(async (jobId: string): Promise<ProcessingJob | null> => {
    try {
      return await documentProcessingAPI.getProcessingStatus(jobId) as ProcessingJob;
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to get processing status');
      setError(error);
      return null;
    }
  }, []);

  const queryKB = useCallback(async (
    kbName: string,
    query: string,
    chatHistory?: string[]
  ): Promise<RAGQueryResponse | null> => {
    try {
      setLoading(true);
      setError(null);
      return await ragQueryAPI.query(kbName, query, chatHistory) as RAGQueryResponse;
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to query KB');
      setError(error);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    loading,
    error,
    listKnowledgeBases,
    getKBDetails,
    deleteKB,
    deleteFileFromKB,
    reindexFile,
    processFile,
    getProcessingStatus,
    queryKB,
  };
}
