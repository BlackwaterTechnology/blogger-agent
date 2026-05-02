from pathlib import Path
from loguru import logger
import markdown
import frontmatter

def parse_markdown_payload(md_path: Path) -> dict:
    if not md_path.exists():
        raise FileNotFoundError(f"Markdown file not found: {md_path}")
        
    try:
        post = frontmatter.load(md_path)
    except Exception as e:
        logger.error(f"Failed to parse Front Matter in {md_path}: {e}")
        raise ValueError(f"Invalid Front Matter format in {md_path}") from e
    
    title = post.metadata.get("title", "")
    author = post.metadata.get("author", "")
    collection = post.metadata.get("collection", "AI")
    desc = post.metadata.get("desc", "")
    cover_filename = post.metadata.get("cover", "")
    illustration_filename = post.metadata.get("illustration", "")
    content = post.content.strip()
    
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
