import argparse
from pathlib import Path
from loguru import logger
from .core.markdown_parser import parse_markdown_payload
from .platforms.wechat import WechatPublisher

def main():
    parser = argparse.ArgumentParser(description="Blogger Agent Publish Script")
    parser.add_argument("--payload", default="test_data", help="Directory containing the article markdown files")
    parser.add_argument("--platform", default="wechat", choices=["wechat", "juejin", "csdn"], help="Target platform to publish to")
    args = parser.parse_args()
    
    payload_dir = Path(args.payload)
    md_path = payload_dir / "ARC-AGI-文章.md"
    
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
