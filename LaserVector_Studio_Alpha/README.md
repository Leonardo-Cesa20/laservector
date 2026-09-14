# LaserVector Studio Alpha 5

Nova versão com o modo **Reconstrução geométrica experimental**.

## O que esse modo faz

- Detecta linhas retas usando Hough.
- Une segmentos quase colineares.
- Redesenha as linhas como geometrias limpas.
- Remove essas linhas da imagem antes de vetorizar o restante.
- Mantém letras e formas curvas como contornos tradicionais.
- Exporta o resultado combinado em SVG e DXF.

## Como testar na logo Creative Process

- Método: Automático
- Modo: Reconstrução geométrica experimental
- Ruído: 1
- Fechar falhas: 1
- Área mínima: 10
- Simplificação: 0,25
- Recorte automático: ligado

## Resultado esperado

O hexágono e os raios internos devem ficar mais retos e leves.
As letras ainda não serão reconstruídas como fonte: elas continuam sendo
vetorizadas por contorno. O próximo passo será melhorar curvas e texto.

## Limitações

- Linhas muito próximas podem ser unidas incorretamente.
- Detecção de círculos e arcos ainda não foi adicionada.
- OCR e reconstrução tipográfica ainda não estão presentes.
- Este é um protótipo de validação geométrica.
