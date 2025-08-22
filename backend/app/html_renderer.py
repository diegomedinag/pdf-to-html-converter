"""
HTML Renderer Module

Uses Playwright to render HTML in a headless browser and take screenshots.
Optimized for accurate visual comparison with original PDF pages.
"""

from playwright.async_api import async_playwright, Browser, BrowserContext, Page
import asyncio
import uuid
import os
from typing import Optional, Dict, Any
from pathlib import Path
import logging
import base64

logger = logging.getLogger(__name__)


class HTMLRenderer:
    """
    Renders HTML content using Playwright and captures screenshots for comparison.
    """
    
    def __init__(self, screenshots_dir: str = "./screenshots", headless: bool = True):
        """
        Initialize HTML renderer.
        
        Args:
            screenshots_dir: Directory to save screenshots
            headless: Run browser in headless mode
        """
        self.screenshots_dir = Path(screenshots_dir)
        self.screenshots_dir.mkdir(exist_ok=True, parents=True)
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.playwright = None
        
    async def __aenter__(self):
        """Async context manager entry."""
        await self.start_browser()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop_browser()
    
    async def start_browser(self) -> None:
        """Start the Playwright browser."""
        try:
            self.playwright = await async_playwright().start()
            
            # Use Chromium for consistency
            self.browser = await self.playwright.chromium.launch(
                headless=self.headless,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--no-first-run',
                    '--no-default-browser-check',
                    '--disable-extensions'
                ]
            )
            
            # Create browser context with specific viewport
            self.context = await self.browser.new_context(
                viewport={'width': 1200, 'height': 800},
                device_scale_factor=1,
                ignore_https_errors=True
            )
            
            logger.info("Playwright browser started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start browser: {str(e)}")
            raise Exception(f"Browser startup failed: {str(e)}")
    
    async def stop_browser(self) -> None:
        """Stop the Playwright browser."""
        try:
            if self.context:
                await self.context.close()
                self.context = None
            
            if self.browser:
                await self.browser.close()
                self.browser = None
                
            if self.playwright:
                await self.playwright.stop()
                self.playwright = None
                
            logger.info("Playwright browser stopped successfully")
            
        except Exception as e:
            logger.warning(f"Error stopping browser: {str(e)}")
    
    async def render_and_screenshot(
        self, 
        html_content: str, 
        page_info: Dict, 
        wait_for_load: int = 2000,
        full_page: bool = True
    ) -> str:
        """
        Render HTML content and take a screenshot.
        
        Args:
            html_content: HTML content to render
            page_info: Page metadata dictionary
            wait_for_load: Milliseconds to wait for page load
            full_page: Whether to capture full page or viewport only
            
        Returns:
            Path to the screenshot file
        """
        if not self.browser or not self.context:
            raise Exception("Browser not started. Use async context manager or call start_browser()")
        
        page = None
        try:
            # Create a new page
            page = await self.context.new_page()
            
            # Set viewport size based on page dimensions if provided
            if page_info.get('pixel_width') and page_info.get('pixel_height'):
                viewport_width = min(page_info['pixel_width'], 1920)  # Cap at reasonable size
                viewport_height = min(page_info['pixel_height'], 1080)
                await page.set_viewport_size({
                    'width': int(viewport_width),
                    'height': int(viewport_height)
                })
            
            logger.info(f"Rendering HTML for page {page_info.get('page_number', 'unknown')}")
            
            # Load HTML content
            await page.set_content(html_content, wait_until='networkidle')
            
            # Additional wait for any dynamic content
            await page.wait_for_timeout(wait_for_load)
            
            # Generate unique filename
            screenshot_filename = f"screenshot_{page_info.get('page_number', 'unknown')}_{uuid.uuid4().hex}.png"
            screenshot_path = self.screenshots_dir / screenshot_filename
            
            # Take screenshot
            await page.screenshot(
                path=str(screenshot_path),
                full_page=full_page,
                type='png'
            )
            
            logger.info(f"Screenshot saved: {screenshot_path}")
            
            return str(screenshot_path)
            
        except Exception as e:
            logger.error(f"Error rendering HTML for page {page_info.get('page_number', 'unknown')}: {str(e)}")
            raise Exception(f"Failed to render HTML: {str(e)}")
        finally:
            if page:
                await page.close()
    
    async def compare_with_target_size(
        self, 
        html_content: str, 
        target_width: int, 
        target_height: int,
        page_number: int = 1
    ) -> str:
        """
        Render HTML with specific target dimensions for better comparison.
        
        Args:
            html_content: HTML content to render
            target_width: Target width in pixels
            target_height: Target height in pixels  
            page_number: Page number for naming
            
        Returns:
            Path to the screenshot file
        """
        if not self.browser or not self.context:
            raise Exception("Browser not started. Use async context manager or call start_browser()")
        
        page = None
        try:
            # Create a new page with exact target dimensions
            page = await self.context.new_page()
            await page.set_viewport_size({
                'width': target_width,
                'height': target_height
            })
            
            # Load HTML content
            await page.set_content(html_content, wait_until='networkidle')
            await page.wait_for_timeout(2000)
            
            # Generate filename
            screenshot_filename = f"comparison_{page_number}_{target_width}x{target_height}_{uuid.uuid4().hex}.png"
            screenshot_path = self.screenshots_dir / screenshot_filename
            
            # Take screenshot with exact dimensions
            await page.screenshot(
                path=str(screenshot_path),
                full_page=False,  # Use viewport size
                type='png'
            )
            
            logger.info(f"Comparison screenshot saved: {screenshot_path}")
            return str(screenshot_path)
            
        except Exception as e:
            logger.error(f"Error in comparison rendering: {str(e)}")
            raise Exception(f"Failed to render for comparison: {str(e)}")
        finally:
            if page:
                await page.close()
    
    async def get_page_dimensions(self, html_content: str) -> Dict[str, int]:
        """
        Get the actual rendered dimensions of HTML content.
        
        Args:
            html_content: HTML content to analyze
            
        Returns:
            Dictionary with width and height of rendered content
        """
        if not self.browser or not self.context:
            raise Exception("Browser not started. Use async context manager or call start_browser()")
        
        page = None
        try:
            page = await self.context.new_page()
            await page.set_content(html_content, wait_until='networkidle')
            await page.wait_for_timeout(1000)
            
            # Get document dimensions
            dimensions = await page.evaluate("""
                () => {
                    return {
                        width: Math.max(
                            document.body.scrollWidth,
                            document.body.offsetWidth,
                            document.documentElement.clientWidth,
                            document.documentElement.scrollWidth,
                            document.documentElement.offsetWidth
                        ),
                        height: Math.max(
                            document.body.scrollHeight,
                            document.body.offsetHeight,
                            document.documentElement.clientHeight,
                            document.documentElement.scrollHeight,
                            document.documentElement.offsetHeight
                        )
                    }
                }
            """)
            
            return {
                'width': int(dimensions['width']),
                'height': int(dimensions['height'])
            }
            
        except Exception as e:
            logger.warning(f"Error getting page dimensions: {str(e)}")
            return {'width': 800, 'height': 600}  # Default fallback
        finally:
            if page:
                await page.close()
    
    def cleanup_screenshot(self, screenshot_path: str) -> None:
        """
        Clean up a screenshot file.
        
        Args:
            screenshot_path: Path to the screenshot file to delete
        """
        try:
            screenshot_file = Path(screenshot_path)
            if screenshot_file.exists():
                screenshot_file.unlink()
                logger.debug(f"Cleaned up screenshot: {screenshot_path}")
        except Exception as e:
            logger.warning(f"Could not clean up screenshot {screenshot_path}: {str(e)}")
    
    def cleanup_all_screenshots(self) -> None:
        """Clean up all screenshot files in the screenshots directory."""
        try:
            for screenshot_file in self.screenshots_dir.glob("*.png"):
                screenshot_file.unlink()
                logger.debug(f"Cleaned up screenshot: {screenshot_file}")
            logger.info("All screenshots cleaned up")
        except Exception as e:
            logger.warning(f"Error cleaning up screenshots: {str(e)}")


# Utility functions for easy access
async def render_html_to_screenshot(
    html_content: str, 
    page_info: Dict, 
    screenshots_dir: str = "./screenshots"
) -> str:
    """
    Convenience function to render HTML and get screenshot.
    
    Args:
        html_content: HTML content to render
        page_info: Page metadata dictionary
        screenshots_dir: Directory for screenshots
        
    Returns:
        Path to screenshot file
    """
    async with HTMLRenderer(screenshots_dir) as renderer:
        return await renderer.render_and_screenshot(html_content, page_info)


async def get_html_dimensions(html_content: str) -> Dict[str, int]:
    """
    Convenience function to get HTML content dimensions.
    
    Args:
        html_content: HTML content to analyze
        
    Returns:
        Dictionary with width and height
    """
    async with HTMLRenderer() as renderer:
        return await renderer.get_page_dimensions(html_content)


async def render_for_comparison(
    html_content: str,
    target_width: int,
    target_height: int,
    page_number: int = 1,
    screenshots_dir: str = "./screenshots"
) -> str:
    """
    Convenience function to render HTML with specific dimensions for comparison.
    
    Args:
        html_content: HTML content to render
        target_width: Target width in pixels
        target_height: Target height in pixels
        page_number: Page number for naming
        screenshots_dir: Directory for screenshots
        
    Returns:
        Path to screenshot file
    """
    async with HTMLRenderer(screenshots_dir) as renderer:
        return await renderer.compare_with_target_size(
            html_content, target_width, target_height, page_number
        )
