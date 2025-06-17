# ClaudeBox Quick Start Guide

## 🚀 5-Minute Setup

### 1. Install ClaudeBox

```bash
curl -O https://raw.githubusercontent.com/samjtro/claudebox/main/claudebox
chmod +x claudebox
sudo ln -s $(pwd)/claudebox /usr/local/bin/claudebox
```

### 2. Set Your API Key

```bash
export ANTHROPIC_API_KEY="your-api-key-here"
```

### 3. Launch Claude

```bash
claudebox
```

That's it! ClaudeBox will:
- ✅ Install Docker if needed
- ✅ Build the container image
- ✅ Configure MCP servers
- ✅ Set up APM framework
- ✅ Launch Claude Code

## 🎯 Common Tasks

### Working on a Python Project

```bash
cd my-python-project
claudebox profile python
claudebox
```

Inside Claude:
```
/apm-manager
# Let the Manager Agent set up your project structure
```

### Building a Web App

```bash
claudebox profile javascript web
claudebox --model opus
```

### Machine Learning Development

```bash
claudebox profile python ml datascience
export OPENROUTER_API_KEY="your-key"  # For GPT-4 access
claudebox
```

## 💡 Pro Tips

1. **Use APM for Complex Projects**
   - Start with `/apm-manager` to create a structured plan
   - Use `/apm-implement` when working on specific features

2. **Leverage MCP Servers**
   - Memory server maintains context between sessions
   - Sequential thinking helps with complex problems
   - OpenRouter gives access to multiple AI models

3. **Profile Combinations**
   ```bash
   claudebox profile python rust go  # Multi-language project
   ```

4. **Quick Shell Access**
   ```bash
   claudebox shell  # Debug or install custom tools
   ```

## 📚 Next Steps

- Read the full [README](README.md) for advanced features
- Explore [APM documentation](lib/apm/docs/README.md)
- Check available [development profiles](#)
- Join the community discussions

---

**Need help?** Open an issue on [GitHub](https://github.com/samjtro/claudebox)