"""
Iterative Refinement Engine

Coordinates the complete PDF to HTML conversion process with iterative refinement.
This is the core orchestration module that brings together PDF processing, 
AI generation, and visual comparison for maximum fidelity.
"""

import asyncio
import os
import uuid
from typing import Dict, List, Optional, Callable, Any
from pathlib import Path
import logging
from dotenv import load_dotenv

from .pdf_processor import PDFProcessor
from .gemini_client import GeminiClient
from .html_renderer import HTMLRenderer

load_dotenv()
logger = logging.getLogger(__name__)


class RefinementEngine:
    """
    Main orchestration engine for PDF to HTML conversion with iterative refinement.
    """
    
    def __init__(
        self,
        temp_dir: str = "./temp",
        screenshots_dir: str = "./screenshots", 
        max_iterations: int = 2,
        gemini_api_key: Optional[str] = None,
        progress_callback: Optional[Callable] = None
    ):
        """
        Initialize the refinement engine.
        
        Args:
            temp_dir: Directory for temporary files
            screenshots_dir: Directory for screenshots
            max_iterations: Maximum refinement iterations per page
            gemini_api_key: Gemini API key (loads from env if None)
            progress_callback: Function to call for progress updates
        """
        self.temp_dir = Path(temp_dir)
        self.screenshots_dir = Path(screenshots_dir)
        self.max_iterations = max_iterations
        self.progress_callback = progress_callback
        
        # Create directories
        self.temp_dir.mkdir(exist_ok=True, parents=True)
        self.screenshots_dir.mkdir(exist_ok=True, parents=True)
        
        # Initialize components
        self.pdf_processor = PDFProcessor(str(self.temp_dir))
        self.gemini_client = GeminiClient(api_key=gemini_api_key)
        self.html_renderer = HTMLRenderer(str(self.screenshots_dir))
        
        # Task storage
        self.active_tasks: Dict[str, Dict] = {}
        
        logger.info("Refinement engine initialized successfully")
    
    async def convert_pdf_to_html(
        self, 
        pdf_path: str, 
        task_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Convert entire PDF to HTML with iterative refinement.
        
        Args:
            pdf_path: Path to the PDF file
            task_id: Optional task ID for tracking
            
        Returns:
            Dictionary containing conversion results
        """
        if not task_id:
            task_id = str(uuid.uuid4())
        
        # Initialize task tracking
        task_info = {
            'task_id': task_id,
            'pdf_path': pdf_path,
            'status': 'started',
            'total_pages': 0,
            'completed_pages': 0,
            'pages': [],
            'errors': [],
            'start_time': asyncio.get_event_loop().time()
        }
        self.active_tasks[task_id] = task_info
        
        try:
            await self._update_progress(task_id, "Extracting PDF pages...")
            
            # Step 1: Extract PDF pages as images
            pages_data, pdf_info = await self.pdf_processor.process_pdf_file(pdf_path, str(self.temp_dir))
            
            task_info['total_pages'] = len(pages_data)
            task_info['pdf_info'] = pdf_info
            
            await self._update_progress(
                task_id, 
                f"Processing {len(pages_data)} pages with iterative refinement..."
            )
            
            # Step 2: Process each page with refinement
            converted_pages = []
            for page_data in pages_data:
                try:
                    page_result = await self._process_single_page(task_id, page_data)
                    converted_pages.append(page_result)
                    task_info['completed_pages'] += 1
                    
                    # Send page completion update
                    await self._update_progress(
                        task_id,
                        f"Completed page {page_data['page_number']} of {len(pages_data)}"
                    )
                    
                except Exception as e:
                    error_msg = f"Error processing page {page_data['page_number']}: {str(e)}"
                    logger.error(error_msg)
                    task_info['errors'].append(error_msg)
                    
                    # Add a fallback page with basic HTML
                    fallback_page = {
                        'page_number': page_data['page_number'],
                        'html_content': self._generate_fallback_html(page_data),
                        'refinement_iterations': 0,
                        'final_quality_score': 0,
                        'processing_time': 0,
                        'error': str(e)
                    }
                    converted_pages.append(fallback_page)
                    task_info['completed_pages'] += 1
            
            # Step 3: Combine all pages into final result
            combined_html = self._combine_pages_to_html(converted_pages, pdf_info)
            
            # Update final task status
            task_info['status'] = 'completed'
            task_info['pages'] = converted_pages
            task_info['combined_html'] = combined_html
            task_info['end_time'] = asyncio.get_event_loop().time()
            task_info['total_time'] = task_info['end_time'] - task_info['start_time']
            
            await self._update_progress(task_id, "Conversion completed successfully!")
            
            # Cleanup temporary files
            await self._cleanup_temp_files(pages_data)
            
            return {
                'task_id': task_id,
                'status': 'success',
                'total_pages': len(pages_data),
                'completed_pages': len(converted_pages),
                'pages': converted_pages,
                'combined_html': combined_html,
                'pdf_info': pdf_info,
                'processing_time': task_info['total_time'],
                'errors': task_info['errors']
            }
            
        except Exception as e:
            error_msg = f"Fatal error in PDF conversion: {str(e)}"
            logger.error(error_msg)
            
            task_info['status'] = 'failed'
            task_info['errors'].append(error_msg)
            
            await self._update_progress(task_id, f"Conversion failed: {str(e)}")
            
            return {
                'task_id': task_id,
                'status': 'error',
                'error': str(e),
                'errors': task_info['errors']
            }
    
    async def _process_single_page(self, task_id: str, page_data: Dict) -> Dict[str, Any]:
        """
        Process a single PDF page with iterative refinement.
        
        Args:
            task_id: Task identifier
            page_data: Page data from PDF processor
            
        Returns:
            Dictionary containing page processing results
        """
        page_number = page_data['page_number']
        start_time = asyncio.get_event_loop().time()
        
        logger.info(f"Processing page {page_number} with iterative refinement")
        
        # Step 1: Generate initial HTML from PDF image
        await self._update_progress(
            task_id, 
            f"Generating HTML for page {page_number}..."
        )
        
        current_html = await self.gemini_client.generate_initial_html(
            page_data['image_path'], 
            page_data
        )
        
        # Step 2: Iterative refinement process
        refinement_iterations = 0
        quality_scores = []
        
        # Start browser for this page processing
        await self.html_renderer.start_browser()
        
        try:
            for iteration in range(self.max_iterations):
                refinement_iterations += 1
                
                await self._update_progress(
                    task_id,
                    f"Refining page {page_number} (iteration {iteration + 1}/{self.max_iterations})..."
                )
                
                # Render current HTML and take screenshot
                screenshot_path = await self.html_renderer.render_and_screenshot(
                    current_html, 
                    page_data
                )
                
                # Refine HTML using visual comparison
                try:
                    refined_html = await self.gemini_client.refine_html(
                        page_data['image_path'],
                        current_html,
                        screenshot_path,
                        page_data,
                        iteration + 1
                    )
                    
                    # Optional: Analyze quality (if we want to track improvement)
                    try:
                        quality_analysis = await self.gemini_client.analyze_visual_similarity(
                            page_data['image_path'],
                            screenshot_path
                        )
                        quality_scores.append(quality_analysis.get('overall_score', 7))
                    except Exception as e:
                        logger.warning(f"Quality analysis failed for page {page_number}: {str(e)}")
                        quality_scores.append(7)  # Default score
                    
                    # Update current HTML for next iteration
                    current_html = refined_html
                    
                    # Clean up screenshot
                    self.html_renderer.cleanup_screenshot(screenshot_path)
                    
                except Exception as e:
                    logger.warning(f"Refinement iteration {iteration + 1} failed for page {page_number}: {str(e)}")
                    # Continue with current HTML if refinement fails
                    break
            
        finally:
            # Stop browser for this page
            await self.html_renderer.stop_browser()
        
        # Calculate processing time
        processing_time = asyncio.get_event_loop().time() - start_time
        
        # Determine final quality score
        final_quality_score = max(quality_scores) if quality_scores else 7
        
        result = {
            'page_number': page_number,
            'html_content': current_html,
            'refinement_iterations': refinement_iterations,
            'final_quality_score': final_quality_score,
            'quality_progression': quality_scores,
            'processing_time': processing_time,
            'original_dimensions': {
                'width': page_data['width'],
                'height': page_data['height']
            },
            'pixel_dimensions': {
                'width': page_data['pixel_width'],
                'height': page_data['pixel_height']
            }
        }
        
        logger.info(f"Completed page {page_number} processing in {processing_time:.2f}s with {refinement_iterations} iterations")
        
        return result
    
    def _combine_pages_to_html(self, pages: List[Dict], pdf_info: Dict) -> str:
        """
        Combine individual page HTML into a single document.
        
        Args:
            pages: List of page processing results
            pdf_info: PDF metadata
            
        Returns:
            Combined HTML string
        """
        # Sort pages by page number
        sorted_pages = sorted(pages, key=lambda p: p['page_number'])
        
        # Build combined HTML
        html_parts = [
            '<!DOCTYPE html>',
            '<html lang="en">',
            '<head>',
            '    <meta charset="UTF-8">',
            '    <meta name="viewport" content="width=device-width, initial-scale=1.0">',
            f'    <title>{pdf_info.get("title", "Converted PDF Document")}</title>',
            '    <style>',
            '        body { margin: 0; padding: 20px; font-family: Arial, sans-serif; }',
            '        .pdf-page { margin-bottom: 40px; border-bottom: 2px solid #eee; padding-bottom: 20px; }',
            '        .page-header { color: #666; font-size: 12px; margin-bottom: 10px; }',
            '        .page-content { /* Individual page styles will be embedded */ }',
            '    </style>',
            '</head>',
            '<body>'
        ]
        
        # Add each page
        for page in sorted_pages:
            html_parts.extend([
                f'    <div class="pdf-page" id="page-{page["page_number"]}">',
                f'        <div class="page-header">Page {page["page_number"]} of {len(sorted_pages)}</div>',
                '        <div class="page-content">'
            ])
            
            # Extract body content from individual page HTML
            page_html = page['html_content']
            try:
                # Extract content between <body> tags
                body_start = page_html.find('<body')
                if body_start != -1:
                    body_start = page_html.find('>', body_start) + 1
                    body_end = page_html.rfind('</body>')
                    if body_end != -1:
                        page_content = page_html[body_start:body_end].strip()
                    else:
                        page_content = page_html[body_start:].strip()
                else:
                    # Fallback: use entire HTML if no body tags
                    page_content = page_html
                
                html_parts.append(f'            {page_content}')
                
            except Exception as e:
                logger.warning(f"Error extracting content from page {page['page_number']}: {str(e)}")
                html_parts.append(f'            <p>Error rendering page {page["page_number"]}</p>')
            
            html_parts.extend([
                '        </div>',
                '    </div>'
            ])
        
        html_parts.extend([
            '</body>',
            '</html>'
        ])
        
        return '\n'.join(html_parts)
    
    def _generate_fallback_html(self, page_data: Dict) -> str:
        """
        Generate a basic fallback HTML for pages that failed to process.
        
        Args:
            page_data: Page data dictionary
            
        Returns:
            Basic HTML string
        """
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Page {page_data['page_number']}</title>
    <style>
        body {{
            margin: 40px;
            font-family: Arial, sans-serif;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 60vh;
            background-color: #f8f9fa;
        }}
        .error-message {{
            text-align: center;
            color: #6c757d;
            padding: 40px;
            border: 2px dashed #dee2e6;
            border-radius: 10px;
        }}
    </style>
</head>
<body>
    <div class="error-message">
        <h2>Page {page_data['page_number']}</h2>
        <p>This page could not be processed automatically.</p>
        <p><small>Original dimensions: {page_data['width']}pt × {page_data['height']}pt</small></p>
    </div>
</body>
</html>"""
    
    async def _update_progress(self, task_id: str, message: str, data: Optional[Dict] = None) -> None:
        """
        Send progress update via callback.
        
        Args:
            task_id: Task identifier
            message: Progress message
            data: Optional additional data
        """
        if self.progress_callback:
            try:
                update = {
                    'task_id': task_id,
                    'message': message,
                    'timestamp': asyncio.get_event_loop().time()
                }
                if data:
                    update.update(data)
                
                # Call progress callback
                if asyncio.iscoroutinefunction(self.progress_callback):
                    await self.progress_callback(update)
                else:
                    self.progress_callback(update)
                    
            except Exception as e:
                logger.warning(f"Progress callback failed: {str(e)}")
        
        # Also log the progress
        logger.info(f"Task {task_id}: {message}")
    
    async def _cleanup_temp_files(self, pages_data: List[Dict]) -> None:
        """
        Clean up temporary files created during processing.
        
        Args:
            pages_data: List of page data dictionaries
        """
        try:
            # Clean up PDF page images
            self.pdf_processor.cleanup_temp_files(pages_data)
            
            # Clean up screenshots
            self.html_renderer.cleanup_all_screenshots()
            
            logger.info("Temporary files cleaned up successfully")
            
        except Exception as e:
            logger.warning(f"Error during cleanup: {str(e)}")
    
    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """
        Get current status of a task.
        
        Args:
            task_id: Task identifier
            
        Returns:
            Task status dictionary or None if not found
        """
        return self.active_tasks.get(task_id)
    
    def cleanup_task(self, task_id: str) -> None:
        """
        Clean up task data after completion.
        
        Args:
            task_id: Task identifier
        """
        if task_id in self.active_tasks:
            del self.active_tasks[task_id]
            logger.info(f"Task {task_id} cleaned up")


# Utility function for easy access
async def convert_pdf_with_refinement(
    pdf_path: str,
    temp_dir: str = "./temp",
    screenshots_dir: str = "./screenshots",
    max_iterations: int = 2,
    progress_callback: Optional[Callable] = None
) -> Dict[str, Any]:
    """
    Convenience function to convert PDF with refinement.
    
    Args:
        pdf_path: Path to PDF file
        temp_dir: Directory for temporary files
        screenshots_dir: Directory for screenshots
        max_iterations: Maximum refinement iterations
        progress_callback: Optional progress callback function
        
    Returns:
        Conversion results dictionary
    """
    engine = RefinementEngine(
        temp_dir=temp_dir,
        screenshots_dir=screenshots_dir,
        max_iterations=max_iterations,
        progress_callback=progress_callback
    )
    
    return await engine.convert_pdf_to_html(pdf_path)
