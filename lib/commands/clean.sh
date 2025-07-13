#!/usr/bin/env bash
# Clean Commands - Cleanup and maintenance operations
# ============================================================================
# Commands: clean, undo, redo
# Manages Docker cleanup, backups, and restoration

_cmd_clean() {
    case "${1:-}" in
        all)
            warn "Complete Docker cleanup: removing all claudebox containers, images, volumes, and cache..."
            # Remove all claudebox containers
            docker ps -a --filter "label=claudebox.project" -q | xargs -r docker rm -f 2>/dev/null || true
            docker ps -a --format "{{.Names}}" | grep "^claudebox-" | xargs -r docker rm -f 2>/dev/null || true

            # Remove ALL claudebox images (including base)
            docker images --filter "reference=claudebox-*" -q | xargs -r docker rmi -f 2>/dev/null || true
            docker images --filter "reference=claudebox" -q | xargs -r docker rmi -f 2>/dev/null || true

            # Remove dangling images
            docker images -f "dangling=true" -q | xargs -r docker rmi -f 2>/dev/null || true

            # Prune build cache
            docker builder prune -af 2>/dev/null || true

            # Remove volumes
            docker volume ls -q --filter "name=claudebox" | xargs -r docker volume rm 2>/dev/null || true

            success "Docker cleanup complete!"
            echo
            docker system df
            exit 0
            ;;
        image)
            warn "Removing ClaudeBox containers and image..."
            # Remove any containers from this image
            docker ps -a --filter "label=claudebox.project" -q | xargs -r docker rm -f 2>/dev/null || true
            # Remove orphaned containers from images that no longer exist
            # This is safer as it only removes containers whose images are gone
            docker ps -a --filter "status=exited" --format "{{.ID}} {{.Image}}" | while read id image; do
                if ! docker image inspect "$image" >/dev/null 2>&1; then
                    docker rm -f "$id" 2>/dev/null || true
                fi
            done
           # Remove all claudebox project images
           docker images --filter "reference=claudebox-*" -q | xargs -r docker rmi -f 2>/dev/null || true
            success "Containers and image removed! Build cache preserved."
            echo
            docker system df
            exit 0
            ;;
        cache)
            warn "Cleaning Docker build cache..."
            docker builder prune -af
            success "Build cache cleaned!"
            echo
            docker system df
            exit 0
            ;;
        volumes)
            warn "Removing ClaudeBox-related volumes..."
            docker volume ls -q --filter "name=claudebox" | xargs -r docker volume rm 2>/dev/null || true
            docker volume prune -f 2>/dev/null || true
            success "Volumes cleaned!"
            echo
            docker system df
            exit 0
            ;;
        containers)
            warn "Cleaning ClaudeBox containers..."
            # Remove any containers from this image
            docker ps -a --filter "label=claudebox.project" -q | xargs -r docker rm -f 2>/dev/null || true
            # Remove orphaned containers from images that no longer exist
            # This is safer as it only removes containers whose images are gone
            docker ps -a --filter "status=exited" --format "{{.ID}} {{.Image}}" | while read id image; do
                if ! docker image inspect "$image" >/dev/null 2>&1; then
                    docker rm -f "$id" 2>/dev/null || true
                fi
            done
            success "Containers cleaned!"
            echo
            docker system df
            exit 0
            ;;
        dangling)
            warn "Removing dangling images and unused containers..."
            docker image prune -f
            docker container prune -f
            success "Dangling resources cleaned!"
            echo
            docker system df
            exit 0
            ;;
        logs)
            warn "Clearing Docker container logs..."
            docker ps -a --filter "label=claudebox.project" -q | while read -r container; do
                docker logs "$container" >/dev/null 2>&1 && echo -n | docker logs "$container" 2>/dev/null || true
            done
            success "Container logs cleared!"
            echo
            docker system df
            exit 0
            ;;
        project)
            shift
            local target_path="$PROJECT_DIR"
            local project_folder_name

            if [[ $# -gt 0 ]] && [[ "${1:0:1}" != "-" ]] && [[ "$1" != "all" && "$1" != "data" && "$1" != "docker" && "$1" != "profiles" && "$1" != "tools" ]]; then
                target_path="$1"
                shift

                project_folder_name=$(resolve_project_path "$target_path")
                if [[ -z "$project_folder_name" ]]; then
                    error "No ClaudeBox project found at: $target_path"
                fi
            else
                project_folder_name=$(get_project_folder_name "$PROJECT_DIR")
            fi

            local project_claudebox_dir="$HOME/.claudebox/projects/$project_folder_name"
            local image_name="claudebox-${project_folder_name}"

            local display_path="$PROJECT_DIR"
            local config_file="$project_claudebox_dir/profiles.ini"
            if [[ -f "$config_file" ]]; then
                local path_value=$(read_config_value "$config_file" "project" "path")
                [[ -n "$path_value" ]] && display_path="$path_value"
            fi

            case "${1:-}" in
                profiles|tools)
                    warn "Clearing profile configuration for: $display_path"
                    if [[ -f "$config_file" ]]; then
                        {
                            awk '/^\[profiles\]/ { profiles=1; print; print ""; next }
                                 /^\[packages\]/ { packages=1; print; print ""; next }
                                 /^\[/ { profiles=0; packages=0 }
                                 !profiles && !packages { print }' "$config_file"
                        } > "${config_file}.tmp" && mv "${config_file}.tmp" "$config_file"
                        success "Cleared profile configuration"
                    else
                        info "No configuration file found"
                    fi
                    ;;
                data)
                    warn "Removing project data for: $display_path"
                    if [[ -d "$project_claudebox_dir" ]]; then
                        rm -rf "$project_claudebox_dir"
                        success "Removed project data folder: $project_claudebox_dir"
                    else
                        info "No project data folder found"
                    fi
                    ;;
                docker)
                    warn "Removing Docker image for: $display_path"
                    docker rmi -f "$image_name" 2>/dev/null && \
                        success "Removed Docker image: $image_name" || \
                        info "No Docker image found for this project"
                    ;;
                all)
                    warn "Removing all project artifacts for: $display_path"
                    if [[ -f "$config_file" ]]; then
                        rm -f "$config_file"
                        success "Removed profile configuration"
                    fi
                    if [[ -d "$project_claudebox_dir" ]]; then
                        rm -rf "$project_claudebox_dir"
                        success "Removed project data folder"
                    fi
                    docker rmi -f "$image_name" 2>/dev/null && \
                        success "Removed Docker image" || \
                        info "No Docker image found"
                    ;;
                *)
                    cecho "ClaudeBox Project Clean Options:" "$CYAN"
                    echo
                    echo -e "  ${GREEN}clean project [path] profiles${NC}   Remove installed profiles & packages"
                    echo -e "  ${GREEN}clean project [path] data${NC}       Remove project data (auth, history, configs)"
                    echo -e "  ${GREEN}clean project [path] docker${NC}     Remove project Docker image"
                    echo -e "  ${GREEN}clean project [path] all${NC}        Remove everything for this project"
                    echo
                    cecho "Usage examples:" "$WHITE"
                    echo "  claudebox clean project data                      # Current directory"
                    echo "  claudebox clean project /path/to/project all      # Specific path"
                    echo
                    cecho "Current project: $PROJECT_DIR" "$YELLOW"
                    echo
                    cecho "What gets removed:" "$WHITE"
                    echo "  profiles: Clears [profiles] and [packages] sections in profiles.ini"
                    echo "  data:     ~/.claudebox/projects/${project_folder_name}/ (entire project folder)"
                    echo "  docker:   Docker image claudebox-${project_folder_name}"
                    exit 0
                    ;;
            esac
            exit 0
            ;;
        *)
            cecho "ClaudeBox Clean Options:" "$CYAN"
            echo
            echo -e "  ${GREEN}clean containers${NC}         Remove all containers (preserves image)"
            echo -e "  ${GREEN}clean project${NC}            Show project cleanup options"
            echo -e "  ${GREEN}clean all${NC}                Remove all Docker artifacts (containers, images, cache, volumes)"
            echo -e "  ${GREEN}clean image${NC}              Remove containers and image (preserves build cache)"
            echo -e "  ${GREEN}clean cache${NC}              Remove Docker build cache only"
            echo -e "  ${GREEN}clean volumes${NC}            Remove associated Docker volumes"
            echo -e "  ${GREEN}clean dangling${NC}           Remove dangling images and unused containers"
            echo -e "  ${GREEN}clean logs${NC}               Clear Docker container logs"
            echo
            cecho "Examples:" "$YELLOW"
            echo "  claudebox clean containers  # Remove all containers"
            echo "  claudebox clean project     # Show project cleanup menu"
            echo "  claudebox clean image       # Remove containers and image"
            echo "  claudebox clean all         # Complete Docker cleanup"
            exit 0
            ;;
    esac
}

_cmd_undo() {
    local backups_dir="$HOME/.claudebox/backups"
    if [[ ! -d "$backups_dir" ]] || [[ -z "$(ls -A "$backups_dir" 2>/dev/null)" ]]; then
        error "No backups found"
    fi
    
    # Get oldest backup (smallest timestamp)
    local oldest=$(ls -1 "$backups_dir" | sort -n | head -1)
    local installed_path=$(which claudebox 2>/dev/null || echo "/usr/local/bin/claudebox")
    
    info "Restoring oldest backup from $(date -d @$oldest '+%Y-%m-%d %H:%M:%S' 2>/dev/null || date -r $oldest '+%Y-%m-%d %H:%M:%S')"
    
    if [[ -w "$installed_path" ]] || [[ -w "$(dirname "$installed_path")" ]]; then
        cp "$backups_dir/$oldest" "$installed_path"
        chmod +x "$installed_path"
    else
        sudo cp "$backups_dir/$oldest" "$installed_path"
        sudo chmod +x "$installed_path"
    fi
    
    success "✓ Restored claudebox from backup"
    exit 0
}

_cmd_redo() {
    local backups_dir="$HOME/.claudebox/backups"
    if [[ ! -d "$backups_dir" ]] || [[ -z "$(ls -A "$backups_dir" 2>/dev/null)" ]]; then
        error "No backups found"
    fi
    
    # Get newest backup (largest timestamp)
    local newest=$(ls -1 "$backups_dir" | sort -n | tail -1)
    local installed_path=$(which claudebox 2>/dev/null || echo "/usr/local/bin/claudebox")
    
    info "Restoring newest backup from $(date -d @$newest '+%Y-%m-%d %H:%M:%S' 2>/dev/null || date -r $newest '+%Y-%m-%d %H:%M:%S')"
    
    if [[ -w "$installed_path" ]] || [[ -w "$(dirname "$installed_path")" ]]; then
        cp "$backups_dir/$newest" "$installed_path"
        chmod +x "$installed_path"
    else
        sudo cp "$backups_dir/$newest" "$installed_path"
        sudo chmod +x "$installed_path"
    fi
    
    success "✓ Restored claudebox from backup"
    exit 0
}

export -f _cmd_clean _cmd_undo _cmd_redo