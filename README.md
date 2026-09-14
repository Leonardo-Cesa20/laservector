# LaserVector Studio Alpha 5

Protótipo desktop para transformar imagens em vetores e experimentar reconstrução geométrica de linhas e formas.

> O código está em [`LaserVector_Studio_Alpha/`](./LaserVector_Studio_Alpha/).

## Principais recursos

- detecção de linhas retas com Hough;
- união de segmentos quase colineares;
- reconstrução de linhas como geometrias limpas;
- preservação de letras e curvas por contorno;
- remoção das linhas reconstruídas antes da vetorização restante;
- exportação combinada em SVG e DXF;
- controles de ruído, simplificação e fechamento de falhas.

## Tecnologias

- Python
- PySide6
- OpenCV
- NumPy

## Executando no Windows

```powershell
cd LaserVector_Studio_Alpha
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Também é possível utilizar `instalar_e_iniciar.bat` para preparar e abrir o projeto.

## Status

Protótipo Alpha voltado à validação da reconstrução geométrica. Detecção de círculos, OCR e reconstrução tipográfica ainda estão em desenvolvimento.

Desenvolvido por **Leonardo Cesa**.
