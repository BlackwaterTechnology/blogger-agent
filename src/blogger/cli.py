import argparse
from pathlib import Path
from loguru import logger
from .core.markdown_parser import parse_markdown_payload
from .platforms.wechat import WechatPublisher

def main():
    parser = argparse.ArgumentParser(description="Blogger Agent Publish Script")
    parser.add_argument("--payload", default="articles/test_data", help="Directory containing the article markdown files")
    parser.add_argument("--platform", default="wechat", choices=["wechat", "juejin", "csdn"], help="Target platform to publish to")
    args = parser.parse_args()
    
    payload_path = Path(args.payload)
    
    if payload_path.is_file() and payload_path.suffix == ".md":
        md_path = payload_path
    else:
        md_files = list(payload_path.glob("*.md"))
        if not md_files:
            logger.error(f"No Markdown files found in {payload_path}")
            return
            
        # Prioritize the default name if it exists, otherwise pick the first one
        default_path = payload_path / "ARC-AGI-文章.md"
        if default_path in md_files:
            md_path = default_path
        else:
            md_path = md_files[0]
            if len(md_files) > 1:
                logger.warning(f"Multiple Markdown files found. Using {md_path.name}")
    
    logger.info(f"Parsing payload from: {md_path}")
    article_data = parse_markdown_payload(md_path)
    
    if args.platform == "wechat":
        logger.info("Initiating WeChat publishing flow...")
        publisher = WechatPublisher()
        publisher.publish(article_data)
    else:
        logger.warning(f"Platform '{args.platform}' is currently not implemented.")

if __name__ == "__main__":
    main()
