# Fotos – Spieltagsgalerie mit Gesichtserkennung

Eigenes Projekt neben dem Liveticker ([unihockey-portal](https://github.com/floorba11/unihockey-portal)), auf demselben
Hetzner-Server. Die Galerie ist [Immich](https://immich.app) (Docker Compose). Die Originalfotos liegen auf einer
Hetzner Storage Box, Immich liest sie als externe Bibliothek und gruppiert die Gesichter nach Personen.

```
Internet → Caddy (Portal, ~/unihockey) ─┬─ liveticker-Domain → web
                                         └─ FOTOS_DOMAIN      → immich-server:2283 (Netzwerk "web")
/mnt/fotos (Storage Box, SMB, nur lesend) → Immich "externe Bibliothek" /external/fotos
```

| Datei | Zweck |
|---|---|
| `docker-compose.yml` | Immich (Server, Machine Learning, Valkey, Postgres) |
| `env.example` | Vorlage für `~/fotos/.env` |
| `storagebox-einhaengen.sh` | Storage Box dauerhaft unter `/mnt/fotos` einhängen |
| `deploy.sh` | startet Immich und trägt die Domain beim Caddy des Portals ein |
| `.github/workflows/deploy.yml` | kopiert die Dateien per SSH auf den Server und ruft `deploy.sh` auf |

## Auf dem gleichen Server wie der Liveticker

Immich läuft hier neben dem Portal auf einem kleinen Server (Hetzner CX23: 2 vCPU, 4 GB RAM, 40 GB Disk). Das funktioniert,
ist aber knapp:

- `docker-compose.yml` begrenzt Immich auf rund 3 GB RAM und der Gesichtserkennung auf 1 CPU. Das Portal und die 2 GB Swap
  bleiben als Puffer.
- Ein grosser Foto-Scan (hunderte Bilder) dauert lange und macht den Server träge. Starte ihn nicht kurz vor oder während
  eines Spieltags mit Liveticker.
- In Immich unter *Administration → Jobs* die gleichzeitigen Jobs auf 1 stellen (Gesichtserkennung, Vorschaubilder).
- Die 40 GB Disk reichen nicht für Originale. Sie liegen deshalb auf der Storage Box.
- Wird es zu eng (Portal wird langsam, `docker stats` zeigt Swap-Nutzung), den Server in der Hetzner-Konsole vergrössern.

## Einrichten (einmalig)

Voraussetzung: Das Portal läuft schon in `~/unihockey` (es legt das Netzwerk `web` an und bedient Caddy).

1. **Storage Box** (BX11) bestellen. In der Hetzner-Konsole *Samba-Support* und *Externe Erreichbarkeit* einschalten.
2. **DNS**: A-Eintrag der Fotos-Subdomain auf die Server-IP. Bei Cloudflare den Eintrag auf *DNS only* (graue Wolke)
   stellen, sonst begrenzt Cloudflare Uploads auf 100 MB.
3. Auf dem Server `~/fotos` anlegen und einhängen:
   ```bash
   mkdir -p ~/fotos && cd ~/fotos      # Dateien kommen beim ersten Deploy, oder von Hand per scp
   bash storagebox-einhaengen.sh u123456 u123456.your-storagebox.de
   cp env.example .env && nano .env    # FOTOS_DOMAIN und DB_PASSWORD setzen
   ```
4. GitHub-Secrets `VM_HOST`, `VM_USER`, `VM_SSH_KEY` in diesem Repo setzen (dieselben Werte wie beim Portal), dann
   *Actions → Deploy → Run workflow*. Oder auf dem Server: `bash deploy.sh`.
5. `https://<FOTOS_DOMAIN>` öffnen, Admin-Konto anlegen. Dann *Administration → Externe Bibliotheken*: Bibliothek anlegen,
   Import-Pfad `/external/fotos`, **Scan-Intervall** auf z.B. stündlich stellen (siehe unten).

## Spieltags-Ablauf

1. Bearbeitete JPEGs in einen Ordner pro Spiel auf die Storage Box legen, z.B. per SFTP/SMB vom Mac
   (`/mnt/fotos/2026-10-18_Team-gegen-Team/`).
2. Immich scannt die Bibliothek, erstellt Vorschauen und erkennt Gesichter. Das dauert bei hunderten Fotos auf 4 vCPUs
   eine Weile (Machine Learning läuft auf der CPU).
3. Einmalig pro Spieler: unter *Personen* dem Gesicht den Namen geben. Neue Fotos ordnet Immich danach selbst zu.

## Wichtig zu wissen

- **Kein Live-Erkennen von Änderungen auf der Storage Box.** Über SMB meldet das Dateisystem keine neuen Dateien. Darum
  das Scan-Intervall setzen oder den Scan von Hand starten (*Externe Bibliotheken → Scannen*).
- **Personen gehören einem Immich-Konto.** Ein Spieler mit eigenem Konto sieht die vom Admin benannten Personen *nicht*,
  sondern nur Alben, die mit ihm geteilt sind. „Spieler klickt auf sein Gesicht" geht also nicht direkt. Praktikabel:
  pro Spieler ein Album bzw. ein Freigabe-Link mit seinen Fotos (kann man über die Immich-API aus den benannten Personen
  automatisch erzeugen) – das ist noch nicht gebaut.
- **Uploads über die Weboberfläche** landen auf der lokalen Disk (`./library`), nicht auf der Storage Box. Für viele
  Fotos besser direkt auf die Storage Box laden.
- **Datenschutz:** Gesichtserkennung verarbeitet biometrische Daten. Für die Spieler (bei Minderjährigen die Eltern) braucht
  es eine Einwilligung, und die Galerie sollte nicht öffentlich erreichbar sein.
- **Backups:** Die Datenbank (Personen, Namen, Alben) liegt lokal in `./postgres`. Immich sichert sie täglich selbst nach
  `./library/backups`; diesen Ordner zusätzlich wegkopieren (z.B. auf die Storage Box). Die Originale auf der Storage Box
  haben sonst nur ein Exemplar – Hetzner-Snapshots der Box aktivieren.
- Updates: `IMMICH_VERSION` in `.env` erhöhen, vorher die [Release Notes](https://github.com/immich-app/immich/releases)
  lesen, dann `bash deploy.sh`.
