"""Adaptador para um modelo público; nenhum resultado é simulado."""

import math
from PIL import Image

MODEL_ID = "Ateeqq/ai-vs-human-image-detector"
REVISION = "2706389b1a9272b233aa38a3f179b807ebdb5d94"


class ModelUnavailable(RuntimeError):
    pass


def validate_score(value: float) -> float:
    value = float(value)
    if not math.isfinite(value) or not 0 <= value <= 1:
        raise ValueError("O modelo retornou um escore inválido.")
    return value


class Classifier:
    """CPU, Safetensors, código remoto desativado e revisão fixa."""

    model_id = MODEL_ID
    revision = REVISION

    def __init__(self, offline: bool = False):
        self.offline = offline
        self.model = None
        self.processor = None

    def load(self):
        if self.model is not None:
            return
        try:
            import torch
            from transformers import AutoImageProcessor, AutoModelForImageClassification

            options = dict(revision=REVISION, trust_remote_code=False,
                           local_files_only=self.offline)
            processor = AutoImageProcessor.from_pretrained(MODEL_ID, use_fast=False, **options)
            model = AutoModelForImageClassification.from_pretrained(
                MODEL_ID, use_safetensors=True, **options
            ).to("cpu").eval()
            labels = {int(k): str(v).lower() for k, v in model.config.id2label.items()}
            if labels != {0: "ai", 1: "hum"}:
                raise ValueError("Mapeamento de classes inesperado; análise interrompida.")
            self.torch = torch
            self.processor = processor
            self.model = model
        except Exception as exc:
            raise ModelUnavailable(
                "Não foi possível carregar o classificador. Instale .[ia]; na primeira "
                "execução, permita o download do modelo Hugging Face. Para modo offline, "
                "o modelo precisa estar no cache. Nenhum escore foi inventado. "
                f"Detalhe técnico: {type(exc).__name__}: {exc}"
            ) from exc

    def predict(self, image: Image.Image) -> float:
        self.load()
        inputs = self.processor(images=image, return_tensors="pt")
        with self.torch.inference_mode():
            logits = self.model(**inputs).logits
            value = logits.softmax(dim=-1)[0, 0].item()
        return validate_score(value)
