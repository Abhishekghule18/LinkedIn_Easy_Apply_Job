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

        # Ensure total configuration independence (No hardcoded frameworks or locations)
        job_titles = self.preferences.get("search_queries", self.preferences.get("job_titles", []))
        if not job_titles:
            log_error("CRITICAL: No 'search_queries' or 'job_titles' arrays found in preferences.json.")
            return

        locations = self.preferences.get("locations", [])
        if not locations:
            log_error("CRITICAL: No 'locations' array found in preferences.json.")
            return
            
        daily_limit = self.preferences.get("max_applications_per_run", 30)
        pages_per_search = self.preferences.get("max_pages", 3)

        try:
            for loc in locations:
                for title in job_titles:
                    for page_num in range(pages_per_search):
                        if self.tracker.reached_daily_limit(daily_limit):
                            log_info(f"Daily application quota ({daily_limit}) hit. Suspending orchestrator indefinitely bounds.")
                            return
                            
                        offset = page_num * 25
                        log_info(f"==== Queue Bound: [{title}] in [{loc}] (Scraping Page {page_num+1}/{pages_per_search}) ====")
                        try:
                            await self.process_search_query(linkedin, title, loc, offset)
                        except Exception as e:
                            log_error(f"Search query node collapsed for parameters [{title} | {loc}]: {e}")
                            break # Terminate inner pagination loops preventing chained URL timeouts
                        
        except Exception as e:
            log_error(f"Fatal unhandled error inside orchestrator loop: {e}")
        finally:
            log_info("Shutting down BrowserManager safely.")
            await self.browser_manager.close()

    async def process_search_query(self, linkedin: LinkedInAutomator, title: str, loc: str, offset: int):
        # 3. Search Jobs
        await linkedin.search_jobs(title, loc, offset)
        
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
            
            try:
                # Wait for the single-page app AJAX hook to hydrate the content block fully.
                await linkedin.page.wait_for_selector("h1", timeout=8000)
            except:
                pass
            
            await self.browser_manager.human_delay(2, 4)
            
            # Clean boolean hooks from search_title to prevent AI hallucination on scrape fail
            fallback_title = search_title.replace("title:(", "").replace(")", "").replace('"', "")
            
            # Dynamically extract real data for accurate filtering
            company_element = linkedin.page.locator(
                ".job-details-jobs-unified-top-card__company-name, "
                ".job-details-top-card__company, "
                ".tvm__text--low-emphasis, "
                ".job-details-jobs-unified-top-card__primary-description"
            )
            company = await company_element.first.inner_text() if await company_element.count() > 0 else "Unknown Company"
            company = company.split('\\n')[0].strip() if company else "Unknown Company"
            
            title_element = linkedin.page.locator("h1")
            real_title = await title_element.first.inner_text() if await title_element.count() > 0 else fallback_title
            real_title = real_title.strip()
            
            desc_element = linkedin.page.locator("div.jobs-description__container, div#job-details, article, .jobs-description-content__text")
            if await desc_element.count() > 0:
                job_desc = await desc_element.first.inner_text()
            else:
                # Ultimate failsafe: if LinkedIn radically altered the description container, grab the entire page body natively.
                job_desc = await linkedin.page.evaluate("document.body.innerText")
            
            # 4. Filter Jobs and Score
            min_score_pref = self.preferences.get("min_match_score", 0.65)
            # Support both float notation (0.65) and integer notation (65) natively
            min_score = int(min_score_pref * 100) if min_score_pref <= 1 else int(min_score_pref)

            is_match, score, target_resume = self.job_filter.evaluate_job(real_title, company, loc, job_desc)
            if not is_match or score < min_score:
                log_info(f"[SKIP] Failed threshold (score: {score} vs min: {min_score}): {company} - {real_title}")
                return
                
            from config.settings import BASE_DIR
            resume_path_abs = BASE_DIR / "requirements" / target_resume

            # 5. Apply Jobs
            log_info(f"[APPLY] Launching execution flow tracking ({target_resume}) against {company} [Score: {score}/100]")
            success = await linkedin.apply_to_job(job_link, self.llm_agent, resume_path_abs)
            
            # 6. Track Applications (Append Result)
            if success:
                self.tracker.save_applied_job(company, real_title, loc, job_link, notes=f"Automated Score: {score}")
            else:
                self.tracker.save_failed_job(company, real_title, job_link, error="Fatal modal traversal desync.")
                
        except Exception as e:
            log_error(f"Error inspecting or applying to job {job_link}: {e}")
            self.tracker.save_failed_job("Unknown", search_title, job_link, error=str(e))
