from pathlib import Path
from loguru import logger
import markdown
import frontmatter
import re
import hashlib
from ..config import get_all_wechat_collections

def render_math_formula(formula: str, output_path: Path):
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        
        # Clean up common unsupported LaTeX sequences in matplotlib
        formula_clean = formula.replace(r'\le ', r'\leq ').replace(r'\ge ', r'\geq ')
        formula_clean = formula_clean.replace(r'\le}', r'\leq}').replace(r'\ge}', r'\geq}')
        formula_clean = formula_clean.strip()
        
        # Configure matplotlib to support Chinese characters and prevent errors
        matplotlib.rcParams['font.sans-serif'] = ['Heiti TC', 'Heiti SC', 'sans-serif']
        matplotlib.rcParams['axes.unicode_minus'] = False
        matplotlib.rcParams['mathtext.fontset'] = 'custom'
        matplotlib.rcParams['mathtext.rm'] = 'Heiti TC'
        matplotlib.rcParams['mathtext.it'] = 'Heiti TC'
        matplotlib.rcParams['mathtext.bf'] = 'Heiti TC'
        
        fig = plt.figure(figsize=(8, 1.5))
        text_str = formula_clean if formula_clean.startswith('$') else f"${formula_clean}$"
        
        fig.text(0.5, 0.5, text_str, size=16, va="center", ha="center", color="black")
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=200, transparent=True, bbox_inches='tight', pad_inches=0.04)
        plt.close(fig)
    except Exception as e:
        logger.error(f"Failed to render math formula '{formula}' to {output_path}: {e}")

def latex_to_unicode(latex_str: str) -> str:
    text = latex_str
    replacements = {
        r'\Delta': 'Δ',
        r'\approx': '≈',
        r'\leq': '≤',
        r'\le': '≤',
        r'\geq': '≥',
        r'\ge': '≥',
        r'\times': '×',
        r'\%': '%',
        r'\_': '_',
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    text = re.sub(r'\\text\{([^}]+)\}', r'\1', text)
    text = re.sub(r'_\{([^}]+)\}', r'_\1', text)
    text = text.replace('{', '').replace('}', '')
    return text

def is_likely_latex(s: str) -> bool:
    s = s.strip()
    if not s:
        return False
    if len(s) <= 5:
        return True
    math_chars = ['\\', '_', '^', '+', '-', '*', '/', '=', '<', '>', '{', '}']
    if any(c in s for c in math_chars):
        return True
    return False

def preprocess_math(content: str, payload_dir: Path) -> str:
    # 1. Process Block Math $$ ... $$
    block_pattern = re.compile(r'\$\$(.*?)\$\$', re.DOTALL)
    
    def block_replacer(match):
        formula = match.group(1).strip()
        if not formula:
            return ""
        hash_val = hashlib.md5(formula.encode('utf-8')).hexdigest()[:16]
        relative_path = f"formulas/formula_{hash_val}.png"
        full_path = payload_dir / relative_path
        
        if not full_path.exists():
            logger.info(f"Rendering LaTeX block formula to {relative_path}...")
            render_math_formula(formula, full_path)
            
        try:
            import base64
            with open(full_path, "rb") as f:
                img_data = f.read()
            b64_str = base64.b64encode(img_data).decode("utf-8")
            return f'\n\n<div style="text-align: center; margin: 16px 0;"><img src="data:image/png;base64,{b64_str}" alt="formula" style="max-width: 100%;" /></div>\n\n'
        except Exception as e:
            logger.error(f"Failed to inline formula to base64: {e}")
            return f"\n\n![formula]({relative_path})\n\n"
        
    content = block_pattern.sub(block_replacer, content)
    
    # 2. Process Inline Math $ ... $
    inline_pattern = re.compile(r'\$([^\s$](?:[^$\n]*?[^\s$])?)\$')
    
    def inline_replacer(match):
        formula = match.group(1).strip()
        if is_likely_latex(formula):
            return latex_to_unicode(formula)
        return match.group(0)
        
    content = inline_pattern.sub(inline_replacer, content)
    return content

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
    
    # Validate Collection against config
    allowed = get_all_wechat_collections()
    collection = post.metadata.get("collection", "AI")
    if allowed and collection not in allowed:
        logger.warning(f"Collection '{collection}' in {md_path.name} is not in the allowed list {allowed}. This may cause publishing errors.")
    
    desc = post.metadata.get("desc", "")
    cover_filename = post.metadata.get("cover", "")
    video_filename = post.metadata.get("video", "")
    illustration_filename = post.metadata.get("illustration", "")
    payload_dir = md_path.parent
    
    # Use post content as raw content (for Juejin/CSDN)
    content = post.content.strip()
    
    # 避免正文开头重复出现标题（很多 Markdown 写作习惯会在正文开头写 # 标题，发布平台通常有独立标题字段）
    lines = content.splitlines()
    if lines and lines[0].strip().startswith('#'):
        heading_text = lines[0].strip().lstrip('#').strip()
        if heading_text == title.strip():
            lines.pop(0)
            content = '\n'.join(lines).strip()
            
    if desc:
        if len(desc) < 60 or len(desc) > 120:
            logger.warning(f"Summary (简介) length is {len(desc)} chars. It should be between 60 and 120 chars!")
            
    # For Juejin/CSDN, scan the raw content to find normal local images
    local_images = []
    for match in re.finditer(r'!\[(.*?)\]\((.*?)\)', content):
        img_src = match.group(2)
        if not (img_src.startswith('http://') or img_src.startswith('https://')):
            local_img_path = payload_dir / img_src
            if local_img_path.exists() and local_img_path not in local_images:
                local_images.append(local_img_path)

    # For WeChat, we preprocess math formulas (render block formulas to PNGs, translate inline to Unicode)
    wechat_content = preprocess_math(content, payload_dir)
    
    # Scan wechat_content to find both normal local images and generated formula images
    wechat_local_images = []
    image_alts: dict[Path, str] = {}
    
    def wechat_image_replacer(match):
        alt_text = (match.group(1) or '').strip()
        img_src = match.group(2)
        if img_src.startswith('http://') or img_src.startswith('https://'):
            return match.group(0)
        local_img_path = payload_dir / img_src
        if not local_img_path.exists():
            return match.group(0)
        if local_img_path not in wechat_local_images:
            wechat_local_images.append(local_img_path)
        if alt_text and local_img_path not in image_alts:
            image_alts[local_img_path] = alt_text
        return f"[UPLOAD_IMAGE: {local_img_path.absolute()}]"

    wechat_content = re.sub(r'!\[(.*?)\]\((.*?)\)', wechat_image_replacer, wechat_content)

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

        # 微信编辑器(ProseMirror) paste schema 对围栏代码块不可靠:
        # <pre> 内部的 \n 经常被吞掉,<pre> 还可能被降级成普通 <p>,只剩
        # <code> 的等宽字体没有底色和换行(2026-05-10 HyperFrames 那篇实测)。
        # 双保险:1) <pre>/<code> 都内联样式,不依赖编辑器主题
        #        2) 内部 \n 全换成 <br>,即使 <pre> 被剥成 <p>,换行也保住。
        _PRE_STYLE = (
            'background-color:#f6f8fa; border-radius:6px; padding:12px 14px; '
            'overflow-x:auto; white-space:pre-wrap; word-break:break-all; '
            'font-family:Menlo,Monaco,Consolas,monospace; '
            'font-size:13px; line-height:1.5; color:#24292e; '
            'margin:14px 0; border:1px solid #e1e4e8;'
        )
        _CODE_BLOCK_STYLE = (
            'font-family:Menlo,Monaco,Consolas,monospace; '
            'background:transparent; padding:0; color:#24292e; '
            'font-size:inherit;'
        )

        def _style_code_blocks(match):
            attrs = match.group(1) or ''
            body = match.group(2).rstrip('\n').replace('\n', '<br>')
            return (
                f'<pre style="{_PRE_STYLE}">'
                f'<code{attrs} style="{_CODE_BLOCK_STYLE}">{body}</code>'
                '</pre>'
            )

        html_content = re.sub(
            r'<pre[^>]*><code([^>]*)>([\s\S]*?)</code></pre>',
            _style_code_blocks,
            html_content,
        )

        # 行内 <code> 也补一层等宽 + 浅底色,避免被微信 ProseMirror 当成裸文本。
        # 注意:上面 _style_code_blocks 已经给块级 <code> 加了 style,这里的
        # 替换只命中没有 style 属性的 <code>(即正文里的 inline code)。
        html_content = html_content.replace(
            '<code>',
            '<code style="background-color:#f3f4f6; color:#d63384; padding:1px 5px; '
            'border-radius:3px; font-family:Menlo,Monaco,Consolas,monospace; font-size:0.92em;">',
        )

        # Inject inline styles for WeChat editor compatibility
        html_content = html_content.replace('<h1>', '<h1 style="font-size: 28px; font-weight: bold; margin-top: 20px; margin-bottom: 15px;">')
        html_content = html_content.replace('<h2>', '<h2 style="font-size: 24px; font-weight: bold; margin-top: 20px; margin-bottom: 15px;">')
        html_content = html_content.replace('<h3>', '<h3 style="font-size: 20px; font-weight: bold; margin-top: 20px; margin-bottom: 15px;">')
        html_content = html_content.replace('<h4>', '<h4 style="font-size: 18px; font-weight: bold; margin-top: 20px; margin-bottom: 15px;">')
        html_content = html_content.replace('<blockquote>', '<blockquote style="border-left: 4px solid #ccc; padding-left: 10px; color: #666; background-color: #f9f9f9; padding: 10px; margin: 10px 0;">')

        # 微信阅读器对正文 <p> 默认 `text-align: justify; text-justify: auto; word-break: break-word`,
        # 浏览器(尤其 iOS WebKit)把 auto 解释为 CJK inter-character 分布,导致
        # "打开"、"标语" 这种相邻汉字也被 justify 拉宽。试过 `text-justify: inter-word`
        # 在 Safari/iOS 微信里被忽略仍然糊掉(2026-05-10 实测),只能直接关掉两端对齐。
        # inline style 优先级高于阅读器类样式,跨浏览器都生效。视觉上右边沿会从齐变锯齿,
        # 但比字间距撑开可读性更好。
        html_content = html_content.replace('<p>', '<p style="text-align: left;">')
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
    video_path = payload_dir / video_filename if video_filename and (payload_dir / video_filename).exists() else None

    if video_path:
        logger.info(f"Found video: {video_path.name}")
    
    # We still keep the original illustration check for backwards compatibility if no inline images exist
    illustration_path = payload_dir / illustration_filename if illustration_filename and (payload_dir / illustration_filename).exists() else None

    # Merge inline images with front-matter illustration for the publishers to process
    # 1. Normal illustrations (for Juejin/CSDN)
    all_illustrations = list(local_images)
    if illustration_path and illustration_path not in all_illustrations:
        all_illustrations.insert(0, illustration_path)

    # 2. WeChat illustrations (including formulas)
    wechat_illustrations = list(wechat_local_images)
    if illustration_path and illustration_path not in wechat_illustrations:
        wechat_illustrations.insert(0, illustration_path)

    # 与 illustrations 同序的 caption 文本(没有/不达标就空串),供发布器
    # 在 paste 后把 ProseMirror trailing empty <p> 填成图注。
    # 过滤"不像图注"的:空值、太短(<5)、或干脆就是文件名(![architecture.png](architecture.png))。
    def _captionable(alt: str, path: Path) -> str:
        a = (alt or '').strip()
        if len(a) < 5:
            return ''
        if a.lower() in (path.name.lower(), path.stem.lower()):
            return ''
        return a

    image_captions = [_captionable(image_alts.get(p, ''), p) for p in all_illustrations]
    wechat_image_captions = [_captionable(image_alts.get(p, ''), p) for p in wechat_illustrations]

    return {
        "title": title,
        "author": author,
        "collection": collection,
        "desc": desc,
        "content": content,  # Raw markdown (LaTeX intact)
        "html_content": html_content,  # WeChat HTML (LaTeX converted to PNG/Unicode)
        "cover_path": cover_path,
        "video_path": video_path,
        "illustration_path": illustration_path,
        "local_images": all_illustrations,  # Normal images only
        "wechat_local_images": wechat_illustrations,  # Normal + formulas
        "image_captions": image_captions,
        "wechat_image_captions": wechat_image_captions,
    }
