"""Análise de arquivos locais e amostragem limitada de vídeo."""

from datetime import datetime, timezone
import hashlib
import math
from pathlib import Path
import statistics
import warnings

from PIL import Image, ImageOps, UnidentifiedImageError

from . import __version__
from .classifier import validate_score

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
VIDEO_SUFFIXES = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
MAX_BYTES = 500 * 1024 * 1024
MAX_PIXELS = 40_000_000
NOTICE = (
    "Triagem experimental. Escores do modelo não são probabilidades calibradas de "
    "origem nem prova. Ausência de metadados não demonstra geração por IA; "
    "metadados podem ser alterados. Conteúdo real também pode ter sido editado por IA."
)
MARKERS = ("stable diffusion", "midjourney", "dall-e", "dall·e", "comfyui",
           "automatic1111", "trainedalgorithmicmedia", "flux.1")


class AnalysisError(ValueError):
    pass


def validate_file(value) -> Path:
    path = Path(value).expanduser()
    if not path.is_file():
        raise AnalysisError("Selecione um arquivo local existente.")
    size = path.stat().st_size
    if size == 0 or size > MAX_BYTES:
        raise AnalysisError("O arquivo deve ter entre 1 byte e 500 MiB.")
    if path.suffix.lower() not in IMAGE_SUFFIXES | VIDEO_SUFFIXES:
        raise AnalysisError("Formato não aceito. Use JPG, PNG, WEBP, BMP, TIFF ou vídeo MP4/MOV/AVI/MKV/WEBM.")
    return path.resolve()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inspect_image(path):
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(path) as image:
                if image.width * image.height > MAX_PIXELS:
                    raise AnalysisError("Imagem excede o limite de 40 megapixels.")
                if getattr(image, "n_frames", 1) > 1:
                    raise AnalysisError("Imagens animadas/multipágina não são suportadas. Exporte um quadro ou use vídeo.")
                image.load()
                exif = image.getexif()
                # GPS, prompts e outros metadados pessoais não são exportados.
                text = " ".join(str(v)[:100_000] for v in image.info.values()
                                if isinstance(v, (str, bytes)))
                text += " " + str(exif.get(305, ""))
                markers = [marker for marker in MARKERS if marker in text.lower()]
                metadata = {
                    "formato": image.format, "largura": image.width, "altura": image.height,
                    "modo": image.mode,
                    "software_declarado": str(exif.get(305, ""))[:250] or None,
                    "referencias_a_geradores": markers,
                    "interpretacao": "Declarações editáveis, sem assinatura validada. Não comprovam origem.",
                }
                prepared = ImageOps.exif_transpose(image).convert("RGB")
                prepared.thumbnail((2048, 2048))
                return prepared.copy(), metadata
    except AnalysisError:
        raise
    except (OSError, ValueError, UnidentifiedImageError, Image.DecompressionBombError,
            Image.DecompressionBombWarning) as exc:
        raise AnalysisError("Não foi possível decodificar a imagem com segurança.") from exc


def sample_indices(total: int, count: int) -> list[int]:
    if total < 1 or not 1 <= count <= 32:
        raise AnalysisError("Use de 1 a 32 amostras e um vídeo com quadros disponíveis.")
    count = min(total, count)
    if count == 1:
        return [total // 2]
    return sorted({round(i * (total - 1) / (count - 1)) for i in range(count)})


def score_summary(scores: list[float]) -> dict:
    values = [validate_score(x) for x in scores]
    if not values:
        return {"quantidade": 0, "media": None, "minimo": None, "maximo": None,
                "leitura": "Sem escores; resultado inconclusivo."}
    mean = statistics.mean(values)
    # Limiares operacionais arbitrários, ainda não calibrados em dados próprios.
    if mean >= 0.8:
        reading = "O modelo favorece a classe IA nas amostras. Requer verificação independente."
    elif mean <= 0.2:
        reading = "O modelo favorece a classe humana nas amostras. Isso não autentica o conteúdo."
    else:
        reading = "Escores intermediários; resultado inconclusivo."
    return {"quantidade": len(values), "media": mean, "minimo": min(values),
            "maximo": max(values), "leitura": reading}


def analyze(value, classifier=None, frames: int = 12, progress=None) -> dict:
    path = validate_file(value)
    if not 1 <= frames <= 32:
        raise AnalysisError("Escolha de 1 a 32 quadros.")
    notify = progress or (lambda message: None)
    notify("Calculando identificação SHA-256…")
    report = {
        "aplicativo": "OrigemIA", "versao": __version__,
        "analisado_em_utc": datetime.now(timezone.utc).isoformat(),
        "arquivo": {"nome": path.name, "bytes": path.stat().st_size, "sha256": sha256(path)},
        "tipo": "imagem" if path.suffix.lower() in IMAGE_SUFFIXES else "video",
        "aviso": NOTICE,
        "proveniencia": {"status": "nao_verificada",
                         "detalhe": "Esta versão não valida assinaturas C2PA nem marcas-d'água proprietárias."},
        "classificador": {
            "status": "desativado" if classifier is None else "pendente",
            "modelo": getattr(classifier, "model_id", None),
            "revisao": getattr(classifier, "revision", None),
            "escore": "Saída softmax da classe ai; não é probabilidade calibrada de origem.",
            "limiares_experimentais": {"favorece_humana_ate": 0.2, "favorece_ia_desde": 0.8},
        },
        "amostras": [], "alertas": [],
    }
    model_failed = False

    def consume(image, index=None, seconds=None):
        nonlocal model_failed
        sample = {"quadro": index, "segundos": seconds, "escore_ia": None}
        if classifier is not None and not model_failed:
            try:
                sample["escore_ia"] = validate_score(classifier.predict(image))
            except Exception as exc:
                model_failed = True
                report["classificador"]["status"] = "indisponivel"
                report["classificador"]["erro"] = str(exc)[:2000]
                report["alertas"].append("Classificador falhou; análise visual incompleta, sem conclusão de origem.")
        report["amostras"].append(sample)

    if report["tipo"] == "imagem":
        notify("Lendo imagem e metadados…")
        image, report["midia"] = inspect_image(path)
        notify("Analisando imagem… O primeiro uso de IA pode baixar o modelo.")
        consume(image)
    else:
        report["alertas"].append(
            "Somente quadros distribuídos no vídeo foram examinados. Áudio, movimento e "
            "sincronização labial não foram analisados. Trechos curtos podem não ser amostrados."
        )
        _analyze_video(path, frames, report, consume, notify)
    if classifier is not None and not model_failed:
        report["classificador"]["status"] = "executado"
    scores = [x["escore_ia"] for x in report["amostras"] if x["escore_ia"] is not None]
    report["resumo_escores"] = score_summary(scores)
    if classifier is None or model_failed or not scores:
        report["conclusao"] = "Inconclusivo: classificação visual não concluída."
    elif report["tipo"] == "video":
        report["conclusao"] = "Inconclusivo sobre o vídeo completo. Consulte os escores dos quadros amostrados."
    else:
        report["conclusao"] = report["resumo_escores"]["leitura"]
    report["alertas"].append("Compressão, edição, capturas de tela e geradores não vistos podem causar erros.")
    return report


def _analyze_video(path, frames, report, consume, notify):
    try:
        import cv2
    except ImportError as exc:
        raise AnalysisError("Instale opencv-python-headless para analisar vídeos.") from exc
    cap = cv2.VideoCapture(str(path), cv2.CAP_FFMPEG)
    try:
        if not cap.isOpened():
            raise AnalysisError("Vídeo não pôde ser aberto. Arquivo danificado ou codec não disponível.")
        raw_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        fps = cap.get(cv2.CAP_PROP_FPS)
        if not math.isfinite(raw_count) or raw_count < 1 or not math.isfinite(fps) or fps <= 0:
            raise AnalysisError("Duração ou taxa de quadros inválida; não é possível distribuir as amostras.")
        total = int(raw_count)
        width, height = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        if width <= 0 or height <= 0 or width * height > MAX_PIXELS:
            raise AnalysisError("Dimensões de vídeo inválidas ou maiores que 40 megapixels.")
        requested = sample_indices(total, frames)
        report["midia"] = {"largura": width, "altura": height, "fps_declarado": fps,
                           "quadros_declarados": total, "duracao_estimada_s": total / fps,
                           "quadros_solicitados": requested}
        failures = []
        for pos, index in enumerate(requested, 1):
            notify(f"Lendo quadro {pos}/{len(requested)}…")
            if not cap.set(cv2.CAP_PROP_POS_FRAMES, index):
                failures.append(index)
                continue
            ok, frame = cap.read()
            if not ok:
                failures.append(index)
                continue
            image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            image.thumbnail((2048, 2048))
            consume(image, index, index / fps)
        report["midia"]["quadros_nao_lidos"] = failures
        if failures:
            report["alertas"].append(f"Não foi possível ler {len(failures)} quadros solicitados; amostragem parcial.")
        if not report["amostras"]:
            raise AnalysisError("Nenhum quadro do vídeo foi decodificado.")
    except cv2.error as exc:
        raise AnalysisError("Falha na decodificação do vídeo.") from exc
    finally:
        cap.release()
