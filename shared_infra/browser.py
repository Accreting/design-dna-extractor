"""
shared_infra.browser
~~~~~~~~~~~~~~~~~~~~
Playwright 异步抓取与渲染封装模块。
支持：
- 防检测无头浏览器上下文管理
- 页面 HTML 与 DOM 异步抓取
- HTML/CSS 字符串直接渲染为高清图片（专用于 P2 批图与视觉预览）
- 目标页面高清/全屏截图
- 页面关键视觉资产（SVG、图片、计算样式）提取支持
"""

import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional
from playwright.async_api import Browser, BrowserContext, Page, async_playwright

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

DEFAULT_VIEWPORT = {"width": 1280, "height": 800}


@asynccontextmanager
async def get_browser_context(
    headless: Optional[bool] = None,
    viewport: Optional[Dict[str, int]] = None,
    user_agent: Optional[str] = None,
    device_scale_factor: float = 1.0,
) -> AsyncGenerator[Page, None]:
    """
    异步上下文管理器：快速获取带反检测预设的 Playwright Page 对象。
    
    用法：
        async with get_browser_context() as page:
            await page.goto("https://example.com")
    """
    if headless is None:
        headless_env = os.getenv("BROWSER_HEADLESS", "true").lower()
        headless = headless_env in ("true", "1", "yes")

    vp = viewport or DEFAULT_VIEWPORT
    ua = user_agent or DEFAULT_USER_AGENT

    async with async_playwright() as p:
        browser = None
        # Try local system browsers first (chrome, msedge) to avoid 300MB download
        for channel in ["chrome", "msedge", None]:
            try:
                launch_args = {
                    "headless": headless,
                    "args": [
                        "--disable-blink-features=AutomationControlled",
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                    ],
                }
                if channel:
                    launch_args["channel"] = channel
                browser = await p.chromium.launch(**launch_args)
                break
            except Exception:
                continue

        if not browser:
            raise RuntimeError(
                "No compatible browser found. Please ensure Google Chrome / Microsoft Edge is installed, "
                "or run `playwright install chromium` to download the default browser."
            )

        context: BrowserContext = await browser.new_context(
            viewport=vp,
            user_agent=ua,
            device_scale_factor=device_scale_factor,
            locale="en-US",
            timezone_id="America/New_York",
        )
        page: Page = await context.new_page()
        try:
            yield page
        finally:
            await context.close()
            await browser.close()


async def fetch_page_content(
    url: str,
    timeout: int = 30000,
    wait_until: str = "domcontentloaded",
) -> Dict[str, Any]:
    """
    抓取目标 URL 渲染后的 DOM HTML、标题与 HTTP 状态码。
    
    返回：
        {
            "url": str,
            "title": str,
            "html": str,
            "status": int
        }
    """
    async with get_browser_context() as page:
        response = await page.goto(url, wait_until=wait_until, timeout=timeout)
        title = await page.title()
        html = await page.content()
        status = response.status if response else 200

        return {
            "url": url,
            "title": title,
            "html": html,
            "status": status,
        }


async def render_html_to_image(
    html_content: str,
    output_path: str,
    width: int = 1000,
    height: int = 1500,
    device_scale_factor: float = 2.0,
    wait_time_ms: int = 500,
) -> str:
    """
    将 HTML/CSS 字符串通过无头浏览器渲染为高质量 PNG 图片。
    特别适用于 P2 (Pinterest 1000x1500 竖图) 与 P1/P3 生成报告截图。
    
    参数：
        html_content: 包含内联样式或外链 CSS 的完整 HTML 代码
        output_path: 保存 PNG 的目标文件路径
        width: 渲染宽度 (像素)
        height: 渲染高度 (像素)
        device_scale_factor: 缩放比（2.0 为 Retina 高清）
    """
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    viewport = {"width": width, "height": height}
    async with get_browser_context(viewport=viewport, device_scale_factor=device_scale_factor) as page:
        await page.set_content(html_content, wait_until="networkidle")
        if wait_time_ms > 0:
            await asyncio.sleep(wait_time_ms / 1000.0)
        await page.screenshot(path=str(out), full_page=False)

    return str(out.resolve())


async def take_screenshot(
    url: str,
    output_path: str,
    full_page: bool = True,
    timeout: int = 30000,
    viewport: Optional[Dict[str, int]] = None,
) -> str:
    """
    访问目标 URL 并截图保存。
    """
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    async with get_browser_context(viewport=viewport) as page:
        await page.goto(url, wait_until="networkidle", timeout=timeout)
        await page.screenshot(path=str(out), full_page=full_page)

    return str(out.resolve())


async def extract_visual_elements(url: str, timeout: int = 30000) -> Dict[str, Any]:
    """
    提取目标页面的关键视觉要素：
    - 所有内联与外链 SVG 标签代码
    - 图片资产链接 (img src, background-image)
    - 常见色彩聚类 (从 computedStyle 采样)
    - 字体族 (font-family)
    """
    async with get_browser_context() as page:
        await page.goto(url, wait_until="networkidle", timeout=timeout)

        # 在浏览器上下文中执行提取脚本
        data = await page.evaluate(
            """() => {
                const svgs = Array.from(document.querySelectorAll('svg')).map(s => s.outerHTML);
                const images = Array.from(document.querySelectorAll('img'))
                    .map(i => i.src)
                    .filter(src => src && !src.startsWith('data:'));
                
                // 采样计算样式中的颜色和字体
                const elements = Array.from(document.querySelectorAll('body, header, main, footer, h1, h2, h3, p, a, button'));
                const colors = new Set();
                const bgColors = new Set();
                const fonts = new Set();

                for (const el of elements.slice(0, 50)) {
                    const style = window.getComputedStyle(el);
                    if (style.color) colors.add(style.color);
                    if (style.backgroundColor && style.backgroundColor !== 'rgba(0, 0, 0, 0)') {
                        bgColors.add(style.backgroundColor);
                    }
                    if (style.fontFamily) fonts.add(style.fontFamily);
                }

                return {
                    title: document.title,
                    svg_count: svgs.length,
                    svg_samples: svgs.slice(0, 15),
                    image_urls: Array.from(new Set(images)).slice(0, 20),
                    text_colors: Array.from(colors),
                    bg_colors: Array.from(bgColors),
                    font_families: Array.from(fonts)
                };
            }"""
        )
        data["url"] = url
        return data
