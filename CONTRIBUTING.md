# Contributing to TUR

TUR (Turbie User Repository) is the community package repository for Turbie Linux.

## How to Submit a Package

### 1. Fork the repository
```
https://github.com/turbie-linux/TUR/fork
```

### 2. Create your package directory
```bash
mkdir -p packages/<your-package>
```

### 3. Write a TURBUILD file
```
packages/<your-package>/TURBUILD
```

### TURBUILD Format

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
build_type  = deb     # or: source

[deps]
depends     = libc,bash
makedepends = gcc,make

[source]
url         = https://example.com/source.tar.gz
sha256      = abc123...
# Optional: pre-built binary
binary_url  = https://example.com/binary.tpkg
binary_sha256 = abc123...

[build]
# Only needed for build_type=source
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
- `deb` — Repackage from Debian bookworm (fastest, most packages)
- `source` — Compile from source using TURBUILD functions

### 4. Submit Pull Request
- Title: `Add package: <name>`
- Description: What the package does and why it's useful

### 5. Wait for review
Maintainers will review your submission. The bot will automatically:
- Validate your TURBUILD
- Run security scan
- Build test on aarch64 + x86_64

## Rules
- No malware or malicious code
- No duplicate packages (check existing ones first)
- Package must be useful to Turbie Linux users
- Must have a valid open source license
- Source URLs must use HTTPS

## Questions?
Open an issue or join the Turbie Discord.
