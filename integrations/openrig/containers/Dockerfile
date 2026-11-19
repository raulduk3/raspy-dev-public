FROM node:24.14.0-bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends tmux git ripgrep ca-certificates python3 make g++ \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /opt/openrig
RUN npm install --omit=dev --save-exact @openrig/cli@0.5.14 @openai/codex@0.144.6 @anthropic-ai/claude-code@2.1.280 @earendil-works/pi-coding-agent@0.87.1
ENV PATH="/opt/openrig/node_modules/.bin:${PATH}" HOME=/home/node OPENRIG_HOME=/home/node/.openrig CODEX_HOME=/home/node/.codex CLAUDE_CONFIG_DIR=/home/node/.claude
COPY entrypoint.sh /usr/local/bin/account-environment
USER node
# Session naming (docs/session-naming.md): `bin/ai-title-bundle > integrations/openrig/containers/naming-install.py` before the build.
COPY --chown=node naming-install.py /tmp/naming-install.py
RUN mkdir -p /home/node/.claude /home/node/.codex && python3 /tmp/naming-install.py install && rm /tmp/naming-install.py
WORKDIR /workspace
ENTRYPOINT ["/usr/local/bin/account-environment"]
