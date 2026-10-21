"""Relatório legível e JSON, com proteção contra sobrescrever a mídia."""

import json
from pathlib import Path


def render_text(report: dict) -> str:
    score = report["resumo_escores"]
    lines = ["ORIGEM IA • RELATÓRIO EXPERIMENTAL", "", report["arquivo"]["nome"],
             report["conclusao"], "", f"Classificador: {report['classificador']['status']}"]
    if score["media"] is not None:
        lines += [f"Escore médio da classe IA: {score['media']:.3f} (escala 0–1)",
                  f"Amostras com escore: {score['quantidade']}", score["leitura"]]
    if "erro" in report["classificador"]:
        lines += ["", report["classificador"]["erro"]]
    lines += ["", report["aviso"], "", "PROVENIÊNCIA", report["proveniencia"]["detalhe"],
              "", "DADOS DA MÍDIA", json.dumps(report["midia"], ensure_ascii=False, indent=2),
              "", "AMOSTRAS"]
    for sample in report["amostras"]:
        value = sample["escore_ia"]
        formatted = "não calculado" if value is None else f"{value:.3f}"
        position = "imagem" if sample["quadro"] is None else f"quadro {sample['quadro']} • {sample['segundos']:.2f}s"
        lines.append(f"{position}: {formatted}")
    lines += ["", "ALERTAS", *report["alertas"], "", f"SHA-256: {report['arquivo']['sha256']}",
              f"Data UTC: {report['analisado_em_utc']}"]
    return "\n".join(lines)


def save_report(report: dict, destination, source=None, *, overwrite=False):
    path = Path(destination).expanduser().resolve()
    if source is not None and path == Path(source).expanduser().resolve():
        raise ValueError("O relatório não pode substituir o arquivo analisado.")
    if path.suffix.lower() not in {".json", ".txt"}:
        raise ValueError("Salve o relatório como .json ou .txt.")
    content = (json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)
               if path.suffix.lower() == ".json" else render_text(report))
    # Criação exclusiva por padrão também protege contra colisões/hardlinks.
    with path.open("w" if overwrite else "x", encoding="utf-8") as stream:
        stream.write(content + "\n")
    return path
