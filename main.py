import asyncio
import logging
from dotenv import load_dotenv
from config.settings import setup_logging
from agents.application_agent import ApplicationAgent

def main():
    load_dotenv()
    setup_logging()
    
    logger = logging.getLogger("MAIN")
    logger.info("Booting up LinkedIn Automation Agent...")
    
    agent = ApplicationAgent()
    try:
        asyncio.run(agent.run())
    except KeyboardInterrupt:
        logger.info("Process interrupted by user. Shutting down...")

if __name__ == "__main__":
    main()
