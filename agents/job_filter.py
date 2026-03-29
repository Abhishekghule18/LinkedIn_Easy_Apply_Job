import logging
import json
from config.settings import get_preferences, get_profile
from llm.gemini_agent import GeminiAgent

logger = logging.getLogger(__name__)

class JobFilter:
    def __init__(self, llm_agent: GeminiAgent):
        self.preferences = get_preferences()
        self.profile = get_profile()
        self.llm_agent = llm_agent

    def evaluate_job(self, job_title: str, company: str, location: str, job_description: str) -> bool:
        """
        Determines whether to apply to a job based on configuration.
        Implements smart filtering logic evaluating:
        - location
        - skills coverage
        - experience requirement match
        """
        logger.info(f"Evaluating Match: '{job_title}' at {company} ({location})")
        
        # 1. Quick Heuristic Filter (Strict Remote Constraint)
        is_remote_job = "remote" in location.lower() or "remote" in job_description.lower()
        if self.preferences.get("remote_only", False) and not is_remote_job:
            logger.info("Filter rejection: Candidate requires Remote only, but job does not indicate remote.")
            return False
            
        # 2. Smart Filter via LLM for deep semantic extraction
        # Truncating job description to 4500 chars to ensure minimal latency and token usage
        safe_jd = job_description[:4500] 
        prompt = f"""
        You are an advanced AI recruiting filter. Determine if the candidate should apply to this job.
        
        Candidate Profile: {json.dumps(self.profile)}
        Candidate Preferences: {json.dumps(self.preferences)}
        
        Target Job Title: {job_title}
        Target Company: {company}
        Target Location: {location}
        Job Description: {safe_jd}
        
        Evaluation Checklist:
        1. LOCATION: Does the job location match the candidate's preferred_locations or remote constraints?
        2. EXPERIENCE: Does the mandatory experience requirement align with the candidate's {self.profile.get('experience_years', 0)} years of experience, or fall within their preferred experience_range ({self.preferences.get('experience_range', [])})?
        3. SKILLS: Is there an acceptable overlap between the required tech stack and the candidate's skills array? Let 1 or 2 missing skills slide if the core role matches.
        
        If it meets the criteria and is a reasonable fit, output exactly "YES". 
        If it is a senior role requiring significantly more experience, entirely wrong industry, or zero skill matching, output exactly "NO".
        Do not provide reasoning, only return "YES" or "NO".
        """
        
        try:
            result = self.llm_agent._call_gemini(prompt).strip().upper()
            if "YES" in result:
                logger.debug(f"Smart Filter PASSED for {job_title}.")
                return True
            else:
                logger.info(f"Smart Filter REJECTED {job_title} (Failed skills, experience, or deeper location mismatch).")
                return False
        except Exception as e:
            logger.error(f"Error during smart filtering sequence: {e}. Defaulting to True.")
            # Default to True on API error so we don't accidentally miss valid applications due to network issues
            return True
