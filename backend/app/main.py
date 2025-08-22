"""
FastAPI Main Application

PDF to HTML Converter with Iterative Refinement
Main FastAPI application with endpoints for PDF upload, WebSocket communication, and HTML download.
"""

import asyncio
import os
import uuid
import logging
import json
from typing import Optional, Dict, Any
from pathlib import Path
import tempfile
import shutil

from fastapi import FastAPI, File, UploadFile, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
from dotenv import load_dotenv

from .refinement_engine import RefinementEngine
from .websocket_manager import websocket_manager, create_progress_callback, notify_task_completion, notify_error
from .pdf_processor import PDFProcessor

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="PDF to HTML Converter",
    description="Advanced PDF to HTML converter with AI-powered iterative refinement using screenshots",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "*"],  # Add frontend URLs
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Environment configuration
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "./uploads"))
TEMP_DIR = Path(os.getenv("TEMP_DIR", "./temp"))
SCREENSHOTS_DIR = Path(os.getenv("SCREENSHOTS_DIR", "./screenshots"))
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", 50000000))  # 50MB default
MAX_REFINEMENT_ITERATIONS = int(os.getenv("MAX_REFINEMENT_ITERATIONS", 2))

# Create directories
for directory in [UPLOAD_DIR, TEMP_DIR, SCREENSHOTS_DIR]:
    directory.mkdir(exist_ok=True, parents=True)

# Global storage for conversion results
conversion_results: Dict[str, Dict[str, Any]] = {}

# Initialize refinement engine
refinement_engine = None


async def get_refinement_engine() -> RefinementEngine:
    """Get or create refinement engine instance."""
    global refinement_engine
    if refinement_engine is None:
        refinement_engine = RefinementEngine(
            temp_dir=str(TEMP_DIR),
            screenshots_dir=str(SCREENSHOTS_DIR),
            max_iterations=MAX_REFINEMENT_ITERATIONS
        )
    return refinement_engine


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "PDF to HTML Converter with Iterative Refinement",
        "version": "1.0.0",
        "features": [
            "High-resolution PDF page extraction",
            "AI-powered HTML generation with Gemini",
            "Iterative refinement using screenshot comparison",
            "Real-time WebSocket progress updates",
            "Combined multi-page HTML output"
        ],
        "endpoints": {
            "upload": "/api/convert",
            "websocket": "/ws/{task_id}",
            "download": "/api/download/{task_id}",
            "status": "/api/status/{task_id}",
            "docs": "/api/docs"
        }
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "active_connections": websocket_manager.get_active_connections_count(),
        "active_tasks": len(conversion_results)
    }


@app.post("/api/convert")
async def convert_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="PDF file to convert")
):
    """
    Upload PDF file and start conversion process.
    
    Args:
        file: PDF file to convert
        
    Returns:
        Task ID for tracking conversion progress
    """
    # Validate file
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    if file.size and file.size > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail=f"File too large. Maximum size: {MAX_FILE_SIZE} bytes")
    
    # Generate task ID
    task_id = str(uuid.uuid4())
    
    try:
        # Save uploaded file
        file_path = UPLOAD_DIR / f"{task_id}_{file.filename}"
        
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        logger.info(f"Uploaded file saved: {file_path} ({len(content)} bytes)")
        
        # Validate PDF file
        pdf_processor = PDFProcessor(str(TEMP_DIR))
        if not pdf_processor.validate_pdf(str(file_path)):
            # Clean up invalid file
            file_path.unlink(missing_ok=True)
            raise HTTPException(status_code=400, detail="Invalid or corrupted PDF file")
        
        # Initialize conversion result
        conversion_results[task_id] = {
            "task_id": task_id,
            "filename": file.filename,
            "file_path": str(file_path),
            "status": "uploaded",
            "created_at": asyncio.get_event_loop().time()
        }
        
        # Start conversion in background
        background_tasks.add_task(process_pdf_conversion, task_id, str(file_path))
        
        logger.info(f"Started PDF conversion task: {task_id}")
        
        return {
            "task_id": task_id,
            "message": "PDF uploaded successfully. Connect to WebSocket for real-time updates.",
            "websocket_url": f"/ws/{task_id}",
            "filename": file.filename
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in PDF upload: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to process PDF upload: {str(e)}")


async def process_pdf_conversion(task_id: str, pdf_path: str):
    """
    Background task to process PDF conversion.
    
    Args:
        task_id: Task identifier
        pdf_path: Path to uploaded PDF file
    """
    try:
        logger.info(f"Starting PDF conversion for task {task_id}")
        
        # Update status
        conversion_results[task_id]["status"] = "processing"
        
        # Create progress callback that integrates with WebSocket
        progress_callback = await create_progress_callback(task_id)
        
        # Get refinement engine
        engine = await get_refinement_engine()
        engine.progress_callback = progress_callback
        
        # Process the PDF
        result = await engine.convert_pdf_to_html(pdf_path, task_id)
        
        # Update conversion results
        conversion_results[task_id].update({
            "status": result["status"],
            "result": result,
            "completed_at": asyncio.get_event_loop().time()
        })
        
        if result["status"] == "success":
            # Notify completion via WebSocket
            await notify_task_completion(
                task_id=task_id,
                status="success",
                combined_html=result["combined_html"],
                total_pages=result["total_pages"],
                processing_time=result["processing_time"],
                errors=result["errors"]
            )
            logger.info(f"PDF conversion completed successfully for task {task_id}")
        else:
            # Notify error via WebSocket
            await notify_error(task_id, result.get("error", "Unknown error occurred"))
            logger.error(f"PDF conversion failed for task {task_id}: {result.get('error')}")
        
    except Exception as e:
        error_message = f"PDF conversion failed: {str(e)}"
        logger.error(f"Error in PDF conversion task {task_id}: {error_message}")
        
        # Update status
        if task_id in conversion_results:
            conversion_results[task_id].update({
                "status": "error",
                "error": error_message,
                "completed_at": asyncio.get_event_loop().time()
            })
        
        # Notify error via WebSocket
        await notify_error(task_id, error_message)
    
    finally:
        # Clean up uploaded file after processing
        try:
            pdf_file_path = Path(pdf_path)
            if pdf_file_path.exists():
                pdf_file_path.unlink()
                logger.info(f"Cleaned up uploaded file: {pdf_path}")
        except Exception as e:
            logger.warning(f"Failed to clean up uploaded file {pdf_path}: {str(e)}")


@app.websocket("/ws/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str):
    """
    WebSocket endpoint for real-time conversion progress updates.
    
    Args:
        websocket: WebSocket connection
        task_id: Task identifier
    """
    logger.info(f"WebSocket connection request for task: {task_id}")
    
    # Connect to WebSocket manager
    connected = await websocket_manager.connect(websocket, task_id)
    
    if not connected:
        logger.error(f"Failed to establish WebSocket connection for task {task_id}")
        return
    
    try:
        # Keep connection alive and handle any client messages
        while True:
            try:
                # Wait for messages from client (keep-alive, etc.)
                data = await websocket.receive_text()
                logger.debug(f"Received WebSocket message from task {task_id}: {data}")
                
                # Echo back or handle specific client messages if needed
                # For now, we just acknowledge receipt
                await websocket.send_text(json.dumps({
                    "type": "acknowledgment",
                    "message": "Message received",
                    "timestamp": asyncio.get_event_loop().time()
                }))
                
            except WebSocketDisconnect:
                logger.info(f"WebSocket client disconnected for task {task_id}")
                break
            except Exception as e:
                logger.error(f"Error in WebSocket communication for task {task_id}: {str(e)}")
                break
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for task {task_id}")
    except Exception as e:
        logger.error(f"WebSocket error for task {task_id}: {str(e)}")
    finally:
        # Clean up connection
        websocket_manager.disconnect(task_id)


@app.get("/api/status/{task_id}")
async def get_task_status(task_id: str):
    """
    Get current status of a conversion task.
    
    Args:
        task_id: Task identifier
        
    Returns:
        Task status information
    """
    if task_id not in conversion_results:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task_info = conversion_results[task_id]
    websocket_status = websocket_manager.get_task_status(task_id)
    
    return {
        "task_id": task_id,
        "status": task_info["status"],
        "filename": task_info["filename"],
        "created_at": task_info["created_at"],
        "completed_at": task_info.get("completed_at"),
        "websocket_connected": websocket_manager.is_connected(task_id),
        "websocket_status": websocket_status,
        "result_available": task_info["status"] == "success" and "result" in task_info,
        "error": task_info.get("error")
    }


@app.get("/api/download/{task_id}")
async def download_html(task_id: str):
    """
    Download the converted HTML file.
    
    Args:
        task_id: Task identifier
        
    Returns:
        HTML file download
    """
    if task_id not in conversion_results:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task_info = conversion_results[task_id]
    
    if task_info["status"] != "success":
        raise HTTPException(status_code=400, detail="Conversion not completed successfully")
    
    if "result" not in task_info or "combined_html" not in task_info["result"]:
        raise HTTPException(status_code=404, detail="HTML result not available")
    
    try:
        # Create temporary HTML file
        html_content = task_info["result"]["combined_html"]
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False)
        temp_file.write(html_content)
        temp_file.close()
        
        # Generate filename
        original_filename = Path(task_info["filename"]).stem
        download_filename = f"{original_filename}_converted.html"
        
        logger.info(f"Serving HTML download for task {task_id}: {download_filename}")
        
        return FileResponse(
            path=temp_file.name,
            filename=download_filename,
            media_type='text/html',
            background=BackgroundTasks()  # This will clean up the temp file after download
        )
        
    except Exception as e:
        logger.error(f"Error serving HTML download for task {task_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate download")


@app.get("/api/tasks")
async def list_tasks():
    """
    List all active and recent conversion tasks.
    
    Returns:
        List of task summaries
    """
    tasks = []
    current_time = asyncio.get_event_loop().time()
    
    for task_id, task_info in conversion_results.items():
        # Only include tasks from the last 24 hours
        age = current_time - task_info["created_at"]
        if age < 86400:  # 24 hours
            tasks.append({
                "task_id": task_id,
                "filename": task_info["filename"],
                "status": task_info["status"],
                "created_at": task_info["created_at"],
                "completed_at": task_info.get("completed_at"),
                "websocket_connected": websocket_manager.is_connected(task_id),
                "age_seconds": age
            })
    
    # Sort by creation time (newest first)
    tasks.sort(key=lambda x: x["created_at"], reverse=True)
    
    return {
        "tasks": tasks,
        "total_tasks": len(tasks),
        "active_connections": websocket_manager.get_active_connections_count()
    }


@app.delete("/api/task/{task_id}")
async def cleanup_task(task_id: str):
    """
    Clean up a completed task and its data.
    
    Args:
        task_id: Task identifier
        
    Returns:
        Cleanup confirmation
    """
    if task_id not in conversion_results:
        raise HTTPException(status_code=404, detail="Task not found")
    
    try:
        # Clean up WebSocket data
        websocket_manager.cleanup_task(task_id)
        
        # Remove from conversion results
        del conversion_results[task_id]
        
        logger.info(f"Cleaned up task {task_id}")
        
        return {
            "message": f"Task {task_id} cleaned up successfully",
            "task_id": task_id
        }
        
    except Exception as e:
        logger.error(f"Error cleaning up task {task_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to cleanup task")


# Application startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Application startup tasks."""
    logger.info("PDF to HTML Converter API starting up...")
    logger.info(f"Upload directory: {UPLOAD_DIR}")
    logger.info(f"Temp directory: {TEMP_DIR}")
    logger.info(f"Screenshots directory: {SCREENSHOTS_DIR}")
    logger.info(f"Max file size: {MAX_FILE_SIZE} bytes")
    logger.info(f"Max refinement iterations: {MAX_REFINEMENT_ITERATIONS}")
    
    # Test Gemini API key
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if gemini_api_key:
        logger.info("Gemini API key configured ✓")
    else:
        logger.warning("Gemini API key not configured - API will fail!")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown tasks."""
    logger.info("PDF to HTML Converter API shutting down...")
    
    # Clean up any remaining resources
    try:
        # Clean up temporary files
        for temp_file in TEMP_DIR.glob("*"):
            if temp_file.is_file():
                temp_file.unlink()
        
        for screenshot_file in SCREENSHOTS_DIR.glob("*"):
            if screenshot_file.is_file():
                screenshot_file.unlink()
                
        logger.info("Temporary files cleaned up")
        
    except Exception as e:
        logger.warning(f"Error during cleanup: {str(e)}")


# Run the application
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
