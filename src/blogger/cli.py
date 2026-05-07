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

    # Video command
    video_parser = subparsers.add_parser("video", help="Generate a cinematic video and publish to platforms")
    video_parser.add_argument("--payload", default="articles/test_data", help="Directory containing the article markdown files for metadata")
    video_parser.add_argument("--prompt", help="Prompt for video generation. If not provided, the article content is used.")
    video_parser.add_argument("--platform", default="bilibili,wechat_channels", help="Target platform(s) to publish to, comma-separated (e.g. bilibili,wechat_channels)")


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
    
    if args.command == "video":
        handle_video(args, md_path)
        return

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
            logger.warning(f"Platform '{platform}' is currently not implemented or unknown for publish command.")

def handle_video(args, md_path):
    import subprocess
    import json
    import tempfile
    import urllib.request

    logger.info(f"Parsing payload from: {md_path}")
    article_data = parse_markdown_payload(md_path)
    
    prompt = args.prompt if args.prompt else f"Title: {article_data['title']}\nDescription: {article_data['desc']}"
    
    logger.info("Generating cinematic video via notebooklm-py...")
    try:
        result = subprocess.run(
            ["uv", "run", "notebooklm", "generate", "cinematic-video", prompt, "--language", "zh_Hans", "--wait", "--json"],
            capture_output=True,
            text=True,
            check=True
        )
        try:
            data = json.loads(result.stdout)
            if data.get("error"):
                logger.error(f"Video generation error: {data.get('message')}")
                return
            
            video_url = data.get("url")
            video_path = data.get("file_path")
            
            if not video_path and video_url:
                logger.info(f"Downloading generated video from {video_url}...")
                fd, video_path = tempfile.mkstemp(suffix=".mp4")
                urllib.request.urlretrieve(video_url, video_path)
                logger.info(f"Video downloaded to {video_path}")
            elif not video_path:
                logger.error(f"No video URL or file_path in response: {data}")
                return
            else:
                logger.info(f"Video generated at {video_path}")
                
            article_data["video_path"] = video_path
            
            platforms = [p.strip().lower() for p in args.platform.split(",") if p.strip()]
            for platform in platforms:
                if platform == "bilibili":
                    from .platforms.bilibili import BilibiliPublisher
                    logger.info("Initiating Bilibili publishing flow...")
                    publisher = BilibiliPublisher()
                    publisher.publish(article_data)
                elif platform == "wechat_channels":
                    from .platforms.wechat_channels import WechatChannelsPublisher
                    logger.info("Initiating WeChat Channels publishing flow...")
                    publisher = WechatChannelsPublisher()
                    publisher.publish(article_data)
                elif platform == "none":
                    logger.info("Platform is none, skipping publishing.")
                else:
                    logger.warning(f"Platform '{platform}' is currently not implemented or unknown for video command.")

        except json.JSONDecodeError:
            logger.error(f"Failed to parse notebooklm output: {result.stdout}")
    except subprocess.CalledProcessError as e:
        logger.error(f"notebooklm command failed: {e.stderr}")


if __name__ == "__main__":
    main()
