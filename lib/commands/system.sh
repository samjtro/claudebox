#!/usr/bin/env bash
# System Commands - System-level operations and utilities
# ============================================================================
# Commands: save, unlink, rebuild, tmux, open
# System utilities and special features

_cmd_save() {
    local defaults_file="${CLAUDEBOX_HOME}/default-flags"

    if [[ $# -eq 0 ]]; then
        if [[ -f "$defaults_file" ]]; then
            rm -f "$defaults_file"
            success "Cleared saved default flags"
        else
            info "No saved default flags to clear"
        fi
    else
        mkdir -p "${CLAUDEBOX_HOME}"
        printf '%s\n' "$@" > "$defaults_file"
        success "Saved default flags: $*"
    fi
    exit 0
}

_cmd_unlink() {
    if [[ -L "$LINK_TARGET" ]]; then
        rm -f "$LINK_TARGET"
        success "Removed claudebox symlink from $(dirname "$LINK_TARGET")"
    else
        info "No claudebox symlink found at $LINK_TARGET"
    fi
    exit 0
}

_cmd_rebuild() {
    # Set rebuild flag and continue with normal execution
    export REBUILD=true
    
    # Remove 'rebuild' from the arguments and continue
    # This allows "claudebox rebuild" to rebuild then launch Claude
    # or "claudebox rebuild shell" to rebuild then open shell
    _forward_to_container "${@}"
}

_cmd_tmux() {
    # Check if tmux is installed in the host
    if ! command -v tmux >/dev/null 2>&1; then
        error "tmux is not installed on the host system.\nPlease install tmux first:\n  Ubuntu/Debian: sudo apt-get install tmux\n  macOS: brew install tmux\n  RHEL/CentOS: sudo yum install tmux"
    fi
    
    # Set up slot variables if not already set
    if [[ -z "${IMAGE_NAME:-}" ]]; then
        local project_folder_name
        project_folder_name=$(get_project_folder_name "$PROJECT_DIR" 2>/dev/null || echo "NONE")
        
        if [[ "$project_folder_name" == "NONE" ]]; then
            error "No container slots available. Please run 'claudebox create' to create a container slot."
        fi
        
        IMAGE_NAME=$(get_image_name)
        PROJECT_CLAUDEBOX_DIR="$PROJECT_PARENT_DIR/$project_folder_name"
        export PROJECT_CLAUDEBOX_DIR
    fi
    
    # Generate container name
    local slot_name=$(basename "$PROJECT_CLAUDEBOX_DIR")
    local container_name="claudebox-${project_folder_name}-${slot_name}"
    
    info "Starting ClaudeBox with tmux support..."
    echo
    cecho "Tmux will be available inside the container for multi-pane workflows." "$YELLOW"
    echo
    
    # Export flag to indicate tmux mode
    export CLAUDEBOX_TMUX_MODE=true
    
    # Run the container - tmux socket will be mounted if available
    run_claudebox_container "$container_name" "interactive" "${@:-}"
    exit 0
}

_cmd_open() {
    local search="${1:-}"
    shift || true
    
    if [[ -z "$search" ]]; then
        error "Usage: claudebox open <project-name> [command...]\nExample: claudebox open myproject\nExample: claudebox open cc618e36 shell"
    fi
    
    # Convert search to lowercase for case-insensitive matching
    local search_lower=$(echo "$search" | tr '[:upper:]' '[:lower:]')
    local matches=()
    
    # Search through all project directories
    for parent_dir in "$HOME/.claudebox/projects"/*/ ; do
        [[ -d "$parent_dir" ]] || continue
        
        local dir_name=$(basename "$parent_dir")
        local dir_lower=$(echo "$dir_name" | tr '[:upper:]' '[:lower:]')
        
        # Check if search matches directory name (partial match)
        if [[ "$dir_lower" == *"$search_lower"* ]]; then
            # Read the actual project path
            if [[ -f "$parent_dir/.project_path" ]]; then
                local project_path=$(cat "$parent_dir/.project_path")
                matches+=("$project_path|$dir_name")
            fi
        fi
    done
    
    # Handle results
    if [ ${#matches[@]} -eq 0 ]; then
        error "No projects found matching '$search'"
    elif [ ${#matches[@]} -eq 1 ]; then
        # Single match - use it
        local project_path="${matches[0]%%|*}"
        local project_name="${matches[0]##*|}"
        
        #info "Opening project: $project_name"
        #info "Path: $project_path"
        #echo
        
        # Save current directory
        local original_dir="$PWD"
        
        # Change to project directory and run claudebox
        cd "$project_path" || error "Failed to change to project directory"
        
        # Set PROJECT_DIR explicitly
        export PROJECT_DIR="$project_path"
        
        # Run claudebox with any additional arguments
        if [[ $# -eq 0 ]]; then
            # No arguments - run interactive claude
            "$SCRIPT_PATH"
        else
            # Pass through arguments
            "$SCRIPT_PATH" "$@"
        fi
        
        # Return to original directory
        cd "$original_dir"
    else
        # Multiple matches - show them
        error "Multiple projects match '$search':"
        for match in "${matches[@]}"; do
            local path="${match%%|*}"
            local name="${match##*|}"
            echo "  $name -> $path"
        done
        echo
        echo "Please be more specific."
    fi
}

# Special command handler for commands that need container modification
_cmd_special() {
    local cmd="$1"
    shift
    
    # Check if image exists first (for non-update commands)
    if [[ "$cmd" != "update" ]] && ! docker image inspect "$IMAGE_NAME" >/dev/null 2>&1; then
        error "No Docker image found for this project folder: $PROJECT_DIR\nRun 'claudebox' first to build the image, or cd to your project directory."
    fi
    
    # Create temporary container
    local project_folder_name=$(get_project_folder_name "$PROJECT_DIR")
    local temp_container="claudebox-temp-${project_folder_name}-$$"
    
    # Run container with all arguments passed through
    run_claudebox_container "$temp_container" "detached" "$cmd" "$@" >/dev/null
    
    # Show progress while waiting
    if [[ "$cmd" == "update" ]]; then
        # Show hint during update
        echo
        cecho "Hint:" "$YELLOW"
        echo "  claudebox update all            # Pull the latest claudebox features!"
        echo
    fi
    fillbar
    
    # Wait for container to finish
    docker wait "$temp_container" >/dev/null
    
    fillbar stop
    
    # Show container output for commands that produce output
    docker logs "$temp_container" 2>&1
    
    # For update command, show version after update
    if [[ "$cmd" == "update" ]]; then
        docker exec -u "$DOCKER_USER" "$temp_container" bash -c "
            source \$HOME/.nvm/nvm.sh && nvm use default >/dev/null 2>&1 && claude --version
        " 2>/dev/null || true
    fi

    # Commit changes back to image
    docker commit "$temp_container" "$IMAGE_NAME" >/dev/null
    docker stop "$temp_container" >/dev/null 2>&1 || true
    docker rm "$temp_container" >/dev/null 2>&1 || true
    
    exit 0
}

_cmd_import() {
    local host_commands="$HOME/.claude/commands"
    local parent_dir=$(get_parent_dir "$PROJECT_DIR")
    local project_commands="$parent_dir/commands"
    
    # Check if host commands directory exists
    if [[ ! -d "$host_commands" ]]; then
        warn "No commands found at $host_commands"
        info "Create markdown files in ~/.claude/commands to use with Claude"
        return 1
    fi
    
    # List available commands
    local commands=()
    while IFS= read -r -d '' file; do
        commands+=("$(basename "$file")")
    done < <(find "$host_commands" -maxdepth 1 -name "*.md" -type f -print0 | sort -z)
    
    if [[ ${#commands[@]} -eq 0 ]]; then
        warn "No markdown command files found in $host_commands"
        return 1
    fi
    
    # Show available commands
    cecho "Available commands to import:" "$CYAN"
    echo
    local i=1
    for cmd in "${commands[@]}"; do
        printf "  %2d. %s\n" "$i" "$cmd"
        ((i++))
    done
    echo
    printf "  %2s. %s\n" "a" "Import all commands"
    echo
    
    # Get user selection
    read -p "Select command(s) to import (number, 'a' for all, or 'q' to quit): " selection
    
    case "$selection" in
        q|Q)
            info "Import cancelled"
            return 0
            ;;
        a|A|all|ALL)
            # Import all commands
            local imported=0
            for cmd in "${commands[@]}"; do
                if cp "$host_commands/$cmd" "$project_commands/"; then
                    ((imported++))
                fi
            done
            success "✓ Imported $imported command(s) to project"
            ;;
        [0-9]*)
            # Import specific command
            if [[ $selection -ge 1 && $selection -le ${#commands[@]} ]]; then
                local cmd="${commands[$((selection-1))]}"
                if cp "$host_commands/$cmd" "$project_commands/"; then
                    success "✓ Imported $cmd to project"
                else
                    error "Failed to import $cmd"
                fi
            else
                error "Invalid selection: $selection"
            fi
            ;;
        *)
            error "Invalid selection: $selection"
            ;;
    esac
    
    # Show current project commands
    echo
    info "Current project commands:"
    ls -la "$project_commands"
}

export -f _cmd_save _cmd_unlink _cmd_rebuild _cmd_tmux _cmd_open _cmd_special _cmd_import