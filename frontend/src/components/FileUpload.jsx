import { useState, useCallback } from 'react';
import axios from 'axios';
import './FileUpload.css';

const FileUpload = ({ onUploadSuccess, onError }) => {
  const [isDragOver, setIsDragOver] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);

  const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50MB

  const validateFile = (file) => {
    if (!file.type.includes('pdf')) {
      throw new Error('Only PDF files are supported');
    }
    if (file.size > MAX_FILE_SIZE) {
      throw new Error(`File too large. Maximum size: ${MAX_FILE_SIZE / (1024 * 1024)}MB`);
    }
  };

  const uploadFile = async (file) => {
    try {
      validateFile(file);
      setIsUploading(true);
      setUploadProgress(0);

      const formData = new FormData();
      formData.append('file', file);

      const response = await axios.post('/api/convert', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        onUploadProgress: (progressEvent) => {
          const progress = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total
          );
          setUploadProgress(progress);
        },
      });

      onUploadSuccess(response.data);
    } catch (error) {
      const errorMessage = error.response?.data?.detail || error.message || 'Upload failed';
      onError(errorMessage);
    } finally {
      setIsUploading(false);
      setUploadProgress(0);
    }
  };

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setIsDragOver(false);
    
    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      uploadFile(files[0]);
    }
  }, []);

  const handleFileSelect = useCallback((e) => {
    const files = Array.from(e.target.files);
    if (files.length > 0) {
      uploadFile(files[0]);
    }
  }, []);

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <div className="file-upload">
      <div
        className={`upload-zone ${isDragOver ? 'drag-over' : ''} ${isUploading ? 'uploading' : ''}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        {isUploading ? (
          <div className="upload-progress">
            <div className="upload-spinner"></div>
            <div className="upload-progress-bar">
              <div 
                className="upload-progress-fill" 
                style={{ width: `${uploadProgress}%` }}
              ></div>
            </div>
            <p>Uploading... {uploadProgress}%</p>
          </div>
        ) : (
          <>
            <div className="upload-icon">
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                <polyline points="14,2 14,8 20,8"></polyline>
                <line x1="16" y1="13" x2="8" y2="13"></line>
                <line x1="16" y1="17" x2="8" y2="17"></line>
                <polyline points="10,9 9,9 8,9"></polyline>
              </svg>
            </div>
            <h3>Upload PDF Document</h3>
            <p className="upload-description">
              Drag and drop your PDF file here, or click to browse
            </p>
            <div className="upload-specs">
              <span>Maximum file size: {formatFileSize(MAX_FILE_SIZE)}</span>
              <span>Supported format: PDF</span>
            </div>
            <input
              type="file"
              accept=".pdf,application/pdf"
              onChange={handleFileSelect}
              disabled={isUploading}
              className="file-input"
              id="file-input"
            />
            <label htmlFor="file-input" className="upload-button">
              Choose File
            </label>
          </>
        )}
      </div>
      
      <div className="features-list">
        <h4>Features:</h4>
        <ul>
          <li>✨ AI-powered HTML generation with Gemini</li>
          <li>🔄 Iterative refinement using screenshot comparison</li>
          <li>📱 Real-time progress updates</li>
          <li>🎯 High-fidelity visual reproduction</li>
          <li>📄 Multi-page document support</li>
        </ul>
      </div>
    </div>
  );
};

export default FileUpload;
