#!/usr/bin/env bash
# Unified CLI parser for ClaudeBox
# Implements the four-bucket architecture for clean, predictable CLI handling

# ============================================================================
# CLI PARSER - SINGLE SOURCE OF TRUTH
# ============================================================================

# Four flag buckets (Bash 3.2 compatible - no associative arrays)
readonly HOST_ONLY_FLAGS=(--verbose rebuild tmux)
readonly CONTROL_FLAGS=(--enable-sudo --disable-firewall)
readonly SCRIPT_COMMANDS=(shell create slot slots revoke profiles projects profile info help -h --help add remove install allowlist clean)

# parse_cli_args - Central CLI parsing with four-bucket architecture
# Usage: parse_cli_args "$@"
# Sets global variables:
#   host_flags: Array of host-only flags (help, version, etc)
#   control_flags: Array of control flags (verbose, enable-sudo, etc)
#   script_command: Single command for ClaudeBox to execute
#   pass_through: Array of args to pass to Claude in container
# Note: Each argument goes into exactly ONE bucket - no duplication
parse_cli_args() {
    local all_args=("$@")
    
    # Initialize bucket arrays
    host_flags=()
    control_flags=()
    script_command=""
    pass_through=()
    
    # Single parsing loop - each arg goes into exactly ONE bucket
    local found_script_command=false
    
    for arg in "${all_args[@]}"; do
        if [[ " ${HOST_ONLY_FLAGS[*]} " == *" $arg "* ]]; then
            # Bucket 1: Host-only flags
            host_flags+=("$arg")
        elif [[ " ${CONTROL_FLAGS[*]} " == *" $arg "* ]]; then
            # Bucket 2: Control flags (pass to container)
            control_flags+=("$arg")
        elif [[ "$found_script_command" == "false" ]] && [[ " ${SCRIPT_COMMANDS[*]} " == *" $arg "* ]]; then
            # Bucket 3: Script commands (first one wins)
            script_command="$arg"
            found_script_command=true
        else
            # Bucket 4: Pass-through (everything else)
            pass_through+=("$arg")
        fi
    done
    
    # Export results for use by main script
    export CLI_HOST_FLAGS=("${host_flags[@]}")
    export CLI_CONTROL_FLAGS=("${control_flags[@]}")
    export CLI_SCRIPT_COMMAND="$script_command"
    export CLI_PASS_THROUGH=("${pass_through[@]}")
}

# Process host-only flags and set environment variables
process_host_flags() {
    for flag in "${CLI_HOST_FLAGS[@]}"; do
        case "$flag" in
            --verbose)
                export VERBOSE=true
                ;;
            rebuild)
                export REBUILD=true
                ;;
            tmux)
                export CLAUDEBOX_WRAP_TMUX=true
                ;;
        esac
    done
}

# Check if current command requires Docker image
requires_docker_image() {
    local cmd="${1:-}"
    
    # Commands that don't need Docker
    case "$cmd" in
        profiles|projects|profile|add|remove|install|allowlist|info|help|-h|--help|slots|revoke|clean)
            return 1  # false - doesn't need Docker
            ;;
        *)
            return 0  # true - needs Docker
            ;;
    esac
}

# Check if current command requires a slot
requires_slot() {
    local cmd="${1:-}"
    
    # Commands that need a slot
    case "$cmd" in
        shell|update|config|mcp|migrate-installer|create|slot|"")
            return 0  # true - needs slot
            ;;
        *)
            return 1  # false - doesn't need slot
            ;;
    esac
}

# Debug output for parsed arguments (only if VERBOSE=true)
debug_parsed_args() {
    if [[ "${VERBOSE:-false}" == "true" ]]; then
        echo "[DEBUG] CLI Parser Results:" >&2
        echo "[DEBUG]   Host flags: ${CLI_HOST_FLAGS[*]}" >&2
        echo "[DEBUG]   Control flags: ${CLI_CONTROL_FLAGS[*]}" >&2
        echo "[DEBUG]   Script command: ${CLI_SCRIPT_COMMAND}" >&2
        echo "[DEBUG]   Pass-through: ${CLI_PASS_THROUGH[*]}" >&2
    fi
}

# Export all functions
export -f parse_cli_args process_host_flags requires_docker_image requires_slot debug_parsed_args