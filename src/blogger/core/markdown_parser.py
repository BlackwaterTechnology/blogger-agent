from pathlib import Path
from loguru import logger
import markdown
import frontmatter
import re

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
            
    payload_dir = md_path.parent

    local_images = []
    
    def wechat_image_replacer(match):
        img_src = match.group(1)
        if not img_src.startswith('http://') and not img_src.startswith('https://'):
            local_img_path = payload_dir / img_src
            if local_img_path.exists():
                if local_img_path not in local_images:
                    local_images.append(local_img_path)
                return f"[UPLOAD_IMAGE: {local_img_path.absolute()}]"
        return match.group(0)

    wechat_content = re.sub(r'!\[.*?\]\((.*?)\)', wechat_image_replacer, content)

    # python-markdown 的 sane_lists 扩展严格要求列表前有空行;否则
    # `段落：\n- item` 会被并进同一个 <p>,导致微信里出现 "段落：- item" 单行长串。
    # 在这里把"非空行 + 列表项"之间自动塞一个空行,作者忘了写也能渲染对。
    # 注意:不能跨进围栏代码块,所以分块处理。
    def _ensure_blank_before_lists(md: str) -> str:
        out_lines: list[str] = []
        in_fence = False
        list_re = re.compile(r'^(\s{0,3})([-*+]|\d+\.)\s+\S')
        for line in md.splitlines():
            if line.lstrip().startswith('```') or line.lstrip().startswith('~~~'):
                in_fence = not in_fence
                out_lines.append(line)
                continue
            if not in_fence and list_re.match(line) and out_lines:
                prev = out_lines[-1]
                # 上一行非空、且本身不是列表项时,补一个空行
                if prev.strip() and not list_re.match(prev):
                    out_lines.append('')
            out_lines.append(line)
        return '\n'.join(out_lines)

    wechat_content = _ensure_blank_before_lists(wechat_content)

    try:
        html_content = markdown.markdown(wechat_content, extensions=['fenced_code', 'tables', 'sane_lists'])

        # WeChat 编辑器(ProseMirror) 列表 schema 要求 <li> 内容包到 <p> 里。
        # python-markdown 的 tight list 输出 <li>X</li>,粘贴时编辑器会把内联内容
        # 拆成多个 <p>(尤其是 <strong>/<em>/<code> 之后断开),导致一个列表项显示成两行。
        # 在这里主动给只有内联子元素的 <li> 包上 <p>,避免被拆段。
        def _wrap_li_inline(match):
            inner = match.group(1).strip()
            if not inner:
                return match.group(0)
            if inner.startswith(('<p', '<ul', '<ol', '<blockquote', '<pre', '<div')):
                return match.group(0)
            return f"<li><p>{inner}</p></li>"

        html_content = re.sub(r'<li>(.*?)</li>', _wrap_li_inline, html_content, flags=re.DOTALL)

        # Inject inline styles for WeChat editor compatibility
        html_content = html_content.replace('<h1>', '<h1 style="font-size: 28px; font-weight: bold; margin-top: 20px; margin-bottom: 15px;">')
        html_content = html_content.replace('<h2>', '<h2 style="font-size: 24px; font-weight: bold; margin-top: 20px; margin-bottom: 15px;">')
        html_content = html_content.replace('<h3>', '<h3 style="font-size: 20px; font-weight: bold; margin-top: 20px; margin-bottom: 15px;">')
        html_content = html_content.replace('<h4>', '<h4 style="font-size: 18px; font-weight: bold; margin-top: 20px; margin-bottom: 15px;">')
        html_content = html_content.replace('<blockquote>', '<blockquote style="border-left: 4px solid #ccc; padding-left: 10px; color: #666; background-color: #f9f9f9; padding: 10px; margin: 10px 0;">')
    except Exception as e:
        logger.warning(f"Failed to parse markdown, falling back to raw text: {e}")
        html_content = f"<p>{wechat_content.replace(chr(10), '<br>')}</p>"
        
    logger.info(f"Parsed Title: {title}")
    logger.info(f"Parsed Author: {author}")
    logger.info(f"Parsed Collection: {collection}")
    logger.info(f"Parsed Description: {desc[:20]}... ({len(desc)} chars)")
    logger.info(f"Parsed Content Length: {len(content)}")
    logger.info(f"Generated HTML Length: {len(html_content)}")
    logger.info(f"Found {len(local_images)} local images inline.")
    
    cover_path = payload_dir / cover_filename if cover_filename and (payload_dir / cover_filename).exists() else None
    
    # We still keep the original illustration check for backwards compatibility if no inline images exist
    illustration_path = payload_dir / illustration_filename if illustration_filename and (payload_dir / illustration_filename).exists() else None

    # Merge inline images with front-matter illustration for the publishers to process
    all_illustrations = list(local_images)
    if illustration_path and illustration_path not in all_illustrations:
        all_illustrations.insert(0, illustration_path)

    return {
        "title": title,
        "author": author,
        "collection": collection,
        "desc": desc,
        "content": content,
        "html_content": html_content,
        "cover_path": cover_path,
        "illustration_path": illustration_path,
        "local_images": all_illustrations
    }
