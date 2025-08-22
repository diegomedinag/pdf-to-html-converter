import { useState } from 'react';
import FileUpload from './components/FileUpload';
import ConversionProgress from './components/ConversionProgress';
import HtmlPreview from './components/HtmlPreview';
import './App.css';

function App() {
  const [currentStep, setCurrentStep] = useState('upload'); // 'upload', 'converting', 'completed'
  const [taskId, setTaskId] = useState(null);
  const [filename, setFilename] = useState('');
  const [conversionResult, setConversionResult] = useState(null);
  const [error, setError] = useState(null);

  const handleUploadSuccess = (uploadData) => {
    setTaskId(uploadData.task_id);
    setFilename(uploadData.filename);
    setCurrentStep('converting');
    setError(null);
  };

  const handleUploadError = (errorMessage) => {
    setError(errorMessage);
  };

  const handleConversionComplete = (result) => {
    setConversionResult(result);
    setCurrentStep('completed');
  };

  const handleConversionError = (errorMessage) => {
    setError(errorMessage);
    setCurrentStep('upload');
  };

  const handleReset = () => {
    setCurrentStep('upload');
    setTaskId(null);
    setFilename('');
    setConversionResult(null);
    setError(null);
  };

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-content">
          <div className="logo">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="currentColor">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14,2 14,8 20,8"/>
              <line x1="16" y1="13" x2="8" y2="13"/>
              <line x1="16" y1="17" x2="8" y2="17"/>
              <polyline points="10,9 9,9 8,9"/>
            </svg>
            <h1>PDF to HTML Converter</h1>
          </div>
          
          <div className="header-subtitle">
            <p>AI-powered PDF to HTML conversion with iterative refinement</p>
          </div>
        </div>
      </header>

      <main className="app-main">
        {error && (
          <div className="error-banner">
            <div className="error-content">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
              </svg>
              <span>{error}</span>
              <button onClick={() => setError(null)} className="close-error">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
                </svg>
              </button>
            </div>
          </div>
        )}

        {currentStep === 'upload' && (
          <div className="step-content">
            <FileUpload
              onUploadSuccess={handleUploadSuccess}
              onError={handleUploadError}
            />
          </div>
        )}

        {currentStep === 'converting' && (
          <div className="step-content">
            <div className="conversion-header">
              <h2>Converting: {filename}</h2>
              <p>Please wait while we convert your PDF using AI-powered iterative refinement...</p>
            </div>
            <ConversionProgress
              taskId={taskId}
              onCompletion={handleConversionComplete}
              onError={handleConversionError}
            />
          </div>
        )}

        {currentStep === 'completed' && (
          <div className="step-content">
            <HtmlPreview
              taskId={taskId}
              conversionResult={conversionResult}
              onReset={handleReset}
            />
          </div>
        )}
      </main>

      <footer className="app-footer">
        <div className="footer-content">
          <p>
            Powered by <strong>Gemini AI</strong> • 
            Built with <strong>React</strong> & <strong>FastAPI</strong> • 
            <strong>Playwright</strong> for screenshot comparison
          </p>
          <div className="footer-links">
            <a href="/api/docs" target="_blank" rel="noopener noreferrer">
              API Documentation
            </a>
            <span>•</span>
            <a href="https://github.com" target="_blank" rel="noopener noreferrer">
              View on GitHub
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
