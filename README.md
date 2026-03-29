# LinkedIn Easy Apply Automation Agent

A production-grade, open-source friendly LinkedIn application automation agent. It uses Playwright for browser automation and Google Gemini for intelligent form filling.

## Features
- **Fully Automated Flow**: Logs into LinkedIn, searches for jobs, filters for Easy Apply, and applies automatically.
- **Smart Form Filling**: Leverages Google Gemini models to intelligently answer varied job application questions.
- **Human-like Interactions**: Implements random scrolling, dynamic delays, and browser stealth modes to bypass detection.
- **Persistent Storage**: Utilizes an SQLite database to track applied jobs, ensuring you never apply to the same job twice.
- **Extensible Architecture**: Clean, modular structure divided into Configuration, Storage, LLM Agents, Browser Automation, and Orchestration.

## Pre-requisites
- Python 3.9+ 
- A Google Gemini API Key (free tier available via Google AI Studio).

## Directory Structure
- `requirements/`: Contains your `profile.json`, `preferences.json`, and `resume.pdf`.
- `config/`: Settings and configuration/logging loaders.
- `storage/`: Local SQLite database configuration (`db.py`).
- `llm/`: Integrations with AI APIs (`gemini_agent.py`).
- `automation/`: Playwright automation wrapper (`browser.py`, `linkedin.py`).
- `agents/`: Orchestration logic that structures the job application loop (`application_agent.py`).

## Setup Instructions

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

2. **Configure Requirements**:
   - Edit `requirements/profile.json` with your personal details, experience, and skills.
   - Edit `requirements/preferences.json` to modify your desired job search parameters (titles, locations, remote options).
   - Place your resume document as `requirements/resume.pdf`.

3. **Set Environment Variables**:
   - Update the `.env` file with your actual `GEMINI_API_KEY`.

4. **Run the Agent**:
   ```bash
   python main.py
   ```
   *Note: During your first run, a visible browser window will open. You will have 60 seconds to manually log in to LinkedIn before the automated tracking begins.*
