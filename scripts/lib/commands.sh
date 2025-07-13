#!/usr/bin/env bash
# Command Module Loader and Reference
# ============================================================================
# This is the central command management system for ClaudeBox.
# All command implementations are organized into logical modules below.

# Get the commands subdirectory path
COMMANDS_DIR="${LIB_DIR}/commands"

# ============================================================================
# CORE COMMANDS - Essential ClaudeBox operations
# ============================================================================
# Commands: help, shell, update
# - help: Shows ClaudeBox help and Claude CLI help
# - shell: Opens an interactive shell in the container
# - update: Updates Claude CLI and optionally ClaudeBox itself
source "${COMMANDS_DIR}/core.sh"

# ============================================================================
# PROFILE COMMANDS - Development profile management
# ============================================================================
# Commands: profiles, profile, add, remove, install
# - profiles: Lists all available development profiles
# - profile: Shows profile management help
# - add: Adds development profiles to the project
# - remove: Removes profiles from the project
# - install: Installs additional apt packages
source "${COMMANDS_DIR}/profile.sh"

# ============================================================================
# SLOT COMMANDS - Container slot management
# ============================================================================
# Commands: create, slots, slot, revoke
# - create: Creates a new container slot for parallel instances
# - slots: Lists all container slots for the project
# - slot: Launches a specific numbered slot
# - revoke: Removes container slots
source "${COMMANDS_DIR}/slot.sh"

# ============================================================================
# INFO COMMANDS - Information display
# ============================================================================
# Commands: info, projects, allowlist
# - info: Shows comprehensive project and system information
# - projects: Lists all ClaudeBox projects system-wide
# - allowlist: Shows/manages the firewall allowlist
source "${COMMANDS_DIR}/info.sh"

# ============================================================================
# CLEAN COMMANDS - Cleanup and maintenance
# ============================================================================
# Commands: clean, undo, redo
# - clean: Various cleanup operations (containers, images, cache, etc.)
# - undo: Restores the oldest backup of claudebox script
# - redo: Restores the newest backup of claudebox script
source "${COMMANDS_DIR}/clean.sh"

# ============================================================================
# SYSTEM COMMANDS - System utilities and special features
# ============================================================================
# Commands: save, unlink, rebuild, tmux, open
# - save: Saves default command-line flags
# - unlink: Removes the claudebox symlink
# - rebuild: Forces a Docker image rebuild
# - tmux: Launches ClaudeBox with tmux support
# - open: Opens a project by name from anywhere
source "${COMMANDS_DIR}/system.sh"

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

# Show menu when no slots exist
show_no_slots_menu() {
    # Reuse the same options and commands from help
    local our_options="  --verbose                       Show detailed output
  --enable-sudo                   Enable sudo without password
  --disable-firewall              Disable network restrictions"
    
    local our_commands="  create                          Create new authenticated container slot
  slots                           List all container slots
  profiles                        List all available profiles
  projects                        List all projects with paths
  add <profiles...>               Add development profiles
  remove <profiles...>            Remove development profiles
  install <packages>              Install apt packages
  save [flags...]                 Save default flags
  allowlist                       Show/edit firewall allowlist
  info                            Show comprehensive project info
  clean                           Menu of cleanup tasks
  help                            Display help for command"
    
    # Show colored header
    echo
    logo header
    echo "Usage: claudebox [OPTIONS] [COMMAND]"
    echo
    echo "No container slots found for this project."
    echo
    echo "Options:"
    echo "  -h, --help                      Display help for command"
    echo "$our_options"
    echo
    echo "Commands:"
    echo "$our_commands"
    echo
    cecho "To get started: claudebox create in the base of your folder." "$YELLOW"
    echo
}

# Show help function
show_help() {
    # Our additional options to inject
    local our_options="  --verbose                       Show detailed output
  --enable-sudo                   Enable sudo without password
  --disable-firewall              Disable network restrictions"
    
    # Our additional commands to append
    local our_commands="  profiles                        List all available profiles
  projects                        List all projects with paths
  add <profiles...>               Add development profiles
  remove <profiles...>            Remove development profiles
  install <packages>              Install apt packages
  save [flags...]                 Save default flags
  shell                           Open transient shell
  shell admin                     Open admin shell (sudo enabled)
  allowlist                       Show/edit firewall allowlist
  info                            Show comprehensive project info
  clean                           Menu of cleanup tasks
  create                          Create new authenticated container slot
  slots                           List all container slots
  slot <number>                   Launch a specific container slot
  open <project>                  Open project by name/hash from anywhere
  tmux                            Launch ClaudeBox with tmux support enabled"
    
    if [[ -n "${IMAGE_NAME:-}" ]] && docker image inspect "$IMAGE_NAME" &>/dev/null; then
        # Get Claude's help and blend our additions
        local claude_help=$(docker run --rm "$IMAGE_NAME" claude --help 2>&1 | grep -v "iptables")
        
        # Process and combine everything in memory
        local full_help=$(echo "$claude_help" | \
            sed '1s/claude/claudebox/g' | \
            sed '/^Commands:/i\
  --verbose                       Show detailed output\
  --enable-sudo                   Enable sudo without password\
  --disable-firewall              Disable network restrictions\
' | \
            sed '$ a\
  profiles                        List all available profiles\
  projects                        List all projects with paths\
  add <profiles...>               Add development profiles\
  remove <profiles...>            Remove development profiles\
  install <packages>              Install apt packages\
  save [flags...]                 Save default flags\
  shell                           Open transient shell\
  shell admin                     Open admin shell (sudo enabled)\
  allowlist                       Show/edit firewall allowlist\
  info                            Show comprehensive project info\
  clean                           Menu of cleanup tasks\
  create                          Create new authenticated container slot\
  slots                           List all container slots\
  slot <number>                   Launch a specific container slot\
  open <project>                  Open project by name/hash from anywhere\
  tmux                            Launch ClaudeBox with tmux support enabled')
        
        # Output everything at once
        echo
        logo_small
        echo
        echo "$full_help"
    else
        # No Docker image - show compact menu
        echo
        logo_small
        echo
        echo "Usage: claudebox [OPTIONS] [COMMAND]"
        echo
        echo "Docker Environment for Claude CLI"
        echo
        echo "Options:"
        echo "  -h, --help                      Display help for command"
        echo "$our_options"
        echo
        echo "Commands:"
        echo "$our_commands"
        echo
        warn "Run 'claudebox create' to get started!"
    fi
}

# Forward unknown commands to container
_forward_to_container() {
    run_claudebox_container "" "interactive" "$@"
}

# ============================================================================
# MAIN DISPATCHER
# ============================================================================
# Routes commands to their handlers based on the parsed CLI_SCRIPT_COMMAND
dispatch_command() {
    local cmd="${1:-help}"; shift || true
    [[ "$VERBOSE" == "true" ]] && echo "[DEBUG] dispatch_command called with: cmd='$cmd' remaining args='$@'" >&2
    
    case "${cmd}" in
        # Core commands
        help|-h|--help)   _cmd_help "$@" ;;
        shell)            _cmd_shell "$@" ;;
        update)           _cmd_update "$@" ;;
        
        # Profile commands
        profiles)         _cmd_profiles "$@" ;;
        profile)          _cmd_profile "$@" ;;
        add)              _cmd_add "$@" ;;
        remove)           _cmd_remove "$@" ;;
        install)          _cmd_install "$@" ;;
        
        # Slot commands
        create)           _cmd_create "$@" ;;
        slots)            _cmd_slots "$@" ;;
        slot)             _cmd_slot "$@" ;;
        revoke)           _cmd_revoke "$@" ;;
        
        # Info commands
        projects)         _cmd_projects "$@" ;;
        allowlist)        _cmd_allowlist "$@" ;;
        info)             _cmd_info "$@" ;;
        
        # Clean commands
        clean)            _cmd_clean "$@" ;;
        undo)             _cmd_undo "$@" ;;
        redo)             _cmd_redo "$@" ;;
        
        # System commands
        save)             _cmd_save "$@" ;;
        unlink)           _cmd_unlink "$@" ;;
        rebuild)          _cmd_rebuild "$@" ;;
        tmux)             _cmd_tmux "$@" ;;
        open)             _cmd_open "$@" ;;
        
        # Special commands that modify container
        config|mcp|migrate-installer) 
                          _cmd_special "$cmd" "$@" ;;
        
        # Unknown command - forward to Claude in container
        *)                _forward_to_container "${cmd}" "$@" ;;
    esac
    
    local exit_code=$?
    [[ "$VERBOSE" == "true" ]] && echo "[DEBUG] dispatch_command returning with exit code: $exit_code" >&2
    return $exit_code
}

# Export all public functions
export -f dispatch_command show_help show_no_slots_menu _forward_to_container