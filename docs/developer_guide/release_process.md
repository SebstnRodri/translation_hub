# Release Process

This document describes the process for creating a new release of Translation Hub.

## Version Numbering

We follow [Semantic Versioning](https://semver.org/):
- **MAJOR.MINOR.PATCH** (e.g., `1.2.3`)
- **MAJOR.MINOR.PATCH-beta** (e.g., `1.2.0-beta`) for pre-releases

Examples:
- `1.0.0` - First stable release
- `1.1.0-beta` - Beta release for version 1.1.0
- `1.1.0` - Stable release
- `1.1.1` - Patch release

## Automated Release Script

Use the automated release script to ensure version consistency:

```bash
./scripts/release.sh
```

This script will:
1. ✅ Update `translation_hub/__init__.py` with new version
2. ✅ Commit the version change
3. ✅ Create a Git tag
4. ✅ Provide next steps for pushing

## Manual Release Process

If you prefer to do it manually, follow these steps:

### 1. Update Version Files

Update the version in `translation_hub/__init__.py`:

```python
__version__ = "1.2.0-beta"
```

### 2. Update CHANGELOG.md

Add a new section at the top of `CHANGELOG.md`:

```markdown
## [v1.2.0-beta] - 2025-12-04

### 🚀 Features
- Feature 1
- Feature 2

### 🐛 Bug Fixes
- Fix 1

### 📚 Documentation
- Doc update 1
```

### 3. Update Documentation

If there are architectural changes, update:
- `docs/developer_guide/architecture.md`
- `docs/user_guide/getting_started.md`
- `README.md`

### 4. Commit Changes

```bash
git add translation_hub/__init__.py CHANGELOG.md docs/
git commit -m "chore: bump version to 1.2.0-beta"
```

### 5. Create Tag

```bash
git tag -a v1.2.0-beta -m "Release v1.2.0-beta: Brief description

Features:
- Feature 1
- Feature 2

Bug Fixes:
- Fix 1"
```

### 6. Merge to Main (for stable releases)

```bash
git checkout main
git merge develop --no-ff -m "Merge branch 'develop' for v1.2.0-beta release"
```

### 7. Push Everything

```bash
# Push develop
git push origin develop

# Push main (if merged)
git push origin main

# Push tag
git push origin v1.2.0-beta
```

### 8. Create GitHub Release

1. Go to https://github.com/your-repo/translation_hub/releases
2. Click "Draft a new release"
3. Select the tag `v1.2.0-beta`
4. Title: `Translation Hub v1.2.0-beta - Brief Description`
5. Description: Copy from CHANGELOG.md
6. Check "This is a pre-release" for beta versions
7. Publish release

## Release Checklist

Before creating a release, ensure:

- [ ] All tests pass (`bench run-tests --app translation_hub`)
- [ ] Version updated in `translation_hub/__init__.py`
- [ ] CHANGELOG.md updated with all changes
- [ ] Documentation updated (if needed)
- [ ] No uncommitted changes
- [ ] On correct branch (develop for beta, main for stable)

## Post-Release

After releasing:

1. **Announce** the release in relevant channels
2. **Monitor** for issues in the first 24-48 hours
3. **Update** project boards/issues
4. **Plan** next release based on feedback

## Hotfix Process

For urgent fixes on a stable release:

1. Create hotfix branch from main:
   ```bash
   git checkout main
   git checkout -b hotfix/1.2.1
   ```

2. Make the fix and test thoroughly

3. Update version to patch (e.g., `1.2.1`)

4. Merge to both main and develop:
   ```bash
   git checkout main
   git merge hotfix/1.2.1
   git tag v1.2.1
   
   git checkout develop
   git merge hotfix/1.2.1
   ```

5. Push everything:
   ```bash
   git push origin main develop
   git push origin v1.2.1
   ```

## Version History

| Version | Date | Type | Description |
|---------|------|------|-------------|
| v1.1.0-beta | 2025-12-04 | Beta | Git-based backup & restore |
| v1.0.0-beta | 2025-11-27 | Beta | Initial beta release |
| v0.2.1 | 2025-11-26 | Alpha | Automated POT generation |
| v0.2.0 | 2025-11-26 | Alpha | Multi-language support |
