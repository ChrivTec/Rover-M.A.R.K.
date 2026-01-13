# Auto-Detection Update - test_gnss.py

## ✅ Änderung

**`test_gnss.py` unterstützt jetzt "auto" in config.json!**

---

## 📋 Was wurde geändert

**Datei:** `test_gnss.py` (Zeile 34-50)

**Neue Funktion:**

```python
# Auto-detect port if configured as "auto"
if gnss_port == "auto":
    logger.info("🔍 Auto-detecting GNSS port...")
    from port_detector import auto_detect_ports
    gnss_detected, _ = auto_detect_ports()
    if gnss_detected:
        gnss_port = gnss_detected
        logger.info(f"✅ Auto-detected GNSS port: {gnss_port}")
    else:
        logger.error("❌ Auto-detection failed!")
        return
```

---

## 🚀 Wie nutzen

### 1. config.json mit "auto"

```json
"serial_ports": {
  "gnss": "auto",
  "motor_controller": "auto",
  ...
}
```

### 2. USB auf Raspberry Pi kopieren

**Von Windows:**

```powershell
copy c:\Users\Luis\OneDrive\MARK\rover-steuerung07.01.26\rover-steuerung\test_gnss.py D:\
```

**Auf Raspberry Pi:**

```bash
USB_PATH="/media/stein/$(ls /media/stein/ | head -1)"
cp "$USB_PATH/test_gnss.py" ~/mark-rover/
```

### 3. Test

```bash
cd ~/mark-rover
python3 test_gnss.py
```

**Output:**

```
🔍 Auto-detecting GNSS port...
✅ Auto-detected GNSS port: /dev/ttyACM0
Connected to GNSS successfully
```

---

## ✅ Dann funktioniert Auto-Detection überall

- ✅ `main.py` - hatte schon Auto-Detection
- ✅ `test_gnss.py` - **NEU!**
- ✅ `rtk_diagnostics.py` - hat eigene Detection

**→ Keine manuellen Ports mehr nötig!** 🎉
