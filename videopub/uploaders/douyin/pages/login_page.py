"""抖音登录页 Page Object。"""

import asyncio

from loguru import logger

class DouyinLoginPage:
    """抖音创作者中心登录流程。"""

    SELECTORS = {
        "login_url": "https://creator.douyin.com",
        "logged_in_indicator": "[class*='avatar'], [class*='user-info']",
        "qrcode_login": "text=扫码登录",
        "qrcode_image": "img[src*='qrcode']",
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

        indicator = self.page.locator(self.SELECTORS["logged_in_indicator"])
        return await indicator.count() > 0

    async def wait_for_qrcode_scan(self, timeout: int = 120) -> bool:
        """等待用户扫码完成登录。"""
        await self.page.goto(self.SELECTORS["login_url"], wait_until="domcontentloaded")
        await self.page.wait_for_timeout(3000)

        qrcode_login = self.page.locator(self.SELECTORS["qrcode_login"])
        if await qrcode_login.count() > 0:
            await qrcode_login.first.click()
            await self.page.wait_for_timeout(1000)

        logger.info("\n" + "=" * 50)
        logger.info("请在浏览器中扫描二维码登录抖音创作者中心...")
        logger.info(f"超时时间: {timeout} 秒")
        logger.info("=" * 50)

        try:
            # 等待登录成功的特定元素出现
            # 这个 wait_for_selector 会在元素存在（无论是否可见）时就返回，如果加上 state="visible" 更保险
            await self.page.wait_for_selector(
                self.SELECTORS["logged_in_indicator"],
                state="visible",
                timeout=timeout * 1000,
            )
            logger.info("登录成功!")
            return True
        except Exception:
            logger.warning("登录超时或异常，请重试")
            return False
