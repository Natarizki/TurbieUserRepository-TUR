#!/bin/bash
# scripts/deb-to-tpkg.sh — Convert Debian .deb to Turbie .tpkg
# Usage: deb-to-tpkg.sh <package-name> <arch> <output-dir>

set -euo pipefail

PKG_NAME="$1"
ARCH="$2"
OUTPUT_DIR="$3"
DEBIAN_SUITE="${DEBIAN_SUITE:-bookworm}"
DEBIAN_MIRROR="${DEBIAN_MIRROR:-http://deb.debian.org/debian}"

C='\033[36m'; G='\033[32m'; Y='\033[33m'; R='\033[31m'; N='\033[0m'

info()    { echo -e "${C}[deb2tpkg]${N} $*"; }
success() { echo -e "${G}[✓]${N} $*"; }
warn()    { echo -e "${Y}[!]${N} $*"; }
die()     { echo -e "${R}[✗]${N} $*"; exit 1; }

# Map Turbie arch to Debian arch
case "$ARCH" in
  aarch64|arm64) DEB_ARCH="arm64" ;;
  x86_64|amd64)  DEB_ARCH="amd64" ;;
  *)              DEB_ARCH="$ARCH" ;;
esac

WORK_DIR=$(mktemp -d)
trap "rm -rf $WORK_DIR" EXIT

info "Converting $PKG_NAME ($DEB_ARCH) from Debian $DEBIAN_SUITE..."

# ── Step 1: Download .deb ──────────────────────
info "Downloading from Debian mirror..."

# Get package URL from apt
apt-get download --print-uris \
  -o APT::Architecture="$DEB_ARCH" \
  "$PKG_NAME" 2>/dev/null | head -1 > "$WORK_DIR/uri.txt" || true

DEB_URL=$(cat "$WORK_DIR/uri.txt" | grep -o "'.*'" | tr -d "'" || true)

if [ -z "$DEB_URL" ]; then
  # Fallback: search debian packages directly
  info "Searching Debian package pool..."
  DEB_URL=$(curl -fsSL \
    "https://packages.debian.org/${DEBIAN_SUITE}/${DEB_ARCH}/${PKG_NAME}/download" \
    2>/dev/null | grep -o "http[s]*://[^\"']*\.deb" | head -1 || true)
fi

[ -n "$DEB_URL" ] || die "Could not find $PKG_NAME for $DEB_ARCH in Debian $DEBIAN_SUITE"

info "URL: $DEB_URL"
wget -q "$DEB_URL" -O "$WORK_DIR/${PKG_NAME}.deb" \
  || curl -fsSL "$DEB_URL" -o "$WORK_DIR/${PKG_NAME}.deb" \
  || die "Download failed"

# ── Step 2: Extract .deb ──────────────────────
info "Extracting .deb..."
mkdir -p "$WORK_DIR/extract" "$WORK_DIR/pkg"

cd "$WORK_DIR/extract"
ar x "$WORK_DIR/${PKG_NAME}.deb"

# Extract data archive
if [ -f data.tar.xz ]; then
  tar -xJf data.tar.xz -C "$WORK_DIR/pkg"
elif [ -f data.tar.gz ]; then
  tar -xzf data.tar.gz -C "$WORK_DIR/pkg"
elif [ -f data.tar.zst ]; then
  tar -I zstd -xf data.tar.zst -C "$WORK_DIR/pkg"
else
  die "Unknown data archive format"
fi

# Extract control info
if [ -f control.tar.xz ]; then
  tar -xJf control.tar.xz -C "$WORK_DIR/control"
elif [ -f control.tar.gz ]; then
  tar -xzf control.tar.gz -C "$WORK_DIR/control"
fi

# ── Step 3: Parse debian control ──────────────
info "Parsing package metadata..."
CONTROL_FILE="$WORK_DIR/control/control"
mkdir -p "$WORK_DIR/control"
[ -f "$CONTROL_FILE" ] || tar -xf "$WORK_DIR/extract/control.tar."* -C "$WORK_DIR/control" 2>/dev/null || true

parse_control() {
  grep "^${1}:" "$CONTROL_FILE" 2>/dev/null | head -1 | cut -d: -f2- | xargs || echo ""
}

PKG_VERSION=$(parse_control "Version")
PKG_DESC=$(parse_control "Description")
PKG_DEPENDS=$(parse_control "Depends" | sed 's/ ([^)]*),*/,/g' | tr -d ' ')
PKG_MAINTAINER=$(parse_control "Maintainer")
PKG_HOMEPAGE=$(parse_control "Homepage")
PKG_LICENSE=$(parse_control "License" || echo "see-debian")

# Convert debian version to turbie version (remove epoch)
TURBIE_VERSION=$(echo "$PKG_VERSION" | sed 's/^[0-9]*://')

# ── Step 4: Create .tpkg metadata ─────────────
info "Creating .tpkg metadata..."
mkdir -p "$WORK_DIR/pkg/etc/tpm/installed/${PKG_NAME}"

cat > "$WORK_DIR/pkg/etc/tpm/installed/${PKG_NAME}/METADATA" << META
name=${PKG_NAME}
version=${TURBIE_VERSION}
arch=${ARCH}
description=${PKG_DESC}
depends=${PKG_DEPENDS}
maintainer=${PKG_MAINTAINER}
homepage=${PKG_HOMEPAGE}
license=${PKG_LICENSE}
source=debian-${DEBIAN_SUITE}
installed=$(date '+%Y-%m-%d %H:%M:%S')
META

# ── Step 5: Pack as .tpkg ─────────────────────
info "Packing .tpkg..."
mkdir -p "$OUTPUT_DIR"
TPKG_NAME="${PKG_NAME}-${TURBIE_VERSION}-${ARCH}.tpkg"
TPKG_PATH="$OUTPUT_DIR/$TPKG_NAME"

tar --exclude="./etc/tpm" \
    -czf "$TPKG_PATH" \
    -C "$WORK_DIR/pkg" \
    . \
    2>/dev/null

# Add metadata separately
tar -czf "$OUTPUT_DIR/${PKG_NAME}-${TURBIE_VERSION}-${ARCH}-meta.tpkg" \
    -C "$WORK_DIR/pkg" \
    "./etc/tpm/installed/${PKG_NAME}" \
    2>/dev/null || true

# ── Step 6: Checksums ─────────────────────────
sha256sum "$TPKG_PATH" | cut -d' ' -f1 > "${TPKG_PATH}.sha256"
SIZE=$(du -sb "$TPKG_PATH" | cut -f1)

# ── Step 7: Update package entry in TUR.json ──
info "Updating package index..."
python3 - << PYEOF
import json, os, sys
from datetime import datetime

tur_json = "TUR.json"
try:
    with open(tur_json) as f:
        db = json.load(f)
except:
    db = {"meta": {}, "stats": {}, "packages": {}}

sha256 = open("${TPKG_PATH}.sha256").read().strip()

pkg_entry = db["packages"].get("${PKG_NAME}", {
    "name": "${PKG_NAME}",
    "votes": 0,
    "status": "approved",
    "submitted": datetime.utcnow().isoformat() + "Z",
    "source": "debian-${DEBIAN_SUITE}"
})

pkg_entry.update({
    "version": "${TURBIE_VERSION}",
    "description": "${PKG_DESC}",
    "depends": "${PKG_DEPENDS}".split(",") if "${PKG_DEPENDS}" else [],
    "license": "${PKG_LICENSE}",
    "homepage": "${PKG_HOMEPAGE}",
    "updated": datetime.utcnow().isoformat() + "Z",
    "binaries": pkg_entry.get("binaries", {})
})

pkg_entry["binaries"]["${ARCH}"] = {
    "url": "packages/${PKG_NAME}/${TPKG_NAME}",
    "sha256": sha256,
    "size": ${SIZE}
}

db["packages"]["${PKG_NAME}"] = pkg_entry

# Update stats
db["stats"]["total"] = len(db["packages"])
db["stats"]["approved"] = sum(1 for p in db["packages"].values() if p.get("status") == "approved")
db["stats"]["pending"] = sum(1 for p in db["packages"].values() if p.get("status") == "pending")

with open(tur_json, "w") as f:
    json.dump(db, f, indent=2)

print(f"✓ Updated TUR.json: {pkg_entry['name']} {pkg_entry['version']}")
PYEOF

SIZE_HUMAN=$(du -sh "$TPKG_PATH" | cut -f1)
success "$PKG_NAME-$TURBIE_VERSION-$ARCH.tpkg ($SIZE_HUMAN)"
