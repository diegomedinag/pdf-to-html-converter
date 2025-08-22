import { useState, useEffect, useRef } from 'react';
import './ConversionProgress.css';

const ConversionProgress = ({ taskId, onCompletion, onError }) => {
  const [connectionStatus, setConnectionStatus] = useState('connecting');
  const [progress, setProgress] = useState({
    message: 'Connecting...',
    progressPercentage: 0,
    currentPage: 0,
    totalPages: 0,
  });
  const [pages, setPages] = useState([]);
  const [logs, setLogs] = useState([]);
  const websocketRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const maxReconnectAttempts = 5;
  const reconnectAttempts = useRef(0);

  useEffect(() => {
    if (taskId) {
      connectWebSocket();
    }

    return () => {
      disconnectWebSocket();
    };
  }, [taskId]);

  const connectWebSocket = () => {
    try {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.host}/ws/${taskId}`;
      
      addLog('info', `Connecting to WebSocket: ${wsUrl}`);
      
      websocketRef.current = new WebSocket(wsUrl);

      websocketRef.current.onopen = () => {
        setConnectionStatus('connected');
        reconnectAttempts.current = 0;
        addLog('success', 'Connected to conversion server');
        
        setProgress(prev => ({
          ...prev,
          message: 'Connected. Waiting for processing to begin...'
        }));
      };

      websocketRef.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          handleWebSocketMessage(data);
        } catch (error) {
          addLog('error', `Error parsing WebSocket message: ${error.message}`);
        }
      };

      websocketRef.current.onclose = (event) => {
        setConnectionStatus('disconnected');
        addLog('warning', `WebSocket connection closed (code: ${event.code})`);

        // Attempt to reconnect if it wasn't a clean close
        if (event.code !== 1000 && reconnectAttempts.current < maxReconnectAttempts) {
          const delay = Math.pow(2, reconnectAttempts.current) * 1000; // Exponential backoff
          addLog('info', `Attempting to reconnect in ${delay / 1000} seconds...`);
          
          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectAttempts.current++;
            connectWebSocket();
          }, delay);
        }
      };

      websocketRef.current.onerror = (error) => {
        setConnectionStatus('error');
        addLog('error', `WebSocket error: ${error.message || 'Connection failed'}`);
      };

    } catch (error) {
      setConnectionStatus('error');
      addLog('error', `Failed to create WebSocket connection: ${error.message}`);
    }
  };

  const disconnectWebSocket = () => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    
    if (websocketRef.current) {
      websocketRef.current.close(1000, 'Component unmounting');
      websocketRef.current = null;
    }
  };

  const handleWebSocketMessage = (data) => {
    addLog('info', `Received: ${data.type} - ${data.message || 'No message'}`);

    switch (data.type) {
      case 'connection':
        setProgress(prev => ({
          ...prev,
          message: data.message
        }));
        break;

      case 'progress':
        setProgress({
          message: data.message,
          progressPercentage: data.progress_percentage || 0,
          currentPage: data.current_page || 0,
          totalPages: data.total_pages || 0,
        });
        break;

      case 'page_completed':
        setPages(prevPages => {
          const newPages = [...prevPages];
          const existingIndex = newPages.findIndex(p => p.pageNumber === data.page_number);
          
          const pageData = {
            pageNumber: data.page_number,
            htmlContent: data.page_html,
            completed: true,
            timestamp: new Date(data.timestamp * 1000).toLocaleTimeString()
          };
          
          if (existingIndex >= 0) {
            newPages[existingIndex] = pageData;
          } else {
            newPages.push(pageData);
          }
          
          return newPages.sort((a, b) => a.pageNumber - b.pageNumber);
        });

        setProgress({
          message: data.message,
          progressPercentage: data.progress_percentage,
          currentPage: data.current_page,
          totalPages: data.total_pages,
        });
        break;

      case 'task_completed':
        if (data.status === 'success') {
          addLog('success', 'PDF conversion completed successfully!');
          onCompletion(data);
        } else {
          addLog('error', `Conversion failed: ${data.errors?.join(', ') || 'Unknown error'}`);
          onError(data.errors?.join(', ') || 'Conversion failed');
        }
        
        setProgress(prev => ({
          ...prev,
          message: data.status === 'success' ? 'Conversion completed!' : 'Conversion failed',
          progressPercentage: data.status === 'success' ? 100 : 0
        }));
        break;

      case 'error':
        addLog('error', `Error: ${data.message}`);
        onError(data.message);
        break;

      default:
        addLog('info', `Unknown message type: ${data.type}`);
    }
  };

  const addLog = (level, message) => {
    const timestamp = new Date().toLocaleTimeString();
    setLogs(prevLogs => {
      const newLogs = [...prevLogs, { level, message, timestamp }];
      // Keep only the last 50 log entries
      return newLogs.slice(-50);
    });
  };

  const getConnectionStatusClass = () => {
    switch (connectionStatus) {
      case 'connected': return 'connected';
      case 'connecting': return 'connecting';
      case 'disconnected': return 'disconnected';
      case 'error': return 'error';
      default: return '';
    }
  };

  const formatTimeRemaining = () => {
    if (!progress.totalPages || progress.currentPage === 0) return 'Calculating...';
    
    const avgTimePerPage = 15; // Rough estimate: 15 seconds per page
    const remainingPages = progress.totalPages - progress.currentPage;
    const remainingSeconds = remainingPages * avgTimePerPage;
    
    if (remainingSeconds < 60) {
      return `~${remainingSeconds}s remaining`;
    } else {
      const minutes = Math.ceil(remainingSeconds / 60);
      return `~${minutes}m remaining`;
    }
  };

  return (
    <div className="conversion-progress">
      <div className="progress-header">
        <div className="connection-status">
          <div className={`status-indicator ${getConnectionStatusClass()}`}></div>
          <span>WebSocket: {connectionStatus}</span>
        </div>
        <div className="task-info">
          Task: {taskId}
        </div>
      </div>

      <div className="progress-main">
        <div className="progress-bar-container">
          <div className="progress-info">
            <span className="progress-message">{progress.message}</span>
            <span className="progress-stats">
              {progress.totalPages > 0 && (
                <>
                  Page {progress.currentPage} of {progress.totalPages} ({progress.progressPercentage}%)
                  <br />
                  <small>{formatTimeRemaining()}</small>
                </>
              )}
            </span>
          </div>
          
          <div className="progress-bar">
            <div 
              className="progress-fill" 
              style={{ width: `${progress.progressPercentage}%` }}
            ></div>
          </div>
        </div>

        {pages.length > 0 && (
          <div className="pages-grid">
            <h3>Completed Pages:</h3>
            <div className="pages-list">
              {pages.map(page => (
                <div key={page.pageNumber} className="page-item">
                  <div className="page-header">
                    <span className="page-number">Page {page.pageNumber}</span>
                    <span className="page-timestamp">{page.timestamp}</span>
                  </div>
                  <div className="page-preview">
                    <iframe
                      srcDoc={page.htmlContent}
                      title={`Page ${page.pageNumber}`}
                      style={{ 
                        width: '100%', 
                        height: '150px', 
                        border: '1px solid #e5e7eb',
                        borderRadius: '4px'
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="logs-section">
        <details>
          <summary>Conversion Logs ({logs.length})</summary>
          <div className="logs-container">
            {logs.map((log, index) => (
              <div key={index} className={`log-entry log-${log.level}`}>
                <span className="log-timestamp">{log.timestamp}</span>
                <span className="log-message">{log.message}</span>
              </div>
            ))}
          </div>
        </details>
      </div>
    </div>
  );
};

export default ConversionProgress;
