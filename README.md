# CAD Importer for Blender

[![Blender](https://img.shields.io/badge/Blender-4.2%2B-orange?logo=blender)](https://www.blender.org/)
[![FreeCAD](https://img.shields.io/badge/FreeCAD-0.20%2B-blue)](https://www.freecad.org/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-green.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![GitHub stars](https://img.shields.io/github/stars/postsilver/import_step?style=social)](https://github.com/postsilver/import_step/stargazers)

**Import CAD STEP and IGES files directly into Blender** with part hierarchy preservation, quality presets, and drag-and-drop support.

![CAD Importer Demo](https://raw.githubusercontent.com/postsilver/import_step/main/docs/demo.png)

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| **STEP & IGES Support** | Import `.step`, `.stp`, `.iges`, `.igs` files |
| **Hierarchy Preservation** | Maintains part names and structure from CAD files |
| **Quality Presets** | Draft, Standard, High, Ultra - control mesh detail vs speed |
| **Drag & Drop** | Drop CAD files directly into the 3D viewport |
| **Cross-Platform** | Windows, macOS, and Linux support |
| **Auto-Detection** | Automatically finds FreeCAD installation |
| **Blender 4.2+ Extensions** | Native support for new extensions format |

---

## 📋 Requirements

| Requirement | Version | Download |
|-------------|---------|----------|
| Blender | 4.2.0+ | [blender.org](https://www.blender.org/download/) |
| FreeCAD | 0.20+ | [freecad.org](https://www.freecad.org/downloads.php) |

> **Note:** FreeCAD is required because Blender cannot natively parse STEP/IGES geometry. This addon uses FreeCAD's robust OpenCASCADE-based CAD kernel for accurate conversion.

---

## 📥 Installation

### Method 1: Blender Extensions (Recommended for 4.2+)

1. Download the latest `.zip` from [Releases](https://github.com/postsilver/import_step/releases)
2. In Blender: **Edit → Preferences → Get Extensions**
3. Click **⚙️ → Install from Disk** and select the zip file
4. Enable the addon

### Method 2: Legacy Install (Blender 4.0-4.1)

1. Download `__init__.py` from releases
2. In Blender: **Edit → Preferences → Add-ons → Install**
3. Select the file and enable the addon

---

## ⚙️ Configuration

### Setting FreeCAD Path

The addon will attempt to auto-detect FreeCAD. If it fails:

1. Go to **Edit → Preferences → Add-ons**
2. Find **CAD Importer** and expand settings
3. Click 🔍 to auto-detect, or manually set the path:

| OS | Typical FreeCAD Path |
|----|---------------------|
| **Windows** | `C:\Program Files\FreeCAD 0.21\bin\FreeCADCmd.exe` |
| **macOS** | `/Applications/FreeCAD.app/Contents/MacOS/FreeCADCmd` |
| **Linux** | `/usr/bin/freecadcmd` |

---

## 🚀 Usage

### Import via Menu

1. **File → Import → CAD Files (.step/.iges)**
2. Select your CAD file
3. Adjust quality preset if needed
4. Click **Import**

### Drag and Drop

Simply drag a `.step` or `.iges` file into Blender's 3D viewport.

### Quality Presets

| Preset | Deflection | Use Case |
|--------|------------|----------|
| **Draft** | 1.0 | Quick previews, very large assemblies |
| **Standard** | 0.1 | General use, good balance |
| **High** | 0.01 | Detailed models, product visualization |
| **Ultra** | 0.001 | Maximum detail, close-up renders |
| **Custom** | User-defined | Fine-tune for specific needs |

> **Tip:** Lower deflection = more polygons = more detail but slower import

---

## 🔧 Troubleshooting

### "FreeCAD not found"

1. Ensure FreeCAD is installed (not just downloaded)
2. Click the 🔍 auto-detect button in preferences
3. If auto-detect fails, manually browse to `FreeCADCmd` executable

### Conversion fails / No output

- **Check FreeCAD version:** Must be 0.20 or newer
- **Check file integrity:** Try opening the file in FreeCAD directly
- **Large files:** Increase timeout or use Draft quality first
- **Linux permissions:** Ensure `freecadcmd` is executable

### Import is very slow

- Use **Draft** or **Standard** quality for initial preview
- Complex assemblies (1000+ parts) may take several minutes
- Consider simplifying geometry in CAD software first

### Missing colors/materials

STEP files can contain color data, but conversion via mesh formats may lose this. For critical color preservation:
- Export from CAD as glTF if possible
- Apply materials manually in Blender
- Consider the [STEPper addon](https://ambient.gumroad.com/l/stepper) (paid, Windows-only) for direct color support

---

## 🆚 Comparison with Alternatives

| Feature | **CAD Importer** (this) | STEPper | SimLab |
|---------|------------------------|---------|--------|
| Price | **Free** | €17 | $72/yr |
| Platform | **Cross-platform** | Windows only | Win/Mac |
| IGES Support | ✅ | ❌ | ✅ |
| Dependency | FreeCAD | None | None |
| Color Support | Partial | ✅ | ✅ |
| Drag & Drop | ✅ | ❌ | ✅ |

---

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Setup

```bash
# Clone the repo
git clone https://github.com/postsilver/import_step.git
cd import_step

# Symlink to Blender addons folder (adjust path as needed)
# Linux/Mac:
ln -s $(pwd)/cad_importer ~/.config/blender/4.2/extensions/user_default/cad_importer

# Windows (run as admin):
mklink /D "%APPDATA%\Blender Foundation\Blender\4.2\extensions\user_default\cad_importer" "%cd%\cad_importer"
```

---

## 📜 License

[GPL-3.0](LICENSE) - Compatible with Blender's licensing.

---

## 🙏 Acknowledgments

- [FreeCAD](https://www.freecad.org/) for the CAD kernel
- [OpenCASCADE](https://www.opencascade.com/) technology
- Blender community for feedback and testing

---

## 📊 Version History

### v2.0.0 (2025)
- Complete rewrite for Blender 4.2+
- Added IGES support
- Added drag-and-drop
- Added quality presets
- Added auto-detection of FreeCAD
- Improved error handling and reporting
- Native extensions format support

### v1.1.2 (2024)
- OS detection for default paths
- Bug fixes

### v1.0.0 (2024)
- Initial release
