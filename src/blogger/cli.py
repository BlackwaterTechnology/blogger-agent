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
    publish_parser.add_argument("--platform", default="wechat", help="Target platform(s) to publish to, comma-separated (e.g. wechat,juejin,csdn,blogger,medium,wechat_video,wechat_channels,bilibili)")
    publish_parser.add_argument(
        "--no-publish",
        action="store_true",
        help="Fill the publish dialog but stop before clicking the final submit button. "
             "Useful for previewing or testing without spamming the platform. "
             "Currently honored by juejin, csdn, blogger and medium; wechat is always manual.",
    )

    # Diagram command
    diagram_parser = subparsers.add_parser("generate-diagram", help="Generate an image from diagram text")
    diagram_parser.add_argument("--type", required=True, choices=["mermaid", "plantuml", "excalidraw"], help="Type of diagram")
    diagram_parser.add_argument("--input", required=True, help="Path to the text file containing diagram code")
    diagram_parser.add_argument("--output", required=True, help="Path to save the generated image (e.g. cover.png)")

    # Infographic command
    infographic_parser = subparsers.add_parser("infographic", help="Generate a customized infographic via notebooklm")
    infographic_parser.add_argument("--payload", default="articles/test_data", help="Directory containing article markdown files or path to markdown file")
    infographic_parser.add_argument("--prompt", help="Custom prompt / instructions for the infographic")
    infographic_parser.add_argument("--style", default="bento-grid", choices=["bento-grid", "editorial", "professional", "instructional", "scientific", "sketch-note", "clay", "bricks", "anime", "kawaii", "auto"], help="Visual style")
    infographic_parser.add_argument("--orientation", default="portrait", choices=["portrait", "landscape", "square"], help="Orientation")
    infographic_parser.add_argument("--detail", default="detailed", choices=["concise", "standard", "detailed"], help="Level of detail")
    infographic_parser.add_argument("--output", help="Output path for downloaded infographic image")

    # Video command
    video_parser = subparsers.add_parser("video", help="Generate a cinematic video and publish to platforms")
    video_parser.add_argument("--payload", default="articles/test_data", help="Directory containing the article markdown files for metadata")
    video_parser.add_argument("--prompt", help="Prompt for video generation. If not provided, the article content is used.")
    video_parser.add_argument("--platform", default="bilibili,wechat_channels,wechat_video", help="Target platform(s) to publish to, comma-separated (e.g. bilibili,wechat_channels,wechat_video)")
    video_parser.add_argument(
        "--no-publish",
        action="store_true",
        help="Fill the publish dialog but stop before clicking the final submit button.",
    )



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

    if args.command == "video":
        handle_video(args, args.payload)
        return

    # Fallback/Default to publish or infographic
    payload_path = Path(args.payload)
    md_path = None
    
    if payload_path.is_file() and payload_path.suffix == ".md":
        md_path = payload_path
    else:
        md_files = list(payload_path.glob("*.md"))
        if not md_files:
            mp4_files = list(payload_path.glob("*.mp4"))
            if not mp4_files:
                logger.error(f"No Markdown files found in {payload_path}")
                return
            else:
                logger.info(f"No Markdown files found, but found video files in {payload_path}. Operating in video-only mode.")
        else:
            # Prioritize payload.md, article.md, or default name if they exist
            for candidate in ["payload.md", "article.md", "ARC-AGI-文章.md"]:
                candidate_path = payload_path / candidate
                if candidate_path in md_files:
                    md_path = candidate_path
                    break
            if not md_path:
                md_path = md_files[0]
                if len(md_files) > 1:
                    logger.warning(f"Multiple Markdown files found. Using {md_path.name}")
    
    if md_path:
        logger.info(f"Parsing payload from: {md_path}")
        
        if args.command == "infographic":
            handle_infographic(args, md_path)
            return

        article_data = parse_markdown_payload(md_path)
        article_data["payload_path"] = md_path
    else:
        if args.command == "infographic":
            handle_infographic(args, None, payload_path)
            return
            
        article_data = {"payload_path": payload_path}
        
        # Prioritize watermark-removed video if it exists
        clean_mp4s = list(payload_path.glob("*_clean.mp4"))
        if clean_mp4s:
            article_data["video_path"] = clean_mp4s[0]
        else:
            all_mp4s = list(payload_path.glob("*.mp4"))
            if all_mp4s:
                article_data["video_path"] = all_mp4s[0]

        cover_pngs = list(payload_path.glob("cover.png"))
        if cover_pngs:
            article_data["cover_path"] = cover_pngs[0]
                
        metadata_file = payload_path / "metadata.txt"
        if metadata_file.exists():
            logger.info(f"Parsing basic metadata from: {metadata_file}")
            content = metadata_file.read_text(encoding="utf-8")
            import re
            title_match = re.search(r"###\s*标题：\s*(.*?)(?:\n|$)", content)
            if title_match:
                article_data["title"] = title_match.group(1).strip()
            
            desc_match = re.search(r"####\s*【发布简介/文案】\s*\n(.*)", content, re.DOTALL)
            if desc_match:
                article_data["desc"] = desc_match.group(1).strip()
            else:
                article_data["desc"] = content.strip()
    
    platforms = [p.strip().lower() for p in args.platform.split(",") if p.strip()]
    
    dry_run = bool(getattr(args, "no_publish", False))
    if dry_run:
        logger.info("--no-publish set: will skip the final submit click on platforms that auto-submit (juejin, csdn).")

    for platform in platforms:
        if platform == "wechat":
            logger.info("Initiating WeChat publishing flow...")
            publisher = WechatPublisher()
            publisher.publish(article_data)
        elif platform == "juejin":
            from .platforms.juejin import JuejinPublisher
            logger.info("Initiating Juejin publishing flow...")
            publisher = JuejinPublisher()
            publisher.publish(article_data, dry_run=dry_run)
        elif platform == "csdn":
            from .platforms.csdn import CsdnPublisher
            logger.info("Initiating CSDN publishing flow...")
            publisher = CsdnPublisher()
            publisher.publish(article_data, dry_run=dry_run)
        elif platform == "bilibili":
            from .platforms.bilibili import BilibiliPublisher
            logger.info("Initiating Bilibili publishing flow...")
            publisher = BilibiliPublisher()
            publisher.publish(article_data, dry_run=dry_run)
        elif platform == "blogger":
            from .platforms.blogger import BloggerPublisher
            logger.info("Initiating Blogger publishing flow...")
            publisher = BloggerPublisher()
            publisher.publish(article_data, dry_run=dry_run)
        elif platform == "medium":
            from .platforms.medium import MediumPublisher
            logger.info("Initiating Medium publishing flow...")
            publisher = MediumPublisher()
            publisher.publish(article_data, dry_run=dry_run)
        elif platform == "wechat_video":
            from .platforms.wechat_video import WechatVideoPublisher
            logger.info("Initiating WeChat Official Account Video publishing flow...")
            publisher = WechatVideoPublisher()
            publisher.publish(article_data)
        elif platform == "wechat_channels":
            from .platforms.wechat_channels import WechatChannelsPublisher
            logger.info("Initiating WeChat Channels publishing flow...")
            publisher = WechatChannelsPublisher()
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
            dry_run = bool(getattr(args, "no_publish", False))
            if dry_run:
                logger.info("--no-publish set: will skip the final submit click on Bilibili.")

            for platform in platforms:
                if platform == "bilibili":
                    from .platforms.bilibili import BilibiliPublisher
                    logger.info("Initiating Bilibili publishing flow...")
                    publisher = BilibiliPublisher()
                    publisher.publish(article_data, dry_run=dry_run)
                elif platform == "wechat_channels":
                    from .platforms.wechat_channels import WechatChannelsPublisher
                    logger.info("Initiating WeChat Channels publishing flow...")
                    publisher = WechatChannelsPublisher()
                    publisher.publish(article_data)
                elif platform == "wechat_video":
                    from .platforms.wechat_video import WechatVideoPublisher
                    logger.info("Initiating WeChat Official Account Video publishing flow...")
                    publisher = WechatVideoPublisher()
                    publisher.publish(article_data)
                elif platform == "none":
                    logger.info("Platform is none, skipping publishing.")
                else:
                    logger.warning(f"Platform '{platform}' is currently not implemented or unknown for video command.")

        except json.JSONDecodeError:
            logger.error(f"Failed to parse notebooklm output: {result.stdout}")
        except subprocess.CalledProcessError as e:
            logger.error(f"notebooklm command failed: {e.stderr}")
    except subprocess.CalledProcessError as e:
        logger.error(f"notebooklm command failed: {e.stderr}")


def handle_infographic(args, md_path=None, payload_path=None):
    import subprocess
    import json

    prompt = args.prompt
    if not prompt and md_path:
        article_data = parse_markdown_payload(md_path)
        prompt = f"Title: {article_data.get('title', '')}\nDescription: {article_data.get('desc', '')}"
    elif not prompt:
        prompt = "Synthesize key insights and architecture into a high-density infographic"

    output_path = args.output
    if not output_path:
        target_dir = md_path.parent if md_path else (payload_path if payload_path else Path("."))
        output_path = str(target_dir / f"infographic_{args.style}.png")

    logger.info(f"Generating infographic ({args.style}, {args.orientation}) via notebooklm-py...")
    cmd = [
        "uv", "run", "notebooklm", "generate", "infographic",
        prompt,
        "--style", args.style,
        "--orientation", args.orientation,
        "--detail", args.detail,
        "--language", "zh_Hans",
        "--wait",
        "--json",
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        try:
            data = json.loads(result.stdout)
            if data.get("error"):
                logger.error(f"Infographic generation error: {data.get('message')}")
                return
            
            logger.info(f"Infographic generated successfully. Downloading to {output_path}...")
            dl_result = subprocess.run(
                ["uv", "run", "notebooklm", "download", "infographic", output_path, "--latest"],
                capture_output=True,
                text=True,
                check=True
            )
            logger.info(f"Infographic downloaded to: {output_path}")
        except json.JSONDecodeError:
            logger.error(f"Failed to parse notebooklm output: {result.stdout}")
    except subprocess.CalledProcessError as e:
        logger.error(f"notebooklm command failed: {e.stderr}")


if __name__ == "__main__":
    main()
