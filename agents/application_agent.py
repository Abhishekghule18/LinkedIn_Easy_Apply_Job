import logging
from typing import List
from automation.browser import BrowserManager
from automation.linkedin import LinkedInAutomator
from llm.gemini_agent import GeminiAgent
from storage.db import init_db, is_applied, add_job
from config.settings import get_preferences

logger = logging.getLogger(__name__)

class ApplicationAgent:
    def __init__(self):
        self.browser_manager = BrowserManager(headless=False)
        self.llm_agent = GeminiAgent()
        self.preferences = get_preferences()
        
    async def run(self):
        logger.info("Initializing Agent System...")
        init_db()
        
        page = await self.browser_manager.init_browser()
        linkedin = LinkedInAutomator(page)
        
        try:
            await linkedin.login()
            
            job_titles = self.preferences.get("job_titles", ["Software Engineer"])
            locations = self.preferences.get("locations", ["Remote"])
            
            for title in job_titles:
                for loc in locations:
                    logger.info(f"== Starting search for '{title}' in '{loc}' ==")
                    await linkedin.search_jobs(title, loc)
                    
                    jobs = await linkedin.extract_jobs_from_page()
                    logger.info(f"Extracted {len(jobs)} jobs from page.")
                    
                    for job in jobs:
                        job_id = job["id"]
                        if is_applied(job_id):
                            logger.info(f"Skipping job {job_id}: Already applied.")
                            continue
                            
                        logger.info(f"Attempting to apply to job: {job_id}")
                        success = await linkedin.apply_to_job(job["link"], self.llm_agent)
                        
                        if success:
                            add_job(job_id, title, "Unknown", loc, job["link"], "APPLIED")
                            logger.info(f"Successfully applied and recorded job: {job_id}")
                        else:
                            add_job(job_id, title, "Unknown", loc, job["link"], "FAILED")
                            logger.warning(f"Failed to apply to job: {job_id}")
                            
                        # Anti-detection delay between applications
                        await self.browser_manager.human_delay(5, 12) 
                        
        except Exception as e:
            logger.error(f"Fatal error in agent run loop: {e}")
        finally:
            await self.browser_manager.close()
            logger.info("Agent run complete. Browser closed.")
