# 🌾 Krishikaran  
### Aerial Intelligence for Zero Hunger  

Krishikaran is a precision agriculture platform designed to empower smallholder farmers by detecting invisible crop stress **before irreversible yield loss occurs**. By leveraging drone-based imagery and advanced computer vision, the system transforms raw aerial data into actionable insights within minutes.

---

## 🚨 The Problem  

- By the time crop stress becomes visible to the naked eye, **20–30% of yield potential is already lost**  
- Satellite imagery lacks **field-level resolution**  
- Manual scouting is **slow, labor-intensive, and inefficient**

---

## ⚙️ Architecture & Workflow  

Krishikaran provides a fast pipeline — from **raw pixels to actionable insights in under 60 minutes**:

### 1. 📥 Ingest  
- Accepts **RGB & Multispectral imagery**  
- Formats supported: `GeoTIFF`, `JPEG`, `PNG`  
- Works with **standard commercial drones**  
- No specialized hardware required  

### 2. 🧠 Analyze  
- Uses **Computer Vision models**  
- Detects:
  - Early crop stress  
  - Irrigation issues  
  - Nutrient deficiencies  
- Identifies spectral variations invisible to humans  

### 3. 📍 Act  
- Generates **geo-tagged health maps**:
  - ✅ Optimal  
  - ⚠️ Alert  
  - 🚨 Critical  
- Provides **exact GPS coordinates** for intervention  

---

## 🌟 Core Features  

- **Severity Scoring**
  - 🔴 Critical — Immediate action required  
  - 🟡 Warning — Monitor closely  
  - 🟢 Stable — Healthy crops  

- **Exportable Report** 
  - 🧾 JSON  
- Includes precise coordinates for field-level action  

---

## 📊 Example JSON Report  

```json
{
  "field_id": "KR-001",
  "timestamp": "2026-03-19T14:30:00Z",
  "overall_health": "Warning",
  "zones": [
    {
      "zone_id": "Z1",
      "status": "Optimal",
      "coordinates": [9.3842, 76.5740],
      "action": "No action needed"
    },
    {
      "zone_id": "Z2",
      "status": "Alert",
      "coordinates": [9.3845, 76.5745],
      "action": "Check irrigation"
    },
    {
      "zone_id": "Z3",
      "status": "Critical",
      "coordinates": [9.3850, 76.5750],
      "action": "Apply nutrients immediately"
    }
  ]
}
