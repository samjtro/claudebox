#!/usr/bin/env bash
# ==============================================================================
#  ClaudeBox – Docker-based Claude CLI environment
#
#  Clean CLI implementation following the four-bucket architecture
# ==============================================================================

set -euo pipefail

# Add error handler to show where script fails
trap 'exit_code=$?; [[ $exit_code -eq 130 ]] && exit 130 || { echo "Error at line $LINENO: Command failed with exit code $exit_code" >&2; echo "Failed command: $BASH_COMMAND" >&2; echo "Call stack:" >&2; for i in ${!BASH_LINENO[@]}; do if [[ $i -gt 0 ]]; then echo "  at ${FUNCNAME[$i]} (${BASH_SOURCE[$i]}:${BASH_LINENO[$i-1]})" >&2; fi; done; }' ERR INT

# ------------------------------------------------------------------ constants --
# Cross-platform script path resolution
get_script_path() {
    local source="${BASH_SOURCE[0]:-$0}"
    while [[ -L "$source" ]]; do
        local dir="$(cd -P "$(dirname "$source")" && pwd)"
        source="$(readlink "$source")"
        [[ $source != /* ]] && source="$dir/$source"
    done
    echo "$(cd -P "$(dirname "$source")" && pwd)/$(basename "$source")"
}

readonly SCRIPT_PATH="$(get_script_path)"
readonly SCRIPT_DIR="$(dirname "$SCRIPT_PATH")"
# Now that script is at root, SCRIPT_DIR is the repo/install root
readonly INSTALL_ROOT="$HOME/.claudebox"
export SCRIPT_PATH
export CLAUDEBOX_SCRIPT_DIR="${SCRIPT_DIR}"

# Set PROJECT_DIR early (but allow override from environment)
export PROJECT_DIR="${PROJECT_DIR:-$(pwd)}"

# Initialize VERBOSE to false (will be set properly by CLI parser)
export VERBOSE=false

# Load saved default flags if they exist
declare -a DEFAULT_FLAGS=()
if [[ -f "$HOME/.claudebox/default-flags" ]]; then
    while IFS= read -r flag; do
        [[ -n "$flag" ]] && DEFAULT_FLAGS+=("$flag")
    done < "$HOME/.claudebox/default-flags"
fi

# --------------------------------------------------------------- source libs --
# LIB_DIR is always relative to where the script is located
LIB_DIR="${SCRIPT_DIR}/lib"

# Load libraries in order - cli.sh must be loaded first for parsing
for lib in cli common env os state project docker config commands welcome; do
    # shellcheck disable=SC1090
    source "${LIB_DIR}/${lib}.sh"
done

# -------------------------------------------------------------------- main() --
main() {
    # Enable BuildKit for all Docker operations
    export DOCKER_BUILDKIT=1
    
    # Step 1: Update symlink
    update_symlink
    
    # Step 2: Parse ALL arguments (already includes default flags)
    parse_cli_args "$@"
    
    # Step 3: Process host flags (sets VERBOSE, REBUILD, CLAUDEBOX_WRAP_TMUX)
    process_host_flags
    
    # Step 4: Debug output if verbose
    debug_parsed_args
    
    # Step 5: Docker checks
    local docker_status
    docker_status=$(check_docker; echo $?)
    case $docker_status in
        1) install_docker ;;
        2)
            warn "Docker is installed but not running."
            warn "Starting Docker requires sudo privileges..."
            sudo systemctl start docker
            docker info || error "Failed to start Docker"
            docker ps || configure_docker_nonroot
            ;;
        3)
            warn "Docker requires sudo. Setting up non-root access..."
            configure_docker_nonroot
            ;;
    esac
    
    # Step 5a: Build core image if it doesn't exist
    local core_image="claudebox-core"
    if ! docker image inspect "$core_image" >/dev/null 2>&1; then
        # Show logo during build
        logo
        
        local build_context="$HOME/.claudebox/docker-build-context"
        mkdir -p "$build_context"
        
        # Copy build files
        local root_dir="$SCRIPT_DIR"
        cp "${root_dir}/build/docker-entrypoint" "$build_context/docker-entrypoint.sh" || error "Failed to copy docker-entrypoint.sh"
        cp "${root_dir}/build/init-firewall" "$build_context/init-firewall" || error "Failed to copy init-firewall"
        cp "${root_dir}/build/generate-tools-readme" "$build_context/generate-tools-readme" || error "Failed to copy generate-tools-readme"
        cp "${root_dir}/build/dockerignore" "$build_context/.dockerignore" || error "Failed to copy .dockerignore"
        chmod +x "$build_context/docker-entrypoint.sh" "$build_context/init-firewall" "$build_context/generate-tools-readme"
        
        # Create core Dockerfile
        local core_dockerfile="$build_context/Dockerfile.core"
        local base_dockerfile=$(cat "${root_dir}/build/Dockerfile") || error "Failed to read base Dockerfile"
        
        # Remove profile installations and labels placeholders for core
        local core_dockerfile_content="$base_dockerfile"
        core_dockerfile_content="${core_dockerfile_content//\{\{PROFILE_INSTALLATIONS\}\}/}"
        core_dockerfile_content="${core_dockerfile_content//\{\{LABELS\}\}/LABEL claudebox.type=\"core\"}"
        
        echo "$core_dockerfile_content" > "$core_dockerfile"
        
        # Build core image
        docker build \
            --progress=${BUILDKIT_PROGRESS:-auto} \
            --build-arg BUILDKIT_INLINE_CACHE=1 \
            --build-arg USER_ID="$USER_ID" \
            --build-arg GROUP_ID="$GROUP_ID" \
            --build-arg USERNAME="$DOCKER_USER" \
            --build-arg NODE_VERSION="$NODE_VERSION" \
            --build-arg DELTA_VERSION="$DELTA_VERSION" \
            -f "$core_dockerfile" -t "$core_image" "$build_context" || error "Failed to build core image"
            
        # Check if this is truly a first-time setup (no projects exist)
        local project_count=$(ls -1d "$HOME/.claudebox/projects"/*/ 2>/dev/null | wc -l)
        
        if [[ $project_count -eq 0 ]]; then
            # First-time user - show welcome menu
            logo_small
            printf '\n'
            cecho "Welcome to ClaudeBox!" "$CYAN"
            printf '\n'
            printf '%s\n' "ClaudeBox is ready to use. Here's how to get started:"
            printf '\n'
            printf '%s\n' "1. Navigate to your project directory:"
            printf "   ${CYAN}%s${NC}\n" "cd /path/to/your/project"
            printf '\n'
            printf '%s\n' "2. Create your first container slot:"
            printf "   ${CYAN}%s${NC}\n" "claudebox create"
            printf '\n'
            printf '%s\n' "3. Launch Claude:"
            printf "   ${CYAN}%s${NC}\n" "claudebox"
            printf '\n'
            printf '%s\n' "Other useful commands:"
            printf "  ${CYAN}%-20s${NC} - %s\n" "claudebox help" "Show all available commands"
            printf "  ${CYAN}%-20s${NC} - %s\n" "claudebox profiles" "List available development profiles"
            printf "  ${CYAN}%-20s${NC} - %s\n" "claudebox projects" "List all ClaudeBox projects"
            printf '\n'
            exit 0
        fi
        
        # Existing user - core rebuilt, continue normal flow
        if [[ "$VERBOSE" == "true" ]]; then
            echo "[DEBUG] Core image built, continuing with normal flow..." >&2
        fi
    fi
    
    # Step 6: Initialize project directory (creates parent with profiles.ini)
    init_project_dir "$PROJECT_DIR"
    PROJECT_PARENT_DIR=$(get_parent_dir "$PROJECT_DIR")
    export PROJECT_PARENT_DIR
    
    # Step 7: Handle rebuild if requested (will use IMAGE_NAME from step 8)
    local rebuild_requested="${REBUILD:-false}"
    
    # Step 8: Always set up project variables
    # Get the actual parent folder name for the project
    local parent_folder_name=$(generate_parent_folder_name "$PROJECT_DIR")
    
    # Get the slot to use (might be empty)
    project_folder_name=$(get_project_folder_name "$PROJECT_DIR")
    
    # Always set IMAGE_NAME based on parent folder
    IMAGE_NAME=$(get_image_name)
    export IMAGE_NAME
    
    # Set PROJECT_CLAUDEBOX_DIR if we have a slot
    if [[ -n "$project_folder_name" ]] && [[ "$project_folder_name" != "NONE" ]]; then
        PROJECT_CLAUDEBOX_DIR="$PROJECT_PARENT_DIR/$project_folder_name"
        export PROJECT_CLAUDEBOX_DIR
    fi
    
    # Handle rebuild if requested
    if [[ "$rebuild_requested" == "true" ]]; then
        warn "Forcing full rebuild of ClaudeBox Docker image..."
        rm -f "$PROJECT_PARENT_DIR/.docker_layer_checksums"
        docker rmi -f "$IMAGE_NAME" 2>/dev/null || true
    fi
    
    # Step 9: Handle commands that need slots but don't have them
    if [[ -z "$project_folder_name" ]] || [[ "$project_folder_name" == "NONE" ]]; then
        # Check if this command actually needs a slot
        case "${CLI_SCRIPT_COMMAND}" in
            shell|update|config|mcp|migrate-installer|"")
                # These commands need a slot
                show_no_slots_menu
                exit 0
                ;;
            help|-h|--help)
                show_help
                exit 0
                ;;
            # All other commands (like open, create, etc) can proceed without a slot
        esac
    fi
    
    # Step 10: Check command requirements
    local cmd_requirements="none"
    
    if [[ -n "${CLI_SCRIPT_COMMAND}" ]]; then
        cmd_requirements=$(get_command_requirements "${CLI_SCRIPT_COMMAND}")
    else
        # No script command means we're running claude - needs Docker
        cmd_requirements="docker"
    fi
    
    if [[ "$VERBOSE" == "true" ]]; then
        echo "[DEBUG] Command requirements: $cmd_requirements" >&2
    fi
    
    # Step 10a: Set IMAGE_NAME if needed (for "image" or "docker" requirements)
    if [[ "$cmd_requirements" != "none" ]]; then
        # Commands that need image name should have it set even without Docker
        IMAGE_NAME=$(get_image_name)
        export IMAGE_NAME
    fi
    
    # Step 10b: Build Docker image if needed (only for "docker" requirements)
    if [[ "$cmd_requirements" == "docker" ]]; then
        # Check if rebuild needed
        local need_rebuild=false
        
        if [[ "${REBUILD:-false}" == "true" ]] || ! docker image inspect "$IMAGE_NAME" >/dev/null 2>&1; then
            need_rebuild=true
        elif needs_docker_rebuild "$PROJECT_DIR" "$IMAGE_NAME"; then
            need_rebuild=true
            info "Detected changes in Docker build files, rebuilding..."
        else
            # Check profiles
            local profiles_file="$PROJECT_PARENT_DIR/profiles.ini"
            if [[ -f "$profiles_file" ]]; then
                local profiles_file_hash=$(crc32_file "$profiles_file")
                local image_profiles_crc=$(docker inspect "$IMAGE_NAME" --format '{{index .Config.Labels "claudebox.profiles.crc"}}' 2>/dev/null || echo "")
                
                if [[ "$profiles_file_hash" != "$image_profiles_crc" ]]; then
                    info "Profiles changed, rebuilding..."
                    docker rmi -f "$IMAGE_NAME" 2>/dev/null || true
                    need_rebuild=true
                fi
            fi
        fi
        
        if [[ "$need_rebuild" == "true" ]]; then
            # Set rebuild timestamp to bust Docker cache when templates change
            export CLAUDEBOX_REBUILD_TIMESTAMP=$(date +%s)
            if [[ "$VERBOSE" == "true" ]]; then
                echo "[DEBUG] About to build Docker image..." >&2
            fi
            build_docker_image
            if [[ "$VERBOSE" == "true" ]]; then
                echo "[DEBUG] Docker build completed, continuing..." >&2
            fi
        fi
    fi
    
    # Step 11: Set up shared resources
    setup_shared_commands
    setup_claude_agent_command
    
    # Step 12: Fix permissions if needed
    if [[ ! -d "$HOME/.claudebox" ]]; then
        mkdir -p "$HOME/.claudebox"
    fi
    if [[ ! -w "$HOME/.claudebox" ]]; then
        warn "Fixing .claudebox permissions..."
        sudo chown -R "$USER:$USER" "$HOME/.claudebox" || true
    fi
    
    # Step 13: Create allowlist if needed
    if [[ -n "${PROJECT_PARENT_DIR:-}" ]]; then
        local allowlist_file="$PROJECT_PARENT_DIR/allowlist"
        if [[ ! -f "$allowlist_file" ]]; then
            # Root directory is where the script is located
            local root_dir="$SCRIPT_DIR"
            
            local allowlist_template="${root_dir}/build/allowlist"
            if [[ -f "$allowlist_template" ]]; then
                cp "$allowlist_template" "$allowlist_file" || error "Failed to copy allowlist template"
            fi
        fi
    fi
    
    # Step 14: Single dispatch point
    if [[ -n "${CLI_SCRIPT_COMMAND}" ]]; then
        # Script command - dispatch on host
        # Pass control flags and pass-through args to dispatch_command
        dispatch_command "${CLI_SCRIPT_COMMAND}" "${CLI_CONTROL_FLAGS[@]}" "${CLI_PASS_THROUGH[@]}"
        exit $?
    else
        # No script command - run container with control flags + pass-through
        if [[ -n "${PROJECT_CLAUDEBOX_DIR:-}" ]]; then
            local slot_name=$(basename "$PROJECT_CLAUDEBOX_DIR")
            # parent_folder_name already set in step 8
            local container_name="claudebox-${parent_folder_name}-${slot_name}"
            
            if [[ "$VERBOSE" == "true" ]]; then
                echo "[DEBUG] PROJECT_CLAUDEBOX_DIR=$PROJECT_CLAUDEBOX_DIR" >&2
                echo "[DEBUG] slot_name=$slot_name" >&2
                echo "[DEBUG] parent_folder_name=$parent_folder_name" >&2
                echo "[DEBUG] container_name=$container_name" >&2
            fi
            
            # Check if stdin is not a terminal (i.e., we're receiving piped input)
            # and -p/--print flag isn't already present
            local has_print_flag=false
            for arg in "${CLI_PASS_THROUGH[@]}"; do
                if [[ "$arg" == "-p" ]] || [[ "$arg" == "--print" ]]; then
                    has_print_flag=true
                    break
                fi
            done
            
            if [[ ! -t 0 ]] && [[ "$has_print_flag" == "false" ]]; then
                # Add -p flag for piped input, but don't consume stdin
                run_claudebox_container "$container_name" "interactive" "${CLI_CONTROL_FLAGS[@]}" "-p" "${CLI_PASS_THROUGH[@]}"
            else
                run_claudebox_container "$container_name" "interactive" "${CLI_CONTROL_FLAGS[@]}" "${CLI_PASS_THROUGH[@]}"
            fi
        else
            error "No command specified and no slot available"
        fi
    fi
}

# Helper function to build Docker image
build_docker_image() {
    local build_context="$HOME/.claudebox/docker-build-context"
    mkdir -p "$build_context"
    
    # Copy build files to Docker build context
    # Root directory is where the script is located
    local root_dir="$SCRIPT_DIR"
    
    cp "${root_dir}/build/docker-entrypoint" "$build_context/docker-entrypoint.sh" || error "Failed to copy docker-entrypoint.sh"
    cp "${root_dir}/build/init-firewall" "$build_context/init-firewall" || error "Failed to copy init-firewall"
    cp "${root_dir}/build/generate-tools-readme" "$build_context/generate-tools-readme" || error "Failed to copy generate-tools-readme"
    cp "${root_dir}/build/dockerignore" "$build_context/.dockerignore" || error "Failed to copy .dockerignore"
    chmod +x "$build_context/docker-entrypoint.sh" "$build_context/init-firewall" "$build_context/generate-tools-readme"
    
    
    # Build profile installations
    local profiles_file="$PROJECT_PARENT_DIR/profiles.ini"
    local profile_installations=""
    local profile_hash=""
    local profiles_file_hash=""
    
    if [[ -f "$profiles_file" ]]; then
        profiles_file_hash=$(crc32_file "$profiles_file")
        
        local current_profiles=()
        while IFS= read -r line; do
            [[ -n "$line" ]] && current_profiles+=("$line")
        done < <(read_profile_section "$profiles_file" "profiles")
        
        # Generate profile installations
        for profile in "${current_profiles[@]}"; do
            profile=$(echo "$profile" | tr -d '[:space:]')
            [[ -z "$profile" ]] && continue
            
            local profile_fn="get_profile_${profile}"
            if type -t "$profile_fn" >/dev/null; then
                profile_installations+=$'\n'"$($profile_fn)"
            fi
        done
        
        if [[ ${#current_profiles[@]} -gt 0 ]]; then
            profile_hash=$(printf '%s\n' "${current_profiles[@]}" | sort | cksum | cut -d' ' -f1)
        fi
    fi
    
    # Create Dockerfile
    local dockerfile="$build_context/Dockerfile"
    
    # Use the minimal project Dockerfile template
    local base_dockerfile=$(cat "${root_dir}/build/Dockerfile.project") || error "Failed to read project Dockerfile template"
    
    # Build labels
    local project_folder_name=$(generate_parent_folder_name "$PROJECT_DIR")
    local labels="
LABEL claudebox.profiles=\"$profile_hash\"
LABEL claudebox.profiles.crc=\"$profiles_file_hash\"
LABEL claudebox.project=\"$project_folder_name\""
    
    # Replace placeholders in the project template
    local final_dockerfile="$base_dockerfile"
    final_dockerfile="${final_dockerfile//\{\{PROFILE_INSTALLATIONS\}\}/$profile_installations}"
    final_dockerfile="${final_dockerfile//\{\{LABELS\}\}/$labels}"
    
    echo "$final_dockerfile" > "$dockerfile"
    
    # Build the image
    run_docker_build "$dockerfile" "$build_context"
    
    # Save checksums
    save_docker_layer_checksums "$PROJECT_DIR"
}

# Run main with all arguments including default flags
# Pass user arguments first, then DEFAULT_FLAGS
main "$@" "${DEFAULT_FLAGS[@]}"