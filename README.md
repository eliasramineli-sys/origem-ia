# OrigemIA

Aplicativo local em Python para investigar indícios de geração por IA em fotos e em quadros de vídeos. Inclui interface desktop em português, terminal e exportação de relatórios. Versão **0.1.0 experimental**.

**É possível detectar indícios, mas não garantir a origem de qualquer arquivo.** O aplicativo não certifica autenticidade. Um resultado favorável à classe humana não prova captura por câmera; um resultado favorável à classe IA pode estar errado. As duas classes do modelo também não representam toda a variedade de imagens reais, ilustrações e conteúdo parcialmente editado.

## Funcionalidades implementadas

- Importação de arquivos locais: JPG/JPEG, PNG, WEBP, BMP, TIFF; MP4, MOV, AVI, MKV e WEBM conforme codecs disponíveis.
- Classificador público opcional executado em CPU, com revisão fixa e sem código remoto.
- Vídeos: até 32 quadros distribuídos ao longo do arquivo, com escores individuais e resumo descritivo. Não é um detector temporal de vídeo ou de áudio.
- Inspeção técnica de imagens e identificação de referências textuais a alguns geradores nos metadados. São declarações editáveis, nunca provas.
- SHA-256, identificação do modelo/revisão, estados de falha explícitos e relatório JSON/TXT.
- Tema escuro desktop, processamento em segundo plano e escolha da quantidade de quadros.
- Limites de 500 MiB por arquivo e 40 megapixels por quadro/imagem. Imagens animadas e TIFF multipágina são rejeitados explicitamente.
- Sem histórico automático e sem envio das mídias para uma API. O primeiro uso de IA consulta o Hugging Face para baixar arquivos do modelo. Depois do download, use a opção offline para impedir novas consultas do carregador.

## Instalação no Windows (PowerShell)

Instale **Python 3.11 ou 3.12 de 64 bits**, com pip e Tcl/Tk. Extraia o ZIP e abra o terminal na pasta que contém este README.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install ".[ia]"
.\.venv\Scripts\origemia-desktop.exe
```

A instalação IA usa PyTorch e baixa dependências grandes. O modelo é baixado na primeira análise com o classificador ativado; a duração depende da conexão e do computador. Não há necessidade de chave de API. Não foi produzido um executável Windows independente: o comando acima abre o aplicativo Python instalado.

Para instalar apenas a inspeção técnica, sem o classificador:

```powershell
.\.venv\Scripts\python.exe -m pip install .
.\.venv\Scripts\origemia-desktop.exe
```

Nesse caso, desmarque **Usar classificador de IA**. O relatório mostrará origem inconclusiva. Se o classificador continuar marcado, a falha será exibida e nenhum escore será inventado.

## Usar pela interface

1. Clique em **Selecionar arquivo** e escolha uma foto ou vídeo.
2. Mantenha o classificador marcado para a análise visual; ajuste os quadros se for um vídeo.
3. Clique em **Analisar conteúdo**. A primeira execução pode demorar para baixar e carregar o modelo.
4. Leia a conclusão, o estado do classificador e os alertas.
5. Use **Salvar relatório** para criar um arquivo JSON ou TXT. Escolha um nome novo: arquivos existentes não são substituídos.

O app processa o conteúdo localmente e não altera o original. Relatórios contêm nome do arquivo, hash e alguns metadados: revise essas informações antes de compartilhá-los. Prompts, GPS e metadados completos não são exportados.

## Terminal

Exemplos depois de instalar o pacote e ativar o ambiente, ou substituindo `origemia` pelo caminho `.\.venv\Scripts\origemia.exe`:

```powershell
origemia "C:\Midias\foto.jpg" --ia --saida foto_relatorio.json
origemia "C:\Midias\video.mp4" --ia --quadros 16 --saida video_relatorio.txt
origemia "C:\Midias\foto.jpg" --ia --offline --json
origemia "C:\Midias\foto.jpg" --json
```

Saídas de processo: `0` = operação concluída (não significa autenticidade); `2` = entrada/saída inválida; `3` = classificador solicitado, mas indisponível. Um relatório com os dados disponíveis ainda pode ser salvo no caso `3`.

No Linux/macOS, o fluxo equivalente é:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install '.[ia]'
.venv/bin/origemia-desktop
```

O desktop precisa de ambiente gráfico e Tkinter. Em distribuições Linux pode ser necessário instalar o pacote Tcl/Tk do sistema. O terminal não depende de uma tela.

## Como interpretar

| Campo | Significado |
| --- | --- |
| Escore IA 0–1 | Saída softmax da classe `ai` do classificador; não é probabilidade calibrada de o arquivo ter sido gerado por IA. |
| Escore ≥ 0,80 | Modelo favorece classe IA. Limiar experimental, sem calibração própria. |
| Escore ≤ 0,20 | Modelo favorece classe humana. Não certifica origem nem ausência de edição. |
| Escore entre 0,20 e 0,80 | Faixa de abstenção: inconclusivo. |
| Média em vídeo | Resumo descritivo de quadros correlacionados; não é probabilidade de o vídeo inteiro ser IA. |
| Referências nos metadados | Textos editáveis que mencionam ferramentas; podem ser removidos, copiados ou falsificados. |
| Proveniência não verificada | Esta versão não implementa validação criptográfica C2PA ou detecção de marcas-d'água proprietárias. |

Mesmo com escores altos, a conclusão do vídeo completo permanece inconclusiva. Os índices e tempos dos quadros dependem do que o decodificador informa e são aproximados, especialmente em vídeo com taxa variável. A amostragem pode perder manipulações curtas. A ausência de metadados não aumenta a suspeita de IA.

## Modelo e limitações

O adaptador usa [Ateeqq/ai-vs-human-image-detector](https://huggingface.co/Ateeqq/ai-vs-human-image-detector), revisão `2706389b1a9272b233aa38a3f179b807ebdb5d94`, com classes `ai` e `hum`. A configuração é conferida ao carregar. Os pesos são baixados diretamente pelo usuário e não estão incluídos no ZIP.

O [cartão da revisão utilizada](https://huggingface.co/Ateeqq/ai-vs-human-image-detector/blob/2706389b1a9272b233aa38a3f179b807ebdb5d94/README.md) declara restrições de desempenho em retratos, imagens de baixa qualidade e capturas de tela. Métricas do autor não medem a precisão deste aplicativo em suas fotos. A transferência desse classificador de imagens para quadros de vídeo é experimental e não foi validada como detector de vídeo.

**Não há taxa de acerto própria estabelecida.** Compressão, edição, conteúdo híbrido, recortes e novos geradores podem causar falsos positivos e falsos negativos. Resultados intermediários são úteis para triagem, não para acusações ou decisões automáticas sobre pessoas.

Licenças: o código deste projeto está sem licença escolhida; decida isso antes de distribuir permissões de reutilização. A revisão fixada do modelo declara `cc-by-nc-nd-3.0` em seu próprio cartão, embora a página atual possa mostrar outra licença. Confira os termos da revisão antes de uso comercial ou redistribuição. As dependências têm suas próprias licenças. Este projeto não redistribui pesos.

## Verificação

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m compileall -q origemia
```

Os testes comuns usam imagens e um vídeo gerados durante o teste, além de dublês explicitamente identificados para conferir a lógica. Esses testes **não medem acurácia de detecção**. O teste separado de inferência real exige a instalação IA e download/cache:

```powershell
$env:ORIGEMIA_REAL_MODEL_TEST = "1"
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
Remove-Item Env:ORIGEMIA_REAL_MODEL_TEST
```

Consulte [docs/VALIDACAO.md](docs/VALIDACAO.md) para o resultado observado nesta entrega e os limites de verificação. O workflow GitHub Actions testa o núcleo em Linux e Windows; seu resultado remoto só existirá após publicar e executar no GitHub.

## Estrutura

```text
origemia/
  analysis.py     # arquivos, metadados, amostragem e conclusões
  classifier.py   # adaptador de inferência real opcional
  desktop.py      # interface local Tkinter
  cli.py          # terminal
  report.py       # exportação JSON/TXT
tests/            # regressões e teste opcional com modelo real
docs/             # escopo e validação
.github/workflows/ci.yml
pyproject.toml
```

## Código-fonte no GitHub

Repositório: [eliasramineli-sys/origem-ia](https://github.com/eliasramineli-sys/origem-ia).

Para obter o código com Git:

```powershell
git clone https://github.com/eliasramineli-sys/origem-ia.git
cd origem-ia
```

Depois, siga a instalação descrita acima. O acesso a um repositório privado exige uma conta autorizada no GitHub.

Não adicione fotos privadas, vídeos, relatórios ou cache de modelos ao repositório.

## Referências técnicas

- [NIST AI 100-4 — Reducing Risks Posed by Synthetic Content](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.100-4.pdf)
- [C2PA — perguntas frequentes e limites de proveniência](https://c2pa.org/faqs/)
- [Transformers 4.57.1 — documentação](https://huggingface.co/docs/transformers/v4.57.1/en/index)
- [OpenCV — VideoCapture](https://docs.opencv.org/4.x/d8/dfe/classcv_1_1VideoCapture.html)
