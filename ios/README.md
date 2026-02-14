# Neuroion iOS App

Chat-frontend voor Neuroion (zoals ChatGPT/Ollama): praat met je Homebase-agent, ontvang antwoorden en bevestig acties (bijv. cronjobs) met één tik.

## Vereisten

- Xcode 15+ (op macOS)
- iOS 16+ (voor deployment op je iPhone)
- Neuroion Homebase draait ergens bereikbaar (lokaal netwerk of server)

## Quick start: project genereren en bouwen (aanbevolen)

Vanuit de **repo-root** (waar `package.json` staat):

1. **Eenmalig:** installeer XcodeGen of Mint (voor projectgeneratie):
   ```bash
   brew install xcodegen
   ```
   Of: `brew install mint` — dan haalt het script XcodeGen automatisch op bij de eerste run.

2. **Genereren en bouwen:**
   ```bash
   npm run ios
   ```
   Dit genereert `ios/Neuroion.xcodeproj` uit `ios/project.yml` en bouwt de app. Daarna kun je in Xcode `ios/Neuroion.xcodeproj` openen, je Team kiezen bij Signing, en op je iPhone runnen.

   Alleen het project opnieuw genereren (zonder build): `npm run generate:ios`.

## Project handmatig in Xcode opzetten

1. **Nieuw iOS-appproject maken**
   - Open Xcode → **File → New → Project**
   - Kies **iOS → App**
   - Product Name: `NeuroionApp` (of anders, maar dan overal consistent)
   - Team: kies je Apple ID (voor deployment op je eigen device)
   - Organization Identifier: bijv. `com.jouwnaam.neuroion`
   - Interface: **SwiftUI**
   - Language: **Swift**
   - Storage: geen Core Data
   - Klik **Next**, kies een map en maak het project aan.

2. **Bronbestanden toevoegen**
   - Verwijder in het project de standaard `ContentView.swift` die Xcode heeft aangemaakt (rechtermuisklik → Delete → Move to Trash). Als het template ook een `NeuroionApp.swift` (of *App.swift) heeft, verwijder die ook of vervang de inhoud door de versie uit deze repo—er mag maar één `@main` entry point zijn.
   - In de Project Navigator: rechtermuisklik op de **NeuroionApp**-groep (het gele icoon) → **Add Files to "NeuroionApp"...**
   - Navigeer naar de map **NeuroionApp** in deze `ios`-folder.
   - Selecteer de **gehele NeuroionApp-map** (met daarin o.a. `NeuroionApp.swift`, `Assets.xcassets`, `Models/`, `Services/`, `Views/`).
   - Zet **Copy items if needed** uit (we gebruiken de bestanden op de huidige locatie).
   - Zorg dat **Add to targets: NeuroionApp** is aangevinkt.
   - Klik **Add**.

3. **Info.plist koppelen**
   - Selecteer het project (blauw icoon) in de navigator → selecteer het **NeuroionApp** target.
   - Tab **Build Settings** → zoek op "Info.plist".
   - Bij **Generate Info.plist File** kun je op **No** zetten als je de onze wilt gebruiken.
   - Bij **Info.plist File** vul je in: `NeuroionApp/Info.plist` (of het relatieve pad naar de Info.plist binnen je target, afhankelijk van hoe de map heet in Xcode).
   - De meegeleverde **Info.plist** staat HTTP toe voor je Homebase (lokaal netwerk en development).

4. **App-icoon (optioneel)**
   - Plaats je app-icoon in: **NeuroionApp/Assets.xcassets/AppIcon.appiconset/**.
   - Gebruik één PNG van **1024×1024 px** (geen transparantie) en noem het bestand **Icon-App-1024x1024.png**. Xcode maakt daaruit automatisch alle andere formaten voor het home-scherm.
   - Of: open in Xcode **Assets.xcassets → AppIcon** en sleep daar je 1024×1024-afbeelding naar het vak "App Store iOS".

5. **Op je iPhone deployen**
   - Sluit je iPhone aan en kies hem als run destination (bovenin Xcode).
   - Bij het eerst bouwen: **Signing & Capabilities** → kies je **Team** (je Apple ID). Xcode regelt een gratis development certificate.
   - Op de iPhone: **Instellingen → Algemeen → VPN & apparaatbeheer** → vertrouw je development certificate als dat gevraagd wordt.
   - In Xcode: **Product → Run** (of ⌘R). De app wordt geïnstalleerd en opent op je iPhone.

## Verbinding instellen in de app

1. **Eerste keer (niet gekoppeld)**
   - Open de app → je komt op het **Pairing**-scherm.
   - **Homebase URL**: vul het adres in van je Neuroion-server, bijv.:
     - Op je Mac op hetzelfde netwerk: `http://192.168.x.x:8000` (vervang door het IP van je Mac; poort 8000).
     - Op een Raspberry Pi: `http://192.168.x.x:8000` of `http://neuroion.local:8000` als je mDNS hebt.
   - **Pairing code**: start op je computer de Setup UI, maak daar een pairing code aan (of gebruik de bestaande flow), en voer die 6-cijferige code hier in.
   - Tik op **Pair Device**. Na succes ga je naar het Chat-scherm.

2. **URL later wijzigen**
   - In de app: **Chat → tandwiel (Settings)**.
   - Onder **Connection** kun je de **Homebase URL** aanpassen en daarna opnieuw koppelen indien nodig.

## Chat gebruiken

- Typ een bericht en stuur het; je krijgt een antwoord van de agent (zoals bij ChatGPT/Ollama).
- Als de agent een actie voorstelt (bijv. een cronjob), verschijnt er een kaart met **Uitvoeren**. Tik daarop → bevestig in de dialoog → de actie wordt uitgevoerd en je ziet het resultaat.

## Troubleshooting

- **"The item at … is not a valid bundle" / "Ensure that your bundle's Info.plist contains a value for the CFBundleIdentifier key"**: De gebouwde app mist een geldige CFBundleIdentifier. Doe het volgende:
  1. **Info.plist in je Xcode-project vervangen**  
     Als je project ergens anders staat (bijv. Bureaublad), kopieer de juiste plist erheen. Vanuit de **repo-root**:
     ```bash
     bash ios/scripts/copy-info-plist.sh "$HOME/Desktop/NeuroionApp/Neuroion One"
     ```
     (Dat kopieert naar `…/Neuroion One/NeuroionApp/Info.plist`. Pas het pad aan als je project ergens anders staat.)
  2. **Info.plist uit Copy Bundle Resources halen**  
     Xcode → target "Neuroion One" → **Build Phases** → **Copy Bundle Resources** → **Info.plist** verwijderen (−). Anders overschrijft een kopie de verwerkte plist.
  3. **Build Settings controleren**  
     **Build Settings** → zoek "Info.plist" → **Info.plist File** moet wijzen naar `NeuroionApp/Info.plist`; **Generate Info.plist File** = **No**.
  4. **Schoon opnieuw bouwen**  
     **Product → Clean Build Folder**, daarna **Product → Run** op je iPhone.
- **"Multiple commands produce ... Info.plist"**: Twee buildstappen schrijven naar dezelfde Info.plist. Oplossing: in Xcode → project (blauw icoon) → target (bijv. "Neuroion One") → tab **Build Phases** → **Copy Bundle Resources**. Verwijder **Info.plist** uit deze lijst (selecteer en klik op −). De Info.plist wordt al via Build Settings → Info.plist File verwerkt; die mag niet ook gekopieerd worden.
- **"Cannot find VPNTunnelManager in scope"**: De app-target moet alle Swift-bestanden uit `NeuroionApp` bevatten. **Oplossing:** Genereer het project opnieuw met `npm run generate:ios` (vanuit de repo-root), of voeg in Xcode handmatig toe: target NeuroionOne → **Build Phases** → **Compile Sources** → + → kies `VPNTunnelManager.swift`.
- **"Invalid URL" / geen verbinding**: Controleer of de Homebase URL klopt (inclusief `http://` en poort `:8000`) en of je telefoon op hetzelfde netwerk zit als de server (of dat de server van buiten bereikbaar is).
- **Geen logs in de terminal bij `npm run dev`**: De app praat met de URL die in **Instellingen → Connection** staat. Als **Use VPN tunnel** of **Use remote connection** aan staat, gaan verzoeken naar die URL (bijv. 10.66.66.1 of een Tailscale-URL), niet naar je MacBook. Om tegen je lokale server te testen: zet **Homebase URL** op het IP van je Mac (bijv. `http://192.168.178.201:8000`, zie de "Network"-regel in de `npm run dev`-output), en zet **Use VPN tunnel** en **Use remote connection** uit. Dan zie je `POST /chat/stream` in de terminal wanneer je een bericht stuurt.
- **"Invalid or expired pairing code"**: Haal een nieuwe code uit de Setup UI; codes verlopen na enkele minuten.
- **HTTP wordt geblokkeerd**: De meegeleverde Info.plist staat lokaal netwerk en arbitrary loads toe. Als je die hebt vervangen, voeg dan ten minste **App Transport Security → NSAllowsLocalNetworking = YES** toe voor een HTTP-Homebase op je netwerk.
