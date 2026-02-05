# Neuroion Startup Guide

Complete stap-voor-stap gids om het Neuroion platform te starten en te gebruiken.

## 📋 Vereisten

Zorg dat je de volgende software hebt geïnstalleerd:

- **Python 3.11+** (check met `python3 --version`)
- **Node.js 18+** (check met `node --version`)
- **Ollama** (voor lokale LLM)
- **pip** (Python package manager)

## 🚀 Start Procedure

### Stap 1: Ollama Controleren en Starten

Ollama moet draaien voordat je de Homebase start.

```bash
# Check of Ollama draait
curl http://localhost:11434/api/tags

# Als Ollama niet draait, start het:
ollama serve

# In een andere terminal, check of het model beschikbaar is:
ollama list

# Als llama3.2 niet geïnstalleerd is, installeer het:
ollama pull llama3.2
```

**✅ Verificatie:** Je zou een lijst van modellen moeten zien, inclusief `llama3.2`.

---

### Stap 2: Python Dependencies Installeren

```bash
# Navigeer naar de project root
cd /Users/karelgustin/Neuroion/Neuroion

# Installeer Python dependencies
cd neuroion/core
pip install -r requirements.txt

# Ga terug naar project root
cd ../..
```

**✅ Verificatie:** Geen error messages tijdens installatie.

---

### Stap 3: Database Initialiseren (Eerste Keer)

De database wordt automatisch aangemaakt bij de eerste server start, maar je kunt ook demo data aanmaken:

```bash
# Navigeer naar project root
cd /Users/karelgustin/Neuroion/Neuroion

# Initialiseer demo data (optioneel)
python3 demo_init.py
```

**✅ Verificatie:** Je ziet een bericht met een Household ID.

---

### Stap 4: Homebase Server Starten

**⚠️ Belangrijk:** Start de server in een aparte terminal, zodat je andere commando's kunt uitvoeren.

```bash
# Navigeer naar project root
cd /Users/karelgustin/Neuroion/Neuroion

# Start de server
python3 -m neuroion.core.main
```

**Of met uvicorn (met auto-reload):**
```bash
uvicorn neuroion.core.main:app --reload --host 0.0.0.0 --port 8000
```

**✅ Verificatie:** 
- Je ziet: `Neuroion Homebase starting on 0.0.0.0:8000`
- Test met: `curl http://localhost:8000/health`
- Je zou moeten zien: `{"status":"ok","service":"neuroion-core",...}`

**🔧 Troubleshooting:**
- Als poort 8000 al in gebruik is:
  ```bash
  # Zoek het proces
  lsof -ti:8000
  
  # Stop het (vervang PID)
  kill <PID>
  ```

---

### Stap 5: Setup UI Starten (Optioneel)

De Setup UI is een React interface voor pairing en status monitoring. Open dit in een **nieuwe terminal**:

```bash
# Navigeer naar setup-ui directory
cd /Users/karelgustin/Neuroion/Neuroion/setup-ui

# Installeer dependencies (alleen eerste keer)
npm install

# Start development server
npm run dev
```

**✅ Verificatie:**
- Je ziet: `Local: http://localhost:5173`
- Open in browser: `http://localhost:5173`
- Je zou de Neuroion setup interface moeten zien

**📝 Environment Variables (Optioneel):**
Als je Telegram bot username hebt, voeg toe aan `.env`:
```bash
VITE_TELEGRAM_BOT_USERNAME=your_bot_username
```

---

### Stap 6: Telegram Bot Configureren (Optioneel)

De Telegram bot start **automatisch** met de Homebase als credentials zijn geconfigureerd. Je hoeft geen apart proces te starten!

**Configureer environment variables:**

```bash
# Stel environment variables in (voordat je de Homebase start)
export TELEGRAM_BOT_TOKEN=your_telegram_bot_token
export TELEGRAM_BOT_USERNAME=your_bot_username  # Optioneel, voor QR pairing
```

Of voeg toe aan een `.env` bestand in de project root:
```bash
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_BOT_USERNAME=your_bot_username
```

**✅ Verificatie:**
- Bij Homebase startup zie je: `✅ Telegram bot started successfully`
- Test door een bericht te sturen naar je bot in Telegram
- Gebruik `/start` of `/pair <code>` om te koppelen

**📝 Bot Token Verkrijgen:**
1. Praat met [@BotFather](https://t.me/botfather) op Telegram
2. Gebruik `/newbot` om een nieuwe bot aan te maken
3. Kopieer de token die BotFather geeft

**⚠️ Opmerking:** Als `TELEGRAM_BOT_TOKEN` niet is ingesteld, start de bot niet en draait de Homebase normaal door.

---

## 🧪 Testen

### Health Check
```bash
curl http://localhost:8000/health
```

### API Test Script
```bash
# Navigeer naar project root
cd /Users/karelgustin/Neuroion/Neuroion

# Run het demo test script
./test_demo.sh
```

### Handmatige API Test
```bash
# 1. Vraag een pairing code aan
curl -X POST http://localhost:8000/api/pairing/request \
  -H "Content-Type: application/json" \
  -d '{"household_id": 1}'

# 2. Gebruik de pairing code om te koppelen
curl -X POST http://localhost:8000/api/pairing/confirm \
  -H "Content-Type: application/json" \
  -d '{"pairing_code": "YOUR_CODE", "device_id": "test-device", "device_type": "ios"}'

# 3. Stuur een chat bericht (gebruik de token uit stap 2)
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"message": "Hallo, wat is het weer vandaag?"}'
```

---

## 📊 Overzicht: Welke Terminal voor Wat?

Voor een volledige setup heb je **2-3 terminals** nodig:

| Terminal | Commando | Doel |
|----------|----------|------|
| **Terminal 1** | `ollama serve` | Ollama LLM service |
| **Terminal 2** | `python3 -m neuroion.core.main` | Homebase API server (+ Telegram bot als geconfigureerd) |
| **Terminal 3** | `npm run dev` (in setup-ui/) | Setup UI interface (optioneel) |

---

## 🖥️ Kiosk (7" scherm / Core unit)

Op een vast scherm (bijv. 7" touchscreen) kun je de Setup UI in **kioskmodus** openen:

1. **Startvolgorde:** Start eerst Ollama, dan de Homebase API, dan de Setup UI (bijv. `npm run dev` in `setup-ui/`).
2. **Kiosk-URL:** Open in de browser (of via het script in `infra/kiosk/`):  
   `http://localhost:5173/?kiosk=1`  
   (Vervang 5173 door de poort waarop de Setup UI draait als die anders is.)
3. **Gedrag:**
   - **Setup nog niet klaar:** Het scherm toont alleen een grote **QR-code**. Scan deze met je telefoon om de setup-wizard te openen en daar te voltooien.
   - **Setup klaar:** Het scherm toont het **core dashboard**: verbindingsstatus, ledenlijst, knop “+ Add member” (opent QR voor onboarding), aantal Neuroion Requests, en optie om leden te verwijderen.

Zie `infra/kiosk/README.md` voor het kiosk-script en opties voor automatisch starten.

---

## 🛑 Stoppen

Om alles netjes te stoppen:

```bash
# Stop Homebase server (stopt ook Telegram bot): Ctrl+C in Terminal 2

# Stop Setup UI: Ctrl+C in Terminal 3

# Stop Ollama: Ctrl+C in Terminal 1
```

Of stop alle processen op poort 8000:
```bash
kill $(lsof -ti:8000)
```

---

## 🔍 Troubleshooting

### "ModuleNotFoundError: No module named 'neuroion'"
- Zorg dat je in de project root bent: `/Users/karelgustin/Neuroion/Neuroion`
- Check of je Python dependencies hebt geïnstalleerd

### "Address already in use" op poort 8000
```bash
# Zoek en stop het proces
lsof -ti:8000 | xargs kill
```

### Ollama connection errors
- Check of Ollama draait: `curl http://localhost:11434/api/tags`
- Check of het model geïnstalleerd is: `ollama list`
- Start Ollama: `ollama serve`

### Telegram bot werkt niet
- Check of `TELEGRAM_BOT_TOKEN` is ingesteld (bot start alleen als token aanwezig is)
- Check of je `✅ Telegram bot started successfully` ziet in de Homebase logs
- Check of de Homebase server draait
- Verifieer de bot token met BotFather
- Check de Homebase logs voor Telegram bot errors

---

## 📝 Quick Reference

**Minimale start (alleen Homebase):**
```bash
# Terminal 1: Ollama
ollama serve

# Terminal 2: Homebase
cd /Users/karelgustin/Neuroion/Neuroion
python3 -m neuroion.core.main
```

**Volledige start (alles):**
```bash
# Terminal 1: Ollama
ollama serve

# Terminal 2: Homebase (+ Telegram bot als geconfigureerd)
cd /Users/karelgustin/Neuroion/Neuroion
export TELEGRAM_BOT_TOKEN=your_token  # Optioneel
export TELEGRAM_BOT_USERNAME=your_bot_username  # Optioneel
python3 -m neuroion.core.main

# Terminal 3: Setup UI (optioneel)
cd /Users/karelgustin/Neuroion/Neuroion/setup-ui
npm run dev
```

---

## 🎯 Volgende Stappen

Na het starten:

1. **Pairing:** Gebruik de Setup UI of Telegram bot om een device te koppelen
2. **Chat:** Stuur berichten via Telegram of de API
3. **Monitor:** Check de Setup UI voor status en pairing codes
4. **iOS App:** Gebruik de iOS app om te koppelen en te chatten

Voor meer informatie, zie:
- `README.md` - Algemene documentatie
- `docs/API.md` - API documentatie
- `docs/ARCHITECTURE.md` - Architectuur overzicht
