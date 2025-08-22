import { useState, useEffect } from 'react';
import axios from 'axios';
import './HtmlPreview.css';

const HtmlPreview = ({ taskId, conversionResult, onReset }) => {
  const [previewMode, setPreviewMode] = useState('combined'); // 'combined', 'pages', 'code'
  const [isDownloading, setIsDownloading] = useState(false);
  const [downloadError, setDownloadError] = useState(null);
  const [selectedPage, setSelectedPage] = useState(null);

  const downloadHtml = async () => {
    try {
      setIsDownloading(true);
      setDownloadError(null);

      const response = await axios.get(`/api/download/${taskId}`, {
        responseType: 'blob'
      });

      // Create download link
      const blob = new Blob([response.data], { type: 'text/html' });
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      
      // Extract filename from Content-Disposition header or use default
      const contentDisposition = response.headers['content-disposition'];
      let filename = 'converted_document.html';
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="(.+)"/);
        if (filenameMatch) {
          filename = filenameMatch[1];
        }
      }
      
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(downloadUrl);

    } catch (error) {
      console.error('Download error:', error);
      setDownloadError(error.response?.data?.detail || 'Download failed');
    } finally {
      setIsDownloading(false);
    }
  };

  const copyToClipboard = async (content) => {
    try {
      await navigator.clipboard.writeText(content);
      // You might want to add a toast notification here
      alert('HTML copied to clipboard!');
    } catch (error) {
      console.error('Copy failed:', error);
      alert('Failed to copy to clipboard');
    }
  };

  const formatProcessingTime = (seconds) => {
    if (seconds < 60) {
      return `${seconds.toFixed(1)}s`;
    }
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = (seconds % 60).toFixed(0);
    return `${minutes}m ${remainingSeconds}s`;
  };

  const formatFileSize = (htmlContent) => {
    const bytes = new Blob([htmlContent]).size;
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  if (!conversionResult) {
    return null;
  }

  const { combined_html, pages, processing_time, total_pages, errors } = conversionResult;

  return (
    <div className="html-preview">
      <div className="preview-header">
        <h2>Conversion Complete!</h2>
        <div className="conversion-stats">
          <div className="stat">
            <span className="stat-label">Pages:</span>
            <span className="stat-value">{total_pages}</span>
          </div>
          <div className="stat">
            <span className="stat-label">Time:</span>
            <span className="stat-value">{formatProcessingTime(processing_time)}</span>
          </div>
          <div className="stat">
            <span className="stat-label">Size:</span>
            <span className="stat-value">{formatFileSize(combined_html)}</span>
          </div>
          {errors && errors.length > 0 && (
            <div className="stat error">
              <span className="stat-label">Errors:</span>
              <span className="stat-value">{errors.length}</span>
            </div>
          )}
        </div>
      </div>

      <div className="preview-actions">
        <button
          onClick={downloadHtml}
          disabled={isDownloading}
          className="download-btn primary"
        >
          {isDownloading ? (
            <>
              <div className="spinner"></div>
              Downloading...
            </>
          ) : (
            <>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 15.5l-5-5h3V4h4v6.5h3l-5 5z"/>
                <path d="M4 17v2h16v-2H4z"/>
              </svg>
              Download HTML
            </>
          )}
        </button>
        
        <button
          onClick={() => copyToClipboard(combined_html)}
          className="copy-btn secondary"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
            <path d="M16 1H4c-1.1 0-2 .9-2 2v14h2V3h12V1zm3 4H8c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h11c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2zm0 16H8V7h11v14z"/>
          </svg>
          Copy HTML
        </button>
        
        <button onClick={onReset} className="reset-btn secondary">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
            <path d="M4 12l1.41 1.41L11 7.83V20h2V7.83l5.58 5.59L20 12l-8-8-8 8z"/>
          </svg>
          Convert Another PDF
        </button>
      </div>

      {downloadError && (
        <div className="error-message">
          <strong>Download Error:</strong> {downloadError}
        </div>
      )}

      <div className="preview-modes">
        <div className="mode-tabs">
          <button
            className={previewMode === 'combined' ? 'active' : ''}
            onClick={() => setPreviewMode('combined')}
          >
            Combined Preview
          </button>
          <button
            className={previewMode === 'pages' ? 'active' : ''}
            onClick={() => setPreviewMode('pages')}
          >
            Individual Pages ({pages?.length || 0})
          </button>
          <button
            className={previewMode === 'code' ? 'active' : ''}
            onClick={() => setPreviewMode('code')}
          >
            HTML Source
          </button>
        </div>

        <div className="preview-content">
          {previewMode === 'combined' && (
            <div className="combined-preview">
              <div className="preview-frame">
                <iframe
                  srcDoc={combined_html}
                  title="Combined HTML Preview"
                  className="html-iframe"
                />
              </div>
            </div>
          )}

          {previewMode === 'pages' && (
            <div className="pages-preview">
              {pages && pages.length > 0 ? (
                <div className="pages-grid">
                  {pages.map((page) => (
                    <div key={page.page_number} className="page-card">
                      <div className="page-card-header">
                        <h4>Page {page.page_number}</h4>
                        <div className="page-stats">
                          <span>Quality: {page.final_quality_score}/10</span>
                          <span>Iterations: {page.refinement_iterations}</span>
                          <span>{formatProcessingTime(page.processing_time)}</span>
                        </div>
                      </div>
                      <div className="page-preview-frame">
                        <iframe
                          srcDoc={page.html_content}
                          title={`Page ${page.page_number}`}
                          className="page-iframe"
                        />
                      </div>
                      <div className="page-actions">
                        <button
                          onClick={() => setSelectedPage(page)}
                          className="view-btn small"
                        >
                          View Full Size
                        </button>
                        <button
                          onClick={() => copyToClipboard(page.html_content)}
                          className="copy-btn small"
                        >
                          Copy HTML
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="no-pages">
                  No individual page data available
                </div>
              )}
            </div>
          )}

          {previewMode === 'code' && (
            <div className="code-preview">
              <div className="code-header">
                <span>HTML Source Code</span>
                <button
                  onClick={() => copyToClipboard(combined_html)}
                  className="copy-btn small"
                >
                  Copy All
                </button>
              </div>
              <pre className="code-block">
                <code>{combined_html}</code>
              </pre>
            </div>
          )}
        </div>
      </div>

      {errors && errors.length > 0 && (
        <div className="errors-section">
          <details>
            <summary>Processing Errors ({errors.length})</summary>
            <div className="errors-list">
              {errors.map((error, index) => (
                <div key={index} className="error-item">
                  {error}
                </div>
              ))}
            </div>
          </details>
        </div>
      )}

      {/* Full Size Page Modal */}
      {selectedPage && (
        <div className="page-modal-overlay" onClick={() => setSelectedPage(null)}>
          <div className="page-modal" onClick={(e) => e.stopPropagation()}>
            <div className="page-modal-header">
              <h3>Page {selectedPage.page_number} - Full Size Preview</h3>
              <button
                onClick={() => setSelectedPage(null)}
                className="close-btn"
              >
                <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
                </svg>
              </button>
            </div>
            <div className="page-modal-content">
              <iframe
                srcDoc={selectedPage.html_content}
                title={`Page ${selectedPage.page_number} Full Size`}
                className="page-modal-iframe"
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default HtmlPreview;
