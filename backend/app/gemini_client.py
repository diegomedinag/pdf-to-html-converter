"""
Gemini API Client

Handles communication with Google's Gemini AI for HTML generation and iterative refinement.
Implements rate limiting and specialized prompts for PDF-to-HTML conversion.
"""

import google.generativeai as genai
import asyncio
import base64
from typing import Optional, List, Dict, Any
from pathlib import Path
import logging
import os
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class GeminiClient:
    """
    Client for interacting with Google's Gemini AI API.
    Specialized for PDF to HTML conversion with iterative refinement.
    """
    
    def __init__(self, api_key: Optional[str] = None, rate_limit_seconds: int = 5):
        """
        Initialize Gemini API client.
        
        Args:
            api_key: Google AI API key (if None, loads from env)
            rate_limit_seconds: Seconds to wait between API calls
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.rate_limit_seconds = rate_limit_seconds
        self.last_call_time = 0
        
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is required")
        
        # Configure Gemini
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-1.5-pro')
        
        logger.info("Gemini client initialized successfully")
    
    async def _rate_limit(self) -> None:
        """Implement rate limiting between API calls."""
        import time
        current_time = time.time()
        time_since_last_call = current_time - self.last_call_time
        
        if time_since_last_call < self.rate_limit_seconds:
            sleep_time = self.rate_limit_seconds - time_since_last_call
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            await asyncio.sleep(sleep_time)
        
        self.last_call_time = time.time()
    
    def _encode_image(self, image_path: str) -> str:
        """
        Encode image to base64 string.
        
        Args:
            image_path: Path to image file
            
        Returns:
            Base64 encoded image string
        """
        try:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            logger.error(f"Error encoding image {image_path}: {str(e)}")
            raise
    
    async def generate_initial_html(self, image_path: str, page_info: Dict) -> str:
        """
        Generate initial HTML from a PDF page image.
        
        Args:
            image_path: Path to the page image
            page_info: Dictionary containing page metadata
            
        Returns:
            Generated HTML string
        """
        await self._rate_limit()
        
        try:
            # Prepare the image
            image_file = genai.upload_file(path=image_path, display_name=f"PDF Page {page_info['page_number']}")
            
            # Initial generation prompt
            prompt = f"""You are an expert frontend developer tasked with converting this PDF page image into accurate HTML5 and CSS code.

CRITICAL REQUIREMENTS:
1. Analyze this image carefully and recreate it as HTML with embedded CSS
2. Include ALL text content exactly as shown in the image
3. Preserve the visual layout, fonts, colors, and spacing as closely as possible
4. Use semantic HTML5 elements where appropriate
5. Embed ALL CSS within a <style> tag in the <head>
6. DO NOT use external libraries or frameworks
7. Make the page responsive but prioritize exact visual matching
8. Pay special attention to:
   - Font families, sizes, and weights
   - Colors and backgrounds
   - Margins, padding, and spacing
   - Text alignment and line heights
   - Any images, graphics, or special formatting

PAGE INFORMATION:
- Page number: {page_info['page_number']}
- Original dimensions: {page_info['width']}pt x {page_info['height']}pt
- Image resolution: {page_info['pixel_width']}px x {page_info['pixel_height']}px

RESPONSE FORMAT:
Return ONLY the complete HTML document, starting with <!DOCTYPE html> and ending with </html>. 
Do not include any explanations or markdown formatting."""

            logger.info(f"Generating initial HTML for page {page_info['page_number']}")
            
            response = self.model.generate_content([prompt, image_file])
            
            if not response.text:
                raise Exception("Empty response from Gemini API")
            
            # Clean up uploaded file
            genai.delete_file(image_file.name)
            
            logger.info(f"Successfully generated initial HTML for page {page_info['page_number']}")
            return response.text.strip()
            
        except Exception as e:
            logger.error(f"Error generating initial HTML for page {page_info['page_number']}: {str(e)}")
            raise Exception(f"Failed to generate HTML: {str(e)}")
    
    async def refine_html(
        self, 
        original_image_path: str, 
        current_html: str, 
        screenshot_path: str,
        page_info: Dict,
        iteration: int = 1
    ) -> str:
        """
        Refine HTML by comparing original image with current rendering.
        
        Args:
            original_image_path: Path to original PDF page image
            current_html: Current HTML code to be refined
            screenshot_path: Path to screenshot of current HTML rendering
            page_info: Dictionary containing page metadata
            iteration: Current refinement iteration number
            
        Returns:
            Refined HTML string
        """
        await self._rate_limit()
        
        try:
            # Upload both images
            original_image = genai.upload_file(path=original_image_path, display_name=f"Original Page {page_info['page_number']}")
            screenshot_image = genai.upload_file(path=screenshot_path, display_name=f"Current Rendering Page {page_info['page_number']}")
            
            # Refinement prompt
            prompt = f"""You are a visual quality control system for frontend development. Your task is to perfect HTML code by comparing its rendered output with a target image.

INPUTS PROVIDED:
1. TARGET IMAGE: The original PDF page that we want to recreate perfectly
2. CURRENT RENDERING: Screenshot of how the current HTML code looks when rendered
3. CURRENT HTML CODE: The code that produced the current rendering

YOUR MISSION:
Analyze the visual differences between the TARGET IMAGE and CURRENT RENDERING, then modify the HTML code to eliminate these differences.

ANALYSIS FOCUS:
- Text content accuracy and completeness
- Font families, sizes, weights, and styles
- Colors (text, backgrounds, borders)
- Layout and positioning
- Spacing (margins, padding, line-height)
- Element alignment and justification  
- Missing or incorrectly positioned elements
- Overall visual hierarchy and structure

REFINEMENT GUIDELINES:
1. Fix ANY visual discrepancies you identify
2. Maintain the existing HTML structure if it's working well
3. Adjust CSS properties to match the target image exactly
4. Add missing content or elements if they exist in target but not current rendering
5. Correct any text that doesn't match exactly
6. Ensure colors, fonts, and spacing are pixel-perfect when possible

PAGE INFORMATION:
- Page: {page_info['page_number']}
- Refinement iteration: {iteration}
- Target dimensions: {page_info['width']}pt x {page_info['height']}pt

CURRENT HTML CODE:
{current_html}

RESPONSE FORMAT:
Return ONLY the improved HTML code. Start with <!DOCTYPE html> and end with </html>.
Do not include explanations, comments, or markdown formatting."""

            logger.info(f"Refining HTML for page {page_info['page_number']}, iteration {iteration}")
            
            response = self.model.generate_content([prompt, original_image, screenshot_image])
            
            if not response.text:
                raise Exception("Empty response from Gemini API during refinement")
            
            # Clean up uploaded files
            genai.delete_file(original_image.name)
            genai.delete_file(screenshot_image.name)
            
            logger.info(f"Successfully refined HTML for page {page_info['page_number']}, iteration {iteration}")
            return response.text.strip()
            
        except Exception as e:
            logger.error(f"Error refining HTML for page {page_info['page_number']}, iteration {iteration}: {str(e)}")
            raise Exception(f"Failed to refine HTML: {str(e)}")
    
    async def analyze_visual_similarity(
        self, 
        original_image_path: str, 
        screenshot_path: str
    ) -> Dict[str, Any]:
        """
        Analyze visual similarity between original and rendered images.
        This is an optional feature for advanced quality assessment.
        
        Args:
            original_image_path: Path to original PDF page image
            screenshot_path: Path to screenshot of rendered HTML
            
        Returns:
            Dictionary with similarity analysis results
        """
        await self._rate_limit()
        
        try:
            # Upload both images
            original_image = genai.upload_file(path=original_image_path, display_name="Original")
            screenshot_image = genai.upload_file(path=screenshot_path, display_name="Rendered")
            
            prompt = """Compare these two images and provide a detailed analysis of their visual similarity.

Analyze and rate (1-10 scale) the following aspects:
1. Text content accuracy and completeness
2. Layout and positioning similarity
3. Color accuracy
4. Font and typography matching
5. Overall visual fidelity

Provide a JSON response with:
- overall_score: number (1-10, where 10 is perfect match)
- text_accuracy: number (1-10)
- layout_similarity: number (1-10) 
- color_accuracy: number (1-10)
- typography_match: number (1-10)
- major_differences: array of strings describing key differences
- recommendations: array of strings with improvement suggestions

Return only valid JSON, no other text."""

            response = self.model.generate_content([prompt, original_image, screenshot_image])
            
            # Clean up uploaded files
            genai.delete_file(original_image.name)
            genai.delete_file(screenshot_image.name)
            
            try:
                import json
                return json.loads(response.text.strip())
            except json.JSONDecodeError:
                # Fallback if JSON parsing fails
                return {
                    "overall_score": 7,
                    "text_accuracy": 7,
                    "layout_similarity": 7,
                    "color_accuracy": 7,
                    "typography_match": 7,
                    "major_differences": ["Unable to analyze"],
                    "recommendations": ["Manual review recommended"]
                }
                
        except Exception as e:
            logger.warning(f"Error analyzing visual similarity: {str(e)}")
            # Return default values if analysis fails
            return {
                "overall_score": 5,
                "text_accuracy": 5,
                "layout_similarity": 5,
                "color_accuracy": 5,
                "typography_match": 5,
                "major_differences": ["Analysis failed"],
                "recommendations": ["Manual review needed"]
            }


# Utility functions for easy access
async def generate_html_from_image(image_path: str, page_info: Dict, api_key: Optional[str] = None) -> str:
    """
    Convenience function to generate HTML from a single image.
    
    Args:
        image_path: Path to PDF page image
        page_info: Page metadata dictionary
        api_key: Optional API key override
        
    Returns:
        Generated HTML string
    """
    client = GeminiClient(api_key=api_key)
    return await client.generate_initial_html(image_path, page_info)


async def refine_html_with_comparison(
    original_image_path: str,
    current_html: str,
    screenshot_path: str,
    page_info: Dict,
    iteration: int = 1,
    api_key: Optional[str] = None
) -> str:
    """
    Convenience function to refine HTML with visual comparison.
    
    Args:
        original_image_path: Path to original PDF page image
        current_html: Current HTML code
        screenshot_path: Path to current rendering screenshot
        page_info: Page metadata dictionary
        iteration: Refinement iteration number
        api_key: Optional API key override
        
    Returns:
        Refined HTML string
    """
    client = GeminiClient(api_key=api_key)
    return await client.refine_html(
        original_image_path, 
        current_html, 
        screenshot_path, 
        page_info, 
        iteration
    )
