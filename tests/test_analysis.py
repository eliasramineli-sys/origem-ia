import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from PIL import Image, PngImagePlugin

from origemia.analysis import AnalysisError, analyze, sample_indices, score_summary
from origemia.classifier import Classifier
from origemia.report import save_report


class StubClassifier:
    """Dublê exclusivo de testes; não é um detector de IA."""
    model_id = "test-only"
    revision = "test-only"

    def __init__(self, score=0.9):
        self.score = score

    def predict(self, image):
        return self.score


class AnalysisTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.photo = self.root / "exemplo.png"
        Image.new("RGB", (120, 80), "navy").save(self.photo)

    def test_no_model_is_inconclusive_without_score(self):
        report = analyze(self.photo)
        self.assertEqual(report["classificador"]["status"], "desativado")
        self.assertIsNone(report["resumo_escores"]["media"])
        self.assertIn("Inconclusivo", report["conclusao"])
        self.assertEqual(len(report["arquivo"]["sha256"]), 64)

    def test_editable_metadata_never_authenticates_origin(self):
        info = PngImagePlugin.PngInfo()
        info.add_text("Software", "ComfyUI Stable Diffusion")
        Image.new("RGB", (40, 40)).save(self.photo, pnginfo=info)
        report = analyze(self.photo)
        self.assertIn("comfyui", report["midia"]["referencias_a_geradores"])
        self.assertIn("Inconclusivo", report["conclusao"])
        self.assertEqual(report["proveniencia"]["status"], "nao_verificada")

    def test_classifier_score_and_uncertainty(self):
        for score in (0.1, 0.5, 0.9):
            report = analyze(self.photo, StubClassifier(score))
            self.assertEqual(report["resumo_escores"]["media"], score)
            self.assertIn("não são probabilidades", report["aviso"])

    def test_model_error_remains_visible(self):
        class Broken(StubClassifier):
            def predict(self, image):
                raise RuntimeError("teste de indisponibilidade")
        report = analyze(self.photo, Broken())
        self.assertEqual(report["classificador"]["status"], "indisponivel")
        self.assertIn("Inconclusivo", report["conclusao"])
        self.assertIsNone(report["resumo_escores"]["media"])

    def test_invalid_scores_cannot_leak_into_report(self):
        for score in (float("nan"), float("inf"), -1, 1.1):
            report = analyze(self.photo, StubClassifier(score))
            self.assertEqual(report["classificador"]["status"], "indisponivel")
            json.dumps(report, allow_nan=False)

    def test_bad_inputs(self):
        for path in (self.root / "missing.png", self.root):
            with self.assertRaises(AnalysisError):
                analyze(path)
        broken = self.root / "broken.jpg"
        broken.write_text("not an image")
        with self.assertRaises(AnalysisError):
            analyze(broken)
        with self.assertRaises(AnalysisError):
            analyze(self.photo, frames=0)

    def test_animation_is_not_silently_reduced_to_first_frame(self):
        Image.new("RGB", (10, 10), "red").save(self.photo, save_all=True,
            append_images=[Image.new("RGB", (10, 10), "blue")], duration=100, loop=0)
        with self.assertRaises(AnalysisError):
            analyze(self.photo)

    def test_sampling_is_bounded_and_covers_endpoints(self):
        self.assertEqual(sample_indices(100, 3), [0, 50, 99])
        self.assertEqual(sample_indices(2, 32), [0, 1])
        self.assertEqual(sample_indices(10, 1), [5])
        with self.assertRaises(AnalysisError):
            sample_indices(10, 33)

    def test_report_protects_source_and_existing_file(self):
        report = analyze(self.photo)
        with self.assertRaises(ValueError):
            save_report(report, self.photo, self.photo)
        target = self.root / "report.json"
        save_report(report, target, self.photo)
        self.assertEqual(json.loads(target.read_text())["arquivo"]["nome"], self.photo.name)
        with self.assertRaises(FileExistsError):
            save_report(report, target, self.photo)
        save_report(report, self.root / "report.txt", self.photo)

    def test_cli_success_and_invalid_input(self):
        result = subprocess.run([sys.executable, "-m", "origemia", str(self.photo), "--json"],
                                capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(result.stdout)["tipo"], "imagem")
        result = subprocess.run([sys.executable, "-m", "origemia", "missing.png"], capture_output=True)
        self.assertEqual(result.returncode, 2)

    def test_video_real_decode_and_sample_only_conclusion(self):
        import cv2
        import numpy as np
        path = self.root / "sample.avi"
        writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), 10, (64, 48))
        self.assertTrue(writer.isOpened())
        try:
            for i in range(20):
                writer.write(np.full((48, 64, 3), i * 10, dtype=np.uint8))
        finally:
            writer.release()
        report = analyze(path, StubClassifier(), frames=4)
        self.assertEqual(len(report["amostras"]), 4)
        self.assertEqual([x["quadro"] for x in report["amostras"]], [0, 6, 13, 19])
        self.assertIn("Inconclusivo sobre o vídeo completo", report["conclusao"])
        self.assertIn("Áudio", " ".join(report["alertas"]))

    def test_corrupt_video(self):
        path = self.root / "bad.mp4"
        path.write_bytes(b"not a real video")
        with self.assertRaises(AnalysisError):
            analyze(path)

    def test_summary_has_abstention_band(self):
        self.assertIsNone(score_summary([])["media"])
        self.assertIn("inconclusivo", score_summary([0.5])["leitura"])


@unittest.skipUnless(__import__("os").environ.get("ORIGEMIA_REAL_MODEL_TEST") == "1",
                     "Modelo real exige dependências IA, download/cache e execução explícita.")
class RealModelSmokeTest(unittest.TestCase):
    def test_real_model_loads_and_returns_valid_score(self):
        # Verifica inferência, não mede precisão de detecção em uma imagem artificial.
        score = Classifier().predict(Image.new("RGB", (224, 224), "gray"))
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 1)


if __name__ == "__main__":
    unittest.main()
