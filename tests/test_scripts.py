from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_prompt import build_prompt, choose_layout, suggest_micro_text  # noqa: E402
from check_palette import compare  # noqa: E402
from compose_anchor import compose  # noqa: E402
from extract_palette import extract_palette  # noqa: E402
from normalize_image import normalize  # noqa: E402


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
            self.assertIn("Render exactly one English micro-text line", prompt)

    def test_automatic_micro_text_matches_scene(self) -> None:
        self.assertEqual(
            suggest_micro_text("a sunlit garden café beneath mature trees"),
            "Afternoon Under Leaves",
        )
        self.assertEqual(
            suggest_micro_text("mountains reflected in a clear lake"),
            "Sky Held Below",
        )

    def test_no_text_is_explicit(self) -> None:
        prompt = build_prompt(
            image=self.source,
            style="realist-fine-lines",
            scene="a quiet blue field",
            must_keep="the vertical divide",
            no_text=True,
        )
        self.assertIn("add no new letters", prompt)
        self.assertNotIn("Render exactly one English micro-text line", prompt)

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
        self.assertIn('"Green Hours"', prompt)
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
            )
        self.assertEqual(result.size, background.size)
        self.assertNotEqual(result.getpixel((300, 450)), background.getpixel((300, 450)))


if __name__ == "__main__":
    unittest.main()
