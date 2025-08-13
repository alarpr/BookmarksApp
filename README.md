# BookmarksApp - Eestikeelne Bookmark Organiseerija

## Ülevaade

BookmarksApp on FastAPI-põhine veebirakendus, mis võimaldab hallata ja organiseerida veebilehtede järjehoidjaid (bookmarks) hierarhilises kaustade struktuuris. Rakendus toetab mitut import/export vormingut ja pakub kasutajasõbralikku liidest bookmarkide organiseerimiseks.

## Peamised funktsioonid

### 📚 Bookmarkide haldamine
- **Hierarhiline struktuur**: Loo kaustu ja alamkaustu bookmarkide organiseerimiseks
- **Drag & Drop**: Lohistage bookmarke kaustade vahel
- **Otsing**: Otsige bookmarke pealkirja või URL-i järgi
- **Eelvaade**: Vaadake lehti otse rakenduses (YouTube, GitHub README tugi)

### 📥 Import/Export
- **HTML**: Safari/Netscape bookmark failide import
- **CSV**: Tabelvormingus andmete import/export
- **JSON**: Struktureeritud andmete import/export
- **SQLite**: Andmebaasi varundamine ja taastamine

### 🎛️ Kasutajaliides
- **Resizable veergud**: Muutke külgriba ja eelvaate laiust lohistamisega
- **Topeltklõps**: Kiirlahendused veergude laiusele
- **Tume teema**: Kaasaegne, silmale sõbralik disain
- **Responsive**: Töötab erinevatel ekraani suurustel

### 🔍 Täiendavad võimalused
- **Linkide kontroll**: Automaatne kontroll, kas linkid töötavad
- **Favicon**: Näitab lehtede ikoonid
- **Bulk tegevused**: Korraga mitme bookmarki kustutamine/liigutamine

## Tehniline info

### Backend
- **FastAPI**: Moderne Python web framework
- **SQLAlchemy**: ORM andmebaasi haldamiseks
- **SQLite**: Andmebaas (failipõhine)
- **Jinja2**: Mallimootor HTML-i jaoks

### Frontend
- **Vanilla JavaScript**: Ilma raamistikuta
- **CSS Grid**: Kaasaegne paigutus
- **HTML5**: Semantiline märgistus

### Sõltuvused
```
fastapi==0.114.2
uvicorn[standard]==0.30.6
jinja2==3.1.4
sqlalchemy==2.0.32
pydantic==2.8.2
python-multipart==0.0.9
beautifulsoup4==4.12.3
httpx==0.27.2
```

## Paigaldamine

### 1. Klooni projekt
```bash
git clone <repository-url>
cd BookmarksApp
```

### 2. Loo virtuaalkeskkond
```bash
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# või
.venv\Scripts\activate     # Windows
```

### 3. Installi sõltuvused
```bash
pip install -r requirements.txt
```

### 4. Käivita server
```bash
# HTTP (arenduse jaoks)
./start_server.sh

# või HTTPS (kohalik)
./start_server_https.sh
```

### 5. Ava brauseris
- HTTP: `http://localhost:8000`
- HTTPS: `https://localhost:8444` (kohalik sertifikaat)

## Kasutamine

### Bookmarkide lisamine
1. Vali kaust, kuhu soovid bookmarki lisada
2. Sisesta pealkiri ja URL
3. Klõpsa "Lisa link"

### Kaustade haldamine
- **Lisa kaust**: Sisesta kausta nimi ja klõpsa "Lisa"
- **Ümbernimetamine**: Klõpsa "Tööriistad" → sisesta uus nimi
- **Kustutamine**: Klõpsa "Kustuta" (juurkausta ei saa kustutada)

### Importimine
1. Vali menüüst "Halda Ressursse" → Import
2. Vali fail (HTML/CSV/JSON)
3. Klõpsa "Laadi üles"
4. Vaata tulemusi (imporditud/vahele jäetud)

### Exportimine
- **HTML**: Netscape vorming, ühilduv enamiku brauseritega
- **CSV**: Tabelvorming, avatav Excelis
- **JSON**: Struktureeritud andmed, programmeerimiseks

### Veergude laiuse muutmine
- **Lohistamine**: Vii hiir eraldusriba peale ja lohista
- **Topeltklõps**: Kiirlahendused eelseadistatud laiustele
- **Salvestamine**: Laiused jäävad meelde ka lehe uuesti avamisel

## Andmebaasi struktuur

### Tabelid
- **topics**: Kaustade hierarhia (id, name, parent_id)
- **bookmarks**: Bookmarkide andmed (id, title, url, topic_id)

### Seosed
- Kaust võib sisaldada alamkaustu ja bookmarke
- Bookmark kuulub alati ühte kausta
- Juurkaust: "Minu kogud"

## Arendamine

### Projektistruktuur
```
BookmarksApp/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI rakendus
│   ├── models.py        # SQLAlchemy mudelid
│   ├── db.py           # Andmebaasi ühendus
│   ├── parse_bookmarks.py  # HTML parsimine
│   ├── templates/       # HTML mallid
│   └── static/         # CSS, JavaScript
├── requirements.txt
├── start_server.sh      # HTTP server
└── start_server_https.sh # HTTPS server
```

### Uute funktsioonide lisamine
1. Lisa endpoint `main.py`-sse
2. Vajadusel uuenda `models.py`-d
3. Lisa kasutajaliides `templates/` või `static/` kausta
4. Testi funktsionaalsust

### Andmebaasi muudatused
```bash
# SQLite andmebaasi vaatamine
sqlite3 bookmarks.sqlite3
.tables
.schema topics
.schema bookmarks
```

## Probleemide lahendamine

### Import ei tööta
- Kontrolli faili vormingut (HTML peaks olema Netscape vormingus)
- Vaata serveri logisid veateadete jaoks
- Proovi väiksema failiga

### Server ei käivitu
- Kontrolli, kas port on vaba: `lsof -i :8000`
- Peata olemasolev protsess: `pkill -f uvicorn`
- Kontrolli virtuaalkeskkonda: `which python`

### HTTPS probleemid
- Self-signed sertifikaadid võivad põhjustada hoiatusi
- Kasuta HTTP-d arenduse jaoks
- Tootmiskeskkonda jaoks kasuta Let's Encrypt

## Tulevased funktsioonid

- [ ] Drag & Drop import
- [ ] Duplikaatide ühendamine
- [ ] Täiendavad filtreerimisvõimalused
- [ ] Mobiilne kasutajaliides
- [ ] API dokumentatsioon
- [ ] Kasutajate haldamine
- [ ] Sünkroniseerimine

## Litsents

MIT Litsents - vaba kasutamine ja modifitseerimine.

## Kontakt

Küsimuste või ettepanekute jaoks loo issue GitHubis või võta ühendust arendajaga.

---

**Märge**: See rakendus on loodud eestikeelsete kasutajate jaoks, kuid kood on inglise keeles standardite järgimiseks.
