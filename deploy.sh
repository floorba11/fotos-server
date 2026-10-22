#!/usr/bin/env bash
# Läuft auf dem Server in ~/fotos: Galerie starten und beim Caddy des Portals (~/unihockey) eintragen.
# Wird von der GitHub Action aufgerufen, geht aber auch von Hand: bash deploy.sh
set -euo pipefail
cd "$(dirname "$0")"

[ -f .env ] || { echo ".env fehlt – Vorlage: env.example"; exit 1; }
set -a; . ./.env; set +a
# IMMICH_DOMAIN: Adresse der Immich-Verwaltung (früher FOTOS_DOMAIN; die öffentliche Seite ist das Projekt fotos-web)
IMMICH_DOMAIN="${IMMICH_DOMAIN:-${FOTOS_DOMAIN:-}}"
[ -n "$IMMICH_DOMAIN" ] || { echo "IMMICH_DOMAIN fehlt in .env"; exit 1; }
mountpoint -q /mnt/fotos || { echo "/mnt/fotos ist nicht eingehängt – storagebox-einhaengen.sh ausführen"; exit 1; }
docker network inspect web >/dev/null 2>&1 || { echo "Netzwerk 'web' fehlt – zuerst das Portal in ~/unihockey starten"; exit 1; }

docker compose up -d --remove-orphans

# Caddy des Portals bedient die Domain und liest ~/unihockey/sites/*.caddy
mkdir -p ../unihockey/sites
rm -f ../unihockey/sites/fotos.caddy   # alter Name, sonst doppelte Adresse
cat > ../unihockey/sites/immich.caddy <<CADDY
$IMMICH_DOMAIN {
	reverse_proxy immich-server:2283
}
CADDY
(cd ../unihockey && docker compose exec -T caddy caddy reload --config /etc/caddy/Caddyfile)
echo "Immich läuft: https://$IMMICH_DOMAIN"
