import sys
import argparse
from pathlib import Path
from loguru import logger
from .core.markdown_parser import parse_markdown_payload
from .platforms.wechat import WechatPublisher
from .core.diagrams import generate_from_kroki

def main():
    # Backward compatibility: if no command is provided, or an option is provided first, default to 'publish'
    if len(sys.argv) > 1 and sys.argv[1].startswith("--"):
        sys.argv.insert(1, "publish")
    elif len(sys.argv) == 1:
        sys.argv.append("publish")

    parser = argparse.ArgumentParser(description="Blogger Agent CLI")
    subparsers = parser.add_subparsers(dest="command")
    
    # Publish command
    publish_parser = subparsers.add_parser("publish", help="Publish an article payload")
    publish_parser.add_argument("--payload", default="articles/test_data", help="Directory containing the article markdown files")
    publish_parser.add_argument("--platform", default="wechat", help="Target platform(s) to publish to, comma-separated (e.g. wechat,juejin,csdn)")

    # Diagram command
    diagram_parser = subparsers.add_parser("generate-diagram", help="Generate an image from diagram text")
    diagram_parser.add_argument("--type", required=True, choices=["mermaid", "plantuml", "excalidraw"], help="Type of diagram")
    diagram_parser.add_argument("--input", required=True, help="Path to the text file containing diagram code")
    diagram_parser.add_argument("--output", required=True, help="Path to save the generated image (e.g. cover.png)")

    args = parser.parse_args()
    
    if args.command == "generate-diagram":
        input_file = Path(args.input)
        if not input_file.exists():
            logger.error(f"Input file not found: {args.input}")
            sys.exit(1)
            
        code = input_file.read_text(encoding="utf-8")
        success = generate_from_kroki(args.type, code, args.output)
        if not success:
            sys.exit(1)
        return

    # Fallback/Default to publish
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
    
    platforms = [p.strip().lower() for p in args.platform.split(",") if p.strip()]
    
    for platform in platforms:
        if platform == "wechat":
            logger.info("Initiating WeChat publishing flow...")
            publisher = WechatPublisher()
            publisher.publish(article_data)
        elif platform == "juejin":
            from .platforms.juejin import JuejinPublisher
            logger.info("Initiating Juejin publishing flow...")
            publisher = JuejinPublisher()
            publisher.publish(article_data)
        elif platform == "csdn":
            from .platforms.csdn import CsdnPublisher
            logger.info("Initiating CSDN publishing flow...")
            publisher = CsdnPublisher()
            publisher.publish(article_data)
        else:
            logger.warning(f"Platform '{platform}' is currently not implemented or unknown.")

if __name__ == "__main__":
    main()
