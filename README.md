# ClaudeBox 🐳

[![Docker](https://img.shields.io/badge/Docker-Required-blue.svg)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

The Ultimate Claude Code Docker Development Environment - Run Claude AI's coding assistant in a fully containerized, reproducible environment with pre-configured development profiles.

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

## 🚀 Features

- **Containerized Environment**: Run Claude Code in an isolated Docker container
- **Development Profiles**: Pre-configured language stacks (C/C++, Python, Rust, Go, etc.)
- **Persistent Configuration**: Settings and data persist between sessions
- **Package Management**: Easy installation of additional development tools
- **Auto-Setup**: Handles Docker installation and configuration automatically
- **Cross-Platform**: Works on Ubuntu, Debian, Fedora, Arch, and more

## 📋 Prerequisites

- Linux or macOS (WSL2 for Windows)
- Docker (will be installed automatically if missing)
- Bash shell

## 🛠️ Installation

1. **Download the script**:
```bash
curl -O https://raw.githubusercontent.com/yourusername/claudebox/main/claudebox
chmod +x claudebox
```

2. **Run initial setup**:
```bash
./claudebox
```

The script will:
- Check for Docker (install if needed)
- Configure Docker for non-root usage
- Build the ClaudeBox image
- Create a global symlink for easy access

## 📚 Usage

### Basic Usage

```bash
# Launch Claude CLI with default settings
claudebox

# Pass arguments to Claude
claudebox --model opus -c

# Get help
claudebox help          # ClaudeBox help
claudebox --help        # Claude CLI help
```

### Development Profiles

ClaudeBox includes pre-configured development environments:

```bash
# List available profiles
claudebox profile

# Install specific profiles
claudebox profile python ml        # Python + Machine Learning
claudebox profile c openwrt       # C/C++ + OpenWRT
claudebox profile rust go         # Rust + Go
```

#### Available Profiles:

- **c** - C/C++ Development (gcc, g++, gdb, valgrind, cmake, etc.)
- **openwrt** - OpenWRT Development (cross-compilation, QEMU)
- **rust** - Rust Development (cargo, rustc, clippy, rust-analyzer)
- **python** - Python Development (pip, venv, black, mypy, pylint)
- **go** - Go Development (latest Go toolchain)
- **javascript** - Node.js/TypeScript (npm, yarn, pnpm, TypeScript)
- **java** - Java Development (OpenJDK 17, Maven, Gradle)
- **ruby** - Ruby Development (Ruby, gems, bundler)
- **php** - PHP Development (PHP, Composer, extensions)
- **database** - Database Tools (PostgreSQL, MySQL, SQLite clients)
- **devops** - DevOps Tools (Docker, Kubernetes, Terraform, Ansible)
- **web** - Web Development (nginx, curl, httpie, jq)
- **embedded** - Embedded Development (ARM toolchain, OpenOCD)
- **datascience** - Data Science (NumPy, Pandas, Jupyter, R)
- **security** - Security Tools (nmap, tcpdump, wireshark)
- **ml** - Machine Learning (PyTorch, TensorFlow, scikit-learn)

### Package Management

```bash
# Install additional packages
claudebox install htop vim tmux

# Open a shell in the container
claudebox shell

# Update Claude CLI
claudebox update
```

### Maintenance

```bash
# Remove ClaudeBox image
claudebox clean

# Deep clean (remove all build cache)
claudebox clean --all

# Rebuild the image
claudebox rebuild
```

## 🔧 Configuration

ClaudeBox stores data in:
- `~/.claude/` - Claude configuration and data
- Current directory is mounted as `/workspace` in the container

### Environment Variables

- `ANTHROPIC_API_KEY` - Your Anthropic API key
- `NODE_ENV` - Node environment (default: production)

## 🏗️ Architecture

ClaudeBox creates a Debian-based Docker image with:
- Node.js (via NVM for version flexibility)
- Claude Code CLI (@anthropic-ai/claude-code)
- User account matching host UID/GID
- Sudo access for package installation
- Volume mounts for workspace and configuration

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🐛 Troubleshooting

### Docker Permission Issues
If you encounter permission errors, the script will automatically:
1. Add you to the docker group
2. Configure Docker for non-root usage
3. Prompt you to log out/in or run `newgrp docker`

### Profile Installation Failed
Try cleaning and rebuilding:
```bash
claudebox clean --all
claudebox
claudebox profile <name>
```

### Can't Find Command
Ensure the symlink was created:
```bash
sudo ln -s /path/to/claudebox /usr/local/bin/claudebox
```

## 🎉 Acknowledgments

- [Anthropic](https://www.anthropic.com/) for Claude AI
- Docker community for containerization tools
- All the open-source projects included in the profiles

---

Made with ❤️ for developers who love clean, reproducible environments
