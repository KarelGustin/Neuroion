Neuroion — System Context
1. Doel van het project

Neuroion is een consumer-gerichte, standalone AI core die zonder technische kennis door eindgebruikers kan worden opgezet en gebruikt.
Het systeem is ontworpen als een fysiek AI-apparaat dat:

direct bruikbaar is na aanzetten

volledig lokaal kan draaien (privacy-first)

uitbreidbaar is met agents, services en externe interfaces

een brug slaat tussen lokale AI en persoonlijke communicatiekanalen

Neuroion is geen “computer met een scherm”, maar een AI appliance.

2. Hardware context

Neuroion Core (v1) bestaat uit:

Raspberry Pi 5

5-inch touchscreen (primary UI)

Raspberry Pi Camera v3

Lokale opslag (SD / SSD)

Geen verplicht extern toetsenbord of muis

De gebruiker hoeft geen scherm, toetsenbord of computerkennis te hebben om het systeem in gebruik te nemen.

3. Kernconcept: dual-interface systeem

Neuroion heeft twee gelijktijdige interfaces, elk met een eigen rol:

3.1 Touchscreen UI (Device UI)

Draait altijd lokaal op de Pi

Is leidend bij boot, status en feedback

Wordt gebruikt voor:

bootanimatie

systeemstatus

netwerkstatus (hotspot / wifi)

QR-codes

minimale interactie (confirmaties, status)

Dit scherm is niet bedoeld voor langdurige configuratie of complexe input.

3.2 Web UI (User Device UI)

Wordt geopend op het eigen apparaat van de gebruiker (telefoon, laptop)

Is bereikbaar via:

lokale hotspot (Neuroion Core)

QR-code vanaf het touchscreen

Is de primaire onboarding- en configuratie-omgeving

Alle complexiteit gebeurt hier, niet op het kleine scherm.

4. Eerste gebruikerservaring (Workflow)
4.1 Boot & eerste indruk

Gebruiker zet Neuroion aan

Touchscreen toont:

bootanimatie

“Neuroion Core is starting…”

Na boot:

duidelijke statusweergave

geen technische logs

geen Linux-desktop

De ervaring moet voelen als:

“Dit is een product, geen Raspberry Pi.”

4.2 Hotspot-fase (Initial Access)

Na boot:

Neuroion start automatisch een Wi-Fi hotspot

SSID: Neuroion Core

Touchscreen toont:

hotspotnaam

eenvoudige instructie (“Connect to Neuroion Core”)

QR-code naar de lokale webpagina

Gebruiker:

verbindt met de hotspot

scant de QR-code

komt terecht op een localhost-hosted onboarding page

5. Onboarding wizard (Neuroion Agent)
5.1 Rol van de onboarding

De onboarding wizard is de belangrijkste software-component van Neuroion.

Deze wizard vervangt:

terminalcommando’s

configuratiebestanden

CLI-flows van OpenClaw

Door:

een consumer-friendly flow

met uitleg, keuzes en defaults

gestuurd door een Neuroion agent

5.2 Integratie van OpenClaw

OpenClaw wordt niet verwijderd, maar:

de CLI-wizard van OpenClaw wordt vertaald naar UI-stappen

alle acties die normaal in de terminal gebeuren:

installatie

agent setup

service binding

LLM selectie
gebeuren via de onboarding wizard

Conceptueel:

Neuroion Agent = UI-laag bovenop OpenClaw

De gebruiker hoeft niet te weten wat OpenClaw is.

6. Default configuratie (opinioned, maar aanpasbaar)
6.1 LLM

Default LLM:

Ollama 3.2 3B

lokaal geïnstalleerd

privacy-first

Andere LLM’s kunnen later worden toegevoegd per member / service

6.2 Chat / messaging

Default chat interface: Telegram

Telegram-integratie is:

actief

primair kanaal voor interactie

Eigen Telegram-functionaliteit van Neuroion:

niet verwijderd

maar niet standaard zichtbaar

optioneel / advanced / later te activeren

7. Netwerkconfiguratie (cruciaal onderdeel van onboarding)

Tijdens de onboarding wizard moet de gebruiker:

Een externe Wi-Fi kunnen selecteren

Wachtwoord invoeren

Neuroion laten verbinden met internet

Waarom:

Telegram messages moeten van buitenaf kunnen binnenkomen

toekomstige services vereisen externe connectiviteit

Belangrijk:

de hotspot blijft beschikbaar als fallback

netwerkstatus wordt altijd op het touchscreen getoond

8. Services & members (latere extensie)

Na onboarding:

services (LLM’s, agents, tools) kunnen:

per member

per use-case
worden toegevoegd

De onboarding zelf:

focust op core-functionaliteit

geen overload aan keuzes

“advanced” pas later

9. Filosofie & UX-principes

Neuroion volgt deze principes:

Local-first

Privacy-first

No terminal exposure

Physical device ≠ computer

Small screen = status, not complexity

User’s phone = configuratie & control

Defaults > endless options

De gebruiker moet nooit denken:

“Ik moet Linux begrijpen.”

10. Samenvatting in één zin

Neuroion is een fysieke AI-core die zichzelf presenteert als een consumentenproduct, maar intern een krachtige, uitbreidbare agent-architectuur draait — volledig lokaal, privacy-gericht en zonder terminal-interactie voor de eindgebruiker.