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

    def evaluate_job(self, job_title: str, company: str, location: str, job_description: str) -> tuple[bool, int, str]:
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
            return False, 0, "resume.pdf"
            
        # 2. Smart LLM JSON Scoring Architecture
        from pathlib import Path
        import re
        from config.settings import BASE_DIR
        REQUIREMENTS_DIR = BASE_DIR / "requirements"
        available_resumes = [p.name for p in REQUIREMENTS_DIR.glob("*.pdf")]
        if not available_resumes: available_resumes = ["resume.pdf"]
        
        # Truncating job description to 4500 chars to ensure minimal latency and token usage
        safe_jd = job_description[:4500] 
        prompt = f"""
        You are an advanced AI recruiting filter. Evaluate the job and return ONLY a strict JSON object.
        
        Candidate Profile: {json.dumps(self.profile)}
        Candidate Preferences: {json.dumps(self.preferences)}
        Available Resumes in Database: {available_resumes}
        
        Target Job Title: {job_title}
        Target Company: {company}
        Target Location: {location}
        Job Description: {safe_jd}
        
        RULES:
        1. Evaluate Location match, Experience bracket requirements, and Skill overlap.
        2. "score" must be an integer from 0 (terrible) to 100 (perfect).
        3. Determine which resume from "Available Resumes in Database" natively suits this role best based on keyword matches, and set it to "selected_resume".
        4. "is_match" should be true if it evaluates as a decent viable application without dealbreakers, else false.
        5. Returning ANYTHING non-JSON (like text explanations or markdown blocks) will break the system. Output raw JSON `{{"is_match": bool, "score": int, "selected_resume": "string"}}` ONLY.
        """
        
        try:
            raw_result = self.llm_agent._call_gemini(prompt)
            match = re.search(r'\{.*\}', raw_result.replace('\\n', '').replace('\n', ''), re.S)
            if match:
                data = json.loads(match.group(0))
                is_match = data.get("is_match", False)
                score = data.get("score", 0)
                selected_resume = data.get("selected_resume", "resume.pdf")
                
                logger.info(f"Smart Scoring complete. Quality: [{score}/100]. Status Match: {is_match}")
                return is_match, score, selected_resume
            else:
                logger.warning("LLM response not valid JSON format. Rejecting explicitly due to parser block.")
                return False, 0, "resume.pdf"
        except Exception as e:
            logger.error(f"Error during JSON smart scoring: {e}. Defaulting filter.")
            # Failsafe passing so we don't accidentally freeze queue due to Google API dropout
            return True, 75, "resume.pdf"
