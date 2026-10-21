import argparse
import json
import sys

from .analysis import AnalysisError, analyze
from .classifier import Classifier
from .report import render_text, save_report


def main(argv=None):
    parser = argparse.ArgumentParser(description="OrigemIA — triagem experimental de mídia local")
    parser.add_argument("arquivo", help="Caminho de uma foto ou vídeo local")
    parser.add_argument("--ia", action="store_true", help="Ativar classificador (instale .[ia])")
    parser.add_argument("--offline", action="store_true", help="Não baixar modelo; exige cache prévio")
    parser.add_argument("--quadros", type=int, default=12, help="Quadros distribuídos no vídeo (1–32)")
    parser.add_argument("--saida", help="Novo relatório .json ou .txt (não sobrescreve arquivos)")
    parser.add_argument("--json", action="store_true", help="Imprimir JSON no terminal")
    args = parser.parse_args(argv)
    try:
        report = analyze(args.arquivo, Classifier(offline=args.offline) if args.ia else None,
                         frames=args.quadros)
        if args.saida:
            save_report(report, args.saida, args.arquivo)
        print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)
              if args.json else render_text(report))
        return 3 if args.ia and report["classificador"]["status"] != "executado" else 0
    except (AnalysisError, OSError, ValueError) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
