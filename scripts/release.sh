#!/bin/bash
# ============================================
# Release Script - Translation Hub
# ============================================
# Automates version bumping and release tagging

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ============================================
# Functions
# ============================================

print_header() {
    echo -e "${BLUE}============================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}============================================${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

get_current_version() {
    grep -oP '__version__ = "\K[^"]+' translation_hub/__init__.py
}

update_version_file() {
    local new_version=$1
    sed -i "s/__version__ = \".*\"/__version__ = \"$new_version\"/" translation_hub/__init__.py
    print_success "Updated translation_hub/__init__.py to $new_version"
}

update_changelog() {
    local new_version=$1
    local date=$(date +%Y-%m-%d)
    
    # Check if version already exists in CHANGELOG
    if grep -q "## \[$new_version\]" CHANGELOG.md; then
        print_warning "Version $new_version already exists in CHANGELOG.md"
    else
        print_warning "Please update CHANGELOG.md manually with version $new_version"
    fi
}

# ============================================
# Main Script
# ============================================

print_header "Translation Hub Release Script"

# Check if on correct branch
current_branch=$(git branch --show-current)
if [ "$current_branch" != "develop" ] && [ "$current_branch" != "main" ]; then
    print_error "You must be on 'develop' or 'main' branch to create a release"
    exit 1
fi

# Get current version
current_version=$(get_current_version)
echo ""
echo -e "${BLUE}Current version:${NC} $current_version"
echo ""

# Ask for new version
echo -e "${YELLOW}Enter new version (e.g., 1.2.0-beta, 1.2.0):${NC}"
read -p "> " new_version

if [ -z "$new_version" ]; then
    print_error "Version cannot be empty"
    exit 1
fi

# Confirm
echo ""
echo -e "${YELLOW}You are about to:${NC}"
echo "  1. Update version from $current_version to $new_version"
echo "  2. Commit changes"
echo "  3. Create tag v$new_version"
echo ""
read -p "Continue? (y/N): " confirm

if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
    print_warning "Release cancelled"
    exit 0
fi

echo ""
print_header "Creating Release v$new_version"

# 1. Update version file
echo ""
echo "📝 Updating version files..."
update_version_file "$new_version"

# 2. Update CHANGELOG
update_changelog "$new_version"

# 3. Show diff
echo ""
echo "📋 Changes to be committed:"
git diff translation_hub/__init__.py

# 4. Commit
echo ""
read -p "Commit these changes? (y/N): " commit_confirm
if [ "$commit_confirm" = "y" ] || [ "$commit_confirm" = "Y" ]; then
    git add translation_hub/__init__.py
    git commit -m "chore: bump version to $new_version"
    print_success "Changes committed"
else
    print_warning "Skipping commit"
fi

# 5. Create tag
echo ""
read -p "Create tag v$new_version? (y/N): " tag_confirm
if [ "$tag_confirm" = "y" ] || [ "$tag_confirm" = "Y" ]; then
    echo "Enter tag message (or press Enter for default):"
    read -p "> " tag_message
    
    if [ -z "$tag_message" ]; then
        tag_message="Release v$new_version"
    fi
    
    git tag -a "v$new_version" -m "$tag_message"
    print_success "Tag v$new_version created"
else
    print_warning "Skipping tag creation"
fi

# 6. Summary
echo ""
print_header "Release Summary"
echo ""
echo -e "${GREEN}Version:${NC} $new_version"
echo -e "${GREEN}Branch:${NC} $current_branch"
echo -e "${GREEN}Tag:${NC} v$new_version"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "  1. Review changes: git log -1"
echo "  2. Push changes: git push origin $current_branch"
echo "  3. Push tag: git push origin v$new_version"
if [ "$current_branch" = "develop" ]; then
    echo "  4. Merge to main: git checkout main && git merge develop"
fi
echo ""
print_success "Release v$new_version completed!"
