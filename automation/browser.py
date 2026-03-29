import os
import random
import asyncio
from typing import Optional
from playwright.async_api import async_playwright, Browser, Page, BrowserContext

class BrowserManager:
    def __init__(self, headless: bool = False):
        self.headless = headless
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

    async def init_browser(self) -> Page:
        self.playwright = await async_playwright().start()
        # Add anti-detection arguments and user agent
        args = [
            '--disable-blink-features=AutomationControlled',
            '--start-maximized'
        ]
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=args
        )
        self.context = await self.browser.new_context(
            viewport=None, # Useful for start-maximized
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        self.page = await self.context.new_page()
        # Additional anti-detection script injection
        await self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            })
        """)
        return self.page

    async def close(self):
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    @staticmethod
    async def human_delay(min_sec: float = 1.0, max_sec: float = 3.0):
        """Simulates human typing/reading delays"""
        await asyncio.sleep(random.uniform(min_sec, max_sec))

    @staticmethod
    async def random_scroll(page: Page):
        """Simulates random page scrolling to avoid detection"""
        scroll_amount = random.randint(300, 700)
        direction = random.choice([1, -1]) if random.random() > 0.8 else 1
        await page.evaluate(f"window.scrollBy(0, {scroll_amount * direction})")
        await BrowserManager.human_delay(0.5, 1.5)

    @staticmethod
    async def human_type(locator, text: str, min_delay: int = 50, max_delay: int = 200):
        """Simulates human-like typing speed with variable keystroke delays"""
        await locator.clear()
        for char in text:
            await locator.type(char, delay=random.randint(min_delay, max_delay))
        await BrowserManager.human_delay(0.5, 1.0)
