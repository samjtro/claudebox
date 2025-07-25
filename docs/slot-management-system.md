# ClaudeBox Slot Management System

## Overview

ClaudeBox uses an elegant slot-based system to manage multiple authenticated Claude instances per project. Each slot represents an isolated environment with its own credentials, cache, and configuration, while sharing the same Docker image.

**CRITICAL**: This document describes a working system with specific design decisions. DO NOT modify the core algorithms without understanding all interdependencies.

## Core Concepts

### 1. Slot Identity

Each slot has a unique 8-character CRC32 checksum generated through an **iterative chain**:
- **Slot 0**: Base CRC32 of project path (conceptual parent, never created)
- **Slot 1**: CRC32 of slot 0's checksum
- **Slot 2**: CRC32 of slot 1's checksum
- **Slot n**: CRC32 of slot (n-1)'s checksum

Example chain:
```
Project path: /home/rich/myproject
Slot 0: cc618e36 (base CRC32)
Slot 1: 524b9a6e (CRC32 of "cc618e36")
Slot 2: ab89def0 (CRC32 of "524b9a6e")
```

### 2. Slot Counter

Each project maintains a counter file (`.project_container_counter`) that tracks the **highest slot index ever created**:
- Starts at 1 (not 0)
- Can **increase** when new slots are created
- Can **decrease** when high-numbered slots are pruned
- Lives in the parent project directory

### 3. Directory Structure

```
~/.claudebox/projects/
└── home_rich_myproject_cc618e36/        # Parent directory
    ├── .project_container_counter        # Current max slot (e.g., "3")
    ├── profiles.ini                      # Shared profiles
    ├── 524b9a6e/                        # Slot 1 directory
    │   ├── .claude/                     # Claude config
    │   │   └── .credentials.json        # Auth credentials
    │   ├── .config/
    │   └── .cache/
    ├── ab89def0/                        # Slot 2 directory
    └── [missing]                        # Slot 3 was deleted (dead slot)
```

## Slot Lifecycle

### 1. Slot Creation (`create_container`)

When creating a new slot:
1. **First**: Check for "dead" slots (missing directories) from 1 to max
2. **If found**: Reuse that slot number and recreate directory
3. **If none**: Create new slot at (max + 1) and increment counter

```bash
# Example: Counter is 3, slots 1 and 3 exist, slot 2 is dead
create_container() → Reuses slot 2

# Example: Counter is 3, all slots exist
create_container() → Creates slot 4, updates counter to 4
```

### 2. Slot Selection (`determine_next_start_container`)

When launching a container:
1. Iterate through slots 1 to max
2. Skip non-existent directories (never created)
3. Skip slots with running containers
4. Return first available slot

Running container detection:
```bash
docker ps --format "{{.Names}}" | grep "^claudebox-.*-${slot_name}$"
```

### 3. Slot Deletion (Manual)

Users can manually delete slot directories:
- Remove the slot directory (e.g., `rm -rf ~/.claudebox/projects/*/524b9a6e`)
- Slot becomes "dead" and available for reuse
- Counter remains unchanged (for now)

### 4. Counter Pruning (`prune_slot_counter`)

Automatically adjusts counter downward:
1. Find highest slot index with existing directory
2. If highest < counter, update counter to highest
3. Called before listing slots to keep counter accurate

Example:
```
Before: Counter=5, Slots 1,2,3 exist (4,5 deleted)
After:  Counter=3
```

## Critical Design Decisions

### Why Slots Start at 1

- **Slot 0 is conceptual**: Represents the parent project
- **Different hashes**: Ensures slot 1 has different checksum than parent
- **Docker naming**: Parent uses base checksum, slots use derived checksums

### Shared Docker Images

All slots under a project share the **same Docker image**:
- Image name: `claudebox-{parent_folder_name}`
- Only slot data directories differ
- Efficient disk usage and fast slot creation

### Container Naming Convention

Container names include both project and slot identifiers:
```
claudebox-{parent_name}-{slot_checksum}
```

Example: `claudebox-home_rich_myproject_cc618e36-524b9a6e`

## State Indicators

When listing slots (`claudebox slots`):
- ✔️ = Authenticated (has .credentials.json)
- 🔒 = Not authenticated
- 💀 = Removed/dead slot
- 🟢 = Container running
- 🔴 = Container not running

## Examples

### Example 1: Fresh Project
```
$ claudebox create
Creating slot 1 (524b9a6e)
Counter: 0 → 1

$ claudebox create  
Creating slot 2 (ab89def0)
Counter: 1 → 2
```

### Example 2: Slot Reuse
```
Initial state: Slots 1,2,3 exist (counter=3)
$ rm -rf ~/.claudebox/projects/*/ab89def0  # Delete slot 2

$ claudebox create
Reusing dead slot 2 (ab89def0)
Counter: remains 3
```

### Example 3: Counter Pruning
```
Initial: Slots 1,2,3,4,5 exist (counter=5)
Delete slots 4,5 manually

$ claudebox slots  # Triggers prune
Counter: 5 → 3
```

## Implementation Details

### Key Functions

1. **`generate_container_name(path, idx)`**
   - Implements the iterative CRC32 chain
   - Always produces same checksum for same slot index

2. **`create_container(path)`**
   - Handles dead slot detection and reuse
   - Manages counter increment

3. **`prune_slot_counter(path)`**
   - Keeps counter synchronized with actual slots
   - Prevents counter from growing unbounded

4. **`determine_next_start_container(path)`**
   - Finds available slot for running container
   - Checks Docker for running state

### Checksum Algorithm
```bash
generate_container_name() {
    local path="$1" idx="$2"
    local base_crc=$(crc32_string "$path")
    local cur=$base_crc
    
    # Iterative CRC32 chain
    for ((i=0; i<idx; i++)); do
        cur=$(crc32_word "$cur")
    done
    
    printf '%08x' "$cur"
}
```

## What NOT to Change

**CRITICAL**: These design decisions are interdependent. Changing any could break the entire system:

1. **DO NOT change slot numbering to start at 0**
   - Would make slot 0 = parent checksum (collision)
   - Would break existing installations

2. **DO NOT simplify checksum generation**
   - Iterative chain ensures deterministic, unique IDs
   - Direct "parent + index" would be less robust

3. **DO NOT remove dead slot reuse**
   - Prevents unbounded growth of slot directories
   - Maintains efficient resource usage

4. **DO NOT change counter behavior**
   - Up/down movement is intentional
   - Enables slot reuse and cleanup

5. **DO NOT use different Docker images per slot**
   - Shared images are efficient
   - Slots differ only in data, not code

## Troubleshooting

### "No slots available"
- Check if all slots have running containers
- Use `docker ps` to verify container states
- Create new slot with `claudebox create`

### Counter seems wrong
- Run `claudebox slots` to trigger auto-prune
- Check `.project_container_counter` file
- Verify slot directories match counter

### Slot checksum mismatch
- Checksums are deterministic - same input always gives same output
- Verify project path hasn't changed
- Check if using correct slot index

## Summary

The ClaudeBox slot system elegantly handles:
- Multiple authenticated Claude instances per project
- Efficient slot reuse through dead slot detection  
- Dynamic sizing with pruning
- Deterministic, collision-free identifiers
- Shared Docker images for efficiency

This design supports both simple (single slot) and complex (many slots with OAuth flows) use cases while maintaining system integrity and efficiency.