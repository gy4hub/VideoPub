"""抖音登录页 Page Object。"""

import asyncio

from loguru import logger

class DouyinLoginPage:
    """抖音创作者中心登录流程。"""

    SELECTORS = {
        "home_url": "https://creator.douyin.com/creator-micro/home",
        "logged_in_indicators": [
            "text=高清发布",
            "text=发布视频",
            "text=内容管理",
        ],
        "login_page_indicators": [
            "text=扫码登录",
            "text=验证码登录",
            "text=密码登录",
            "img[src*='qrcode']",
        ],
    }

    def __init__(self, page):
        self.page = page

    async def is_logged_in(self) -> bool:
        """检查当前页面是否已登录。"""
        await self.page.goto(self.SELECTORS["home_url"], wait_until="domcontentloaded")
        await self.page.wait_for_timeout(3000)

        current_url = self.page.url
        if "login" in current_url or "passport" in current_url:
            return False

        for selector in self.SELECTORS["login_page_indicators"]:
            locator = self.page.locator(selector)
            if await locator.count() > 0 and await locator.first.is_visible():
                return False

        for selector in self.SELECTORS["logged_in_indicators"]:
            locator = self.page.locator(selector)
            if await locator.count() > 0 and await locator.first.is_visible():
                return True

        return False

    async def wait_for_qrcode_scan(self, timeout: int = 120) -> bool:
        """等待用户扫码完成登录。"""
        await self.page.goto("https://creator.douyin.com", wait_until="domcontentloaded")
        await self.page.wait_for_timeout(3000)

        qrcode_login = self.page.locator("text=扫码登录")
        if await qrcode_login.count() > 0:
            await qrcode_login.first.click()
            await self.page.wait_for_timeout(1000)

        logger.info("\n" + "=" * 50)
        logger.info("请在浏览器中扫描二维码登录抖音创作者中心...")
        logger.info(f"超时时间: {timeout} 秒")
        logger.info("=" * 50)

        try:
            elapsed = 0
            while elapsed < timeout:
                await asyncio.sleep(2)
                elapsed += 2
                if await self.is_logged_in():
                    logger.info("登录成功!")
                    return True
        except Exception:
            pass

        logger.warning("登录超时或异常，请重试")
        return False
