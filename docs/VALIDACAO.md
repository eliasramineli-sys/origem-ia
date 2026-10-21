# Validação observada — 21/10/2026

Ambiente de execução: Linux, Python 3.12, CPU. Esta validação não foi feita em um computador Windows.

## Resultados

| Verificação executada | Resultado |
| --- | --- |
| Instalação do pacote com `python -m pip install -e .` | Concluída |
| `ORIGEMIA_REAL_MODEL_TEST=1 python -m unittest discover -s tests -v` | 14 testes passaram, nenhum ignorado |
| Inferência real com o modelo/revisão indicados no README | Carregamento dos pesos e escore numérico válido |
| Fluxo adicional com modelo real, em modo offline | Foto e três quadros de vídeo processados; JSON exportado |
| Decodificação de vídeo AVI/MJPEG gerado no teste | Quatro quadros decodificados nos índices esperados |
| Arquivos ausentes e mídia corrompida | Erros tratados |
| Metadados editáveis e falta de modelo | Não produzem falsa confirmação de origem |
| Sobrescrita do original/relatório existente | Bloqueada nos fluxos públicos |
| `python -m compileall -q origemia` | Concluído sem erros |
| `python -m pip check` | Sem dependências incompatíveis |
| `origemia --help` e importação do módulo desktop | Concluídos |

O classificador foi efetivamente executado: não foi apenas substituído por dublês. Nos testes de lógica, os dublês são identificados como `test-only`. As imagens uniformes e os vídeos gerados para teste são exclusivamente fixtures técnicas, sem uso como avaliação de acurácia ou exemplos de conteúdo fotográfico autêntico.

## Dependências observadas

- Pillow 11.3.0
- NumPy 2.2.6
- OpenCV headless 4.12.0.88 (biblioteca 4.12.0)
- Transformers 4.57.1
- PyTorch 2.14.1+cpu
- Safetensors 0.8.0

A primeira tentativa com versões mais recentes de NumPy/OpenCV encerrou o processo nativo. As dependências do núcleo foram fixadas nas versões acima, e a suíte completa passou depois da correção. O pacote entregue usa essas versões fixadas.

## Limites da verificação

- Não foi medida precisão, recall, taxa de falsos positivos/negativos ou calibração. Não há percentual de confiabilidade demonstrado para este aplicativo.
- Não há conjunto independente de fotos/vídeos rotulados nesta entrega.
- A interface Tkinter foi implementada e seu módulo importado, mas a janela não foi inspecionada visualmente: o ambiente não disponibilizou tela/servidor gráfico.
- Não houve teste manual no Windows, celular, vídeo com todos os codecs possíveis, GPU ou conteúdo de longa duração.
- Na validação inicial, o workflow ainda não havia sido executado remotamente. Consulte a aba Actions do repositório para o estado atual.
- O pacote validado não contém pesos do modelo ou mídias do usuário.
