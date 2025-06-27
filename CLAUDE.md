# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ClaudeBox is a Docker-based development environment wrapper for Claude AI's coding assistant. It provides isolated, secure, and reproducible development environments with per-project Docker containers.

## Common Commands

### Running ClaudeBox
- `./claudebox` - Initial setup and launch Claude Code in container
- `claudebox rebuild` - Rebuild the Docker image for current project
- `claudebox clean` - Clean various caches and artifacts
- `claudebox profile` - Install language/tool profiles
- `claudebox install <packages>` - Install apt packages in container

### Development Notes
- This is a bash script project - no build/test/lint commands needed
- Main script: `/home/rich/claudebox/claudebox` (3000+ lines)
- No automated tests exist - manual testing required
- Changes to profiles require rebuild to take effect

## Architecture

### Core Components

1. **Main Script (`claudebox`)**
   - Docker container lifecycle management
   - Profile system for language/tool installation
   - Project isolation and configuration
   - Security and firewall management

2. **Profile System**
   - Located in script's `install_*_profile()` functions
   - Base profiles: core, build-tools
   - Language profiles: python, c, rust, go, node, ruby, php, java
   - Profiles have dependencies (e.g., c depends on build-tools)
   - Profile changes trigger automatic rebuilds via SHA256 hashing

3. **Storage Structure**
   ```
   ~/.claude/          - Claude CLI config and data
   ~/.claudebox/       - Global ClaudeBox data
   ~/.claudebox/<proj> - Project-specific data and config
   ```

4. **Container Architecture**
   - Base image: debian:bookworm
   - Each project gets unique container: `claudebox-<project-name>`
   - Containers mount project directory at `/workdir`
   - Node.js installed via NVM, Claude CLI via npm

### Key Design Patterns

1. **Project Isolation**: Each project has separate Docker image, profiles, and configuration
2. **Security by Default**: Firewall enabled, sudo disabled, allowlist-based network access
3. **Persistent State**: Configuration and context preserved between sessions
4. **Smart Caching**: Docker layers cached per profile, automatic rebuild detection

## Important Functions

Key functions in the claudebox script:

- `setup_project()` - Initialize project-specific configuration
- `rebuild_image()` - Build/rebuild Docker image with profiles
- `launch_claudebox()` - Start container and run Claude Code
- `install_*_profile()` - Profile installation functions
- `manage_firewall()` - Configure network security rules
- `clean_*()` - Various cleanup operations

## Development Guidelines

When modifying ClaudeBox:

1. **Profile Changes**: New profiles should follow the `install_<name>_profile()` pattern
2. **Docker Layers**: Order installations to maximize cache efficiency
3. **Security**: Maintain principle of least privilege - avoid enabling sudo
4. **Cross-Platform**: Test on both macOS and Linux (WSL2 for Windows)
5. **Error Handling**: Use proper exit codes and clear error messages
6. **Configuration**: Store project configs in `~/.claudebox/<project>/`