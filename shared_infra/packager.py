"""
shared_infra.packager
~~~~~~~~~~~~~~~~~~~~~
统一产物打包与报告格式化模块。
支持：
- 目录/内存文件一键打包为标准 ZIP 压缩包
- UTF-8 编码 Markdown 报告规范化持久化
- 带 UTF-8 BOM 的标准 CSV 写入（兼容 Windows Excel 与各类表格处理工具）
"""

import csv
import os
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


def create_zip_archive(
    source: Union[str, Path, List[Union[str, Path]], Dict[str, Union[str, Path, bytes]]],
    output_zip_path: Union[str, Path],
    compression: int = zipfile.ZIP_DEFLATED,
) -> str:
    """
    创建标准 ZIP 压缩包。
    
    支持 3 种输入形态：
    1. 文件夹路径：将该文件夹下所有内容打包进 ZIP 根目录。
    2. 文件路径列表：将列表中指定文件打包进 ZIP。
    3. 字典形态 `{ "arcname_in_zip.txt": "文件内容文本或物理路径" }`：
       支持直接将纯文本/二进制内存数据写入 ZIP，无需创建物理临时文件。
       
    返回：
        生成的 ZIP 文件绝对路径字符串。
    """
    out_path = Path(output_zip_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(out_path, mode="w", compression=compression) as zf:
        if isinstance(source, (str, Path)):
            src_dir = Path(source)
            if src_dir.is_dir():
                for root, _, files in os.walk(src_dir):
                    for file in files:
                        full_path = Path(root) / file
                        arcname = full_path.relative_to(src_dir)
                        zf.write(full_path, arcname=str(arcname))
            elif src_dir.is_file():
                zf.write(src_dir, arcname=src_dir.name)

        elif isinstance(source, list):
            for item in source:
                p = Path(item)
                if p.exists() and p.is_file():
                    zf.write(p, arcname=p.name)

        elif isinstance(source, dict):
            for arcname, content in source.items():
                if isinstance(content, (str, Path)) and os.path.exists(str(content)):
                    # 本地物理文件
                    zf.write(Path(content), arcname=arcname)
                elif isinstance(content, str):
                    # 内存字符串
                    zf.writestr(arcname, content.encode("utf-8"))
                elif isinstance(content, bytes):
                    # 内存二进制
                    zf.writestr(arcname, content)

    return str(out_path.resolve())


def save_markdown_report(content: str, output_path: Union[str, Path]) -> str:
    """
    持久化规范的 Markdown 文本报告，自动创建父级目录，强制 UTF-8 编码。
    """
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(content.strip() + "\n", encoding="utf-8")
    return str(out.resolve())


def save_csv(
    data: List[Dict[str, Any]],
    output_path: Union[str, Path],
    fieldnames: Optional[List[str]] = None,
) -> str:
    """
    保存结构化字典列表为 CSV 文件。
    采用 'utf-8-sig' 编码，确保在 Windows Excel 及其他工具打开时零乱码。
    """
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    if not data and not fieldnames:
        out.write_text("", encoding="utf-8-sig")
        return str(out.resolve())

    headers = fieldnames if fieldnames is not None else list(data[0].keys())

    with open(out, mode="w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for row in data:
            # 过滤掉不在 header 中的多余字段
            filtered_row = {k: row.get(k, "") for k in headers}
            writer.writerow(filtered_row)

    return str(out.resolve())
