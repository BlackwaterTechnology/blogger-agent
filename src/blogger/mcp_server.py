import shutil
import tempfile
import textwrap
from pathlib import Path
from loguru import logger
from mcp.server.fastmcp import FastMCP

from .core.markdown_parser import parse_markdown_payload
from .core.diagrams import generate_from_kroki
from .platforms.wechat import WechatPublisher

# Initialize FastMCP Server
mcp = FastMCP("Blogger Agent")

@mcp.tool()
def generate_diagram(diagram_type: str, code: str, output_path: str) -> str:
    """
    Generate an image from text-based diagram code using the Kroki API.
    
    Args:
        diagram_type: The type of diagram (e.g., 'mermaid', 'plantuml', 'excalidraw').
        code: The raw text code for the diagram.
        output_path: The local absolute path where the generated PNG should be saved.
    """
    success = generate_from_kroki(diagram_type, code, output_path)
    if success:
        return f"Successfully generated {diagram_type} diagram at {output_path}"
    else:
        return f"Error: Failed to generate diagram. Check server logs for details."

@mcp.tool()
def publish_article(
    title: str,
    content: str,
    platform: str = "wechat",
    summary: str = "",
    collection: str = "AI",
    author: str = "Agent",
    cover_path: str = "",
    illustration_path: str = "",
    no_publish: bool = False,
) -> str:
    """
    Publish a tech article directly via local Chrome automation.

    Args:
        title: The title of the article.
        content: The main content of the article in Markdown format.
        platform: The target platform. Currently 'wechat', 'juejin', 'csdn' and 'bilibili' are supported.
        summary: A brief summary of the article (must be 60-120 chars for WeChat).
        collection: The name of the collection/tag to add this article to. Must be either 'AI' or 'Agent'.
        author: The author's name.
        cover_path: Optional absolute path to a cover image.
        illustration_path: Optional absolute path to an illustration image.
        no_publish: If True, fill the publish dialog but stop before clicking the final submit button.
                    Honored by juejin and csdn; wechat is always manual.
    """
    if platform.lower() not in ["wechat", "juejin", "csdn", "bilibili"]:
        return f"Error: Platform '{platform}' is not supported yet. Only 'wechat', 'juejin', 'csdn' and 'bilibili' are available."

    # Create a temporary directory to act as the payload_dir
    payload_dir = Path(tempfile.mkdtemp(prefix="blogger_mcp_"))
    md_path = payload_dir / "ARC-AGI-文章.md"

    cover_filename = ""
    if cover_path:
        src_cover = Path(cover_path)
        if src_cover.exists():
            dst_cover = payload_dir / src_cover.name
            shutil.copy2(src_cover, dst_cover)
            cover_filename = dst_cover.name
        else:
            return f"Error: Cover image not found at {cover_path}"

    illustration_filename = ""
    if illustration_path:
        src_ill = Path(illustration_path)
        if src_ill.exists():
            dst_ill = payload_dir / src_ill.name
            shutil.copy2(src_ill, dst_ill)
            illustration_filename = dst_ill.name
        else:
            return f"Error: Illustration image not found at {illustration_path}"

    # Construct the Markdown strictly according to the existing parser expectations
    raw_md = textwrap.dedent(f"""\
        # 标题
        {title}
        # 作者
        {author}
        # 简介
        {summary}
        # 集合
        {collection}
        # 封面
        {cover_filename}
        # 插图
        {illustration_filename}
        # 正文
        {content}
    """)

    try:
        # 1. Write to temp file
        md_path.write_text(raw_md, encoding="utf-8")
        logger.info(f"Generated temporary payload at: {md_path}")

        # 2. Parse using core parser
        article_data = parse_markdown_payload(md_path)

        # 3. Publish
        logger.info(f"Initiating publish for platform: {platform}")
        if platform.lower() == "wechat":
            publisher = WechatPublisher()
            publisher.publish(article_data)
        elif platform.lower() == "juejin":
            from .platforms.juejin import JuejinPublisher
            publisher = JuejinPublisher()
            publisher.publish(article_data, dry_run=no_publish)
        elif platform.lower() == "csdn":
            from .platforms.csdn import CsdnPublisher
            publisher = CsdnPublisher()
            publisher.publish(article_data, dry_run=no_publish)
        elif platform.lower() == "bilibili":
            from .platforms.bilibili import BilibiliPublisher
            publisher = BilibiliPublisher()
            publisher.publish(article_data, dry_run=no_publish)

        return f"Successfully processed and initiated publish for '{title}' to {platform}. Payload kept at {payload_dir}."

    except Exception as e:
        logger.error(f"Failed to publish article: {str(e)}")
        return f"Error: Failed to publish article - {str(e)}"

def main():
    """Entry point for the MCP server."""
    # FastMCP's run() method automatically handles stdio transport when run as a script.
    mcp.run(transport='stdio')

if __name__ == "__main__":
    main()
