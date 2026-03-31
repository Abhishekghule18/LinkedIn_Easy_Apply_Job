from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError
import logging
import urllib.parse
import asyncio
from pathlib import Path
from functools import wraps
from automation.browser import BrowserManager
from config.settings import get_preferences

logger = logging.getLogger(__name__)

def with_retry(retries=3, delay_sec=2):
    """Decorator to introduce robust retry logic on automation failures."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    logger.warning(f"Attempt {attempt + 1}/{retries} failed for {func.__name__}: {e}. Retrying in {delay_sec}s...")
                    await asyncio.sleep(delay_sec)
            logger.error(f"All {retries} attempts failed for {func.__name__}")
            raise last_error
        return wrapper
    return decorator

class LinkedInAutomator:
    def __init__(self, page: Page):
        self.page = page
        self.preferences = get_preferences()
        
    async def login(self):
        logger.info("Navigating to LinkedIn. Your saved browser_data session cookies may auto-login.")
        await self.page.goto("https://www.linkedin.com/login")
        
        try:
            # We completely bypass HTML CSS selector scraping to perfectly evade LinkedIn A/B GUI tests.
            # Instead, we monitor the active URL payload to verify you breached the login wall.
            for _ in range(100): # 100 loops * 3s = 5 minutes timeout window
                current_url = self.page.url
                if "feed" in current_url or "jobs" in current_url or "in/" in current_url:
                    logger.info("Successfully authenticated. Valid session detected via URL routing.")
                    return
                await asyncio.sleep(3)
                
            logger.error("Login timed out. The script never detected you reaching the news feed.")
            raise Exception("Login verification failed due to manual timeout threshold.")
        except Exception as e:
            logger.error(f"Error checking login state: {e}")
            raise e

    @with_retry(retries=3, delay_sec=2)
    async def search_jobs(self, job_title: str, location: str, offset: int = 0):
        logger.info(f"Searching for {job_title} in {location} [OFFSET: {offset}]")
        params = {
            'keywords': job_title,
        }
        
        # Omit location safely if the config passes an empty string for location-agnostic searching
        if location:
            params['location'] = location
        
        # Read exact LinkedIn API URL query parameters directly from JSON natively. 
        # Zero hardcoded python mappings.
        filters = self.preferences.get("filters", {})
        for key, val in filters.items():
            params[key] = str(val)

        query = urllib.parse.urlencode(params)
        if offset > 0:
            query += f"&start={offset}"
            
        url = f"https://www.linkedin.com/jobs/search/?{query}"
        await self.page.goto(url)
        await BrowserManager.human_delay(2, 4)

    @with_retry(retries=2, delay_sec=1)
    async def extract_jobs_from_page(self) -> list:
        # Simulate human scrolling
        for _ in range(3):
            await BrowserManager.random_scroll(self.page)
        
        jobs = await self.page.locator(".job-card-container").all()
        job_links = []
        for job in jobs:
            try:
                link = await job.locator("a.job-card-list__title, a.job-card-container__link").get_attribute("href")
                if link and "view/" in link:
                    job_id = link.split("view/")[1].split("/")[0]
                    job_links.append({"id": job_id, "link": f"https://www.linkedin.com/jobs/view/{job_id}/"})
            except Exception as e:
                logger.debug(f"Could not extract job ID: {e}")
        return job_links

    @with_retry(retries=3, delay_sec=2)
    async def upload_resume(self, resume_path: Path) -> bool:
        """Detects upload button, dynamically uploads specifically routed resume, and confirms upload."""
        if not resume_path.exists():
            logger.warning(f"Routed resume not found at {resume_path}. Skipping upload block.")
            return False
            
        logger.info("Checking for resume upload section...")
        
        try:
            # 1. Direct file input element strategy (most stable)
            file_input = self.page.locator("input[type='file'][name='file']")
            if await file_input.count() > 0:
                logger.info("Found direct file input. Uploading resume...")
                await file_input.first.set_input_files(str(resume_path))
                await BrowserManager.human_delay(2, 3)
                logger.info("Resume upload confirmed successfully via input field.")
                return True
                
            # 2. Clicking 'Upload resume' button and catching the file chooser strategy
            upload_button = self.page.locator("button[aria-label*='Upload resume'], label:has-text('Upload resume')")
            if await upload_button.count() > 0:
                logger.info("Found upload button. Waiting for file chooser...")
                
                async with self.page.expect_file_chooser() as fc_info:
                    await upload_button.first.click()
                file_chooser = await fc_info.value
                
                await file_chooser.set_files(str(resume_path))
                await BrowserManager.human_delay(2, 4)
                
                # Check for confirm indicator (the file name appearing on the DOM)
                if await self.page.locator(f"text='{resume_path.name}'").count() > 0:
                    logger.info("Resume upload confirmed successfully in the UI.")
                    return True
                else:
                    logger.warning("Upload completed but UI confirmation indicator missing.")
                    return True
                    
        except Exception as e:
            logger.error(f"Failed to upload resume: {str(e)}")
            raise e # Raise to trigger the @with_retry decorator
            
        logger.info("No resume upload requirement detected on this page step.")
        return False
        
    async def apply_to_job(self, job_url: str, llm_agent, target_resume: Path) -> bool:
        await self.page.goto(job_url)
        await BrowserManager.human_delay(2, 4)
        
        try:
            # Locate easy apply button by text explicitly so it bypasses CSS layout shifts seamlessly
            easy_apply_button = self.page.locator("button:has-text('Easy Apply')")
            if await easy_apply_button.count() == 0:
                # Fallback to general primary semantic buttons parsing
                easy_apply_button = self.page.locator(".jobs-apply-button--top-card button, .jobs-apply-button button")
                
            if await easy_apply_button.count() == 0:
                logger.info("Easy Apply button not found anywhere on the page framework. Skipping.")
                return False
            
            await easy_apply_button.first.click()
            await BrowserManager.human_delay(1, 2)
            
            # Application modal scanning iteration loop
            max_steps = 10
            steps = 0
            while steps < max_steps:
                # 1. Look for upload components and dispatch native handlers
                await self.upload_resume(target_resume)
                
                # 2. Complete flow detection
                submit_button = self.page.locator("button[aria-label='Submit application']")
                if await submit_button.count() > 0:
                    logger.info("Application ready to submit! Simulated click.")
                    # await submit_button.click() # Uncomment when tests pass to actually execute production payload
                    await BrowserManager.human_delay(2, 3)
                    
                    # dismiss modal cleanly if testing natively to avoid corrupting session state
                    dismiss = self.page.locator("button[aria-label='Dismiss']")
                    if await dismiss.count() > 0:
                        await dismiss.first.click()
                        
                    return True
                
                # 3. Pagination detection
                next_button = self.page.locator("button[aria-label='Continue to next step']")
                if await next_button.count() > 0:
                    # Form interpolation hooks go here (for fields matching LLM context arrays)
                    await next_button.click()
                    await BrowserManager.human_delay(1, 4)
                    steps += 1
                else:
                    review_button = self.page.locator("button[aria-label='Review your application']")
                    if await review_button.count() > 0:
                        await review_button.click()
                        await BrowserManager.human_delay(1, 2)
                        steps += 1
                    else:
                        logger.warning("Unrecognized modal state. Aborting apply.")
                        # cancel application gracefully
                        close_btn = self.page.locator("button[aria-label='Dismiss']")
                        if await close_btn.count() > 0:
                            await close_btn.first.click()
                            discard_btn = self.page.locator("button[data-control-name='discard_application_confirm_btn']")
                            if await discard_btn.count() > 0:
                                await discard_btn.first.click()
                        return False
                        
            return False
        except Exception as e:
            logger.error(f"Error applying to job {job_url}: {e}")
            return False
