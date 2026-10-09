
import os
import json
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

# GRISU-CAR Einstellungen
BASE_URL = "https://www.grisu-car.eu"
LIST_URL = BASE_URL + "/feuerwehrfahrzeuge/"
DATEI = "bekannte_fahrzeuge.json"

WEBHOOK = os.environ.get("DISCORD_WEBHOOK_URL")

if not WEBHOOK:
    raise SystemExit("Discord Webhook fehlt!")

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (compatible; FahrzeugMonitor/1.0)"
})


def fahrzeuge_suchen():
    fahrzeuge = {}

    # Bis zu 12 Ergebnisseiten prüfen
    for seite in range(1, 13):
        print(f"Prüfe GRISU-CAR Seite {seite}")

        response = session.get(
            LIST_URL,
            params={"pg": seite},
            timeout=30
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        gefunden = 0

        for a in soup.select("a[href]"):
            link = urljoin(BASE_URL, a["href"])
            pfad = urlparse(link).path

            teile = [
                t for t in pfad.split("/") if t
            ]

            # Nur einzelne Fahrzeuganzeigen
            if (
                len(teile) != 2
                or teile[0] != "feuerwehrfahrzeug"
            ):
                continue

            if urlparse(link).netloc not in (
                "www.grisu-car.eu",
                "grisu-car.eu"
            ):
                continue

            titel = a.get_text(" ", strip=True)

            # Bildlinks ohne Text überspringen
            if not titel:
                continue

            link = BASE_URL + pfad.rstrip("/") + "/"
            fahrzeuge[link] = titel
            gefunden += 1

        if gefunden == 0:
            if seite == 1:
                raise RuntimeError(
                    "Keine Fahrzeuganzeigen gefunden!"
                )
            break

        time.sleep(1)

    if not fahrzeuge:
        raise RuntimeError("Keine Fahrzeuge gefunden!")

    return fahrzeuge


def discord_senden(titel, link):
    nachricht = {
        "content": (
            "🚒 **NEUES FEUERWEHRFAHRZEUG!**\n\n"
            f"**{titel[:200]}**\n\n"
            f"🔗 {link}"
        ),
        "allowed_mentions": {"parse": []}
    }

    response = requests.post(
        WEBHOOK,
        json=nachricht,
        timeout=30
    )
    response.raise_for_status()


def bekannte_laden():
    if not os.path.exists(DATEI):
        return None

    with open(DATEI, "r", encoding="utf-8") as f:
        return set(json.load(f))


def bekannte_speichern(bekannt):
    with open(DATEI, "w", encoding="utf-8") as f:
        json.dump(
            sorted(bekannt),
            f,
            indent=2,
            ensure_ascii=False
        )


def main():
    fahrzeuge = fahrzeuge_suchen()
    bekannt = bekannte_laden()

    print(f"{len(fahrzeuge)} Fahrzeuganzeigen erkannt.")

    if bekannt is None:
        bekannte_speichern(set(fahrzeuge))
        print("Erster Bestand gespeichert.")
        return

    neue = [
        (link, titel)
        for link, titel in fahrzeuge.items()
        if link not in bekannt
    ]

    if not neue:
        print("Keine neuen Anzeigen.")
        return

    for link, titel in reversed(neue):
        discord_senden(titel, link)
        bekannt.add(link)
        bekannte_speichern(bekannt)
        print("NEU:", titel)

    print(f"{len(neue)} neue Anzeigen gemeldet.")


if __name__ == "__main__":
    main()
