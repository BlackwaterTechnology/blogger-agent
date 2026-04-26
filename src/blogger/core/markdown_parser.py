from pathlib import Path
from loguru import logger
import markdown

def parse_markdown_payload(md_path: Path) -> dict:
    if not md_path.exists():
        raise FileNotFoundError(f"Markdown file not found: {md_path}")
        
    text = md_path.read_text(encoding="utf-8")
    lines = text.split("\n")
    
    title = ""
    author = ""
    collection = "AI"
    cover_filename = ""
    illustration_filename = ""
    desc_lines = []
    content_lines = []
    
    state = 0
    for line in lines:
        if line.startswith("# 标题"):
            state = 1
        elif line.startswith("# 作者"):
            state = 2
        elif line.startswith("# 简介"):
            state = 4
        elif line.startswith("# 集合"):
            state = 5
        elif line.startswith("# 封面"):
            state = 6
        elif line.startswith("# 插图"):
            state = 7
        elif line.startswith("# 正文"):
            state = 3
        elif line.startswith("---") and state != 3:
            state = 0
        elif state == 1 and line.strip():
            title = line.strip()
            state = 0
        elif state == 2 and line.strip():
            author = line.strip()
            state = 0
        elif state == 5 and line.strip():
            collection = line.strip()
            state = 0
        elif state == 6 and line.strip():
            cover_filename = line.strip()
            state = 0
        elif state == 7 and line.strip():
            illustration_filename = line.strip()
            state = 0
        elif state == 4:
            desc_lines.append(line)
        elif state == 3:
            content_lines.append(line)
            
    content = "\n".join(content_lines).strip()
    desc = "\n".join(desc_lines).strip()
    
    if desc:
        if len(desc) < 60 or len(desc) > 120:
            logger.warning(f"Summary (简介) length is {len(desc)} chars. It should be between 60 and 120 chars!")
            
    try:
        html_content = markdown.markdown(content, extensions=['fenced_code', 'tables', 'sane_lists'])
        # Inject inline styles for WeChat editor compatibility
        html_content = html_content.replace('<h1>', '<h1 style="font-size: 28px; font-weight: bold; margin-top: 20px; margin-bottom: 15px;">')
        html_content = html_content.replace('<h2>', '<h2 style="font-size: 24px; font-weight: bold; margin-top: 20px; margin-bottom: 15px;">')
        html_content = html_content.replace('<h3>', '<h3 style="font-size: 20px; font-weight: bold; margin-top: 20px; margin-bottom: 15px;">')
        html_content = html_content.replace('<h4>', '<h4 style="font-size: 18px; font-weight: bold; margin-top: 20px; margin-bottom: 15px;">')
        html_content = html_content.replace('<blockquote>', '<blockquote style="border-left: 4px solid #ccc; padding-left: 10px; color: #666; background-color: #f9f9f9; padding: 10px; margin: 10px 0;">')
    except Exception as e:
        logger.warning(f"Failed to parse markdown, falling back to raw text: {e}")
        html_content = f"<p>{content.replace(chr(10), '<br>')}</p>"
        
    logger.info(f"Parsed Title: {title}")
    logger.info(f"Parsed Author: {author}")
    logger.info(f"Parsed Collection: {collection}")
    logger.info(f"Parsed Description: {desc[:20]}... ({len(desc)} chars)")
    logger.info(f"Parsed Content Length: {len(content)}")
    logger.info(f"Generated HTML Length: {len(html_content)}")
    
    payload_dir = md_path.parent
    cover_path = payload_dir / cover_filename if cover_filename and (payload_dir / cover_filename).exists() else None
    illustration_path = payload_dir / illustration_filename if illustration_filename and (payload_dir / illustration_filename).exists() else None

    return {
        "title": title,
        "author": author,
        "collection": collection,
        "desc": desc,
        "content": content,
        "html_content": html_content,
        "cover_path": cover_path,
        "illustration_path": illustration_path
    }
