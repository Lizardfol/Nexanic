# Nexanic — Tudásmentő Rendszer / Knowledge Preservation System

> *Mielőtt elfelejtik. / Before it's forgotten.*

---

## 🚀 Gyorsindítás / Quick Start

### Követelmények / Requirements
- Python 3.9+
- Flask (automatikusan telepíthető)

### Indítás / Launch

```bash
# 1. Telepítés
pip install -r requirements.txt

# 2. Indítás
python app.py
# vagy / or:
./start.sh
```

### Elérhetőség / Access

| URL | Leírás |
|-----|--------|
| `http://localhost:5005` | Főoldal (HU/EN) |
| `http://localhost:5005/admin` | Admin felület |


---

## 📁 Fájlszerkezet / File Structure

```
nexonic/
├── app.py                  ← Flask backend
├── requirements.txt        ← Python függőségek
├── start.sh                ← Indítószkript (Linux/Mac)
├── templates/
│   ├── index.html          ← Főoldal (kétnyelvű, dark/light)
│   └── admin.html          ← Admin panel + DB kezelő
└── sql/                    ← Adatbázis mappa (IDE KERÜLNEK A .db FÁJLOK)
    ├── nexonic_demo.db     ← Demo adatbázis (automatikusan generált)
    └── demo_queries.sql    ← Minta SQL lekérdezések
```

---

## 🗄️ Adatbázis-kezelő / Database Manager

### Hogyan adjon hozzá új adatbázist / How to add a new database

1. Másolja a `.db` vagy `.sqlite` fájlt a `./sql/` mappába
2. Az Admin panelen megjelenik a sidebar-ban
3. Kattintson rá → automatikusan betölti a táblákat

### Funkcionalitás / Features

| Funkció | Leírás |
|---------|--------|
| **Browse** | Táblák böngészése, lapozás, keresés, rendezés |
| **SQL Query** | Tetszőleges SQL futtatás (Ctrl+Enter) |
| **Schema** | Oszlopok, típusok, primary key-ek megtekintése |
| **.sql script viewer** | SQL szkriptfájlok szintaxis-kiemelve |

---

## 🌐 Főoldal funkciók / Landing Page Features

- **Nyelvi popup**: első látogatáskor HU/EN választó
- **Sötét/Világos mód**: böngésző preferenciát is figyeli
- **Vissza gomb**: automatikusan megjelenik ha van előzmény
- **Smooth scroll + fade-in animáció**
- **Reszponzív**: mobiltól desktopig

---

## 🤖 A Projektről / About the Project

A Nexonic egy animatronikus robot, amelynek egyetlen célja van:  
**idős emberek mellé ülni, meghallgatni őket, és megőrizni, amit mondanak.**

A robot nem igényel semmilyen digitális eszközt vagy előzetes tudást a felhasználótól — csak a hangját.

### Adatbázis sémája / Database Schema

```sql
knowledge_entries   -- Megőrzött tudásbejegyzések
  ├── id, title, category, location
  ├── person_name, date_recorded
  ├── summary, language (hu/en)
  ├── duration_sec, verified

sessions            -- Interjú sessionök
  ├── entry_id (FK), robot_id
  ├── started_at, ended_at
  └── questions_asked

tags                -- Keresőcímkék
  ├── entry_id (FK)
  └── tag
```

---

## 🔧 Fejlesztés / Development

### Környezeti változók / Environment Variables

```bash
PORT=5000           # Szerver port (alapértelmezett: 5000)
SECRET_KEY=...      # Flask session kulcs (éles környezetben kötelező!)
```

### Éles telepítés / Production

```bash
# Gunicorn (ajánlott)
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5005 app:app
```

---

*Nexanic — robotikus tudásmentő rendszer.*  
*Mielőtt elfelejtik.*
