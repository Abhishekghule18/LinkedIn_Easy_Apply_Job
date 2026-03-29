# 🚀 LinkedIn Easy Apply Automation Agent

A production-grade, open-source-friendly LinkedIn job application automation tool. This agent utilizes **Playwright** for human-like browser automation and the **Google Gemini API** (free-tier compatible) to dynamically score jobs, generate contextual answers, and intelligently upload the best resume for the role.

## ✨ Features
- **Fully Automated End-to-End Loop**: Logs in, searches your preferred job titles, paginates through search results, and autonomously applies.
- **AI-Powered "Smart" Filtering**: Uses `gemini-1.5-flash` to read scraped Job Descriptions and compare them against your profile constraints. Computes a match score out of 100, exclusively applying to jobs passing the 60+ threshold.
- **Dynamic Resume Routing**: Drop multiple PDF resumes into the `requirements/` folder (e.g., `backend-resume.pdf`, `frontend-resume.pdf`). The AI evaluates the job posting and automatically selects the optimal resume file to upload!
- **Human-Like Stealth Behaviors**: Implements randomized curved mouse movements, staggered human typing delays, and organic viewport scrolling to bypass basic bot-detection heuristics.
- **Local Application Analytics**: Tracks your daily application caps natively in `storage/session.json`. Prevents account bans and ensures you NEVER apply to redundant jobs via `applied_jobs.json`.

---

## 🛠️ Setup & Installation

### 1. Install Dependencies
Ensure you have Python 3.9+ installed natively. Run the following commands in your terminal:
```bash
# Initialize a virtual environment
python -m venv venv

# Activate the virtual environment (Windows)
.\venv\Scripts\activate
# Activate the virtual environment (Mac/Linux)
source venv/bin/activate

# Install the Python requirements
pip install -r requirements.txt

# Install the Playwright Chromium browser binaries
python -m playwright install chromium
```

### 2. Configure Your Environment Variables
Locate the `.env` file in the root directory. You must acquire a **Free API Key** from [Google AI Studio](https://aistudio.google.com/). Insert it like this:
```env
GEMINI_API_KEY=your_gemini_api_key_here
```

---

## ⚙️ How to Personalize Your Data

To make the AI apply accurately on your behalf, you need to populate the files inside the `requirements/` directory.

### 1. Your Profile (`requirements/profile.json`)
This acts as the standard "Brain" for the LLM. Open the file and fill in your concrete professional information. The AI relies heavily on this data to calculate your Match Score and answer custom input box questions inside the Easy Apply modal natively!
```json
{
  "name": "Jane Example",
  "email": "jane.example@domain.com",
  "phone": "+1-555-019-8372",
  "experience_years": 5,
  "skills": ["Python", "Machine Learning", "Playwright"],
  "current_location": "San Francisco, CA",
  "preferred_locations": ["Remote", "New York, NY"]
}
```

### 2. Your Search Preferences (`requirements/preferences.json`)
This configures the bounds of the overarching automation loop. Set your job titles, remote constraints, and daily API quotas here to avoid flagging your IP:
```json
{
  "job_titles": ["Software Engineer", "Python Developer"],
  "locations": ["United States", "Remote"],
  "daily_apply_limit": 40,
  "max_pages": 3,
  "remote_only": true,
  "easy_apply_only": true,
  "experience_range": [3, 8],
  "skip_complex_forms": true
}
```

### 3. Add Your Resumes (`requirements/*.pdf`)
Simply drag and drop your resume(s) directly into the `requirements/` folder. 
* *Pro Tip*: You can add multiple distinct templates (e.g., `requirements/data_engineer_resume.pdf`, `requirements/backend_resume.pdf`). The AI filter will analyze each target job card and dynamically cross-reference keywords to select the highest-converting PDF available to upload into Playwright automatically!

---

## 🏃‍♂️ Running the Automation

Once your `requirements/` folder is tailored, simply execute the orchestrator script:
```bash
python main.py
```

### What to expect on the first run:
1. A visible Chrome browser interface will launch.
2. **You will explicitly have 60 seconds** to manually log into your LinkedIn account and solve any immediate Captcha security checks.
3. Once the general LinkedIn feed loads, the automation takes over the browser. It will search your target jobs, scroll the pages organically, visually assess requirements, and execute the application loops.
4. **Logs** will render cleanly inside the `logs/app.log` and `logs/error.log` files mapping your workflow. The `storage/applied_jobs.json` file will safely archive your successful submissions persistently across resets. 
