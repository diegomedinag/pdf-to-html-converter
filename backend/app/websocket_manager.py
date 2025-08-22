"""
WebSocket Manager

Manages WebSocket connections for real-time progress updates during PDF to HTML conversion.
Handles connection lifecycle, task tracking, and message broadcasting.
"""

import asyncio
import json
import uuid
from typing import Dict, List, Optional, Any
import logging
from fastapi import WebSocket, WebSocketDisconnect
from dataclasses import dataclass, asdict
import time

logger = logging.getLogger(__name__)


@dataclass
class ProgressUpdate:
    """Data structure for progress updates."""
    task_id: str
    message: str
    progress_percentage: Optional[int] = None
    current_page: Optional[int] = None
    total_pages: Optional[int] = None
    page_html: Optional[str] = None
    timestamp: Optional[float] = None
    data: Optional[Dict] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()


@dataclass
class TaskCompletion:
    """Data structure for task completion."""
    task_id: str
    status: str
    combined_html: Optional[str] = None
    total_pages: int = 0
    processing_time: float = 0
    errors: List[str] = None
    timestamp: Optional[float] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()
        if self.errors is None:
            self.errors = []


class WebSocketManager:
    """
    Manages WebSocket connections and handles real-time communication.
    """
    
    def __init__(self):
        """Initialize the WebSocket manager."""
        # Active connections mapped by task_id
        self.active_connections: Dict[str, WebSocket] = {}
        
        # Task status tracking
        self.task_statuses: Dict[str, Dict] = {}
        
        # Connection metadata
        self.connection_metadata: Dict[str, Dict] = {}
        
        logger.info("WebSocket manager initialized")
    
    async def connect(self, websocket: WebSocket, task_id: str) -> bool:
        """
        Accept a WebSocket connection and register it.
        
        Args:
            websocket: The WebSocket connection
            task_id: Task identifier
            
        Returns:
            True if connection successful, False otherwise
        """
        try:
            await websocket.accept()
            
            # Store the connection
            self.active_connections[task_id] = websocket
            
            # Initialize connection metadata
            self.connection_metadata[task_id] = {
                'connected_at': time.time(),
                'last_activity': time.time(),
                'messages_sent': 0
            }
            
            # Initialize task status if not exists
            if task_id not in self.task_statuses:
                self.task_statuses[task_id] = {
                    'status': 'connected',
                    'progress_percentage': 0,
                    'current_page': 0,
                    'total_pages': 0,
                    'messages': []
                }
            
            logger.info(f"WebSocket connected for task {task_id}")
            
            # Send initial connection confirmation
            await self._send_message(task_id, {
                'type': 'connection',
                'status': 'connected',
                'task_id': task_id,
                'message': 'Connected successfully. Waiting for PDF processing to begin...'
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Error connecting WebSocket for task {task_id}: {str(e)}")
            return False
    
    def disconnect(self, task_id: str) -> None:
        """
        Remove a WebSocket connection.
        
        Args:
            task_id: Task identifier
        """
        try:
            if task_id in self.active_connections:
                del self.active_connections[task_id]
                
            if task_id in self.connection_metadata:
                connection_time = time.time() - self.connection_metadata[task_id]['connected_at']
                logger.info(f"WebSocket disconnected for task {task_id} after {connection_time:.2f}s")
                del self.connection_metadata[task_id]
                
        except Exception as e:
            logger.warning(f"Error disconnecting WebSocket for task {task_id}: {str(e)}")
    
    async def send_progress_update(self, update: ProgressUpdate) -> bool:
        """
        Send a progress update to the connected WebSocket.
        
        Args:
            update: Progress update data
            
        Returns:
            True if sent successfully, False otherwise
        """
        return await self._send_message(update.task_id, {
            'type': 'progress',
            **asdict(update)
        })
    
    async def send_page_completion(self, task_id: str, page_number: int, page_html: str, current_page: int, total_pages: int) -> bool:
        """
        Send page completion notification with HTML content.
        
        Args:
            task_id: Task identifier
            page_number: Completed page number
            page_html: Generated HTML for the page
            current_page: Current page being processed
            total_pages: Total number of pages
            
        Returns:
            True if sent successfully, False otherwise
        """
        # Calculate progress percentage
        progress_percentage = int((current_page / total_pages) * 100) if total_pages > 0 else 0
        
        # Update task status
        if task_id in self.task_statuses:
            self.task_statuses[task_id].update({
                'current_page': current_page,
                'total_pages': total_pages,
                'progress_percentage': progress_percentage
            })
        
        return await self._send_message(task_id, {
            'type': 'page_completed',
            'task_id': task_id,
            'page_number': page_number,
            'page_html': page_html,
            'current_page': current_page,
            'total_pages': total_pages,
            'progress_percentage': progress_percentage,
            'timestamp': time.time(),
            'message': f'Completed page {page_number} of {total_pages}'
        })
    
    async def send_task_completion(self, completion: TaskCompletion) -> bool:
        """
        Send task completion notification.
        
        Args:
            completion: Task completion data
            
        Returns:
            True if sent successfully, False otherwise
        """
        # Update task status
        if completion.task_id in self.task_statuses:
            self.task_statuses[completion.task_id].update({
                'status': completion.status,
                'progress_percentage': 100 if completion.status == 'success' else 0
            })
        
        return await self._send_message(completion.task_id, {
            'type': 'task_completed',
            **asdict(completion)
        })
    
    async def send_error(self, task_id: str, error_message: str, error_code: Optional[str] = None) -> bool:
        """
        Send error notification.
        
        Args:
            task_id: Task identifier
            error_message: Error message
            error_code: Optional error code
            
        Returns:
            True if sent successfully, False otherwise
        """
        # Update task status
        if task_id in self.task_statuses:
            self.task_statuses[task_id].update({
                'status': 'error',
                'error_message': error_message
            })
        
        return await self._send_message(task_id, {
            'type': 'error',
            'task_id': task_id,
            'message': error_message,
            'error_code': error_code,
            'timestamp': time.time()
        })
    
    async def _send_message(self, task_id: str, message_data: Dict) -> bool:
        """
        Send a message to a specific WebSocket connection.
        
        Args:
            task_id: Task identifier
            message_data: Message data to send
            
        Returns:
            True if sent successfully, False otherwise
        """
        if task_id not in self.active_connections:
            logger.warning(f"No active WebSocket connection for task {task_id}")
            return False
        
        try:
            websocket = self.active_connections[task_id]
            
            # Add the message to task status history
            if task_id in self.task_statuses:
                if len(self.task_statuses[task_id]['messages']) > 50:  # Limit message history
                    self.task_statuses[task_id]['messages'].pop(0)
                self.task_statuses[task_id]['messages'].append(message_data)
            
            # Send the message
            message_json = json.dumps(message_data, default=str)  # default=str handles datetime objects
            await websocket.send_text(message_json)
            
            # Update connection metadata
            if task_id in self.connection_metadata:
                self.connection_metadata[task_id]['last_activity'] = time.time()
                self.connection_metadata[task_id]['messages_sent'] += 1
            
            logger.debug(f"Sent WebSocket message to task {task_id}: {message_data.get('type', 'unknown')}")
            return True
            
        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected for task {task_id} while sending message")
            self.disconnect(task_id)
            return False
        except Exception as e:
            logger.error(f"Error sending WebSocket message to task {task_id}: {str(e)}")
            # Don't disconnect on send errors, might be temporary
            return False
    
    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """
        Get current status of a task.
        
        Args:
            task_id: Task identifier
            
        Returns:
            Task status dictionary or None if not found
        """
        return self.task_statuses.get(task_id)
    
    def is_connected(self, task_id: str) -> bool:
        """
        Check if a WebSocket connection is active for a task.
        
        Args:
            task_id: Task identifier
            
        Returns:
            True if connected, False otherwise
        """
        return task_id in self.active_connections
    
    def get_connection_info(self, task_id: str) -> Optional[Dict]:
        """
        Get connection metadata for a task.
        
        Args:
            task_id: Task identifier
            
        Returns:
            Connection metadata or None if not found
        """
        return self.connection_metadata.get(task_id)
    
    def cleanup_task(self, task_id: str) -> None:
        """
        Clean up all data for a completed task.
        
        Args:
            task_id: Task identifier
        """
        try:
            # Disconnect if still connected
            self.disconnect(task_id)
            
            # Clean up task status
            if task_id in self.task_statuses:
                del self.task_statuses[task_id]
            
            logger.info(f"Cleaned up WebSocket data for task {task_id}")
            
        except Exception as e:
            logger.warning(f"Error cleaning up task {task_id}: {str(e)}")
    
    def get_active_connections_count(self) -> int:
        """
        Get the number of active WebSocket connections.
        
        Returns:
            Number of active connections
        """
        return len(self.active_connections)
    
    def get_all_task_statuses(self) -> Dict[str, Dict]:
        """
        Get status of all active tasks.
        
        Returns:
            Dictionary of all task statuses
        """
        return self.task_statuses.copy()


# Global WebSocket manager instance
websocket_manager = WebSocketManager()


# Convenience functions for easy integration with RefinementEngine
async def create_progress_callback(task_id: str):
    """
    Create a progress callback function for the RefinementEngine.
    
    Args:
        task_id: Task identifier
        
    Returns:
        Progress callback function
    """
    async def progress_callback(update_data: Dict):
        """Progress callback function."""
        try:
            # Extract relevant information
            message = update_data.get('message', 'Processing...')
            current_page = update_data.get('current_page')
            total_pages = update_data.get('total_pages')
            page_html = update_data.get('page_html')
            
            # Calculate progress percentage
            progress_percentage = None
            if current_page is not None and total_pages is not None and total_pages > 0:
                progress_percentage = int((current_page / total_pages) * 100)
            
            # Create progress update
            update = ProgressUpdate(
                task_id=task_id,
                message=message,
                progress_percentage=progress_percentage,
                current_page=current_page,
                total_pages=total_pages,
                page_html=page_html,
                data=update_data
            )
            
            # Send via WebSocket
            await websocket_manager.send_progress_update(update)
            
        except Exception as e:
            logger.error(f"Error in progress callback for task {task_id}: {str(e)}")
    
    return progress_callback


async def notify_task_completion(
    task_id: str, 
    status: str, 
    combined_html: Optional[str] = None,
    total_pages: int = 0,
    processing_time: float = 0,
    errors: List[str] = None
) -> None:
    """
    Send task completion notification.
    
    Args:
        task_id: Task identifier
        status: Task completion status (success/error)
        combined_html: Final combined HTML
        total_pages: Total number of pages processed
        processing_time: Total processing time
        errors: List of errors encountered
    """
    completion = TaskCompletion(
        task_id=task_id,
        status=status,
        combined_html=combined_html,
        total_pages=total_pages,
        processing_time=processing_time,
        errors=errors or []
    )
    
    await websocket_manager.send_task_completion(completion)


async def notify_page_completion(
    task_id: str,
    page_number: int,
    page_html: str,
    current_page: int,
    total_pages: int
) -> None:
    """
    Send page completion notification.
    
    Args:
        task_id: Task identifier
        page_number: Completed page number
        page_html: Generated HTML for the page
        current_page: Current progress (pages completed)
        total_pages: Total pages to process
    """
    await websocket_manager.send_page_completion(
        task_id, page_number, page_html, current_page, total_pages
    )


async def notify_error(task_id: str, error_message: str, error_code: Optional[str] = None) -> None:
    """
    Send error notification.
    
    Args:
        task_id: Task identifier
        error_message: Error message
        error_code: Optional error code
    """
    await websocket_manager.send_error(task_id, error_message, error_code)
