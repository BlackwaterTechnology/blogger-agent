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
    video_parser = subparsers.add_parser("video", help="Generate a video (cinematic or dual-subtitle) and publish to platforms")
    video_parser.add_argument(
        "--type",
        choices=["cinematic", "dual-subtitle"],
        default="cinematic",
        help="Type of video: 'cinematic' (NotebookLM AI video) or 'dual-subtitle' (Edge-TTS + Pillow card video)",
    )
    video_parser.add_argument("--payload", default="articles/test_data", help="Directory or file containing the article or text input")
    video_parser.add_argument("--prompt", help="Prompt for video generation. If not provided, the article content is used.")
    video_parser.add_argument("--platform", default="bilibili,wechat_channels,wechat_video", help="Target platform(s) to publish to, comma-separated (e.g. bilibili,wechat_channels,wechat_video)")
    video_parser.add_argument(
        "--no-publish",
        action="store_true",
        help="Fill the publish dialog but stop before clicking the final submit button.",
    )
    video_parser.add_argument("--voice", default="en-US-JennyNeural", help="Edge-TTS voice for dual-subtitle video")
    video_parser.add_argument("--level", default="a2", choices=["a2", "b1", "b2", "c1", "A2", "B1", "B2", "C1"], help="CEFR English level (a2, b1, b2, c1; default: a2)")
    video_parser.add_argument("--rate", help="Speech rate for dual-subtitle video (defaults to level preset, e.g. -12%% for A2)")
    video_parser.add_argument("--pitch", default="+2Hz", help="Speech pitch for dual-subtitle video")
    video_parser.add_argument("--title", help="Header title for dual-subtitle video")
    video_parser.add_argument("--tag", help="Header badge tag for dual-subtitle video")
    video_parser.add_argument("--desc", help="Summary / description for dual-subtitle video payload (60-120 chars)")
    video_parser.add_argument("--collection", default="软件教程", help="Collection for video matching blogger.toml (e.g. 软件教程, 程序员, agent)")
    video_parser.add_argument("--output", help="Output MP4 path for generated video")
    video_parser.add_argument("--bg-image", help="Ambient background image path (auto-detects bg.png in payload dir)")



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

def handle_video(args, payload_path):
    import subprocess
    import json
    import tempfile
    import urllib.request

    payload_path = Path(payload_path)
    video_type = getattr(args, "type", "cinematic")
    article_data = {}

    if video_type == "dual-subtitle":
        from .core.dual_sub_video import (
            generate_dual_subtitle_video,
            generate_video_cover,
            generate_video_payload_md,
            clean_video_title,
            clean_video_desc,
        )

        input_file = None
        payload_dir = None
        existing_md = None

        if payload_path.is_file():
            if payload_path.suffix == ".md":
                existing_md = payload_path
                payload_dir = payload_path.parent
                candidate_txt = payload_dir / "sentences.txt"
                if candidate_txt.exists():
                    input_file = candidate_txt
            else:
                input_file = payload_path
                payload_dir = payload_path.parent
        elif payload_path.is_dir():
            payload_dir = payload_path
            for candidate in ["payload.md", "article.md"]:
                c_md = payload_dir / candidate
                if c_md.exists():
                    existing_md = c_md
                    break
            for c_txt in [payload_dir / "sentences.txt", payload_dir / "input.txt"]:
                if c_txt.exists():
                    input_file = c_txt
                    break
            if not input_file:
                txts = list(payload_dir.glob("*.txt"))
                if txts:
                    input_file = txts[0]

        if not input_file and existing_md:
            input_file = existing_md

        if not input_file or not input_file.exists():
            logger.error(f"Could not find input text or sentence file for dual-subtitle video in: {payload_path}")
            return

        if not payload_dir:
            payload_dir = input_file.parent

        # 1. Resolve metadata from arguments or existing payload.md
        title = getattr(args, "title", None)
        desc = getattr(args, "desc", None)
        collection = getattr(args, "collection", None) or "软件教程"
        tag = getattr(args, "tag", None)
        level = (getattr(args, "level", None) or "a2").lower()

        if existing_md and existing_md.exists():
            try:
                article_data = parse_markdown_payload(existing_md)
                if not title and article_data.get("title"):
                    title = article_data["title"]
                if not desc and article_data.get("desc"):
                    desc = article_data["desc"]
                if not collection and article_data.get("collection"):
                    collection = article_data["collection"]
                if getattr(args, "level", None) is None and article_data.get("level"):
                    level = str(article_data["level"]).lower()
            except Exception as e:
                logger.debug(f"Failed to parse existing payload.md: {e}")

        if not title:
            title = input_file.stem.replace("-", " ").replace("_", " ").title()
        if not desc:
            desc = f"Master English listening with {title}, featuring dual-tier subtitles and context stream."

        title = clean_video_title(title)
        desc = clean_video_desc(desc, title, level=level)

        # 2. Determine output paths
        if getattr(args, "output", None):
            out_mp4 = Path(args.output)
        else:
            out_mp4 = payload_dir / "video.mp4"

        cover_path = payload_dir / "cover.png"
        payload_md_path = payload_dir / "payload.md"

        # Resolve ambient background image
        bg_image = getattr(args, "bg_image", None)
        if bg_image:
            bg_image = Path(bg_image).resolve()
            if not bg_image.exists():
                logger.warning(f"Specified bg_image '{bg_image}' not found.")
                bg_image = None
        if not bg_image and payload_dir:
            for candidate in [payload_dir / "bg.png", payload_dir / "background.png"]:
                if candidate.exists():
                    bg_image = candidate
                    break

        # 3. Generate dual-subtitle video
        logger.info(f"Generating dual-subtitle video ({level.upper()}) from {input_file} to {out_mp4}...")
        try:
            generate_dual_subtitle_video(
                input_path=input_file,
                output_mp4=out_mp4,
                voice=args.voice,
                rate=args.rate,
                pitch=args.pitch,
                title=title,
                tag=tag,
                bg_image=bg_image,
                level=level,
            )
        except Exception as e:
            logger.error(f"Failed to generate dual-subtitle video: {e}")
            return

        # 4. Generate cover.png if missing
        if not cover_path.exists():
            logger.info(f"Generating standard 16:9 video cover to {cover_path}...")
            generate_video_cover(
                output_path=cover_path,
                title=title,
                tag=tag or "A2 · ELEMENTARY",
                bg_image_path=bg_image,
            )

        # 5. Generate payload.md if missing
        if not payload_md_path.exists():
            logger.info(f"Scaffolding payload.md at {payload_md_path}...")
            generate_video_payload_md(
                payload_dir=payload_dir,
                title=title,
                desc=desc,
                collection=collection,
                video_filename=out_mp4.name,
                cover_filename=cover_path.name,
                sentences_path=input_file if input_file.suffix == ".txt" else None,
                level=level,
            )

        # 6. Parse payload.md to construct complete article_data for publishing
        if payload_md_path.exists():
            article_data = parse_markdown_payload(payload_md_path)
        else:
            article_data["title"] = title
            article_data["desc"] = desc
            article_data["collection"] = collection
            article_data["video_path"] = out_mp4
            article_data["cover_path"] = cover_path

        article_data["video_path"] = out_mp4
        article_data["cover_path"] = cover_path

    else:
        # Cinematic video via NotebookLM
        md_path = None
        if payload_path.is_file() and payload_path.suffix == ".md":
            md_path = payload_path
        elif payload_path.is_dir():
            default_path = payload_path / "ARC-AGI-文章.md"
            md_files = list(payload_path.glob("*.md"))
            if default_path in md_files:
                md_path = default_path
            elif md_files:
                md_path = md_files[0]

        if not md_path:
            logger.error(f"Command 'video' (cinematic) requires a Markdown payload for metadata. Not found in {payload_path}")
            return

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
        except json.JSONDecodeError:
            logger.error(f"Failed to parse notebooklm output: {result.stdout}")
            return
        except subprocess.CalledProcessError as e:
            logger.error(f"notebooklm command failed: {e.stderr}")
            return

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
