# TUR — Turbie User Repository

<div align="center">

![Turbie Linux](https://img.shields.io/badge/Turbie-Linux-00d4ff?style=for-the-badge&logo=linux&logoColor=white)
![Packages](https://img.shields.io/badge/dynamic/json?url=https://turbieuserepo.netlify.app/TUR.json&query=$.stats.total&label=Packages&color=8b5cf6&style=for-the-badge)
![Approved](https://img.shields.io/badge/dynamic/json?url=https://turbieuserepo.netlify.app/TUR.json&query=$.stats.approved&label=Approved&color=10b981&style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)

**Community-driven package repository for Turbie Linux**

[🌐 Website](https://turbieuserepo.netlify.app) · [📦 Browse Packages](https://turbieuserepo.netlify.app#packages) · [📖 Contribute](#contributing) · [📚 Docs](https://docs.turbie.org)

</div>

---

## What is TUR?

TUR (Turbie User Repository) is the official community package repository for [Turbie Linux](https://github.com/Natarizki/turbie-linux). Think of it like the AUR for Arch Linux, but built specifically for Turbie.

Anyone can submit packages. Maintainers review and approve them. Once approved, users can install them directly via `tpm-repo`.

```bash
# Search a package
tpm-repo search firefox

# Install a package
tpm-repo install firefox

# Vote for a package
tpm-repo vote firefox
```

---

## Package Stats

| Stat | Count |
|------|-------|
| Total Packages | See [website](https://turbieuserepo.netlify.app) |
| Approved | ✅ Ready to install |
| Pending | ⏳ Awaiting review |

---

## How to Install a Package

Make sure you're inside Turbie Linux, then:

```bash
# Update TUR database
tpm-repo update

# Search
tpm-repo search <query>

# Install
tpm-repo install <package>

# List installed TUR packages
tpm-repo list

# Show package info
tpm-repo info <package>
```

---

## Contributing

Want to add a package? Follow these steps:

### 1. Fork this repository
```
https://github.com/Natarizki/TurbieUserRepository-TUR/fork
```

### 2. Create your package directory
```bash
mkdir -p packages/<your-package-name>
```

### 3. Write a TURBUILD file

```ini
[meta]
name        = my-package
version     = 1.0.0
release     = 1
arch        = aarch64,x86_64
description = Short description of your package
license     = MIT
url         = https://example.com
maintainer  = your-github-username
build_type  = deb

[deps]
depends     = libc,bash

[source]
url         = https://example.com/source.tar.gz
sha256      = abc123...

[build]
configure() {
  ./configure --prefix=/usr
}

compile() {
  make -j$(nproc)
}

package() {
  make DESTDIR="$PKGDIR" install
}
```

### build_type options

| Type | Description |
|------|-------------|
| `deb` | Repackage from Debian bookworm (fastest) |
| `source` | Compile from source using TURBUILD |

### 4. Submit a Pull Request

- Title: `Add package: <name>`
- Description: What the package does and why it's useful for Turbie users

### 5. Wait for review

Our bot will automatically:
- ✅ Validate your TURBUILD syntax
- 🔒 Run security scan
- 🔨 Build test on aarch64 + x86_64

A maintainer will then review and approve/reject your submission.

---

## Package Rules

- ❌ No malware or malicious code
- ❌ No duplicate packages (check first!)
- ✅ Must have a valid open source license
- ✅ Source URLs must use HTTPS
- ✅ Must be useful to Turbie Linux users
- ✅ Package name must be lowercase, alphanumeric

---

## Repository Structure

```
TUR/
├── .github/
│   └── workflows/
│       ├── build-repo.yml    ← Auto-build .tpkg on PR merge
│       └── review.yml        ← Validate + notify maintainers
├── packages/
│   └── <package-name>/
│       ├── TURBUILD          ← Package definition
│       └── *.tpkg            ← Built binaries (auto-generated)
├── scripts/
│   ├── deb-to-tpkg.sh        ← Debian → .tpkg converter
│   ├── gen-index.py          ← Regenerate TUR.json
│   └── validate-turbuild.py  ← TURBUILD validator
├── website/
│   └── index.html            ← TUR website
├── TUR.json                  ← Package database
├── CONTRIBUTING.md           ← Contribution guide
└── netlify.toml              ← Netlify deploy config
```

---

## CI/CD Pipeline

Every PR submission goes through:

```
Submit PR
    ↓
Bot validates TURBUILD
    ↓
Security scan
    ↓
Maintainer review
    ↓
Merge → Auto-build (aarch64 + x86_64)
    ↓
TUR.json updated
    ↓
Website auto-deploys
```

---

## Self-hosted Runner (Fallback)

If GitHub Actions is unavailable, builds fall back to our self-hosted runner. To set up your own:

```bash
# In Turbie Linux
tpm install github-runner
github-runner install --url https://github.com/Natarizki/TurbieUserRepository-TUR
github-runner start
```

---

## License

MIT License — see [LICENSE](LICENSE)

---

<div align="center">

Made with ❤️ for **Turbie Linux**

[turbieuserepo.netlify.app](https://turbieuserepo.netlify.app)

</div>

