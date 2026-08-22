from __future__ import annotations

import json
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_prompt import (  # noqa: E402
    build_finishing_plan,
    build_prompt,
    choose_layout,
    suggest_micro_text,
)
from check_palette import compare  # noqa: E402
from collage_pipeline import finish_job, prepare_job  # noqa: E402
from compose_anchor import compose  # noqa: E402
from extract_palette import extract_palette  # noqa: E402
from normalize_image import normalize  # noqa: E402
from prepare_working_image import prepare  # noqa: E402
from render_micro_text import render_text  # noqa: E402


class ScriptTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.temp = Path(self.temporary.name)
        self.source = self.temp / "source.png"
        image = Image.new("RGB", (320, 240), "#396A93")
        for x in range(160, 320):
            for y in range(240):
                image.putpixel((x, y), (186, 126, 76))
        image.save(self.source)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_palette_report_is_weighted(self) -> None:
        report = extract_palette(self.source, colors=4)
        self.assertGreaterEqual(len(report["palette"]), 2)
        total = sum(item["weight"] for item in report["palette"])
        self.assertAlmostEqual(total, 1.0, places=3)
        self.assertIn("#", report["prompt_contract"])
        self.assertNotEqual(
            report["dominant"]["hex"],
            report["source_accent_candidate"]["hex"],
        )

    def test_both_prompt_styles_compile(self) -> None:
        for style in ("impressionist-blocks", "realist-fine-lines"):
            prompt = build_prompt(
                image=self.source,
                style=style,
                scene="a blue and brown geometric scene",
                must_keep="the vertical divide and original colors",
            )
            self.assertIn(f"Selected style: {style}", prompt)
            self.assertIn("Palette contract", prompt)
            self.assertIn("Selected layout:", prompt)
            self.assertIn("typography that will be added locally", prompt)
            self.assertIn("Do not render any new letters", prompt)

    def test_automatic_micro_text_matches_scene(self) -> None:
        self.assertEqual(
            suggest_micro_text("a sunlit garden café beneath mature trees"),
            "Afternoon Under Leaves",
        )
        self.assertEqual(
            suggest_micro_text("mountains reflected in a clear lake"),
            "Sky Held Below",
        )

    def test_finishing_plan_keeps_exact_text_out_of_remote_prompt(self) -> None:
        plan = build_finishing_plan(
            scene="a sunlit garden café beneath mature trees",
            layout="offset-left",
            micro_text="Green Hours",
        )
        prompt = build_prompt(
            image=self.source,
            style="impressionist-blocks",
            scene="a sunlit garden café beneath mature trees",
            must_keep="the garden geometry",
            layout="offset-left",
            micro_text="Green Hours",
        )

        self.assertEqual(plan["micro_text"], "Green Hours")
        self.assertEqual(plan["text_position"], "upper-right")
        self.assertNotIn("Green Hours", prompt)

    def test_no_text_is_explicit(self) -> None:
        prompt = build_prompt(
            image=self.source,
            style="realist-fine-lines",
            scene="a quiet blue field",
            must_keep="the vertical divide",
            no_text=True,
        )
        self.assertIn("render no new letters", prompt)
        self.assertNotIn("typography that will be added locally", prompt)

    def test_micro_text_constraints_are_enforced(self) -> None:
        with self.assertRaisesRegex(ValueError, "one to four words"):
            build_prompt(
                image=self.source,
                style="realist-fine-lines",
                scene="a quiet blue field",
                must_keep="the vertical divide",
                micro_text="One Two Three Four Five",
            )
        with self.assertRaisesRegex(ValueError, "24 characters"):
            build_prompt(
                image=self.source,
                style="realist-fine-lines",
                scene="a quiet blue field",
                must_keep="the vertical divide",
                micro_text="An Excessively Lengthy Line",
            )

    def test_auto_layout_uses_scene_geometry(self) -> None:
        garden_layout = choose_layout("a garden café with a winding path", seed=0)
        mountain_layout = choose_layout("a mountain reflected across a lake", seed=0)
        self.assertIn(
            garden_layout,
            {"diagonal-rise", "diagonal-fall", "offset-left", "offset-right"},
        )
        self.assertIn(
            mountain_layout,
            {"upper-band", "lower-band", "center-island", "offset-right"},
        )
        self.assertNotEqual(
            garden_layout,
            choose_layout("a garden café with a winding path", seed=1),
        )
        self.assertNotEqual(
            mountain_layout,
            choose_layout("a mountain reflected across a lake", seed=1),
        )

    def test_explicit_split_layout_compiles(self) -> None:
        prompt = build_prompt(
            image=self.source,
            style="impressionist-blocks",
            scene="a busy garden gathering",
            must_keep="the central group",
            layout="split-fragments",
            micro_text="Green Hours",
        )
        self.assertIn("Selected layout: split-fragments", prompt)
        self.assertNotIn("Green Hours", prompt)
        self.assertIn("lower-right", prompt)
        self.assertIn("eight to fourteen", prompt)

    def test_local_color_note_is_compiled(self) -> None:
        prompt = build_prompt(
            image=self.source,
            style="realist-fine-lines",
            scene="a blue and brown geometric scene",
            must_keep="the vertical divide",
            color_note="clean snow white and a small coral garment",
        )
        self.assertIn("clean snow white and a small coral garment", prompt)

    def test_normalize_writes_rgb_png(self) -> None:
        output = self.temp / "normalized.png"
        size = normalize(self.source, output)
        self.assertEqual(size, (320, 240))
        with Image.open(output) as normalized:
            self.assertEqual(normalized.format, "PNG")
            self.assertEqual(normalized.mode, "RGB")

    def test_working_copy_is_bounded_and_original_is_untouched(self) -> None:
        large_source = self.temp / "large-source.png"
        Image.new("RGB", (2400, 1200), "#718A62").save(large_source)
        working = self.temp / "working.png"

        original_size, working_size = prepare(large_source, working, max_side=1024)

        self.assertEqual(original_size, (2400, 1200))
        self.assertEqual(working_size, (1024, 512))
        with Image.open(large_source) as original:
            self.assertEqual(original.size, (2400, 1200))
        with Image.open(working) as prepared:
            self.assertEqual(prepared.mode, "RGB")
            self.assertEqual(prepared.format, "PNG")

    def test_small_standard_jpeg_working_copy_is_byte_identical(self) -> None:
        source = self.temp / "source.jpg"
        Image.new("RGB", (640, 480), "#718A62").save(source, quality=91)
        working = self.temp / "working.jpg"

        original_size, working_size = prepare(source, working, max_side=2048)

        self.assertEqual(original_size, (640, 480))
        self.assertEqual(working_size, (640, 480))
        self.assertEqual(source.read_bytes(), working.read_bytes())

    def test_batched_prepare_and_finish_pipeline(self) -> None:
        output_dir = self.temp / "job"
        prepare_result = prepare_job(
            Namespace(
                source=self.source,
                output_dir=output_dir,
                stem="sample",
                style="impressionist-blocks",
                scene="a calm sea with a level horizon",
                must_keep="the horizon and source colors",
                layout="lower-band",
                layout_seed=0,
                anchor_share=52,
                anchor_box=None,
                crop_center=(0.5, 0.8),
                micro_text="Quiet Tide",
                no_text=False,
                text_position="auto",
                colors=6,
                color_note="",
                max_side=2048,
            )
        )
        plan_path = Path(str(prepare_result["plan_file"]))
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        self.assertEqual(plan["anchor_box"], [0.0, 0.68, 1.0, 0.32])
        self.assertEqual(plan["crop_center"], [0.5, 0.8])
        self.assertIn("locally restorable photo fragment", str(prepare_result["prompt"]))

        generated = self.temp / "generated.png"
        Image.new("RGB", (600, 1000), "#DDE7E9").save(generated)
        final = self.temp / "final.png"
        finish_result = finish_job(
            Namespace(
                generated=generated,
                source=self.source,
                plan=plan_path,
                output=final,
                generated_copy=None,
                anchored_output=None,
                seed=7,
                edge_jitter=0.018,
                colors=6,
            )
        )
        self.assertTrue(final.is_file())
        self.assertEqual(finish_result["phase"], "finish")
        self.assertLess(float(finish_result["elapsed_seconds"]), 3.0)

    def test_local_micro_text_is_exact_and_deterministic(self) -> None:
        background = Image.new("RGB", (600, 900), "#EEE7D8")
        first = render_text(background, "Still Water", "lower-right", seed=11)
        second = render_text(background, "Still Water", "lower-right", seed=11)

        self.assertEqual(first.size, background.size)
        self.assertEqual(first.tobytes(), second.tobytes())
        self.assertNotEqual(first.tobytes(), background.tobytes())

    def test_compositor_preserves_palette(self) -> None:
        background = Image.new("RGB", (600, 900), "#EEE7D8")
        with Image.open(self.source) as source:
            result = compose(background, source, (0.2, 0.2, 0.6, 0.5), seed=4, jitter_ratio=0.015)
        output = self.temp / "result.png"
        result.save(output)

        anchor = result.crop((120, 180, 480, 630))
        anchor_path = self.temp / "anchor.png"
        anchor.save(anchor_path)
        difference = compare(extract_palette(self.source), extract_palette(anchor_path))
        self.assertLess(difference, 6.0)

    def test_compositor_supports_diagonal_rotation(self) -> None:
        background = Image.new("RGB", (600, 900), "#EEE7D8")
        with Image.open(self.source) as source:
            result = compose(
                background,
                source,
                (0.18, 0.25, 0.64, 0.42),
                seed=8,
                jitter_ratio=0.015,
                rotation=-9,
                crop_center=(0.65, 0.5),
            )
        self.assertEqual(result.size, background.size)
        self.assertNotEqual(result.getpixel((300, 450)), background.getpixel((300, 450)))


if __name__ == "__main__":
    unittest.main()
