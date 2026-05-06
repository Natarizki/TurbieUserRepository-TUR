#!/usr/bin/env python3
# scripts/validate-turbuild.py — Validate TURBUILD files
# Usage: validate-turbuild.py packages/pkg1/TURBUILD packages/pkg2/TURBUILD

import sys, re, os, json

REQUIRED_FIELDS = ["name", "version", "description", "license", "maintainer"]
OPTIONAL_FIELDS = ["url", "depends", "makedepends", "arch", "deb_name", "build_type"]
VALID_BUILD_TYPES = ["source", "deb"]
VALID_ARCHES = ["aarch64", "x86_64", "any"]
DANGEROUS_PATTERNS = [
    r"rm\s+-rf\s+/[^/]",  # rm -rf /something dangerous
    r":\(\)\{.*\}",        # fork bomb
    r"curl.*\|.*sh",       # curl pipe to sh
    r"wget.*\|.*bash",     # wget pipe to bash
    r"eval\s+.*\$\(",      # eval with subshell
    r"base64.*decode.*\|.*(sh|bash|exec)",  # encoded payload
]

class TURBUILDValidator:
    def __init__(self, filepath):
        self.filepath = filepath
        self.errors = []
        self.warnings = []
        self.info = []
        self.fields = {}

    def parse(self):
        if not os.path.exists(self.filepath):
            self.errors.append(f"File not found: {self.filepath}")
            return False

        current_section = None
        current_func = None
        func_lines = []

        with open(self.filepath) as f:
            for lineno, line in enumerate(f, 1):
                line_stripped = line.rstrip()

                # Skip comments and empty lines
                if not line_stripped or line_stripped.startswith('#'):
                    continue

                # Section header
                sec = re.match(r'^\[(\w+)\]$', line_stripped)
                if sec:
                    current_section = sec.group(1)
                    if current_section not in ['meta', 'deps', 'source', 'build']:
                        self.warnings.append(f"Line {lineno}: Unknown section [{current_section}]")
                    continue

                # Key = value
                kv = re.match(r'^(\w+)\s*=\s*(.+)$', line_stripped)
                if kv and current_section in ['meta', 'deps', 'source']:
                    key, val = kv.group(1), kv.group(2).strip()
                    self.fields[key] = val
                    continue

                # Function definition
                func = re.match(r'^(\w+)\(\)\s*\{', line_stripped)
                if func and current_section == 'build':
                    current_func = func.group(1)
                    func_lines = []
                    continue

                if current_func:
                    if line_stripped == '}':
                        self.fields[f"func_{current_func}"] = '\n'.join(func_lines)
                        current_func = None
                    else:
                        func_lines.append(line_stripped)

        return True

    def validate_required_fields(self):
        for field in REQUIRED_FIELDS:
            if field not in self.fields:
                self.errors.append(f"Missing required field: {field}")

    def validate_name(self):
        name = self.fields.get('name', '')
        if not re.match(r'^[a-z][a-z0-9_-]{1,63}$', name):
            self.errors.append(f"Invalid package name: '{name}' (must be lowercase, alphanumeric, hyphens, underscores)")

    def validate_version(self):
        version = self.fields.get('version', '')
        if not re.match(r'^[0-9][0-9a-zA-Z._+-]*$', version):
            self.errors.append(f"Invalid version: '{version}' (must start with digit)")

    def validate_arch(self):
        arch = self.fields.get('arch', 'any')
        archs = [a.strip() for a in arch.split(',')]
        for a in archs:
            if a not in VALID_ARCHES:
                self.warnings.append(f"Unknown arch: '{a}' (valid: {', '.join(VALID_ARCHES)})")

    def validate_build_type(self):
        bt = self.fields.get('build_type', 'source')
        if bt not in VALID_BUILD_TYPES:
            self.errors.append(f"Invalid build_type: '{bt}' (valid: {', '.join(VALID_BUILD_TYPES)})")

        if bt == 'deb' and 'deb_name' not in self.fields:
            self.warnings.append("build_type=deb but deb_name not specified (will use package name)")

        if bt == 'source':
            for func in ['configure', 'compile', 'package']:
                if f'func_{func}' not in self.fields:
                    self.warnings.append(f"build_type=source but {func}() function not defined")

    def security_scan(self):
        content = open(self.filepath).read()
        for pattern in DANGEROUS_PATTERNS:
            if re.search(pattern, content):
                self.errors.append(f"Security: Dangerous pattern detected: {pattern}")

        # Check for suspicious URLs
        urls = re.findall(r'https?://[^\s"\']+', content)
        for url in urls:
            if any(bad in url for bad in ['pastebin.com', 'bit.ly', 'tinyurl']):
                self.warnings.append(f"Suspicious URL: {url}")

    def validate_source_url(self):
        url = self.fields.get('url', '')
        if url and not re.match(r'https?://', url):
            self.errors.append(f"Source URL must use http/https: '{url}'")

    def validate_depends(self):
        depends = self.fields.get('depends', '')
        if depends:
            deps = [d.strip() for d in depends.split(',') if d.strip()]
            for dep in deps:
                if not re.match(r'^[a-z][a-z0-9_-]*$', dep):
                    self.warnings.append(f"Suspicious dependency name: '{dep}'")

    def run(self):
        if not self.parse():
            return False

        self.validate_required_fields()
        self.validate_name()
        self.validate_version()
        self.validate_arch()
        self.validate_build_type()
        self.validate_source_url()
        self.validate_depends()
        self.security_scan()

        return len(self.errors) == 0

    def report(self):
        lines = []
        pkg = self.fields.get('name', os.path.dirname(self.filepath))

        if self.errors:
            lines.append(f"### ❌ {pkg} — {len(self.errors)} error(s)")
            for e in self.errors:
                lines.append(f"- 🔴 {e}")
        else:
            lines.append(f"### ✅ {pkg} — Validation passed")

        if self.warnings:
            lines.append(f"\n**{len(self.warnings)} warning(s):**")
            for w in self.warnings:
                lines.append(f"- 🟡 {w}")

        if not self.errors and not self.warnings:
            lines.append("No issues found.")

        # Package summary
        if self.fields:
            lines.append(f"\n**Package info:**")
            for f in ['name', 'version', 'description', 'license', 'arch', 'build_type']:
                if f in self.fields:
                    lines.append(f"- {f}: `{self.fields[f]}`")

        return '\n'.join(lines)


def main():
    files = sys.argv[1:]
    if not files:
        print("Usage: validate-turbuild.py <TURBUILD> [...]")
        sys.exit(1)

    all_passed = True
    report_sections = ["# TUR Validation Report\n"]

    for filepath in files:
        validator = TURBUILDValidator(filepath)
        passed = validator.run()
        report_sections.append(validator.report())
        if not passed:
            all_passed = False

    report = '\n\n'.join(report_sections)
    print(report)

    # Write report for GitHub Actions comment
    with open('validation-report.md', 'w') as f:
        f.write(report)

    sys.exit(0 if all_passed else 1)


if __name__ == '__main__':
    main()
