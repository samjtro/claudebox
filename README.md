# ClaudeBox 🐳

**The Ultimate Claude Code Docker Development Environment** - Run Claude AI's coding assistant in a fully containerized, reproducible environment with pre-configured development profiles, MCP servers, and Agentic Project Management framework.

## 🚀 Quick Start

```bash
curl -O https://raw.githubusercontent.com/samjtro/claudebox/main/claudebox
chmod +x claudebox
./claudebox
```

## ✨ Key Features

### 🤖 **Integrated MCP Servers**
- **Memory Server** - Persistent knowledge graph across sessions
- **Sequential Thinking** - Complex problem-solving with revision capabilities  
- **Context7** - Enhanced conversation memory management
- **OpenRouter AI** - Access to multiple LLM models (GPT-4, Claude, Gemini, etc.)

### 📋 **Agentic Project Management (APM)**
Complete framework for managing complex projects with specialized AI agents:
- Manager Agents for orchestration and planning
- Implementation Agents for task execution
- Integrated Memory Bank with MCP persistence
- Structured handover protocols

### 🛠️ **15+ Development Profiles**
Pre-configured environments for every stack:
- **Languages**: C/C++, Rust, Go, Python, JavaScript/TypeScript, Java, Ruby, PHP
- **Specialized**: OpenWRT, Embedded Systems, Machine Learning, Data Science
- **Tools**: DevOps, Security, Database, Web Development

### 🔒 **Security & Isolation**
- Containerized environment with network firewall
- Anthropic-only API access by default (configurable)
- Non-root user matching host UID/GID
- Volume mounts for safe workspace access

## 📚 Usage Guide

### Basic Commands

```bash
# Launch Claude with all features enabled
claudebox

# Use specific Claude model
claudebox --model opus

# Install development profiles
claudebox profile python ml    # Python + Machine Learning
claudebox profile rust go      # Rust + Go
claudebox profile              # List all profiles

# Manage packages
claudebox install htop vim
claudebox shell               # Open container shell
claudebox update              # Update Claude CLI
```

### APM Commands (Use within Claude)

```bash
/apm-manager      # Initialize Manager Agent
/apm-implement    # Create Implementation Agent
/apm-task         # Generate task assignments
/apm-memory       # Manage Memory Bank
/apm-handover     # Execute handover protocol
/apm-plan         # Manage Implementation Plan
/apm-review       # Review completed work
```

### Environment Variables

```bash
export ANTHROPIC_API_KEY=your-key-here        # Required
export OPENROUTER_API_KEY=your-key-here       # For OpenRouter AI
export OPENROUTER_DEFAULT_MODEL=gpt-4         # Optional default model
```

## 🏗️ Architecture

```
claudebox/
├── claudebox           # Main executable script
├── lib/
│   ├── apm/           # APM framework
│   │   ├── commands/  # Claude command templates
│   │   ├── prompts/   # Core APM prompts
│   │   └── docs/      # APM documentation
│   └── mcp/           # MCP configurations
│       └── default-config.json
└── README.md
```

### How It Works

1. **Smart Setup**: Automatically installs Docker if needed, configures permissions
2. **Dynamic Image Building**: Creates optimized Docker images based on selected profiles
3. **MCP Integration**: Auto-configures all MCP servers with proper environment
4. **APM Framework**: Provides structured project management through Claude commands
5. **Persistent Storage**: Maintains configuration and data between sessions

## 🚧 Advanced Usage

### Security Overrides

```bash
# Enable sudo in container (use with caution)
claudebox --dangerously-enable-sudo

# Disable network firewall
claudebox --dangerously-disable-firewall

# Skip permission checks
claudebox --dangerously-skip-permissions
```

### Maintenance

```bash
# Clean up Docker images
claudebox clean

# Deep clean (removes all cache)
claudebox clean --all

# Rebuild from scratch
claudebox rebuild
```

### Custom MCP Servers

Edit `~/.claudebox/.mcp.json` to add custom MCP servers:

```json
{
  "mcpServers": {
    "custom-server": {
      "command": "npx",
      "args": ["-y", "@your-org/mcp-server"],
      "env": {
        "API_KEY": "${YOUR_API_KEY}"
      }
    }
  }
}
```

## 📁 Data Storage

- `~/.claude/` - Claude configuration
- `~/.claudebox/` - ClaudeBox data (MCP configs, project data)
- `./` - Current directory mounted as `/workspace` in container
- `.claude/` - Project-specific Claude commands and APM data

## 🐛 Troubleshooting

### Docker Issues
```bash
# ClaudeBox automatically handles Docker setup, but if needed:
newgrp docker  # Refresh group membership
claudebox      # Try again
```

### MCP Servers Not Working
```bash
claudebox shell
~/test-mcp.sh  # Test MCP connectivity
```

### Profile Installation Failed
```bash
claudebox clean --all
claudebox rebuild
claudebox profile <name>
```

---

**Built for developers who demand clean, reproducible AI-powered development environments.**
