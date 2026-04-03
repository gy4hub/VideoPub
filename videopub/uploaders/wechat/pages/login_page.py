"""视频号扫码登录 Page Object。"""

import asyncio

from loguru import logger


class WeChatLoginPage:
    """微信视频号登录流程。"""

    SELECTORS = {
        "login_url": "https://channels.weixin.qq.com",
        "logged_in_indicators": [
            "text=微信小店",
            "text=发表",
            "[class*='avatar']",
        ],
        "login_page_indicators": [
            "text=使用微信扫码登录",
            "img[src*='qrcode']",
        ],
    }

    def __init__(self, page):
        self.page = page

    async def is_logged_in(self) -> bool:
        """检查当前页面是否已登录。"""
        await self.page.goto(self.SELECTORS["login_url"], wait_until="domcontentloaded")
        await self.page.wait_for_timeout(3000)

        current_url = self.page.url
        if "login" in current_url or "passport" in current_url:
            return False

        for selector in self.SELECTORS["logged_in_indicators"]:
            locator = self.page.locator(selector)
            if await locator.count() > 0:
                return True
        return False

    async def wait_for_qrcode_scan(self, timeout: int = 120) -> bool:
        """等待用户扫码登录。"""
        await self.page.goto(self.SELECTORS["login_url"], wait_until="domcontentloaded")
        await self.page.wait_for_timeout(3000)

        logger.info("\n" + "=" * 50)
        logger.info("请在浏览器中使用微信扫描二维码登录视频号")
        logger.info(f"超时时间: {timeout} 秒")
        logger.info("=" * 50)

        elapsed = 0
        poll_interval = 2

        while elapsed < timeout:
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

            current_url = self.page.url
            if "login" in current_url or "passport" in current_url:
                continue

            for selector in self.SELECTORS["logged_in_indicators"]:
                locator = self.page.locator(selector)
                if await locator.count() > 0:
                    logger.info("登录成功!")
                    return True

        logger.warning("登录超时，请重试")
        return False
