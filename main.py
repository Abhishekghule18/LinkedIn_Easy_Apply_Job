import asyncio
import logging
from dotenv import load_dotenv
from logs.logger import log_info, log_error
from agents.application_agent import ApplicationAgent

def main():
    load_dotenv()
    log_info("Booting up LinkedIn Easy Apply Orchestrator...")
    
    agent = ApplicationAgent()
    try:
        asyncio.run(agent.run())
    except KeyboardInterrupt:
        log_info("Process interrupted manually by user. Shutting down gracefully...")
    except Exception as e:
        log_error(f"Fatal application error: {e}")

if __name__ == "__main__":
    main()
