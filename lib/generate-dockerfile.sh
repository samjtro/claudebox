#!/bin/bash
# This script generates a Dockerfile without heredoc issues

cat <<'DOCKERFILE_PART1'
FROM debian:bookworm
ARG USER_ID GROUP_ID USERNAME NODE_VERSION

RUN echo '#!/bin/sh\nexit 101' > /usr/sbin/policy-rc.d && chmod +x /usr/sbin/policy-rc.d

# Install locales first to fix locale warnings
RUN export DEBIAN_FRONTEND=noninteractive && \
    apt-get update -qq && \
    apt-get install -y -qq locales && \
    echo "en_US.UTF-8 UTF-8" > /etc/locale.gen && \
    locale-gen en_US.UTF-8 && \
    rm -rf /var/lib/apt/lists/*

# Set locale environment variables
ENV LANG=en_US.UTF-8 \
    LANGUAGE=en_US:en \
    LC_ALL=en_US.UTF-8

# Install system packages
RUN export DEBIAN_FRONTEND=noninteractive && \
    apt-get update -qq && \
    apt-get install -y -qq \
        curl wget git vim sudo build-essential \
        zsh ncurses-base ncurses-bin python3 python3-pip \
        ca-certificates gnupg lsb-release iptables ipset \
        man-db less htop tmux openssh-client jq ripgrep fd-find bat \
        net-tools iputils-ping dnsutils netcat-openbsd \
        zip unzip gzip bzip2 xz-utils lzma p7zip-full \
        file tree software-properties-common apt-transport-https && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Setup user
RUN groupadd -g ${GROUP_ID} ${USERNAME} && \
    useradd -m -u ${USER_ID} -g ${GROUP_ID} -s /bin/zsh ${USERNAME} && \
    mkdir -p /home/${USERNAME}/.claudebox /home/${USERNAME}/.claudebox-project && \
    chown -R ${USERNAME}:${USERNAME} /home/${USERNAME}

# Install oh-my-zsh
USER ${USERNAME}
RUN sh -c "$(curl -fsSL https://raw.github.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" "" --unattended && \
    sed -i 's/robbyrussell/agnoster/g' ~/.zshrc && \
    echo 'export EDITOR=vim' >> ~/.zshrc && \
    echo 'export VISUAL=vim' >> ~/.zshrc && \
    echo 'export PAGER=less' >> ~/.zshrc && \
    echo 'export LESS="-R"' >> ~/.zshrc && \
    echo 'alias ll="ls -la"' >> ~/.zshrc && \
    echo 'alias la="ls -A"' >> ~/.zshrc && \
    echo 'alias l="ls -CF"' >> ~/.zshrc && \
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc && \
    echo 'if command -v batcat >/dev/null 2>&1; then alias bat=batcat; fi' >> ~/.zshrc && \
    echo 'if command -v fdfind >/dev/null 2>&1; then alias fd=fdfind; fi' >> ~/.zshrc

# Install Node.js via NVM
ENV NVM_DIR=/home/${USERNAME}/.nvm
RUN curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash && \
    . $NVM_DIR/nvm.sh && \
    nvm install ${NODE_VERSION} && \
    nvm use ${NODE_VERSION} && \
    nvm alias default ${NODE_VERSION}

# Install Claude
RUN bash -c "source $NVM_DIR/nvm.sh && \
    nvm use default && \
    npm install -g @anthropic-ai/claude-code"

DOCKERFILE_PART1

# Create firewall script
echo "# Create firewall script"
echo "RUN printf '%s\\\\n' \\"
echo "    '#!/bin/bash' \\"
echo "    'set -euo pipefail' \\"
echo "    'if [ \"\${DISABLE_FIREWALL:-false}\" = \"true\" ]; then' \\"
echo "    '    echo \"Firewall disabled, skipping setup\"' \\"
echo "    '    rm -f \"\$0\"' \\"
echo "    '    exit 0' \\"
echo "    'fi' \\"
echo "    'iptables -F OUTPUT 2>/dev/null || true' \\"
echo "    'iptables -F INPUT 2>/dev/null || true' \\"
echo "    'iptables -A OUTPUT -p udp --dport 53 -j ACCEPT' \\"
echo "    'iptables -A OUTPUT -p tcp --dport 53 -j ACCEPT' \\"
echo "    'iptables -A INPUT -p udp --sport 53 -j ACCEPT' \\"
echo "    'iptables -A OUTPUT -o lo -j ACCEPT' \\"
echo "    'iptables -A INPUT -i lo -j ACCEPT' \\"
echo "    'iptables -A OUTPUT -s 127.0.0.0/8 -d 127.0.0.0/8 -j ACCEPT' \\"
echo "    'iptables -A INPUT -s 127.0.0.0/8 -d 127.0.0.0/8 -j ACCEPT' \\"
echo "    'iptables -A OUTPUT -m state --state ESTABLISHED,RELATED -j ACCEPT' \\"
echo "    'iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT' \\"
echo "    '# Default allowed domains' \\"
echo "    'DEFAULT_DOMAINS=\"api.anthropic.com console.anthropic.com statsig.anthropic.com sentry.io\"' \\"
echo "    '' \\"
echo "    '# Read additional domains from allowlist file if it exists' \\"
echo "    'ALLOWED_DOMAINS=\"\$DEFAULT_DOMAINS\"' \\"
echo "    '# Try project-specific allowlist first, then fall back to global' \\"
echo "    'if [ -f /home/\${USERNAME}/.claudebox-project/firewall/allowlist ]; then' \\"
echo "    '    echo \"Loading project-specific allowlist\"' \\"
echo "    '    while IFS= read -r domain; do' \\"
echo "    '        # Skip comments and empty lines' \\"
echo "    '        [[ \"\$domain\" =~ ^#.* ]] && continue' \\"
echo "    '        [[ -z \"\$domain\" ]] && continue' \\"
echo "    '        # Remove wildcards for now (*.example.com becomes example.com)' \\"
echo "    '        domain=\"\${domain#\\*.}\"' \\"
echo "    '        ALLOWED_DOMAINS=\"\$ALLOWED_DOMAINS \$domain\"' \\"
echo "    '    done < /home/\${USERNAME}/.claudebox-project/firewall/allowlist' \\"
echo "    'elif [ -f /home/\${USERNAME}/.claudebox/allowlist ]; then' \\"
echo "    '    echo \"Loading global allowlist from .claudebox/allowlist\"' \\"
echo "    '    while IFS= read -r domain; do' \\"
echo "    '        # Skip comments and empty lines' \\"
echo "    '        [[ \"\$domain\" =~ ^#.* ]] && continue' \\"
echo "    '        [[ -z \"\$domain\" ]] && continue' \\"
echo "    '        # Remove wildcards for now (*.example.com becomes example.com)' \\"
echo "    '        domain=\"\${domain#\\*.}\"' \\"
echo "    '        ALLOWED_DOMAINS=\"\$ALLOWED_DOMAINS \$domain\"' \\"
echo "    '    done < /home/\${USERNAME}/.claudebox/allowlist' \\"
echo "    'fi' \\"
echo "    '' \\"
echo "    'if command -v ipset >/dev/null 2>&1; then' \\"
echo "    '    ipset destroy allowed-domains 2>/dev/null || true' \\"
echo "    '    ipset create allowed-domains hash:net' \\"
echo "    '    ipset destroy allowed-ips 2>/dev/null || true' \\"
echo "    '    ipset create allowed-ips hash:net' \\"
echo "    '' \\"
echo "    '    for domain in \$ALLOWED_DOMAINS; do' \\"
echo "    '        # Check if it'\"'\"'s an IP range' \\"
echo "    '        if [[ \"\$domain\" =~ ^[0-9]+\\.[0-9]+\\.[0-9]+\\.[0-9]+/[0-9]+\$ ]]; then' \\"
echo "    '            ipset add allowed-ips \$domain 2>/dev/null || true' \\"
echo "    '        else' \\"
echo "    '            # It'\"'\"'s a domain, resolve it' \\"
echo "    '            ips=\$(getent hosts \$domain 2>/dev/null | awk '\"'\"'{print \$1}'\"'\"')' \\"
echo "    '            for ip in \$ips; do' \\"
echo "    '                ipset add allowed-domains \$ip 2>/dev/null || true' \\"
echo "    '            done' \\"
echo "    '        fi' \\"
echo "    '    done' \\"
echo "    '    iptables -A OUTPUT -m set --match-set allowed-domains dst -j ACCEPT' \\"
echo "    '    iptables -A OUTPUT -m set --match-set allowed-ips dst -j ACCEPT' \\"
echo "    'else' \\"
echo "    '    # Fallback without ipset' \\"
echo "    '    for domain in \$ALLOWED_DOMAINS; do' \\"
echo "    '        if [[ \"\$domain\" =~ ^[0-9]+\\.[0-9]+\\.[0-9]+\\.[0-9]+/[0-9]+\$ ]]; then' \\"
echo "    '            iptables -A OUTPUT -d \$domain -j ACCEPT' \\"
echo "    '        else' \\"
echo "    '            # Resolve domain to IPs' \\"
echo "    '            ips=\$(getent hosts \$domain 2>/dev/null | awk '\"'\"'{print \$1}'\"'\"')' \\"
echo "    '            for ip in \$ips; do' \\"
echo "    '                iptables -A OUTPUT -d \$ip -j ACCEPT' \\"
echo "    '            done' \\"
echo "    '        fi' \\"
echo "    '    done' \\"
echo "    'fi' \\"
echo "    'iptables -P OUTPUT DROP' \\"
echo "    'iptables -P INPUT DROP' \\"
echo "    'echo \"Firewall initialized with Anthropic-only access\"' \\"
echo "    'rm -f \"\$0\"' \\"
echo "    > ~/init-firewall.sh"
echo ""
echo "RUN chmod +x ~/init-firewall.sh"
echo ""