"""Fig. 4 (physical setup), built directly from the two images already in Lidar_Paper v8 Redline.docx
(word/media/image4.png, the annotated close-up; word/media/image5.jpeg, the overview with the target board),
so the arXiv figure matches the Word redline exactly instead of a separately re-annotated version.

image4.png carries its own labels (Sensor A, Sensor B, TCA9548A Mux, Pin), already baked in by Jessica; it is
used unmodified. image5.jpeg is the raw overview photo, stored portrait and shown landscape in Word via a 90
degree rotation; this script applies the same rotation and otherwise leaves it unmodified. The two are placed
side by side, as in the Word figure, with no new panel labels added, since this is a reproduction, not a
new re-crop.

Run:   python manuscript_ieee/scripts/make_fig_photo.py
Out:   manuscript_ieee/figures/fig_photo.pdf/png, manuscript_ieee/arxiv/figures/fig_photo.pdf/png

Author: Jessica
"""
from __future__ import annotations

import zipfile
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
DOCX = ROOT / "arxiv" / "Lidar_Paper v8 Redline.docx"
FIG = ROOT / "figures"
AFIG = ROOT / "arxiv" / "figures"

TARGET_HEIGHT = 1400  # px, common row height before placing side by side


def load_from_docx(name: str) -> Image.Image:
    with zipfile.ZipFile(DOCX) as z:
        data = z.read(f"word/media/{name}")
    import io
    return Image.open(io.BytesIO(data)).convert("RGB")


def main():
    a = load_from_docx("image4.png")                       # close-up, already landscape, already labelled
    b = load_from_docx("image5.jpeg").rotate(-90, expand=True)  # overview, rotate to landscape as Word displays it

    def resize_to_height(im, h):
        w = round(im.width * h / im.height)
        return im.resize((w, h), Image.LANCZOS)

    a2 = resize_to_height(a, TARGET_HEIGHT)
    b2 = resize_to_height(b, TARGET_HEIGHT)

    gap = 20
    canvas = Image.new("RGB", (a2.width + gap + b2.width, TARGET_HEIGHT), "white")
    canvas.paste(a2, (0, 0))
    canvas.paste(b2, (a2.width + gap, 0))

    FIG.mkdir(exist_ok=True)
    AFIG.mkdir(exist_ok=True, parents=True)
    canvas.save(FIG / "fig_photo.png", dpi=(600, 600))

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    dpi = 600.0
    fig = plt.figure(figsize=(canvas.width / dpi, canvas.height / dpi), dpi=dpi)
    fig.figimage(np.asarray(canvas), xo=0, yo=0, resize=False)
    fig.savefig(FIG / "fig_photo.pdf", dpi=dpi,
                metadata={"Creator": "", "Producer": "", "Author": "Jessica", "Title": ""})
    plt.close(fig)

    import shutil
    shutil.copy(FIG / "fig_photo.pdf", AFIG / "fig_photo.pdf")
    shutil.copy(FIG / "fig_photo.png", AFIG / "fig_photo.png")
    print(f"wrote fig_photo.pdf/png to both figures/ and arxiv/figures/, canvas {canvas.size}")


if __name__ == "__main__":
    main()
