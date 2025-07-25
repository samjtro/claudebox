# ClaudeBox Checksum and Naming System

## Overview

ClaudeBox uses a dual-checksum system with 8-character hexadecimal CRC32 hashes for:
1. **Path-based identification** - Avoiding folder name collisions
2. **Content-based validation** - Detecting when rebuilds are needed

All checksums are:
- **8 characters** - CRC32 produces 32-bit checksums (8 hex digits)
- **Lowercase** - For Docker compatibility
- **POSIX-compatible** - Works on both macOS and Linux

## Checksum Types

### 1. Project Path Checksum
- **Purpose**: Unique project identification
- **Input**: Full project directory path (before normalization)
- **Example**: `/home/Rich/MyProject` → `cc618e36`
- **Used in**:
  - Folder name: `~/.claudebox/projects/home_rich_myproject_cc618e36/`
  - Docker image: `claudebox-cc618e36`

### 2. Profiles Content Checksum  
- **Purpose**: Detect when profiles have changed
- **Input**: Contents of `profiles.ini` file
- **Example**: File contents → `ab12cd34`
- **Stored in**: Docker image label `claudebox_profiles_crc`
- **Used for**: Triggering rebuilds when profiles change

### 3. Slot Checksum
- **Purpose**: Unique slot identification
- **Input**: Previous slot's checksum (iterative CRC32 chain)
- **Algorithm**: 
  - Slot 0: CRC32(project_path) → `cc618e36`
  - Slot 1: CRC32(slot_0_checksum) → `524b9a6e`
  - Slot 2: CRC32(slot_1_checksum) → `ab89def0`
  - Slot n: CRC32(slot_{n-1}_checksum)
- **Example**: If parent is `cc618e36`, slot 1 is CRC32(`cc618e36`) → `524b9a6e`
- **Note**: Each slot checksum is derived from the previous slot's checksum, creating a chain

## Directory Structure

```
~/.claudebox/
├── projects/
│   ├── home_rich_myproject_cc618e36/      # Path checksum in folder name
│   │   ├── profiles.ini                   # Content gets checksummed
│   │   ├── .docker_layer_checksums        # Stores build state
│   │   └── 524b9a6e/                      # Slot 1 (derived from parent)
│   │       └── .claude/
│   └── home_user_project_ab123def/
│       └── profiles.ini
```

## Docker Naming Convention

All Docker images use the prefix `claudebox-` followed by the appropriate checksum:

### Legacy Architecture (Being Replaced)
```
claudebox-cc618e36    # Project image (monolithic)
claudebox-ab123def    # Another project (monolithic)
```

### Core Image Architecture (Approved)
```
~/.claudebox/
├── core/
│   ├── checksum              # MD5 of core Dockerfile
│   └── image: claudebox-core-{checksum}
├── projects/
│   ├── home_rich_myproject_cc618e36/
│   │   ├── image: claudebox-cc618e36  # FROM claudebox-core-{checksum}
│   │   ├── profiles.ini
│   │   └── 524b9a6e/        # Slot 1
│   │       └── .claude/
│   └── home_user_other_ab123def/
│       └── image: claudebox-ab123def  # FROM claudebox-core-{checksum}
```

**Benefits of Core Image Architecture**:
- Shared base layer reduces disk usage
- Faster project image builds (only profile layers rebuild)
- Consistent claudebox- prefix across all images
- Core updates benefit all projects automatically

**Image Naming**:
- Core: `claudebox-core-{core_dockerfile_md5}`
- Projects: `claudebox-{project_path_crc32}` (unchanged)
- All project images would use: `FROM claudebox-core-{checksum}`

## Checksum Calculation

### Linux (using perl):
```bash
checksum=$(perl -e 'use String::CRC32; printf "%08x\n", crc32($ARGV[0])' "$string")
```

### macOS (using cksum):
```bash
checksum=$(printf "%08x" $(cksum <<< "$string" | cut -d' ' -f1))
```

### In ClaudeBox:
The `get_crc32()` function in `common.sh` handles platform differences automatically.

## Change Detection Flow

1. **Build Time**:
   - Calculate CRC32 of `profiles.ini`
   - Store as Docker label: `--label claudebox_profiles_crc=ab12cd34`

2. **Runtime Check**:
   ```bash
   # Get current profiles.ini checksum
   current_crc=$(get_crc32 < profiles.ini)
   
   # Get image's stored checksum
   image_crc=$(docker image inspect --format '{{.Config.Labels.claudebox_profiles_crc}}' "$IMAGE_NAME")
   
   # Compare
   if [[ "$current_crc" != "$image_crc" ]]; then
       # Rebuild needed
   fi
   ```

## File Storage

### Project Container Folder Contents:
- `profiles.ini` - Selected profiles and installed packages
- `.docker_layer_checksums` - MD5 checksums of build components:
  ```
  DOCKERFILE_CHECKSUM={md5}
  SCRIPTS_CHECKSUM={md5}
  PROFILES_CHECKSUM={md5}
  PROFILES_FILE_CHECKSUM={md5}
  ```

### Important Notes:

1. **Case Sensitivity**: Original paths may have mixed case, but:
   - Folder names are normalized to lowercase
   - Checksums are always lowercase
   - Docker images require lowercase

2. **Collision Avoidance**: Two different paths could theoretically produce the same CRC32, but:
   - Folder name includes normalized path components too
   - 8-character CRC32 has 4.3 billion possible values
   - Collision probability is acceptably low for local development

3. **Slots Share Images**: All slots under a parent use the same Docker image:
   - Parent: `claudebox-cc618e36`
   - Slot 1: Uses `claudebox-cc618e36`
   - Slot 2: Uses `claudebox-cc618e36`
   - Only slot data folders differ

This system ensures consistent, portable, and collision-resistant naming across all platforms while maintaining Docker compatibility.

## Critical Warnings

### DO NOT MODIFY These Core Algorithms:
1. **CRC32 calculation methods** - Platform-specific implementations are intentional
2. **Iterative slot checksum chain** - Changing this breaks existing slots
3. **8-character lowercase format** - Docker compatibility requirement
4. **Path normalization rules** - Ensures consistent project identification

### Related Documentation
- See `slot-management-system.md` for complete slot lifecycle and management rules
- The checksum system and slot management are tightly integrated - changes to one affect the other

## Common Mistakes to Avoid

1. **Attempting to "simplify" slot checksums**:
   ```bash
   # WRONG: Direct concatenation
   slot_checksum = CRC32(parent + slot_number)
   
   # CORRECT: Iterative chain
   slot_checksum = CRC32(previous_slot_checksum)
   ```

2. **Changing checksum length**:
   - Must remain 8 characters for Docker compatibility
   - Longer checksums break existing installations

3. **Case sensitivity issues**:
   - Always lowercase for Docker
   - Original paths may have mixed case, but output is normalized

4. **Assuming slot paths matter**:
   - Slot checksums are NOT based on slot directory paths
   - They're based purely on the iterative CRC32 chain