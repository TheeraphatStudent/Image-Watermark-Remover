# /// script
# requires-python = ">=3.9"
# dependencies = ["numpy", "pillow"]
# ///
"""Image Watermark Remover — a single-window desktop GUI.

Select a scanned document, watch the watermark disappear in a live before/after
preview, tune the three thresholds if the defaults miss, and save the result.

The actual cleaning is done by ``clean_image`` from ``remove_watermark.py`` so the
GUI and the command-line tool always share one source of truth: light and/or
salmon-tinted watermark pixels are whitened while the dark ink is preserved.

Run it with:

    python image_watermark_remover.py
"""

from __future__ import annotations

import os
import sys
import tkinter as tk
from tkinter import filedialog, ttk
from tkinter import messagebox as mbox

try:
    from PIL import Image, ImageTk
except ImportError:  # pragma: no cover - environment guard
    sys.exit("Pillow is required. Install dependencies with: pip install -r requirements.txt")

try:
    # Same folder as this script, so importing works from any working directory
    # (Python puts the script's own directory on sys.path).
    from remove_watermark import clean_image
except ImportError as exc:  # pragma: no cover - environment guard
    sys.exit(
        f"Could not import the cleaning engine ({exc}).\n"
        "Make sure remove_watermark.py sits next to this file and that numpy is\n"
        "installed:  pip install -r requirements.txt"
    )

# Default thresholds, tuned for the salmon-tinted document watermark. The slider
# ranges are deliberately wider so any image can be dialed in.
DEFAULT_LIGHT = 188
DEFAULT_RED = 10
DEFAULT_PINK_MIN = 158

# Largest size (w, h) a preview panel will render; images are downscaled to fit.
PREVIEW_MAX = (460, 560)

# Debounce window (ms) between a slider moving and the recompute firing, so
# dragging stays smooth instead of recomputing on every pixel of travel.
DEBOUNCE_MS = 150

IMAGE_FILETYPES = [
    ("Images", "*.jpg *.jpeg *.png *.bmp *.tif *.tiff *.webp"),
    ("All files", "*.*"),
]


class WatermarkRemoverApp:
    """The whole application: state, widgets, and the load → tune → save flow."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        root.title("Image Watermark Remover")
        root.minsize(1000, 720)

        # --- state ---------------------------------------------------------
        self.original: Image.Image | None = None   # full-res source (RGB)
        self.cleaned: Image.Image | None = None     # full-res cleaned result
        # PhotoImages MUST be held on the instance: tkinter keeps only a weak
        # reference from the label, so a local would be garbage-collected and the
        # panel would go blank on the next event loop tick.
        self._orig_photo: ImageTk.PhotoImage | None = None
        self._clean_photo: ImageTk.PhotoImage | None = None
        self._debounce_id: str | None = None

        self.light_var = tk.IntVar(value=DEFAULT_LIGHT)
        self.red_var = tk.IntVar(value=DEFAULT_RED)
        self.pink_var = tk.IntVar(value=DEFAULT_PINK_MIN)
        self.pct_var = tk.StringVar(value="")
        self.status_var = tk.StringVar(value="Select an image to begin.")

        self._build_ui()
        root.protocol("WM_DELETE_WINDOW", self._on_exit)

    # ------------------------------------------------------------------ UI --
    def _build_ui(self) -> None:
        root = self.root
        root.columnconfigure(0, weight=1)
        root.rowconfigure(2, weight=1)  # previews get the vertical stretch

        title = ttk.Label(root, text="Image Watermark Remover", font=("Segoe UI", 26, "bold"))
        title.grid(row=0, column=0, pady=(16, 4))

        # --- toolbar -------------------------------------------------------
        toolbar = ttk.Frame(root, padding=(16, 8))
        toolbar.grid(row=1, column=0, sticky="ew")
        ttk.Button(toolbar, text="Select Image…", command=self.select_image).pack(side="left")
        ttk.Button(toolbar, text="Save Result…", command=self.save_result).pack(side="left", padx=8)
        ttk.Button(toolbar, text="Exit", command=self._on_exit).pack(side="right")

        # --- previews ------------------------------------------------------
        previews = ttk.Frame(root, padding=16)
        previews.grid(row=2, column=0, sticky="nsew")
        previews.columnconfigure(0, weight=1)
        previews.columnconfigure(1, weight=1)
        previews.rowconfigure(1, weight=1)

        self.orig_panel = self._make_panel(previews, "Original", column=0)
        self.clean_panel = self._make_panel(previews, "Cleaned", column=1)

        # --- controls ------------------------------------------------------
        controls = ttk.LabelFrame(root, text="Thresholds", padding=(16, 8))
        controls.grid(row=3, column=0, sticky="ew", padx=16, pady=(0, 8))
        for col in range(3):
            controls.columnconfigure(col, weight=1)

        self._make_slider(controls, "Light", self.light_var, 0, 255, column=0,
                          hint="whiten pixels this light or lighter")
        self._make_slider(controls, "Red", self.red_var, -50, 50, column=1,
                          hint="how salmon-tinted counts as watermark")
        self._make_slider(controls, "Pink-min", self.pink_var, 0, 255, column=2,
                          hint="tinted pixels must be at least this light")

        pct = ttk.Label(controls, textvariable=self.pct_var, font=("Segoe UI", 10, "italic"))
        pct.grid(row=2, column=0, columnspan=3, pady=(6, 0))

        # --- status bar ----------------------------------------------------
        status = ttk.Label(root, textvariable=self.status_var, relief="sunken",
                           anchor="w", padding=(8, 4))
        status.grid(row=4, column=0, sticky="ew")

    def _make_panel(self, parent: ttk.Frame, heading: str, column: int) -> ttk.Label:
        """A titled, fixed-size frame holding one preview image."""
        ttk.Label(parent, text=heading, font=("Segoe UI", 12, "bold")).grid(
            row=0, column=column, pady=(0, 6))
        holder = ttk.Frame(parent, relief="groove", borderwidth=1,
                           width=PREVIEW_MAX[0], height=PREVIEW_MAX[1])
        holder.grid(row=1, column=column, padx=8, sticky="n")
        holder.grid_propagate(False)  # keep the fixed size even when empty
        holder.columnconfigure(0, weight=1)
        holder.rowconfigure(0, weight=1)
        panel = ttk.Label(holder, text="No image", anchor="center",
                         foreground="#888")
        panel.grid(row=0, column=0)
        return panel

    def _make_slider(self, parent: ttk.Frame, label: str, var: tk.IntVar,
                     lo: int, hi: int, column: int, hint: str) -> None:
        box = ttk.Frame(parent)
        box.grid(row=0, column=column, sticky="ew", padx=8)
        box.columnconfigure(0, weight=1)
        header = ttk.Frame(box)
        header.grid(row=0, column=0, sticky="ew")
        ttk.Label(header, text=label, font=("Segoe UI", 10, "bold")).pack(side="left")
        ttk.Label(header, textvariable=var).pack(side="right")
        scale = tk.Scale(box, from_=lo, to=hi, orient="horizontal", variable=var,
                        showvalue=False, command=self._schedule_recompute)
        scale.grid(row=1, column=0, sticky="ew")
        ttk.Label(box, text=hint, font=("Segoe UI", 8), foreground="#888",
                 wraplength=180, justify="left").grid(row=2, column=0, sticky="w")

    # -------------------------------------------------------------- actions --
    def select_image(self) -> None:
        path = filedialog.askopenfilename(title="Select an image", filetypes=IMAGE_FILETYPES)
        if not path:
            return
        try:
            with Image.open(path) as im:
                self.original = im.convert("RGB")  # convert() loads pixel data now
        except (OSError, ValueError) as exc:
            mbox.showerror("Could not open image", f"{os.path.basename(path)}\n\n{exc}")
            return
        self._render(self.orig_panel, self.original, "_orig_photo")
        self.status_var.set(f"Loaded: {os.path.basename(path)}  ({self.original.width}×{self.original.height})")
        self._recompute()

    def save_result(self) -> None:
        if self.cleaned is None:
            mbox.showinfo("Nothing to save", "Load an image first, then save the cleaned result.")
            return
        path = filedialog.asksaveasfilename(
            title="Save cleaned image",
            defaultextension=".png",
            filetypes=[("PNG image", "*.png"), ("JPEG image", "*.jpg"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            to_save = self.cleaned
            # JPEG has no alpha; RGB is already safe, but guard anyway.
            if os.path.splitext(path)[1].lower() in (".jpg", ".jpeg"):
                to_save = to_save.convert("RGB")
            to_save.save(path)
        except (OSError, ValueError) as exc:
            mbox.showerror("Save failed", str(exc))
            return
        self.status_var.set(f"Saved: {path}")

    # ------------------------------------------------------------ rendering --
    def _schedule_recompute(self, _value: str | None = None) -> None:
        """Coalesce rapid slider movement into one recompute."""
        if self._debounce_id is not None:
            self.root.after_cancel(self._debounce_id)
        self._debounce_id = self.root.after(DEBOUNCE_MS, self._recompute)

    def _recompute(self) -> None:
        self._debounce_id = None
        if self.original is None:
            return
        # Clean the FULL-resolution image (thresholds are per-pixel, so cleaning a
        # downscaled preview would diverge from what actually gets saved), then
        # downscale only for display.
        self.cleaned, pct = clean_image(
            self.original, self.light_var.get(), self.red_var.get(), self.pink_var.get()
        )
        self._render(self.clean_panel, self.cleaned, "_clean_photo")
        self.pct_var.set(f"{pct:.1f}% of pixels whitened")

    def _render(self, panel: ttk.Label, img: Image.Image, attr: str) -> None:
        photo = ImageTk.PhotoImage(self._fit(img))
        setattr(self, attr, photo)  # persist the reference (see __init__ note)
        panel.configure(image=photo, text="")

    @staticmethod
    def _fit(img: Image.Image) -> Image.Image:
        max_w, max_h = PREVIEW_MAX
        scale = min(max_w / img.width, max_h / img.height, 1.0)
        if scale < 1.0:
            new_size = (max(1, round(img.width * scale)), max(1, round(img.height * scale)))
            return img.resize(new_size, Image.LANCZOS)
        return img

    # ---------------------------------------------------------------- exit --
    def _on_exit(self) -> None:
        if mbox.askokcancel("Exit", "Do you want to exit?"):
            self.root.destroy()


def main() -> None:
    root = tk.Tk()
    WatermarkRemoverApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
