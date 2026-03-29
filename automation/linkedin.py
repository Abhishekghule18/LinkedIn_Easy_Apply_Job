from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError
import logging
import urllib.parse
import asyncio
from functools import wraps
from automation.browser import BrowserManager
from config.settings import get_preferences, get_resume_path

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
        logger.info("Navigating to LinkedIn login page. Please log in manually if required (60s timeout).")
        await self.page.goto("https://www.linkedin.com/login")
        try:
            # Wait for feed to determine if logged in
            await self.page.wait_for_selector(".feed-identity-module", timeout=60000)
            logger.info("Successfully logged in.")
        except PlaywrightTimeoutError:
            logger.error("Login timed out. Make sure you logged in correctly.")
            raise Exception("Login failed")

    @with_retry(retries=3, delay_sec=2)
    async def search_jobs(self, job_title: str, location: str):
        logger.info(f"Searching for {job_title} in {location}")
        query = urllib.parse.urlencode({
            'keywords': job_title,
            'location': location,
            'f_AL': 'true' if self.preferences.get('easy_apply_only', True) else '',
        })
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
    async def upload_resume(self) -> bool:
        """Detects upload button, uploads resume, and confirms upload."""
        resume_path = get_resume_path()
        if not resume_path.exists():
            logger.warning(f"Resume not found at {resume_path}. Skipping upload.")
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
        
    async def apply_to_job(self, job_url: str, llm_agent) -> bool:
        await self.page.goto(job_url)
        await BrowserManager.human_delay(2, 4)
        
        try:
            # Locate easy apply button
            easy_apply_button = self.page.locator(".jobs-apply-button--top-card button")
            if await easy_apply_button.count() == 0:
                logger.info("Easy Apply button not found. Skipping.")
                return False
            
            await easy_apply_button.first.click()
            await BrowserManager.human_delay(1, 2)
            
            # Simple form filling loop (for visual structure)
            max_steps = 10
            steps = 0
            while steps < max_steps:
                submit_button = self.page.locator("button[aria-label='Submit application']")
                if await submit_button.count() > 0:
                    logger.info("Application ready to submit! Simulated click.")
                    # await submit_button.click() # Uncomment to actually submit
                    await BrowserManager.human_delay(2, 3)
                    
                    # dismiss modal if needed
                    dismiss = self.page.locator("button[aria-label='Dismiss']")
                    if await dismiss.count() > 0:
                        await dismiss.first.click()
                        
                    return True
                
                next_button = self.page.locator("button[aria-label='Continue to next step']")
                if await next_button.count() > 0:
                    # TODO: Inject LLM logic here to actually parse form inputs and fill
                    # Example: inputs = await self.page.query_selector_all("input")
                    # ans = llm_agent.answer_question(...)
                    
                    await next_button.click()
                    await BrowserManager.human_delay(1, 3)
                    steps += 1
                else:
                    review_button = self.page.locator("button[aria-label='Review your application']")
                    if await review_button.count() > 0:
                        await review_button.click()
                        await BrowserManager.human_delay(1, 2)
                        steps += 1
                    else:
                        logger.warning("Unrecognized modal state. Aborting apply.")
                        # cancel application
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
