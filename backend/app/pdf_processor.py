"""
PDF Processing Module

Extracts PDF pages as high-resolution PNG images using PyMuPDF.
Optimized for visual fidelity to support accurate HTML conversion.
"""

import fitz  # PyMuPDF
import os
import tempfile
import uuid
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class PDFProcessor:
    """
    Handles PDF file processing and page extraction as high-resolution images.
    """
    
    def __init__(self, temp_dir: str = "./temp"):
        """
        Initialize PDF processor.
        
        Args:
            temp_dir: Directory for temporary files
        """
        self.temp_dir = Path(temp_dir)
        self.temp_dir.mkdir(exist_ok=True, parents=True)
        
    async def extract_pages_as_images(
        self, 
        pdf_path: str, 
        dpi: int = 300,
        image_format: str = "png"
    ) -> List[Dict]:
        """
        Extract all pages from PDF as high-resolution images.
        
        Args:
            pdf_path: Path to the PDF file
            dpi: Resolution for image extraction (default: 300 DPI for high quality)
            image_format: Output image format (png, jpeg)
            
        Returns:
            List of dictionaries containing page information and image paths
            
        Raises:
            Exception: If PDF processing fails
        """
        try:
            # Open PDF document
            pdf_document = fitz.open(pdf_path)
            pages_data = []
            
            logger.info(f"Processing PDF with {len(pdf_document)} pages")
            
            for page_num in range(len(pdf_document)):
                page = pdf_document[page_num]
                
                # Calculate zoom matrix for high-resolution rendering
                zoom = dpi / 72.0  # 72 DPI is the default
                mat = fitz.Matrix(zoom, zoom)
                
                # Render page as pixmap
                pix = page.get_pixmap(matrix=mat)
                
                # Generate unique filename for this page image
                image_filename = f"page_{page_num + 1}_{uuid.uuid4().hex}.{image_format}"
                image_path = self.temp_dir / image_filename
                
                # Save image
                if image_format.lower() == "png":
                    pix.save(str(image_path))
                elif image_format.lower() == "jpeg":
                    pix.save(str(image_path), jpg_quality=95)
                else:
                    raise ValueError(f"Unsupported image format: {image_format}")
                
                # Get page dimensions
                rect = page.rect
                page_width = rect.width
                page_height = rect.height
                
                # Store page information
                page_info = {
                    "page_number": page_num + 1,
                    "image_path": str(image_path),
                    "image_filename": image_filename,
                    "width": page_width,
                    "height": page_height,
                    "dpi": dpi,
                    "format": image_format,
                    "pixel_width": pix.width,
                    "pixel_height": pix.height
                }
                
                pages_data.append(page_info)
                
                logger.info(f"Extracted page {page_num + 1}: {page_width}x{page_height}pt -> {pix.width}x{pix.height}px")
                
                # Clean up pixmap
                pix = None
                
            pdf_document.close()
            
            logger.info(f"Successfully extracted {len(pages_data)} pages from PDF")
            return pages_data
            
        except Exception as e:
            logger.error(f"Error processing PDF {pdf_path}: {str(e)}")
            raise Exception(f"Failed to process PDF: {str(e)}")
    
    async def get_pdf_info(self, pdf_path: str) -> Dict:
        """
        Get basic information about a PDF file.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Dictionary containing PDF metadata
        """
        try:
            pdf_document = fitz.open(pdf_path)
            
            metadata = pdf_document.metadata
            page_count = len(pdf_document)
            
            # Get first page dimensions as representative
            first_page = pdf_document[0] if page_count > 0 else None
            page_size = {
                "width": first_page.rect.width if first_page else 0,
                "height": first_page.rect.height if first_page else 0
            }
            
            pdf_info = {
                "title": metadata.get("title", ""),
                "author": metadata.get("author", ""),
                "subject": metadata.get("subject", ""),
                "creator": metadata.get("creator", ""),
                "producer": metadata.get("producer", ""),
                "created": metadata.get("creationDate", ""),
                "modified": metadata.get("modDate", ""),
                "page_count": page_count,
                "page_size": page_size,
                "file_size": os.path.getsize(pdf_path)
            }
            
            pdf_document.close()
            return pdf_info
            
        except Exception as e:
            logger.error(f"Error getting PDF info for {pdf_path}: {str(e)}")
            raise Exception(f"Failed to get PDF info: {str(e)}")
    
    def cleanup_temp_files(self, pages_data: List[Dict]) -> None:
        """
        Clean up temporary image files.
        
        Args:
            pages_data: List of page data dictionaries containing image paths
        """
        for page_data in pages_data:
            try:
                image_path = Path(page_data["image_path"])
                if image_path.exists():
                    image_path.unlink()
                    logger.debug(f"Cleaned up temporary file: {image_path}")
            except Exception as e:
                logger.warning(f"Could not clean up file {page_data.get('image_path')}: {str(e)}")
    
    def validate_pdf(self, pdf_path: str) -> bool:
        """
        Validate if file is a readable PDF.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            True if valid PDF, False otherwise
        """
        try:
            pdf_document = fitz.open(pdf_path)
            page_count = len(pdf_document)
            pdf_document.close()
            return page_count > 0
        except Exception as e:
            logger.warning(f"PDF validation failed for {pdf_path}: {str(e)}")
            return False


# Utility functions for working with PDF processor
async def process_pdf_file(pdf_path: str, temp_dir: str = "./temp") -> Tuple[List[Dict], Dict]:
    """
    Convenience function to process a PDF file and extract pages.
    
    Args:
        pdf_path: Path to the PDF file
        temp_dir: Directory for temporary files
        
    Returns:
        Tuple of (pages_data, pdf_info)
    """
    processor = PDFProcessor(temp_dir)
    
    # Validate PDF first
    if not processor.validate_pdf(pdf_path):
        raise ValueError("Invalid or unreadable PDF file")
    
    # Get PDF info
    pdf_info = await processor.get_pdf_info(pdf_path)
    
    # Extract pages
    pages_data = await processor.extract_pages_as_images(pdf_path)
    
    return pages_data, pdf_info


def cleanup_pdf_temp_files(pages_data: List[Dict], temp_dir: str = "./temp") -> None:
    """
    Convenience function to clean up temporary files.
    
    Args:
        pages_data: List of page data dictionaries
        temp_dir: Directory containing temporary files
    """
    processor = PDFProcessor(temp_dir)
    processor.cleanup_temp_files(pages_data)
