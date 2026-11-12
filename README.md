# PolyXRD Converter

**XRD pattern format converter** — a lightweight tool spun off from [PolyXRD](https://github.com/PolyXRD/PolyXRD): convert pattern files exported by various vendors/software into the target format you need, with **automatic detection of multi-vendor binary RAW**, double-click to run, no installation required.

**Current version v1.5.1** ｜ [Download the latest Release](https://github.com/PolyXRD/PolyXRD-Converter/releases/latest) (Setup installer / Internal single-file exe, with SHA-256) ｜ UI languages: Simplified Chinese / English / Japanese

<div align="center"><img src="src/polyxrd_converter/resources/icon.png" alt="PolyXRD Converter" width="96"></div>

## Features

- **Read**: `xy` `txt` `dat` `csv` `smz` `mdi` `xrdml/xml` `brml` `json`, GSAS powder data (`gsas`/`fxye`/`gda`, four BANK types FXYE/FXY/ESD/STD), FullProf `.dat`, Rigaku `.ras`/`.rasx`, Topas `.xye`/`.qye`, Fit2D `.chi`/`.qchi`, and multi-vendor binary `RAW` (auto-detected, see the table below); the `.ORG/.RSM/.RBG/.RK1/.RAX/.RLZ/.RFI` files of Shimadzu projects share the same structure as `.RAW` and are supported as well
- **Write**: `xy` `txt` `dat` `csv` `mdi` `raw` `xrdml` `json`
- **Batch conversion**: drag in an entire directory, a background thread converts files one by one with live progress
- **Pattern preview**: hand-drawn curve (no matplotlib dependency), scroll to zoom / drag to pan / double-click to reset / strongest-peak marker
- **Angle-axis guardrail**: when RAW header parameters are corrupted, **rather mark the axis as untrustworthy than guess** — automatic conversion is refused and you are guided to specify `(start 2θ, step)` manually, preventing the output of patterns with wrong peak positions
- **Trilingual UI**: Simplified Chinese / English / Japanese, switched via the menu bar "Language" with **immediate effect** (no restart); language names use native spelling, and adding a new language only requires adding a table in `i18n.py`
- **Dual-edition build (v1.5.0)**: two binaries, Setup installer (with registration mechanism) and Internal evaluation build (without registration mechanism), see "Two editions" below

## Two editions (since v1.5.0)

| | **Setup installer** | **Internal evaluation build** |
|---|---|---|
| Artifact | `PolyXRD-Converter-Setup-vX.Y.Z.exe` (Inno Setup installer) | `PolyXRD-Converter-Internal-vX.Y.Z.exe` (single file, double-click to run) |
| Registration mechanism | ✅ Yes (see "Registration" below) | ❌ No |
| Status bar | Unregistered / Registered: institution/department name (right-aligned) | Fixed "Internal Evaluation Version" (centered in the whole status bar, bold, red text) |
| Use case | External distribution / copyright management needed | Internal self-use evaluation |

## Registration (Setup installer)

- **Unregistered**: a prompt appears on every startup: "This software is unregistered. All rights reserved. Commercial use is prohibited. To register, please contact sshztx@outlook.com" — click "OK" to keep using it normally (prompt only); click "Enter Registration Code" to register on the spot
- **Obtaining a registration code**: send the **institution/department name** to sshztx@outlook.com; the developer generates a registration code of the form `PXRD1-XXXX-XXXX-...` (offline HMAC-SHA256 algorithm, shared across the PolyXRD family of software)
- **Entering a registration code**: menu bar "Help" → "Enter Registration Code (&R)…", just paste it; supports with/without prefix, arbitrary spaces and hyphens, and mixed case
- **After registration**: the **far right of the status bar** shows "Registered: institution/department name", and no prompt appears on later startups; the same registration code can be used on multiple computers in the same institution (not machine-bound)
- **Registration state**: stored in `%APPDATA%\PolyXRD\Registration\PolyXRD_Converter.json`; the registration code is re-validated on every startup (hand-editing the JSON to fake it has no effect); uninstalling the software does not clear it, so it remains registered after reinstallation

## Automatic detection of multi-vendor RAW

| Vendor / format | Magic number | Detection key points |
|---|---|---|
| Shimadzu XRD | `Shimadzu XRD` | Private container: variable-length header + **int32 LE** intensities. Point count from `u32@0x34 ÷ 4` in the header (authoritative), data start = `u32@0x30 + 56` (header length varies; some files also count the embedded source path into the header). Start/end/step are `i32@0x12C/0x130/0x134 ×1e-4` (**signed**, supports negative θ scans). The `0x20` record type distinguishes `.RAW/.ORG/.RSM/.RBG/.RK1/.RAX/.RLZ/.RFI` (same structure, all readable) from `PKR/PKK/PKS/PSE/PKF` (peak tables, **explicitly rejected**). **Truncation guard**: when the declared data region extends past end of file, clamp to the actually usable point count, flag `truncated` and highlight the warning — never read header bytes as intensities; truncated files have their angle axis forced to manual specification |
| Rigaku (RINT/SmartLab) | `FI\x00\x00` | Fixed 3162-byte header + variable-length float32 intensities, axis parameters at 0xB92; point count cross-checked by two pieces of evidence (n_axis vs n_fixed) for consistency |
| Scintag RAW2 | `RAW2` | 316-byte header; point count (int16)@0x102, step (float32)@0x10C, start 2θ (float32)@0x110 |
| Bruker/Siemens RAW v1 | `RAW1.01` / `RAW1.00` / `RAW ` | Fixed-length string header + 10 × 892-byte range records + trailing float32 intensities; the axis is matched by strict criteria (step 0.005~0.5°, span≥1°, end≤180°), and is marked untrustworthy if no match |
| MDI / Jade text export | — (two-line header) | Header line `start step mode anode λ stop npoints`, single column of fixed-width intensities; the axis is built from the header only after the anode/target notation and wavelength are cross-checked |
| Unknown RAW | — | Fallback parsing (longest plausible float32 suffix), axis always marked untrustworthy |

> **Design principle**: the parser is organized around "magic-number dispatch + confidence marking". When header parameters are corrupted (e.g. end > 180°, inconsistent point count) it yields `axis_confident=False`, the GUI highlights a warning, and conversion is blocked until an angle axis is given manually.

### Four conventions of the Shimadzu container (all handled)

- **Step field truncated**: `Std/Search.RAW` has 0.0213 written in the header, but the actual value is 0.0212644 (truncated to 4 decimal places). When the point-count consistency check fails, the step is back-computed from `(end − start)/(n − 1)`.
- **The end in the header is off by one step**: some samples use `end = start + step×n` (e.g. `Stress/Heikei-Test`: 34.0 + 0.05×80 = 38.0, exactly closed), others `start + step×(n−1)`. The point count declared at `0x34` in the header and the step field are authoritative, and both conventions are accepted — uniformly re-laying out by `(end−start)/(n−1)` would stretch the axis on this class of files into a step the firmware could never produce (e.g. 0.05063291).
- **The wavelength field may be stale**: in `Stress/std-sokkei.RAW` the target is already Cr but the wavelength field still holds Cu 1.5406 — the target element symbol from the lookup table is authoritative.
- **File truncated**: when the data region declared in the header does not fit in the actual file (incomplete transfer, etc.), clamp to the usable point count, flag `truncated` and highlight "File incomplete" in the list; for a truncated file `end` corresponds to the declared point count rather than the actual one, so the angle axis is untrustworthy and must be specified manually before conversion.

## Usage

### Graphical interface

Double-click `PolyXRD-Converter.exe` (or `python main.py`):

1. Drag files/folders into the window (or click "Add Files")
2. The table automatically detects each file's format, point count, 2θ range, and strongest peak intensity
3. Select any row to preview the pattern on the right
4. Choose the target format + output directory → "Start Conversion"
5. Switch the UI language: menu bar "Language" → Simplified Chinese / English / Japanese, **takes effect immediately**, no restart
6. View the license: menu bar "Help" → "Copyright" (alongside "About") opens a bilingual Chinese-English license notice and contact information

Launch with arguments (equivalent to dragging files onto the exe icon):

```
PolyXRD-Converter.exe D:\data\spectrum.raw D:\data\another.xy
```

### Command line / as a library

```python
from polyxrd_converter.loader import load_pattern
from polyxrd_converter.converter import convert_file

data = load_pattern("spectrum.raw")          # auto-detect format
print(len(data), data.two_theta[0], data.two_theta[-1])

convert_file("spectrum.raw", "spectrum.xrdml")   # single-file conversion
```

## Validation

Full cross-validation on real samples (point-by-point comparison against other-format exports of the same pattern):

```
python tests/validate_samples.py     # 612 assertions
python tests/smoke_gui.py            # GUI off-screen smoke 65 items
python tests/test_registration.py    # registration mechanism 21 items (pure stdlib)
```

Coverage:
- **Shimadzu**: all 72 `.RAW` files in `XRData/Shimadzu Data` parsed successfully (all angle axes trustworthy), of which 5 groups were compared point-by-point with the vendor's official ASCII export — **intensities exactly equal**, 2θ difference <3e-14; includes regression on 5 boundary samples (negative θ scan, truncated step, end off by one step, Cr target, variable-length header) plus peak-table rejection and synthetic truncated-file regression
- **Full Shimadzu cross-check (v1.1.0)**: all 305 Shimadzu container files in the `XRData` library (including 1608/976-byte variable-length header subtypes) parsed successfully, of which 26 genuinely truncated files were correctly flagged and blocked; 206 files cross-checked point-by-point against PolyXRD's main `DataLoader._load_shimadzu_raw`, **intensities all equal**; `smz geshi` 13 pairs of `.RAW`↔PCXRD ASCII exports cross-checked point-by-point (including θ single-axis rocking scans), intensities all equal, 2θ difference <1.5e-14
- **Rigaku**: 39 Rigaku FI files (point-by-point identical to `.txt`)
- **Scintag**: 33 RAW2 files (point-by-point all equal to `.dat/.txt/.xy`)
- **Bruker**: RAW v1 samples with corrupted axes correctly blocked
- **Jade**: text export builds the axis from the header + peak-position cross-check
- **GSAS-II family text formats**: `.gsas/.fxye` (FXYE/FXY/ESD/STD), FullProf `.dat`, Rigaku `.ras/.rasx`, Topas `.xye/.qye`, Fit2D `.chi/.qchi` — full-format regression on synthetic samples, and point-by-point oracle cross-check against GSAS-II itself (Argonne's open-source reference implementation) — 10 formats fully consistent with GSAS-II, the 4 skips are all GSAS-II's own defects (STD `int()` crash, Fit2D header misrouted into the pyFAI branch, etc.), all avoided by this implementation
- Round-trip conservation for 8 formats
- **Trilingual consistency (v1.5.0)**: 141 text entries × 3 languages have aligned key sets, placeholders with the same names and counts, and every entry passes `format`; read/write format names have translations in all three languages; 7 entries (buttons/menu/"About" etc.) are guarded by a "all three languages must differ" check (to catch a whole copied table left unchanged). Plus 3 UI smoke assertions: after switching to ja/en/zh, buttons, table headers, the menu bar, the target-format dropdown, and the "Detected format" column of loaded rows are all re-translated immediately
- **Registration mechanism (v1.5.0)**: 21 items for code generation/validation (Chinese/English unit-name round-trip, input tolerance, tamper rejection, state-file anti-forgery, trilingual status text); 12 GUI smoke items (unregistered prompt flow, status bar showing the unit name after registration and re-translating immediately with the language, internal evaluation build having no registration menu and showing "Internal Evaluation Version")
- **Internal evaluation build status bar (v1.5.1)**: 3 new smoke items — the prompt text horizontally centered (`AlignHCenter`), bold font, and red style `#ff0000`; also measured under native Windows rendering at three window widths 900 / 1100 / 1600, the deviation between the red text's actual rendered center and the status bar's geometric center is consistently **+0.5px** (the width QStatusBar reserves for the bottom-right size grip is compensated by the label's left margin; the reserved width is back-derived from the geometric difference, self-adapting for both off-screen 24px / native 20px); boldness verified by A/B rendering (red pixels 209 → 338 at the same font size), font size still the global 9.5pt, unchanged

## Documentation

- [Project handover record (Chinese)](docs/交接记录-HANDOVER.md) — **Project handover record**: project positioning, module layering, RAW parser registry, acceptance matrix and ground-truth sources, version progress, 24 lessons learned, known issues (required reading for taking over development / collaboration model)

## Development

```bash
python -m venv venv
venv\Scripts\pip install -e . pyinstaller
python main.py                 # run from source
build.bat                      # dual-edition packaging: Internal single-file + Setup installer (requires Inno Setup 6)
```

### Adding a new language

Add a table with the same keys as `ZH` in `src/polyxrd_converter/i18n.py` and hook it into `_LANGS` and `LANGS`; the language menu is then generated automatically.
Consistency of the key set and placeholders is enforced by `tests/validate_samples.py::validate_i18n` (a missing key makes `tr()` silently fall back to Chinese).

## Dependencies

Runtime requires only `numpy` + `PySide6` (the preview is hand-drawn with QPainter; matplotlib/pyqtgraph are deliberately not introduced to keep the single-file size and startup speed down).

## License

Copyright (c) 2026 PolyXRD Team.

This software may be used free of charge for academic research and teaching.
Commercial use is prohibited without separate written permission from the copyright holder.
The software is provided as-is, without any warranty.

See the full terms in [`LICENSE`](LICENSE) (English) and [`LICENSE-CN`](LICENSE-CN) (Chinese); for commercial licensing contact: sshztx@outlook.com.
When using it, please also comply with the upstream third-party license terms of PySide6 (LGPL/GPL), numpy (BSD), etc.

---

<div align="right">
  <i>PolyXRD Team · 2025 — 2026 · Contact: sshztx@outlook.com</i>
</div>
