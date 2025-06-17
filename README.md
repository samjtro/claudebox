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
Revolutionary framework that brings real-world project management to AI-assisted development:
- **Manager Agents** orchestrate entire projects, creating detailed implementation plans
- **Multi-Agent Teams** - NEW! Planner, Developer, Reviewer, and Tester agents work together
- **Implementation Agents** execute specific tasks with laser focus
- **Memory Bank** system preserves context across sessions using MCP persistence
- **Handover Protocols** ensure seamless transitions when context windows fill
- **Structured Workflows** that scale from simple scripts to enterprise applications
- **Codex Integration** - Optional GPT-4 powered code review enhancement

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

### 🤖 Agentic Project Management (APM) Workflow

The APM framework revolutionizes how you manage complex AI-assisted projects by addressing context window limitations through structured agent coordination:

#### Quick Start with APM
```bash
# 1. Start your project with a Manager Agent
/apm-manager

# 2. Manager creates Implementation Plan and assigns tasks
# 3. Launch Implementation Agents for specific tasks
/apm-implement

# 4. Agents work autonomously, logging to Memory Bank
# 5. Review progress and iterate
/apm-review
```

#### APM Commands (Use within Claude)
```bash
/apm-manager      # Initialize Manager Agent - always start here
/apm-implement    # Create Implementation Agent for task execution
/apm-agents       # NEW! Launch multi-agent development team
/apm-task         # Generate detailed task assignments
/apm-memory       # View/manage Memory Bank (persistent knowledge base)
/apm-handover     # Execute smooth handover when context limits approach
/apm-plan         # View/update Implementation Plan
/apm-review       # Manager reviews completed work
```

#### How APM Works
1. **Manager Agent** creates a comprehensive Implementation Plan breaking down your project
2. **Memory Bank** (integrated with MCP) preserves all decisions, code, and context
3. **Implementation Agents** execute specific tasks with focused context
4. **Handover Protocol** ensures seamless transitions between agents
5. **Structured Logging** maintains project continuity across sessions

Perfect for: Multi-day projects, complex refactoring, large feature development, or any work that exceeds single context windows.

#### Multi-Agent Development Team (NEW!)
The `/apm-agents` command provides granular control over development iterations:

**Interactive Workflow**: Plan → Questions → Answers → Agents Execute

- **Plan-Driven Development**: Each iteration starts with a markdown plan file
- **Opus-Powered Q&A**: Claude Opus generates specific questions about your plan
- **Interactive Guidance**: Answer questions in vim to steer development direction
- **Context-Aware Execution**: Agents work based on your specific answers
- **Specialized Roles**: Planner, Developer, Reviewer, and Tester agents collaborate

```bash
# First iteration - Opus will ask questions, you answer in vim
/apm-agents iterate project-plan.md

# Continue with iteration 2
/apm-agents iterate project-plan.md 2

# With Codex integration for enhanced reviews
export CODEX_ENABLED=true
export OPENAI_API_KEY=your-key
/apm-agents iterate project-plan.md
```

Perfect for: Maintaining control over AI development, ensuring alignment with your vision, and getting exactly the code you need.

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
│   ├── agents/        # Multi-agent framework
│   │   ├── core/      # Agent loop implementation
│   │   ├── prompts/   # Agent-specific prompts
│   │   └── codex/     # Codex integration
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
