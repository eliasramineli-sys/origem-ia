# Decisões e escopo

O OrigemIA 0.1.0 é um aplicativo **desktop local**, com terminal alternativo. A escolha permite explorar análise de mídia em Python e manter fotos e vídeos no computador do usuário. Não é site, serviço público, aplicativo mobile nem detector forense certificado.

## Fluxo

1. Validar formato, existência e tamanho do arquivo.
2. Calcular hash e decodificar com limites.
3. Para foto, ler dados técnicos e referências textuais em metadados disponíveis.
4. Para vídeo, obter quadros distribuídos no arquivo; registrar falhas de leitura.
5. Se solicitado, executar um único classificador de imagens nos pixels preparados.
6. Mostrar escores com limites explícitos. Se houver erro do modelo, preservar resultado inconclusivo.
7. Salvar relatório apenas mediante ação do usuário, sem substituir o original.

O modelo é mantido em memória na interface entre análises. A interface usa uma thread de trabalho e uma fila para atualizar Tkinter somente na thread principal. Não há banco de dados, usuários ou servidor.

## Critérios de conclusão desta versão

- Foto válida gera relatório técnico; com módulo IA disponível pode obter escore do modelo real.
- Vídeo válido tem quadros decodificados e relatados individualmente.
- Ausência de modelo não gera uma falsa pontuação.
- Arquivos ausentes, corrompidos e formatos não suportados geram mensagens claras.
- Nenhuma ausência de metadados é interpretada como prova de IA.
- Falhas de inferência e amostragem são visíveis.
- Relatórios são JSON/TXT e o original é protegido contra sobrescrita.
- Código, instruções de instalação e testes são entregues juntos.

## Evoluções que exigem trabalho adicional

Estas funções não estão implementadas nesta versão:

- Verificador C2PA com política explícita de confiança dos certificados.
- Detector temporal treinado e avaliado para vídeos, análise de áudio e lip sync.
- Avaliação independente com conjunto rotulado, separado por gerador e por fonte, com compressões e recortes representativos. Medir precisão, recall, falsos positivos, falsos negativos e calibração.
- Estratégia de distribuição Windows assinada, instalador e teste em computador Windows real.
- Serviço web/mobile e infraestrutura de processamento, se forem necessários depois.

O ganho de confiabilidade depende especialmente de avaliação e calibração em dados representativos, e não apenas de adicionar mais sinais ou apresentar um percentual na interface.
