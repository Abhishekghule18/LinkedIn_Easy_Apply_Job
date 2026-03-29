from config.settings import get_preferences, get_profile
from logs.logger import log_info, log_error, log_success, log_warning, log_debug
from automation.browser import BrowserManager
from automation.linkedin import LinkedInAutomator
from llm.gemini_agent import GeminiAgent
from agents.job_filter import JobFilter
from storage.job_tracker import JobTracker

class ApplicationAgent:
    """Production-Grade Main Agent Orchestrator tying all modules together."""
    
    def __init__(self):
        log_info("Initializing Main Production Orchestrator...")
        # 1. Load Requirements
        self.preferences = get_preferences()
        self.profile = get_profile()
        
        self.browser_manager = BrowserManager(headless=False)
        self.llm_agent = GeminiAgent()
        self.job_filter = JobFilter(self.llm_agent)
        self.tracker = JobTracker()

    async def run(self):
        log_info("Booting up browser and authenticating...")
        page = await self.browser_manager.init_browser()
        linkedin = LinkedInAutomator(page)

        try:
            # 2. Login LinkedIn
            await linkedin.login()
        except Exception as e:
            log_error(f"Critical error during LinkedIn login sequence: {e}")
            await self.browser_manager.close()
            return

        job_titles = self.preferences.get("job_titles", ["Software Engineer"])
        locations = self.preferences.get("locations", ["Remote"])

        try:
            for title in job_titles:
                for loc in locations:
                    log_info(f"==== Starting specific search loop: [{title}] in [{loc}] ====")
                    try:
                        await self.process_search_query(linkedin, title, loc)
                    except Exception as e:
                        log_error(f"Search query combination failed for {title} in {loc}: {e}")
                        continue
                        
        except Exception as e:
            log_error(f"Fatal unhandled error inside orchestrator loop: {e}")
        finally:
            log_info("Shutting down BrowserManager safely.")
            await self.browser_manager.close()

    async def process_search_query(self, linkedin: LinkedInAutomator, title: str, loc: str):
        # 3. Search Jobs
        await linkedin.search_jobs(title, loc)
        
        # Extract job cards visible locally
        jobs = await linkedin.extract_jobs_from_page()
        if not jobs:
            log_warning(f"No jobs found during extraction for {title} in {loc}.")
            return
            
        log_info(f"Extracted {len(jobs)} potential jobs from feed.")

        for job in jobs:
            job_link = job.get("link", "")
            if not job_link:
                continue

            # 6. Track Applications (Anti-Duplicate Check)
            if self.tracker.is_job_applied(job_link):
                log_debug(f"[SKIP] Pre-filtered (Already Applied): {job_link}")
                continue

            # Route to independent job handler (isolates errors to single job)
            await self.process_individual_job(linkedin, title, loc, job_link)
            
            # Rate limiting / stealth anti-bot delay
            await self.browser_manager.human_delay(5, 12)

    async def process_individual_job(self, linkedin: LinkedInAutomator, search_title: str, loc: str, job_link: str):
        log_debug(f"Navigating to job link: {job_link}")
        
        try:
            # Navigate to Job explicitly
            await linkedin.page.goto(job_link)
            await self.browser_manager.human_delay(2, 4)
            
            # Dynamically extract real data for accurate filtering
            company_element = linkedin.page.locator(".job-details-jobs-unified-top-card__company-name a, .job-details-jobs-unified-top-card__primary-description a")
            company = await company_element.inner_text() if await company_element.count() > 0 else "Unknown Company"
            company = company.strip()
            
            title_element = linkedin.page.locator("h1.job-details-jobs-unified-top-card__job-title")
            real_title = await title_element.inner_text() if await title_element.count() > 0 else search_title
            real_title = real_title.strip()
            
            desc_element = linkedin.page.locator("div.jobs-description__container")
            job_desc = await desc_element.inner_text() if await desc_element.count() > 0 else ""
            
            # 4. Filter Jobs
            if not self.job_filter.evaluate_job(real_title, company, loc, job_desc):
                log_info(f"[SKIP] Job failed strict requirements filter: {company} - {real_title}")
                return
                
            # 5. Apply Jobs
            log_info(f"[APPLY] Initiating application flow for {company} - {real_title}")
            success = await linkedin.apply_to_job(job_link, self.llm_agent)
            
            # 6. Track Applications (Append Result)
            if success:
                self.tracker.save_applied_job(company, real_title, loc, job_link, notes="Applied automatically via Easy Apply.")
            else:
                self.tracker.save_failed_job(company, real_title, job_link, error="Apply button missing or form sequence unsupported.")
                
        except Exception as e:
            log_error(f"Error inspecting or applying to job {job_link}: {e}")
            self.tracker.save_failed_job("Unknown", search_title, job_link, error=str(e))
