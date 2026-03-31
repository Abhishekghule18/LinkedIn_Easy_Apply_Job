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
        
        # 1. Quick Heuristic Filters
        lower_loc = location.lower()
        lower_desc = job_description.lower()
        lower_title = job_title.lower()
        
        pref_ex_titles = [t.lower() for t in self.preferences.get("exclude_titles", [])]
        if any(ex in lower_title for ex in pref_ex_titles):
            logger.info(f"Filter rejection: Job title matches exclude_titles constraint.")
            return False, 0, "resume.pdf"
            
        # Merge exclude_keywords from both preferences and profile arrays
        pref_ex_keywords = [k.lower() for k in self.preferences.get("exclude_keywords", [])] + [k.lower() for k in self.profile.get("exclude_keywords", [])]
        if any(ex in lower_desc for ex in pref_ex_keywords):
            logger.info("Filter rejection: Job description matches exclude_keywords constraint.")
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
        1. Evaluate Location match, Experience bracket requirements, and Skill overlap natively.
        2. Pay close attention to the candidate's `must_have_skills`, but DO NOT aggressively issue a 0 score just because one exact technology mention is missing. Scale the score intuitively (e.g. 60-90) based on contextual similarities to the candidate's core industry and standard roles as defined by their profile.
        3. IGNORE THE COMPANY NAME. If the Target Company is "Unknown Company", treat it as a perfectly valid job. DO NOT penalize or lower the score for missing company branding.
        4. "score" must be an integer from 0 (terrible) to 100 (perfect).
        5. If the Job Description appears to contain messy webpage navigation text (e.g., "Messaging, Notifications, My Network"), IGNORE that text and focus purely on the technical qualifications hidden within it. Do NOT score it 0 just because the text is unformatted.
        6. Determine which resume from "Available Resumes in Database" natively suits this role best based on keyword matches, and set it to "selected_resume".
        7. "is_match" should be true if it evaluates as a decent viable application without dealbreakers, else false.
        8. Returning ANYTHING non-JSON (like text explanations or markdown blocks) will break the system. Output raw JSON `{{"is_match": bool, "score": int, "selected_resume": "string"}}` ONLY.
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
