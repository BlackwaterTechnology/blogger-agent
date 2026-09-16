import os
import shutil
import tempfile
import unittest
from pathlib import Path
from PIL import Image

import cv2
import numpy as np

from src.blogger.core.digital_human import (
    VideoFrameSampler,
    get_digital_human_driver,
    ExternalVideoDriver,
    FasterLivePortraitMLXDriver,
    LivePortraitPyTorchDriver,
    CloudApiDriver,
    TemplateMotionDriver,
)
from src.blogger.core.dual_sub_video import (
    create_dual_sub_payload,
    generate_video_cover,
    generate_video_payload_md,
)


class TestDigitalHumanSchemeB(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="dh_test_")
        self.temp_p = Path(self.temp_dir)

        # Create a test avatar image (400x400)
        self.avatar_path = self.temp_p / "test_avatar.png"
        img = Image.new("RGB", (400, 400), color=(56, 189, 248))
        img.save(self.avatar_path)

        # Create a dummy 1-second video using OpenCV VideoWriter
        self.video_path = self.temp_p / "test_avatar.mp4"
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        vw = cv2.VideoWriter(str(self.video_path), fourcc, 10.0, (200, 200))
        for _ in range(10):
            frame = np.zeros((200, 200, 3), dtype=np.uint8)
            frame[:, :] = (0, 255, 0)
            vw.write(frame)
        vw.release()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_video_frame_sampler(self):
        with VideoFrameSampler(self.video_path, (640, 870)) as sampler:
            self.assertEqual(sampler.fps, 10.0)
            self.assertEqual(sampler.total_frames, 10)
            
            # Sample frame at t=0.0s
            frame0 = sampler.get_frame(0.0)
            self.assertIsInstance(frame0, Image.Image)
            self.assertEqual(frame0.size, (640, 870))

            # Sample frame at t=0.5s
            frame_mid = sampler.get_frame(0.5)
            self.assertEqual(frame_mid.size, (640, 870))

            # Sample frame beyond duration (should clamp to last frame)
            frame_end = sampler.get_frame(10.0)
            self.assertEqual(frame_end.size, (640, 870))

    def test_driver_factory(self):
        self.assertIsInstance(get_digital_human_driver("external"), ExternalVideoDriver)
        self.assertIsInstance(get_digital_human_driver("mlx"), FasterLivePortraitMLXDriver)
        self.assertIsInstance(get_digital_human_driver("pytorch"), LivePortraitPyTorchDriver)
        self.assertIsInstance(get_digital_human_driver("cloud"), CloudApiDriver)
        self.assertIsInstance(get_digital_human_driver("template"), TemplateMotionDriver)

        # Auto driver should return an available driver instance
        auto_driver = get_digital_human_driver("auto")
        self.assertIsNotNone(auto_driver)

    def test_external_video_driver(self):
        driver = ExternalVideoDriver(self.video_path)
        self.assertTrue(driver.is_available())
        out_dest = self.temp_p / "output_avatar.mp4"
        res = driver.generate(self.avatar_path, self.video_path, out_dest)
        self.assertTrue(res.exists())
        self.assertEqual(res.resolve(), out_dest.resolve())

    def test_template_motion_driver_generation(self):
        # Create a small dummy audio file via ffmpeg
        audio_path = self.temp_p / "test_audio.mp3"
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "anullsrc=r=16000:cl=mono",
            "-t", "0.5",
            "-q:a", "9",
            str(audio_path)
        ]
        res = os.system(" ".join(cmd) + " > /dev/null 2>&1")
        if res == 0 and audio_path.exists():
            driver = TemplateMotionDriver()
            out_vid = self.temp_p / "template_talking.mp4"
            out = driver.generate(self.avatar_path, audio_path, out_vid, fps=10)
            self.assertTrue(out.exists())
            self.assertGreater(out.stat().st_size, 1000)

    def test_cover_with_avatar_video(self):
        cov_path = self.temp_p / "cover_video.png"
        generate_video_cover(
            output_path=cov_path,
            title="Video Driven Cover Test",
            layout="avatar",
            avatar_image=self.avatar_path,
            avatar_video=self.video_path,
            avatar_badge="TECH TUTOR",
        )
        self.assertTrue(cov_path.exists())
        with Image.open(cov_path) as img:
            self.assertEqual(img.size, (1920, 1080))

    def test_payload_with_avatar_video(self):
        sent_path = self.temp_p / "sentences.txt"
        sent_path.write_text("Sentence one.\nSentence two.\n", encoding="utf-8")
        payload_p = self.temp_p / "payload_scheme_b"

        res = create_dual_sub_payload(
            payload_dir=payload_p,
            sentences_path=sent_path,
            title="Scheme B Standup",
            desc="A standard test description for Scheme B digital human payload.",
            layout="avatar",
            avatar_image=self.avatar_path,
            avatar_video=self.video_path,
        )

        self.assertEqual(res["layout"], "avatar")
        self.assertTrue((payload_p / "avatar_talking.mp4").exists())
        self.assertTrue((payload_p / "payload.md").exists())
        md_text = (payload_p / "payload.md").read_text(encoding="utf-8")
        self.assertIn('avatar_video: "avatar_talking.mp4"', md_text)
        self.assertIn('layout: "avatar"', md_text)


if __name__ == "__main__":
    unittest.main()
