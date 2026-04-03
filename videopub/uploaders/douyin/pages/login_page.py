"""抖音登录页 Page Object。"""


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

        print("请在浏览器中扫描二维码登录抖音创作者中心...")
        try:
            await self.page.wait_for_selector(
                self.SELECTORS["logged_in_indicator"],
                timeout=timeout * 1000,
            )
            return True
        except Exception:
            return False
