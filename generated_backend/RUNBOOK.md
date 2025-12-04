# Operational Runbook: Azure AI Processor

## 1. Deployment
All code changes should be pushed to the `main` branch on GitHub. This triggers the automated pipeline.
- **Check Status:** [GitHub Actions Tab](https://github.com/American-Power-Systems/OllamaQuickBase/actions)

## 2. API Keys & Secrets
Sensitive values are stored in **Azure Environment Variables** (via systemd service files) or **User Environment** (`~/.env_report`).

- **Rotate API Key:**
  1. SSH into server.
  2. Edit `/etc/systemd/system/ai-api.service`.
  3. Update `Environment="API_KEY=new_key_here"`.
  4. Run `sudo systemctl daemon-reload && sudo systemctl restart ai-api`.

- **Update Email Credentials:**
  1. Edit `~/.env_report`.
  2. Update values.

## 3. Service Management
If the API or Workers seem stuck, restart them manually.

```bash
# Restart API
sudo systemctl restart ai-api

# Restart Standard Worker (High/Default/Low)
sudo systemctl restart ai-worker

# Restart Heavy Worker (Long Docs)
sudo systemctl restart ai-worker-heavy

# Restart Nginx (Web Server/SSL)
sudo systemctl restart nginx
```
