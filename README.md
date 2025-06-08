# ClaudeBox 🐳

[![Docker](https://img.shields.io/badge/Docker-Required-blue.svg)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![GitHub](https://img.shields.io/badge/GitHub-RchGrav%2Fclaudebox-blue.svg)](https://github.com/RchGrav/claudebox)

The Ultimate Claude Code Docker Development Environment - Run Claude AI's coding assistant in a fully containerized, reproducible environment with pre-configured development profiles and MCP servers.

```
 ██████╗██╗      █████╗ ██╗   ██╗██████╗ ███████╗
██╔════╝██║     ██╔══██╗██║   ██║██╔══██╗██╔════╝
██║     ██║     ███████║██║   ██║██║  ██║█████╗
██║     ██║     ██╔══██║██║   ██║██║  ██║██╔══╝
╚██████╗███████╗██║  ██║╚██████╔╝██████╔╝███████╗
 ╚═════╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚═════╝ ╚══════╝

██████╗  ██████╗ ██╗  ██╗
██╔══██╗██╔═══██╗╚██╗██╔╝
██████╔╝██║   ██║ ╚███╔╝ 
██╔══██╗██║   ██║ ██╔██╗ 
██████╔╝╚██████╔╝██╔╝ ██╗
╚═════╝  ╚═════╝ ╚═╝  ╚═╝
```

## 🚀 What's New in Latest Update

- **MCP Server Integration**: Built-in Sequential Thinking and Memory servers for enhanced Claude capabilities
- **Automatic Docker Setup**: Complete Docker installation and configuration for Ubuntu, Debian, Fedora, Arch
- **Enhanced Security**: Network firewall restricting to Anthropic APIs (can be disabled)
- **15+ Development Profiles**: From embedded systems to machine learning
- **Visual Progress Indicators**: See exactly what's happening during installation
- **Smart `.mcp.json` Management**: Automatic backup and restore of existing configurations

## ✨ Features

- **Containerized Environment**: Run Claude Code in an isolated Docker container
- **MCP Servers**: Pre-configured Model Context Protocol servers for thinking and memory
- **Development Profiles**: Pre-configured language stacks (C/C++, Python, Rust, Go, etc.)
- **Persistent Configuration**: Settings and data persist between sessions
- **Package Management**: Easy installation of additional development tools
- **Auto-Setup**: Handles Docker installation and configuration automatically
- **Security Features**: Network isolation with optional overrides
- **Cross-Platform**: Works on Ubuntu, Debian, Fedora, Arch, and more

## 📋 Prerequisites

- Linux or macOS (WSL2 for Windows)
- Bash shell
- Docker (will be installed automatically if missing)

## 🛠️ Installation

```bash
# Download and setup ClaudeBox
curl -O https://raw.githubusercontent.com/RchGrav/claudebox/main/claudebox
chmod +x claudebox

# Run initial setup (handles everything automatically)
./claudebox
```

The script will:
- ✅ Check for Docker (install if needed)
- ✅ Configure Docker for non-root usage
- ✅ Build the ClaudeBox image with MCP servers
- ✅ Create a global symlink for easy access
- ✅ Set up MCP configuration in your workspace

## 📚 Usage

### Basic Usage

```bash
# Launch Claude CLI with MCP servers enabled
claudebox

# Pass arguments to Claude
claudebox --model opus -c

# Get help
claudebox help          # ClaudeBox specific help
claudebox --help        # Claude CLI help
```

### Development Profiles

ClaudeBox includes 15+ pre-configured development environments:

```bash
# List all available profiles
claudebox profile

# Install specific profiles
claudebox profile python ml        # Python + Machine Learning
claudebox profile c openwrt       # C/C++ + OpenWRT
claudebox profile rust go         # Rust + Go
```

#### Available Profiles:

- **c** - C/C++ Development (gcc, g++, gdb, valgrind, cmake, cmocka, lcov, ncurses)
- **openwrt** - OpenWRT Development (cross-compilation, QEMU, build essentials)
- **rust** - Rust Development (cargo, rustc, clippy, rust-analyzer)
- **python** - Python Development (pip, venv, black, mypy, pylint, poetry, pipenv)
- **go** - Go Development (latest Go toolchain)
- **javascript** - Node.js/TypeScript (npm, yarn, pnpm, TypeScript, ESLint, Prettier)
- **java** - Java Development (OpenJDK 17, Maven, Gradle, Ant)
- **ruby** - Ruby Development (Ruby, gems, bundler)
- **php** - PHP Development (PHP, Composer, common extensions)
- **database** - Database Tools (PostgreSQL, MySQL, SQLite, Redis, MongoDB clients)
- **devops** - DevOps Tools (Docker, Kubernetes, Terraform, Ansible, AWS CLI)
- **web** - Web Development (nginx, curl, httpie, jq)
- **embedded** - Embedded Development (ARM toolchain, OpenOCD, PlatformIO)
- **datascience** - Data Science (NumPy, Pandas, Jupyter, R)
- **security** - Security Tools (nmap, tcpdump, wireshark, penetration testing)
- **ml** - Machine Learning (PyTorch, TensorFlow, scikit-learn, transformers)

### MCP Servers

ClaudeBox includes two powerful MCP servers:

1. **Sequential Thinking Server** - For complex problem-solving with revision capabilities
2. **Memory Server** - Knowledge graph for persistent memory across sessions

These are automatically configured and available to Claude within the container.

### Package Management

```bash
# Install additional packages
claudebox install htop vim tmux

# Open a shell in the container
claudebox shell

# Update Claude CLI
claudebox update
```

### Security Options

```bash
# Run with sudo enabled (use with caution)
claudebox --dangerously-enable-sudo

# Disable network firewall (allows all network access)
claudebox --dangerously-disable-firewall

# Skip permission checks
claudebox --dangerously-skip-permissions
```

### Maintenance

```bash
# Remove ClaudeBox image
claudebox clean

# Deep clean (remove all build cache)
claudebox clean --all

# Rebuild the image from scratch
claudebox rebuild
```

## 🔧 Configuration

ClaudeBox stores data in:
- `~/.claude/` - Claude configuration and data
- `~/.claudebox/` - ClaudeBox-specific data (MCP memory, etc.)
- Current directory mounted as `/workspace` in container

### Environment Variables

- `ANTHROPIC_API_KEY` - Your Anthropic API key
- `NODE_ENV` - Node environment (default: production)

### MCP Configuration

ClaudeBox automatically manages `.mcp.json` in your workspace:
- Creates configuration if none exists
- Backs up existing configurations
- Restores original on exit

## 🏗️ Architecture

ClaudeBox creates a Debian-based Docker image with:
- Node.js (via NVM for version flexibility)
- Claude Code CLI (@anthropic-ai/claude-code)
- MCP servers (thinking and memory)
- User account matching host UID/GID
- Network firewall (Anthropic-only by default)
- Volume mounts for workspace and configuration

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🐛 Troubleshooting

### Docker Permission Issues
ClaudeBox automatically handles Docker setup, but if you encounter issues:
1. The script will add you to the docker group
2. You may need to log out/in or run `newgrp docker`
3. Run `claudebox` again

### MCP Servers Not Working
Test MCP servers after installation:
```bash
claudebox shell
~/test-mcp.sh
```

### Profile Installation Failed
```bash
claudebox clean --all
claudebox rebuild
claudebox profile <name>
```

### Can't Find Command
Ensure the symlink was created:
```bash
sudo ln -s /path/to/claudebox /usr/local/bin/claudebox
```

## 🎉 Acknowledgments

- [Anthropic](https://www.anthropic.com/) for Claude AI
- [Model Context Protocol](https://github.com/anthropics/model-context-protocol) for MCP servers
- Docker community for containerization tools
- All the open-source projects included in the profiles

---

Made with ❤️ for developers who love clean, reproducible environments

## Contact

**Author/Maintainer:** RchGrav  
**GitHub:** [@RchGrav](https://github.com/RchGrav)
