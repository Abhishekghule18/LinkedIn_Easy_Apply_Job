import os
import logging
from typing import Optional, List
from google import genai
from config.settings import get_profile

logger = logging.getLogger(__name__)

class GeminiAgent:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            logger.warning("GEMINI_API_KEY is not set. Please set it in the .env file.")
        else:
            self.client = genai.Client(api_key=self.api_key)
        # Using gemini-1.5-flash as it is highly capable and free-tier friendly
        self.model = "gemini-1.5-flash" 
        self.profile = get_profile()

    def _call_gemini(self, prompt: str) -> str:
        """Internal method to handle API communication."""
        if not hasattr(self, 'client'):
            logger.error("Gemini Client not initialized. Missing API Key.")
            return ""
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt
            )
            return response.text.strip()
        except Exception as e:
            logger.error(f"Error calling Gemini API: {e}")
            return ""

    def answer_job_question(self, question: str, options: Optional[List[str]] = None, job_description: str = "") -> str:
        """Generates short professional answers to general job application questions."""
        prompt = f"""
        You are an expert acting on my behalf to fill out a job application accurately based on my profile.
        
        My Profile: {self.profile}
        Job Description Context: {job_description}
        
        Question: {question}
        Options (if provided): {options}
        
        RULES:
        1. Provide a short, professional, and direct answer. Return ONLY the final answer without pleasantries.
        2. If it is a boolean question, return exactly 'Yes' or 'No'.
        3. If options are provided, you MUST pick the exact matching option text from the list.
        4. If you absolutely do not know, provide a plausible safe answer.
        """
        return self._call_gemini(prompt)

    def answer_experience_question(self, skill: str, job_description: str = "") -> str:
        """Answers specific numerical experience questions accurately."""
        prompt = f"""
        You are answering a numerical job application question about years of experience on my behalf.
        
        My Profile: {self.profile}
        Job Description Context: {job_description}
        
        Target skill/technology to evaluate: {skill}
        
        RULES:
        1. Based on my profile's total experience and skills list, infer my years of experience using '{skill}'.
        2. Return ONLY a single integer representing the number of years.
        3. If the skill is entirely unrelated or missing, return '0'.
        4. Do not include any other text, characters, or words.
        """
        return self._call_gemini(prompt)

    def generate_cover_letter(self, company_name: str, job_title: str, job_description: str) -> str:
        """Generates a brief, highly targeted cover letter."""
        prompt = f"""
        You are writing a short, professional cover letter to attach to my job application.
        
        My Profile Details: {self.profile}
        Target Job Title: {job_title}
        Target Company Name: {company_name}
        Job Description Highlights: {job_description}
        
        RULES:
        1. Write a concise, engaging, and highly professional cover letter (maximum 150 words). 
        2. Specifically highlight elements of my profile that directly match the Job Description Highlights.
        3. Do not include generic placeholder brackets like [Your Name]. Use my actual name and details.
        4. Keep the tone confident, direct, and ready-to-deliver.
        """
        return self._call_gemini(prompt)
