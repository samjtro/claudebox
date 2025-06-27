# Changelog

All notable changes to ClaudeBox will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

## [2025-06-25]

### Fixed
- Fixed profile selection logic to handle empty profile values correctly (#24)

## [2025-06-22]

### Added
- Cross-platform host detection for Linux and macOS (#22)
- Filesystem case-sensitivity detection for macOS (HFS+/APFS)
- Docker BuildKit normalization for case-insensitive filesystems

### Changed
- Improved host OS detection with proper error handling
- Enhanced cross-platform script path resolution
- Pinned git-delta version to 0.17.0 for consistency

### Fixed
- Fixed grep -P flag compatibility issue on macOS (#21)
- Resolved issues with case-insensitive filesystem handling on macOS

## [2025-06-21]

### Changed
- Multiple README improvements and documentation updates
- Enhanced Docker build process and configuration

## [2025-06-20]

### Fixed
- Resolved initialization errors in the claudebox script
- Improved container performance and stability

### Removed
- Removed duplicate code blocks for cleaner codebase

## [2025-06-19]

### Added
- BuildX compatibility check for Docker builds
- Enhanced WSL (Windows Subsystem for Linux) support

### Changed
- Streamlined feature set and workflow improvements
- Improved error handling and user feedback

## Earlier Changes

### Initial Features
- Project-specific Docker containers for isolated development environments
- Profile system for language and tool installations
- Firewall configuration with allowlist support
- Persistent storage for project data
- Multi-project support with separate containers per project