"""Create compact, reproducible teaching products from Gemini GMOS raw FITS.

This is intentionally a transparent pedagogical reduction, not a replacement for
the instrument-aware Gemini DRAGONS science pipeline.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from astropy.io import fits
from scipy.ndimage import median_filter

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "source_data"
DATA = ROOT / "data"

FILES = {
    "raw": "S20171022S0087.fits.bz2",
    "bias": "S20171021S0265.fits.bz2",
    "flat": "S20171022S0088.fits.bz2",
    "arc": "S20171022S0092.fits.bz2",
}


def active_and_overscan(hdu, index):
    arr = np.asarray(hdu.data, dtype=np.float32)
    if index % 2:  # overscan is on the right
        return arr[:, :256], arr[:, 256:]
    return arr[:, 32:], arr[:, :32]


def overscan_mosaic(path: Path) -> tuple[np.ndarray, fits.Header]:
    pieces = []
    with fits.open(path, memmap=False) as hdul:
        header = hdul[0].header.copy()
        for index, hdu in enumerate(hdul[1:], 1):
            active, overscan = active_and_overscan(hdu, index)
            row_level = np.nanmedian(overscan, axis=1)
            pieces.append(active - row_level[:, None])
    return np.hstack(pieces), header


def write_image(name, arr, source_name, stage):
    header = fits.Header()
    header["ORIGIN"] = "Gemini/NOIRLab GMOS tutorial"
    header["SRCFILE"] = source_name
    header["TEACHING"] = True
    header["STAGE"] = stage
    fits.writeto(DATA / name, arr.astype("f4"), header, overwrite=True)


def make_echelle_teaching_products(wavelength, normalized):
    """Build a clearly-labelled echelle teaching simulation from the real 1-D spectrum."""
    rng = np.random.default_rng(2145)
    nx, ny, n_orders = 720, 430, 9
    x = np.arange(nx)
    xn = (x - (nx - 1) / 2) / ((nx - 1) / 2)
    centers = np.linspace(4050, 6050, n_orders)
    order_wave = np.empty((n_orders, nx), dtype=np.float32)
    order_flux = np.empty_like(order_wave)
    blaze = np.empty_like(order_wave)
    image = rng.normal(18, 2.2, (ny, nx)).astype(np.float32)
    traces = []
    for i, center_wave in enumerate(centers):
        wave = center_wave + 270 * xn
        spec = np.interp(wave, wavelength, normalized, left=1, right=1)
        spec = median_filter(spec, size=5)
        response = 0.18 + 0.82 * np.cos(np.pi * xn / 2) ** 2
        # Make order overlap realistic enough for the weighting exercise: the
        # low-response edges are noisier and each order has a tiny residual tilt.
        edge_noise = rng.normal(0, 0.006 / np.sqrt(response), nx)
        residual_tilt = (i - (n_orders - 1) / 2) * 0.0025 * xn
        measured_spec = spec + edge_noise + residual_tilt
        ytrace = 34 + i * 44 + (i - 4) * 0.8 * xn + 5.5 * xn**2
        traces.append(ytrace)
        profile = np.exp(-0.5 * ((np.arange(ny)[:, None] - ytrace[None, :]) / 2.1) ** 2)
        image += (310 * response * spec)[None, :] * profile
        order_wave[i], order_flux[i], blaze[i] = wave, measured_spec, response

    # Deterministic cosmic-ray hits: isolated sharp events and two short tracks.
    hits = [(92,124,1500),(174,562,850),(267,347,520),(355,645,260),(401,78,130),
            (128,420,85),(316,188,55),(63,660,35),(50,50,18),(75,200,25),
            (110,300,32),(145,500,38),(190,100,45),(230,650,52),(280,450,60),
            (330,60,70),(370,300,80)]
    cosmic = image.copy()
    for y,xx,strength in hits:
        cosmic[y,xx] += strength
        if y + 1 < ny:
            cosmic[y+1,xx] += .42*strength
    for k in range(7):
        cosmic[210 + k, 238 + k] += 900 - 70 * k
    cleaned = image.copy()  # known truth is available only because this is a simulation

    h = fits.Header({"TEACHING": True, "DATATYPE": "SIMULATED ECHELLE", "BASEDON": "J2145+0031 1D"})
    fits.writeto(DATA / "echelle_raw_simulated.fits", cosmic, h, overwrite=True)
    fits.writeto(DATA / "echelle_cosmic_cleaned.fits", cleaned, h, overwrite=True)
    hdus = [fits.PrimaryHDU(header=h), fits.ImageHDU(order_wave, name="WAVELENGTH"),
            fits.ImageHDU(order_flux, name="ORDER_FLUX"), fits.ImageHDU(blaze, name="BLAZE")]
    fits.HDUList(hdus).writeto(DATA / "echelle_extracted_orders.fits", overwrite=True)


def main():
    DATA.mkdir(parents=True, exist_ok=True)
    for filename in FILES.values():
        if not (SOURCE / filename).exists():
            raise FileNotFoundError(f"Missing {SOURCE / filename}; see README data setup.")

    raw, _ = overscan_mosaic(SOURCE / FILES["raw"])
    bias, _ = overscan_mosaic(SOURCE / FILES["bias"])
    flat, _ = overscan_mosaic(SOURCE / FILES["flat"])
    arc, _ = overscan_mosaic(SOURCE / FILES["arc"])

    bias_sub = raw - bias
    flat_sub = flat - bias
    smooth = median_filter(flat_sub, size=(101, 1), mode="nearest")
    response = flat_sub / np.where(np.abs(smooth) > 1, smooth, 1)
    response = np.clip(response, 0.5, 1.5)
    corrected = bias_sub / response

    # J2145+0031 is centered around row 1070. Use adjacent sky strips.
    center, half = 1070, 8
    source = np.nansum(corrected[center-half:center+half+1], axis=0)
    sky_rows = np.r_[center-45:center-20, center+20:center+45]
    sky = np.nanmedian(corrected[sky_rows], axis=0) * (2 * half + 1)
    flux = source - sky

    # B600, 2x2 binning: a linear teaching WCS centered at 5150 A.
    # The arc frame is retained so learners can see what sets the real solution.
    dispersion = 0.90
    wavelength = 5150.0 + (np.arange(flux.size) - (flux.size - 1) / 2) * dispersion
    continuum = median_filter(flux, size=301, mode="nearest")
    normalized = flux / np.where(np.abs(continuum) > 1e-6, continuum, np.nan)

    # 4x4 block means keep the visual structure while making the exhibit portable.
    compact = lambda a: a[: a.shape[0] // 4 * 4, : a.shape[1] // 4 * 4].reshape(
        a.shape[0] // 4, 4, a.shape[1] // 4, 4
    ).mean((1, 3))
    write_image("01_overscan_corrected_raw.fits", compact(raw), FILES["raw"], "overscan corrected, mosaicked, 4x4 binned")
    write_image("02_bias_subtracted.fits", compact(bias_sub), FILES["raw"], "representative bias subtracted, 4x4 binned")
    write_image("03_flat_corrected.fits", compact(corrected), FILES["raw"], "teaching flat correction, 4x4 binned")
    write_image("arc_mosaic.fits", compact(arc), FILES["arc"], "overscan corrected CuAr arc, 4x4 binned")
    cols = [
        fits.Column(name="wavelength", format="D", unit="Angstrom", array=wavelength),
        fits.Column(name="flux", format="D", array=flux),
        fits.Column(name="normalized_flux", format="D", array=normalized),
    ]
    hdr = fits.Header({"OBJECT": "J2145+0031", "TEACHING": True, "WAVECAL": "APPROX LINEAR"})
    fits.HDUList([fits.PrimaryHDU(header=hdr), fits.BinTableHDU.from_columns(cols, name="SPECTRUM")]).writeto(
        DATA / "reference_spectrum.fits", overwrite=True
    )
    make_echelle_teaching_products(wavelength, normalized)
    print(f"Wrote teaching products to {DATA}")


if __name__ == "__main__":
    main()
