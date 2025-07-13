#!/usr/bin/env bash
# Slot Commands - Container slot management
# ============================================================================
# Commands: create, slots, slot, revoke
# Manages multiple container instances per project

_cmd_create() {
    cecho "Creating new container slot..." "$CYAN"
    echo
    
    # Create a new slot
    local slot_name=$(create_container "$PROJECT_DIR")
    local parent_dir=$(get_parent_dir "$PROJECT_DIR")
    local slot_dir="$parent_dir/$slot_name"
    
    success "✓ Created slot: $slot_name"
    echo
    info "Slot directory: $slot_dir"
    echo
    
    # Show updated slots list
    list_project_slots "$PROJECT_DIR"
    
    return 0
}

_cmd_slots() {
    list_project_slots "$PROJECT_DIR"
    return 0
}

_cmd_slot() {
    # Extract slot number - it should be the first argument
    local slot_num="${1:-}"
    shift || true  # Remove slot number from arguments
    
    # Validate slot number
    if [[ ! "$slot_num" =~ ^[0-9]+$ ]]; then
        error "Usage: claudebox slot <number> [claude arguments...]"
    fi
    
    # Get the slot directory
    local slot_dir=$(get_slot_dir "$PROJECT_DIR" "$slot_num")
    local slot_name=$(basename "$slot_dir")
    
    # Check if slot exists
    if [[ ! -d "$slot_dir" ]]; then
        error "Slot $slot_num does not exist. Run 'claudebox slots' to see available slots."
    fi
    
    # Set up environment for this specific slot
    local parent_dir=$(get_parent_dir "$PROJECT_DIR")
    export PROJECT_CLAUDEBOX_DIR="$slot_dir"
    export PROJECT_PARENT_DIR="$parent_dir"
    export IMAGE_NAME=$(get_image_name)
    
    info "Using slot $slot_num: $slot_name"
    
    # Run container with remaining arguments passed to claude
    run_claudebox_container "" "interactive" "$@"
    exit 0
}

_cmd_revoke() {
    [[ "$VERBOSE" == "true" ]] && echo "[DEBUG] Starting _cmd_revoke with PROJECT_DIR=$PROJECT_DIR" >&2
    local parent
    parent=$(get_parent_dir "$PROJECT_DIR")
    [[ "$VERBOSE" == "true" ]] && echo "[DEBUG] parent=$parent" >&2
    local max
    max=$(read_counter "$parent")
    [[ "$VERBOSE" == "true" ]] && echo "[DEBUG] max=$max" >&2
    
    if [ $max -eq 0 ]; then
        echo "No slots to revoke"
        return 0
    fi
    
    [[ "$VERBOSE" == "true" ]] && echo "[DEBUG] Checking argument: ${1:-}" >&2
    
    # Check for "all" argument
    if [ "${1:-}" = "all" ]; then
        [[ "$VERBOSE" == "true" ]] && echo "[DEBUG] Processing revoke all" >&2
        local removed_count=0
        local existing_count=0
        
        # First count how many slots actually exist
        [[ "$VERBOSE" == "true" ]] && echo "[DEBUG] Starting count loop, max=$max" >&2
        for ((idx=1; idx<=max; idx++)); do
            [[ "$VERBOSE" == "true" ]] && echo "[DEBUG] Count loop idx=$idx" >&2
            local name
            name=$(generate_container_name "$PROJECT_DIR" "$idx")
            [[ "$VERBOSE" == "true" ]] && echo "[DEBUG] Generated name=$name" >&2
            local dir="$parent/$name"
            if [ -d "$dir" ]; then
                ((existing_count++)) || true
            fi
        done
        
        [[ "$VERBOSE" == "true" ]] && echo "[DEBUG] Finished count loop, existing_count=$existing_count, max=$max" >&2
        
        # Now remove them
        [[ "$VERBOSE" == "true" ]] && echo "[DEBUG] Starting removal loop" >&2
        for ((idx=$max; idx>=1; idx--)); do
            local name=$(generate_container_name "$PROJECT_DIR" "$idx")
            local dir="$parent/$name"
            
            if [ -d "$dir" ]; then
                # Check if container is running
                if docker ps --format "{{.Names}}" | grep -q "^claudebox-.*-${name}$"; then
                    info "Slot $idx is in use, skipping"
                else
                    [[ "$VERBOSE" == "true" ]] && echo "[DEBUG] Removing slot $idx: $dir" >&2
                    if rm -rf "$dir"; then
                        ((removed_count++)) || true
                    else
                        error "Failed to remove slot $idx: $dir"
                    fi
                fi
            else
                [[ "$VERBOSE" == "true" ]] && echo "[DEBUG] Slot $idx not found: $dir" >&2
            fi
        done
        
        # If we removed all existing slots, set counter to 0
        [[ "$VERBOSE" == "true" ]] && echo "[DEBUG] removed_count=$removed_count, existing_count=$existing_count" >&2
        if [ $removed_count -eq $existing_count ]; then
            [[ "$VERBOSE" == "true" ]] && echo "[DEBUG] Setting counter to 0" >&2
            write_counter "$parent" 0
        else
            # Otherwise prune the counter
            [[ "$VERBOSE" == "true" ]] && echo "[DEBUG] Pruning counter" >&2
            prune_slot_counter "$PROJECT_DIR"
        fi
        
        # Show updated slots list
        list_project_slots "$PROJECT_DIR"
    else
        # Revoke highest slot only
        local name=$(generate_container_name "$PROJECT_DIR" "$max")
        local dir="$parent/$name"
        
        if [ ! -d "$dir" ]; then
            # Slot doesn't exist, just prune the counter
            prune_slot_counter "$PROJECT_DIR"
            local new_max=$(read_counter "$parent")
            info "Slot $max doesn't exist. Counter adjusted to $new_max"
        else
            # Check if container is running
            if docker ps --format "{{.Names}}" | grep -q "^claudebox-.*-${name}$"; then
                error "Cannot revoke slot $max - it is currently in use"
            fi
            
            # Remove the slot
            rm -rf "$dir"
            write_counter "$parent" $((max - 1))
        fi
        
        # Show updated slots list
        [[ "$VERBOSE" == "true" ]] && echo "[DEBUG] About to call list_project_slots" >&2
        list_project_slots "$PROJECT_DIR"
        [[ "$VERBOSE" == "true" ]] && echo "[DEBUG] list_project_slots returned" >&2
    fi
    
    [[ "$VERBOSE" == "true" ]] && echo "[DEBUG] Exiting _cmd_revoke" >&2
    return 0
}

export -f _cmd_create _cmd_slots _cmd_slot _cmd_revoke