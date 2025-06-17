#!/bin/bash
ENABLE_SUDO=false
DISABLE_FIREWALL=false
while [[ $# -gt 0 ]]; do
    case "$1" in
        --dangerously-enable-sudo) ENABLE_SUDO=true; shift ;;
        --dangerously-disable-firewall) DISABLE_FIREWALL=true; shift ;;
        *) break ;;
    esac
done
if [ "$ENABLE_SUDO" = "true" ]; then
    usermod -aG sudo DOCKERUSER
    echo 'DOCKERUSER ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/dockeruser
    chmod 0440 /etc/sudoers.d/dockeruser
fi
export DISABLE_FIREWALL
if [ ! -f /home/DOCKERUSER/.firewall-initialized ]; then
    if [ -f /home/DOCKERUSER/init-firewall.sh ]; then
        su DOCKERUSER -c "bash /home/DOCKERUSER/init-firewall.sh"
        touch /home/DOCKERUSER/.firewall-initialized
    fi
fi
# Auto install packages from install.list
install_list="/home/DOCKERUSER/.claudebox-project/install.list"
installed_file="/home/DOCKERUSER/.claudebox-project/.installed"
if [ -f "$install_list" ]; then
    if [ ! -f "$installed_file" ] || [ "$install_list" -nt "$installed_file" ]; then
        DEBIAN_FRONTEND=noninteractive apt-get update
        cat "$install_list" | grep -v '^#' | grep -v '^$' | xargs -r apt-get install -y
        apt-get clean && rm -rf /var/lib/apt/lists/*
        cp "$install_list" "$installed_file"
    fi
fi
# For Python profile, install UV and setup venv
if [ -f /home/DOCKERUSER/.claudebox-project/profiles/.has_python ]; then
    if [ ! -d /home/DOCKERUSER/.claudebox-project/.venv ]; then
        if ! command -v uv >/dev/null 2>&1; then
            curl -LsSf https://astral.sh/uv/install.sh | sh
            export PATH="/root/.cargo/bin:$PATH"
        fi
        if command -v uv >/dev/null 2>&1; then
            su - DOCKERUSER -c "uv venv /home/DOCKERUSER/.claudebox-project/.venv"
            if [ -f /workspace/pyproject.toml ]; then
                su - DOCKERUSER -c "cd /workspace && uv sync"
            else
                su - DOCKERUSER -c "uv pip install --python /home/DOCKERUSER/.claudebox-project/.venv/bin/python ipython black pylint mypy flake8 pytest ruff"
            fi
        fi

        for shell_rc in /home/DOCKERUSER/.zshrc /home/DOCKERUSER/.bashrc; do
            if ! grep -q "source /home/DOCKERUSER/.claudebox-project/.venv/bin/activate" "$shell_rc"; then
                echo 'if [ -f /home/DOCKERUSER/.claudebox-project/.venv/bin/activate ]; then source /home/DOCKERUSER/.claudebox-project/.venv/bin/activate; fi' >> "$shell_rc"
            fi
        done
    fi
fi

cd /home/DOCKERUSER
# Check if we're in shell mode
if [[ "$1" == "--shell-mode" ]]; then
    shift  # Remove --shell-mode flag
    exec su DOCKERUSER -c "source /home/DOCKERUSER/.nvm/nvm.sh && cd /workspace && exec /bin/zsh"
else
    # Build command with properly quoted arguments
    cmd="cd /workspace && /home/DOCKERUSER/claude-wrapper"
    for arg in "$@"; do
        # Escape single quotes in the argument
        escaped_arg=$(echo "$arg" | sed "s/'/'\\\\''/g")
        cmd="$cmd '$escaped_arg'"
    done
    exec su DOCKERUSER -c "$cmd"
fi