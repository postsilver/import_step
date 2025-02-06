# STEP File Importer for Blender

**Blender Compatibility:** 4.3.2+  
**FreeCAD Required:** ✅ Yes (0.20 or newer)  

📌 **A Blender add-on that enables importing CAD STEP files (`.step` / `.stp`) by converting them to STL using FreeCAD.**  

## Latest Release: v1.1.0
- Added OS detection using `platform.system()`
- Updated default FreeCADCmd paths for macOS, Windows, and Linux
- Various improvements and bug fixes

[See full release notes](https://github.com/postsilver/import_step/releases/tag/v1.1.0)


---

## ✨ Features

✅ **Automatic STEP to STL Conversion**  
- Uses **FreeCAD’s tessellation engine** for accurate conversion.  

✅ **Adjustable Mesh Quality**  
- Set **deflection values** to control mesh detail.  

✅ **Seamless Blender Integration**  
- Works via **File → Import → STEP (.step/.stp)** just like other native Blender importers.  

✅ **Temporary File Cleanup**  
- Automatically removes intermediate files after conversion.  

---

## 📌 Prerequisites

Before installing the add-on, make sure you have the following:  

| **Requirement** | **Version** |
|---------------|------------|
| Blender | **4.3.2+** |
| FreeCAD | **0.20+** ([Download FreeCAD](https://www.freecad.org/)) |
| Python | **3.10+** |

🔹 **FreeCAD** is required because Blender does not natively support STEP file import.  

---

## 📥 Installation

1. **Download** `import_step.py`.  
2. Open **Blender** and go to **Edit → Preferences → Add-ons**.  
3. Click **Install...**, select `import_step.py`, and click **Install Add-on**.  
4. Enable the add-on by checking the checkbox.  

---

## ⚙️ Configuration

Before using the add-on, you need to **set the FreeCAD command-line path** in Blender’s preferences.

### 🔍 **Locate FreeCADCmd Executable**
| **Operating System** | **Path** |
|---------------------|------------|
| **Windows** | `C:\Program Files\FreeCAD\bin\FreeCADCmd.exe` |
| **macOS** | `/Applications/FreeCAD.app/Contents/MacOS/FreeCADCmd` |
| **Linux** | `/usr/bin/FreeCADCmd` |

### 🔧 **Set FreeCAD Path in Blender**
1. **Open Blender Preferences** → **Add-ons** → **Import-Export**.  
2. Find **"Import STEP Files"** and expand its settings.  
3. **Set the correct FreeCADCmd path** based on your OS.  
4. Click **Save Preferences** to retain settings.  

---

## 🚀 Usage

### 📂 **Importing a STEP File**
1. **Go to** `File → Import → STEP (.step/.stp)`.  
2. **Select** your STEP file.  
3. **Adjust the Deflection Parameter** (optional, see below).  
4. Click **Import** and wait for conversion.  

### 🎛 **Deflection Parameter (Mesh Quality)**
- Controls **how detailed** the converted mesh is.  
- **Lower values = More detail, higher values = Less detail**.  

| **Deflection Value** | **Mesh Detail** | **Use Case** |
|----------------------|----------------|--------------|
| `0.01` | **Very High** | Precise models, small details |
| `0.05` | **High** | General CAD models |
| `0.1` *(Default)* | **Balanced** | Good compromise between detail & performance |
| `1.0 - 10.0` | **Low** | Large, rough objects |

---

## 🔧 Troubleshooting

### ❌ **"FreeCADCmd Not Found" Error**
✔ **Check that FreeCAD is installed** and **working**.  
✔ Verify that **the correct FreeCADCmd path** is set in **Blender Preferences**.  
✔ On **Linux/macOS**, ensure **executable permissions** (`chmod +x FreeCADCmd`).  

### ⚠️ **Conversion Errors**
✔ **Try a different deflection value** (increase for complex models).  
✔ **Check STEP file integrity** (corrupt files may fail).  
✔ **Simplify** the geometry before importing.  

### 🚫 **Missing Output**
✔ **Ensure you have sufficient disk space** for temporary files.  
✔ Check **system temp directory permissions** (`/tmp` on Linux/macOS).  

---

## ⚠️ Limitations

🔹 **No Material/Color Support**  
- **STEP files do not store materials or colors** when converted to STL.  

🔹 **Complex Geometries May Require Cleanup**  
- Some **highly detailed models** may require manual adjustments in Blender.  

🔹 **Large Files (>100MB) May Take Time**  
- Import times **increase significantly** with large STEP files.  

---

## 🤝 Contributing

💡 **Want to improve this add-on?** Contributions are welcome! Please follow these steps:  

1. **Fork** this repository.  
2. **Create** a feature branch.  
3. **Submit** a pull request with your changes.  

For bug reports or suggestions, open an **issue** on GitHub.  

---

## 📜 License

📄 **GPL v3** – This add-on is licensed under the **GNU General Public License v3.0** to align with Blender’s open-source licensing.  

See the full **LICENSE** file in this repository for details.  

---

## 💡 Additional Notes

💡 If you encounter **slow conversions**, try:  
- **Increasing the deflection value** (e.g., `0.2 - 1.0`).  
- **Preprocessing the STEP file** in FreeCAD before importing.  

🚀 **This tool is designed for efficient STEP file import into Blender, but some models may require further cleanup.**  
For **advanced CAD workflows**, consider using FreeCAD for direct editing before importing into Blender.  

---
![step_image](https://github.com/user-attachments/assets/589840e6-d927-440e-83d9-40e4fbb9f007)
