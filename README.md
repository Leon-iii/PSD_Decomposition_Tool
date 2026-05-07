# PSD Decomposition Tool

Tkinter/ttk GUI for exporting selected PSD layers as separate PNG or PSD files.

## Setup

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Optional features:

- Drag and drop support uses `tkinterdnd2`.
- PSD layer-preserving export on Windows uses Photoshop via COM automation and requires `pywin32` plus an installed Photoshop.

The output settings include a layer bounds mode:

- Preserve canvas and position: exports each layer on a transparent image with the original PSD canvas size.
- Crop to layer object: exports only the rendered layer object bounds.

## Run

```powershell
python main.py
```
