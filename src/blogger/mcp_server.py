import tempfile
import textwrap
from pathlib import Path
from loguru import logger
from mcp.server.fastmcp import FastMCP

from .core.markdown_parser import parse_markdown_payload
from .platforms.wechat import WechatPublisher

# Initialize FastMCP Server
mcp = FastMCP("Blogger Agent")

@mcp.tool()
def publish_article(
    title: str, 
    content: str, 
    platform: str = "wechat", 
    summary: str = "", 
    collection: str = "AI", 
    author: str = "Agent"
) -> str:
    """
    Publish a tech article directly via local Chrome automation.
    
    Args:
        title: The title of the article.
        content: The main content of the article in Markdown format.
        platform: The target platform. Currently only 'wechat' is supported.
        summary: A brief summary of the article (must be 60-120 chars for WeChat).
        collection: The name of the collection/tag to add this article to.
        author: The author's name.
    """
    if platform.lower() != "wechat":
        return f"Error: Platform '{platform}' is not supported yet. Only 'wechat' is available."

    # Create a temporary directory to act as the payload_dir
    payload_dir = Path(tempfile.mkdtemp(prefix="blogger_mcp_"))
    md_path = payload_dir / "ARC-AGI-文章.md"

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
        
        # 插图
        
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
        publisher = WechatPublisher()
        publisher.publish(article_data)

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
