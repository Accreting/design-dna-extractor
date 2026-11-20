"""
shared_infra
~~~~~~~~~~~~
5个出海 Micro-SaaS 项目共用基础设施底座。
提供：
- 统一 Playwright 异步抓取/渲染封装 (browser)
- 统一 LLM 结构化输出/Mock 回退封装 (llm_client)
- 统一 ZIP/Markdown/CSV 打包持久化封装 (packager)
"""

from .browser import (
    fetch_page_content,
    render_html_to_image,
    take_screenshot,
    get_browser_context,
    extract_visual_elements,
)
from .packager import (
    create_zip_archive,
    save_markdown_report,
    save_csv,
)

__all__ = [
    "fetch_page_content",
    "render_html_to_image",
    "take_screenshot",
    "get_browser_context",
    "extract_visual_elements",
    "create_zip_archive",
    "save_markdown_report",
    "save_csv",
]
