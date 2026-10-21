#!/usr/bin/env bash
# Einmalig auf dem Hetzner-Server: Storage Box per SMB unter /mnt/fotos einhängen (dauerhaft, auch nach Neustart).
#
#   bash storagebox-einhaengen.sh u123456 u123456.your-storagebox.de
#
# Voraussetzung: In der Hetzner-Konsole (Storage Box → Einstellungen) sind "Samba-Support" und "Externe Erreichbarkeit"
# eingeschaltet. Das Passwort wird abgefragt und nur in /root/.storagebox-credentials (nur root lesbar) gespeichert.
set -euo pipefail

USER_NAME="${1:?Aufruf: bash storagebox-einhaengen.sh <u123456> <u123456.your-storagebox.de>}"
HOST="${2:?Aufruf: bash storagebox-einhaengen.sh <u123456> <u123456.your-storagebox.de>}"
MOUNT=/mnt/fotos
CREDS=/root/.storagebox-credentials

sudo apt-get update -qq && sudo apt-get install -y -qq cifs-utils

read -rsp "Passwort der Storage Box: " PW; echo
printf 'username=%s\npassword=%s\n' "$USER_NAME" "$PW" | sudo tee "$CREDS" >/dev/null
sudo chmod 600 "$CREDS"

sudo mkdir -p "$MOUNT"
# seal = SMB-Verschlüsselung (SMB 3); nofail: ein Ausfall der Box verhindert den Serverstart nicht
LINE="//$HOST/backup $MOUNT cifs credentials=$CREDS,vers=3,seal,file_mode=0644,dir_mode=0755,iocharset=utf8,_netdev,nofail 0 0"
sudo sed -i "\|[[:space:]]$MOUNT[[:space:]]|d" /etc/fstab
echo "$LINE" | sudo tee -a /etc/fstab >/dev/null
sudo systemctl daemon-reload
sudo mount "$MOUNT"

echo "Eingehängt:"
df -h "$MOUNT"
