# 🛡️ NanoPD Development Rules

This file outlines the strict rules and guidelines that must be followed when developing or contributing to the NanoPD project.

## 1. Git & Version Control Protocol

### 🚫 STRICTLY PROHIBITED: Do not push `.json` files to GitHub
Under **no circumstances** should any `.json` files be pushed to the remote GitHub repository.
- These files often contain sensitive user telemetry, local configuration paths, or private configuration data.
- **Verification**: The `.gitignore` file must always include `*.json` to actively block these files from being tracked.
- **Double Check**: Before running `git commit`, always review your staging area (`git status`) to guarantee no JSON files have slipped through.

### 🚫 STRICTLY PROHIBITED: Do not push Streamlit Secrets
Never commit or push `.streamlit/secrets.toml`. This file is strictly for local credentials, API keys, and environment variables.

## 2. UI & Aesthetics Guidelines

### 🎨 Pixel-Perfect UI
- **Typography**: Enforce strict monospace typography (`var(--code-font, monospace)`) for any data tables, hardware diagnostics, and hex dumps to maintain the "hacker terminal" aesthetic.
- **Components**: Avoid using Streamlit's default `st.table` when fine-grained aesthetic control is needed. Prefer native HTML table rendering or compact `<pre>`/`div` blocks.
- **Alignment**: Keep UI elements perfectly aligned. If Streamlit's default margins misalign components, adjust them via `vertical_alignment="bottom"` on columns or via explicit CSS wrappers.
