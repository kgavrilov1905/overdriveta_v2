'use client';

import React, { useState, useCallback, useRef } from 'react';
import { Upload, FileText, Check, X, AlertCircle, Loader2 } from 'lucide-react';
import axios from 'axios';
import Header from '../../components/Header';

interface UploadResponse {
  message: string;
  document_id: string;
  filename: string;
  processing_status: string;
}

interface UploadedFile {
  id: string;
  file: File;
  status: 'pending' | 'uploading' | 'processing' | 'completed' | 'error';
  response?: UploadResponse;
  error?: string;
  progress: number;
}

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

export default function UploadPage() {
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [isDragActive, setIsDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const onDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragActive(true);
  }, []);

  const onDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragActive(false);
  }, []);

  const onDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleFiles = useCallback((fileList: FileList) => {
    const newFiles: UploadedFile[] = Array.from(fileList)
      .filter(file => file.type === 'application/pdf')
      .map(file => ({
        id: Math.random().toString(36).substring(7),
        file,
        status: 'pending',
        progress: 0,
      }));

    setFiles(prev => [...prev, ...newFiles]);
  }, []);

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragActive(false);

    const droppedFiles = e.dataTransfer.files;
    handleFiles(droppedFiles);
  }, [handleFiles]);

  const onFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      handleFiles(e.target.files);
    }
  }, [handleFiles]);

  const uploadFile = async (fileItem: UploadedFile) => {
    setFiles(prev => prev.map(f => 
      f.id === fileItem.id 
        ? { ...f, status: 'uploading', progress: 0 }
        : f
    ));

    try {
      const formData = new FormData();
      formData.append('file', fileItem.file);

      const response = await axios.post<UploadResponse>(
        `${BACKEND_URL}/documents/upload`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
          onUploadProgress: (progressEvent) => {
            const progress = progressEvent.total 
              ? Math.round((progressEvent.loaded * 100) / progressEvent.total)
              : 0;
            
            setFiles(prev => prev.map(f => 
              f.id === fileItem.id 
                ? { ...f, progress }
                : f
            ));
          },
        }
      );

      setFiles(prev => prev.map(f => 
        f.id === fileItem.id 
          ? { 
              ...f, 
              status: response.data.processing_status === 'completed' ? 'completed' : 'processing',
              response: response.data,
              progress: 100
            }
          : f
      ));

      // Poll for processing completion if needed
      if (response.data.processing_status === 'processing') {
        pollProcessingStatus(fileItem.id, response.data.document_id);
      }

    } catch (error) {
      console.error('Upload error:', error);
      setFiles(prev => prev.map(f => 
        f.id === fileItem.id 
          ? { 
              ...f, 
              status: 'error',
              error: axios.isAxiosError(error) 
                ? error.response?.data?.detail || 'Upload failed'
                : 'Upload failed',
              progress: 0
            }
          : f
      ));
    }
  };

  const pollProcessingStatus = async (fileId: string, documentId: string) => {
    let attempts = 0;
    const maxAttempts = 30; // 5 minutes max
    
    const checkStatus = async () => {
      try {
        const response = await axios.get(`${BACKEND_URL}/documents/${documentId}/status`);
        
        if (response.data.status === 'completed') {
          setFiles(prev => prev.map(f => 
            f.id === fileId 
              ? { ...f, status: 'completed' }
              : f
          ));
          return;
        }
        
        if (response.data.status === 'failed') {
          setFiles(prev => prev.map(f => 
            f.id === fileId 
              ? { ...f, status: 'error', error: 'Processing failed' }
              : f
          ));
          return;
        }
        
        attempts++;
        if (attempts < maxAttempts) {
          setTimeout(checkStatus, 10000); // Check every 10 seconds
        } else {
          setFiles(prev => prev.map(f => 
            f.id === fileId 
              ? { ...f, status: 'error', error: 'Processing timeout' }
              : f
          ));
        }
      } catch (error) {
        console.error('Status check error:', error);
        setFiles(prev => prev.map(f => 
          f.id === fileId 
            ? { ...f, status: 'error', error: 'Status check failed' }
            : f
        ));
      }
    };
    
    setTimeout(checkStatus, 2000); // Initial delay
  };

  const removeFile = (fileId: string) => {
    setFiles(prev => prev.filter(f => f.id !== fileId));
  };

  const uploadAllPending = () => {
    files
      .filter(f => f.status === 'pending')
      .forEach(uploadFile);
  };

  const getStatusIcon = (status: UploadedFile['status']) => {
    switch (status) {
      case 'pending':
        return <FileText className="w-5 h-5 text-slate-400" />;
      case 'uploading':
      case 'processing':
        return <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />;
      case 'completed':
        return <Check className="w-5 h-5 text-green-500" />;
      case 'error':
        return <AlertCircle className="w-5 h-5 text-red-500" />;
      default:
        return <FileText className="w-5 h-5 text-slate-400" />;
    }
  };

  const getStatusText = (file: UploadedFile) => {
    switch (file.status) {
      case 'pending':
        return 'Ready to upload';
      case 'uploading':
        return `Uploading... ${file.progress}%`;
      case 'processing':
        return 'Processing document...';
      case 'completed':
        return 'Successfully processed';
      case 'error':
        return file.error || 'Upload failed';
      default:
        return 'Unknown status';
    }
  };

  const pendingCount = files.filter(f => f.status === 'pending').length;
  const processingCount = files.filter(f => f.status === 'uploading' || f.status === 'processing').length;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-white dark:from-slate-900 dark:to-slate-800">
      <Header
        title="Document Upload"
        subtitle="Upload PDF documents to expand the knowledge base"
        showUploadLink={false}
        showChatLink={true}
      />

      <div className="max-w-4xl mx-auto px-6 py-8">
        {/* Upload Zone */}
        <div
          className={`relative border-2 border-dashed rounded-2xl p-12 text-center transition-all duration-200 ${
            isDragActive
              ? 'border-blue-400 bg-blue-50 dark:bg-blue-900/20'
              : 'border-slate-300 dark:border-slate-600 hover:border-slate-400 dark:hover:border-slate-500'
          }`}
          onDragEnter={onDragEnter}
          onDragLeave={onDragLeave}
          onDragOver={onDragOver}
          onDrop={onDrop}
        >
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".pdf"
            onChange={onFileSelect}
            className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
          />
          
          <div className="space-y-4">
            <div className="inline-flex items-center justify-center w-16 h-16 bg-blue-100 dark:bg-blue-900 rounded-full">
              <Upload className="w-8 h-8 text-blue-600 dark:text-blue-400" />
            </div>
            
            <div>
              <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-2">
                Drop PDF files here or click to browse
              </h3>
              <p className="text-slate-600 dark:text-slate-400">
                Upload research documents, reports, and policy papers to enhance the RAG system
              </p>
            </div>
            
            <button
              onClick={() => fileInputRef.current?.click()}
              className="inline-flex items-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
            >
              <Upload className="w-5 h-5" />
              Choose Files
            </button>
          </div>
        </div>

        {/* Upload Queue */}
        {files.length > 0 && (
          <div className="mt-8">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
                Upload Queue ({files.length})
              </h2>
              
              {pendingCount > 0 && (
                <button
                  onClick={uploadAllPending}
                  disabled={processingCount > 0}
                  className="px-4 py-2 bg-green-600 hover:bg-green-700 disabled:bg-slate-400 disabled:cursor-not-allowed text-white rounded-lg font-medium transition-colors"
                >
                  Upload All ({pendingCount})
                </button>
              )}
            </div>

            <div className="space-y-3">
              {files.map((file) => (
                <div
                  key={file.id}
                  className="flex items-center gap-4 p-4 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg"
                >
                  <div className="flex-shrink-0">
                    {getStatusIcon(file.status)}
                  </div>
                  
                  <div className="flex-1 min-w-0">
                    <h3 className="font-medium text-slate-900 dark:text-white truncate">
                      {file.file.name}
                    </h3>
                    <p className="text-sm text-slate-600 dark:text-slate-400">
                      {(file.file.size / 1024 / 1024).toFixed(1)} MB • {getStatusText(file)}
                    </p>
                    
                    {(file.status === 'uploading' || file.status === 'processing') && (
                      <div className="mt-2 w-full bg-slate-200 dark:bg-slate-700 rounded-full h-2">
                        <div
                          className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                          style={{ width: `${file.progress}%` }}
                        />
                      </div>
                    )}
                  </div>
                  
                  <div className="flex items-center gap-2">
                    {file.status === 'pending' && (
                      <button
                        onClick={() => uploadFile(file)}
                        className="px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded transition-colors"
                      >
                        Upload
                      </button>
                    )}
                    
                    {(file.status === 'pending' || file.status === 'error') && (
                      <button
                        onClick={() => removeFile(file.id)}
                        className="p-1 hover:bg-slate-100 dark:hover:bg-slate-700 rounded transition-colors"
                      >
                        <X className="w-4 h-4 text-slate-500" />
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
} 