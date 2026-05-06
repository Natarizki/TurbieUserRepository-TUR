#!/usr/bin/env python3
# scripts/gen-index.py — Regenerate TUR.json from all packages

import json, os, glob, hashlib
from datetime import datetime

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()

def parse_turbuild(path):
    fields = {}
    current_section = None
    with open(path) as f:
        for line in f:
            line = line.rstrip()
            if not line or line.startswith('#'):
                continue
            import re
            sec = re.match(r'^\[(\w+)\]$', line)
            if sec:
                current_section = sec.group(1)
                continue
            kv = re.match(r'^(\w+)\s*=\s*(.+)$', line)
            if kv and current_section in ['meta', 'deps', 'source']:
                fields[kv.group(1)] = kv.group(2).strip()
    return fields

def main():
    # Load existing TUR.json to preserve votes/status/submitted dates
    tur_json_path = "TUR.json"
    try:
        with open(tur_json_path) as f:
            existing = json.load(f)
    except:
        existing = {"meta": {}, "stats": {}, "packages": {}}

    existing_pkgs = existing.get("packages", {})
    new_packages = {}

    # Scan all package directories
    for turbuild_path in sorted(glob.glob("packages/*/TURBUILD")):
        pkg_dir = os.path.dirname(turbuild_path)
        pkg_name = os.path.basename(pkg_dir)

        try:
            fields = parse_turbuild(turbuild_path)
        except Exception as e:
            print(f"⚠ Skipping {pkg_name}: {e}")
            continue

        name = fields.get('name', pkg_name)
        version = fields.get('version', '0.0.0')

        # Preserve existing metadata (votes, status, submitted date)
        existing_entry = existing_pkgs.get(name, {})

        entry = {
            "name": name,
            "version": version,
            "description": fields.get('description', ''),
            "license": fields.get('license', 'unknown'),
            "arch": [a.strip() for a in fields.get('arch', 'any').split(',')],
            "depends": [d.strip() for d in fields.get('depends', '').split(',') if d.strip()],
            "homepage": fields.get('url', ''),
            "maintainer": fields.get('maintainer', ''),
            "build_type": fields.get('build_type', 'source'),
            "deb_name": fields.get('deb_name', name),
            "votes": existing_entry.get('votes', 0),
            "status": existing_entry.get('status', 'pending'),
            "submitted": existing_entry.get('submitted', datetime.utcnow().isoformat() + 'Z'),
            "updated": datetime.utcnow().isoformat() + 'Z',
            "binaries": existing_entry.get('binaries', {})
        }

        # Scan for existing .tpkg binaries
        for tpkg_path in glob.glob(f"{pkg_dir}/*.tpkg"):
            if tpkg_path.endswith('-meta.tpkg'):
                continue
            filename = os.path.basename(tpkg_path)
            # Parse arch from filename: name-version-arch.tpkg
            parts = filename.replace('.tpkg', '').rsplit('-', 1)
            if len(parts) == 2:
                arch = parts[1]
                sha256_path = tpkg_path + '.sha256'
                if os.path.exists(sha256_path):
                    sha256 = open(sha256_path).read().strip().split()[0]
                else:
                    sha256 = sha256_file(tpkg_path)
                    with open(sha256_path, 'w') as f:
                        f.write(sha256)

                entry['binaries'][arch] = {
                    "url": f"packages/{name}/{filename}",
                    "sha256": sha256,
                    "size": os.path.getsize(tpkg_path)
                }

        new_packages[name] = entry
        print(f"  {'✅' if entry['status'] == 'approved' else '⏳'} {name} {version} ({entry['status']})")

    # Build final TUR.json
    approved = sum(1 for p in new_packages.values() if p.get('status') == 'approved')
    pending  = sum(1 for p in new_packages.values() if p.get('status') == 'pending')
    rejected = sum(1 for p in new_packages.values() if p.get('status') == 'rejected')

    tur_db = {
        "meta": {
            "name": "Turbie User Repository",
            "short": "TUR",
            "version": "1",
            "description": "Community package repository for Turbie Linux",
            "url": "https://tur.turbie.org",
            "maintainers": existing.get('meta', {}).get('maintainers', ['turbie-team']),
            "updated": datetime.utcnow().isoformat() + 'Z'
        },
        "stats": {
            "total": len(new_packages),
            "approved": approved,
            "pending": pending,
            "rejected": rejected
        },
        "packages": new_packages
    }

    with open(tur_json_path, 'w') as f:
        json.dump(tur_db, f, indent=2)

    print(f"\n✅ TUR.json updated: {len(new_packages)} packages ({approved} approved, {pending} pending)")

if __name__ == '__main__':
    main()
