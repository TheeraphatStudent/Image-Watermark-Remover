<p align = "center">
	<img width = 512 src="Images/front.jpg" /><br>
</p>

- An Image Watermark Remover is a desktop application built in Python with a tkinter GUI (image processing by NumPy + Pillow).
- The user selects any image that has a light, tinted watermark and the watermark is whitened while the dark content is preserved.
- Both the original and the cleaned image are shown side by side in a live before/after preview.
- Three sliders (Light / Red / Pink-min) let the user tune the removal for their own image; a live "% whitened" readout shows the effect.
- The cleaned image can be saved anywhere on the local system using the Save button.

<p align = "center">
	<img src = "https://img.shields.io/github/stars/akash-rajak/Image-Watermark-Remover?style=social", alt = "GitHub Repo stars">
	<img src = "https://img.shields.io/github/forks/akash-rajak/Image-Watermark-Remover?style=social", alt = "GitHub Repo forks">
	<img src = "https://img.shields.io/github/watchers/akash-rajak/Image-Watermark-Remover?style=social", alt = "GitHub Repo watchers">
	<img src = "https://img.shields.io/github/contributors/akash-rajak/Image-Watermark-Remover?style=social", alt = "GitHub contributors">
</p>
<p align = "center">
	<img src = "https://img.shields.io/github/languages/count/akash-rajak/Image-Watermark-Remover?style=social", alt = "GitHub language count">
	<img src = "https://img.shields.io/github/languages/top/akash-rajak/Image-Watermark-Remover?style=social", alt = "GitHub top language">
	<img src = "https://img.shields.io/github/directory-file-count/akash-rajak/Image-Watermark-Remover?style=social", alt = "GitHub repo file count">
	<img src = "https://img.shields.io/github/repo-size/akash-rajak/Image-Watermark-Remover?style=social", alt = "GitHub repo size">
</p>
<p align = "center">
	<img src = "https://img.shields.io/github/issues/akash-rajak/Image-Watermark-Remover", alt = "GitHub issues">
	<img src = "https://img.shields.io/github/issues-closed/akash-rajak/Image-Watermark-Remover", alt = "GitHub closed issues">
	<img src = "https://img.shields.io/github/issues-pr/akash-rajak/Image-Watermark-Remover", alt = "GitHub pull requests">
	<img src = "https://img.shields.io/github/issues-pr-closed/akash-rajak/Image-Watermark-Remover", alt = "GitHub closed pull requests">
</p>
<p align = "center">
	<img src = "https://img.shields.io/github/commit-activity/t/akash-rajak/Image-Watermark-Remover", alt = "GitHub commit activity">
	<img src = "https://img.shields.io/github/commit-activity/y/akash-rajak/Image-Watermark-Remover", alt = "GitHub commit activity/year">
	<img src = "https://img.shields.io/github/commit-activity/m/akash-rajak/Image-Watermark-Remover", alt = "GitHub commit activity/month">
	<img src = "https://img.shields.io/github/commit-activity/w/akash-rajak/Image-Watermark-Remover", alt = "GitHub commit activity/week">
	<img src = "https://img.shields.io/github/last-commit/akash-rajak/Image-Watermark-Remover", alt = "GitHub last commit">
	<img src = "https://img.shields.io/github/discussions/akash-rajak/Image-Watermark-Remover", alt = "GitHub Discussions">
</p>
<p align = "center">
	<img src = "https://img.shields.io/github/license/akash-rajak/Image-Watermark-Remover", alt = "Github">
</p>

---

### 📌REQUIREMENTS :

- Python 3
- NumPy
- Pillow (`from PIL import Image, ImageTk`)
- tkinter (ships with Python; on Debian/Ubuntu: `sudo apt install python3-tk`)

Install everything with:

```bash
pip install -r requirements.txt
```

---

### 📌HOW TO Use it :

- Run it with [uv](https://docs.astral.sh/uv/) — no manual install needed, the dependencies are declared inline in the script:

  ```bash
  uv run image_watermark_remover.py
  ```

  (Or, with a plain Python install: `pip install -r requirements.txt` then `python image_watermark_remover.py`.)

- A single window opens with a toolbar (**Select Image · Save Result · Exit**), two preview panels, and threshold sliders.
- Click **Select Image…** and pick any image that has a light/tinted watermark.
- The **Original** and **Cleaned** previews update side by side; a live "% whitened" figure shows how much was removed.
- If the defaults miss, drag the **Light / Red / Pink-min** sliders — the cleaned preview refreshes as you go.
- Click **Save Result…** to write the cleaned image anywhere on your system.

#### Usage without

```bash
uv run process.py --input "Sample Input" --output "Output"

uv run process.py --input "Sample Input" --output "Output" --scale 2 --svg both --rasterize-svg

uv run process.py --input page.jpg --output Output --scale 4
```

Key options: `--scale {1,2,4}`, `--svg {none,vector,raster,both}`, `--rasterize-svg`,
`--dpi N`, `--trace-scale N`, `--trace-color`, and the raster thresholds
`--light` / `--red` / `--pink-min`. Run `uv run process.py -h` for the full list.

> **Note on fonts:** when rendering an SVG to PNG, text uses the fonts installed on your
> machine. The OCM reports use **TH SarabunPSK** for Thai — that font must be present for Thai
> to render correctly in the PNG (the cleaned `.svg` itself always keeps the real text).

`remove_watermark.py` (raster-only whitening) is still available for simple cases.

---

### GUI tool (`image_watermark_remover.py`)

### 📌Purpose :

- Provides a point-and-click front end over the same cleaning engine as `remove_watermark.py`, so users can remove a watermark without the command line.

### 📌Compilation Steps :

- Run `uv run image_watermark_remover.py` (uv installs NumPy + Pillow automatically; tkinter ships with Python).
- Or install manually with `pip install -r requirements.txt` and run `python image_watermark_remover.py`.
- Select an image, tune the sliders if needed, and save the cleaned result.

---

### 📌SCREENSHOTS :

<p align="center">
  <img width = 512 src="Images/1.png" /><br>
  <img width = 512 src="Images/2.png" /><br>
  <img width = 512 src="Images/3.png" /><br>
  <img width = 512 src="Images/4.png" /><br>
  <img width = 512 src="Images/5.jpg" /><br>
  <img width = 512 src="Images/6.jpg" /><br>
</p>

---

### 🌟Stargazers Over Time:

[![Stargazers repo roster for @akash-rajak/Image-Watermark-Remover](https://reporoster.com/stars/akash-rajak/Image-Watermark-Remover)](https://github.com/akash-rajak/Image-Watermark-Remover/stargazers)
[![Stargazers over time](https://starchart.cc/akash-rajak/Image-Watermark-Remover.svg)](https://starchart.cc/akash-rajak/Image-Watermark-Remover)

---

### 🌟Forkers Over Time:

[![Forkers repo roster for @akash-rajak/Image-Watermark-Remover](https://reporoster.com/forks/akash-rajak/Image-Watermark-Remover)](https://github.com/akash-rajak/Image-Watermark-Remover/network/members)

---

### 📌Contributors:

<a href="https://github.com/akash-rajak/Image-Watermark-Remover/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=akash-rajak/Image-Watermark-Remover" />
</a>
