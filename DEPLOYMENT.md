# Deployment Guide

This guide covers deploying the updated trading bot with all the critical fixes.

## Prerequisites

- Python 3.11 or higher
- Node.js 18 or higher
- MongoDB instance (local or cloud)

## Installation Steps

### 1. Backend Setup

```bash
cd backend

# Create a fresh virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies (cleaned requirements.txt)
pip install -r requirements.txt

# Create environment file
cp .env.example .env  # Or create new .env

# Edit .env with your configuration
nano .env
```

Required environment variables in `.env`:
```env
MONGO_URL=mongodb://localhost:27017
DB_NAME=trading_bot
CORS_ORIGINS=http://localhost:3000
```

### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Create environment file
cp .env.example .env  # Or create new .env

# Edit .env with backend URL
nano .env
```

Required environment variables in `.env`:
```env
REACT_APP_BACKEND_URL=http://localhost:8000
```

### 3. Data Directory

The `backend/data/` directory will be created automatically on first run.

To pre-create it:
```bash
mkdir -p backend/data
```

Data files will be automatically generated:
- `active_positions.json`
- `closed_positions.json`
- `stats.json`
- `seen_tokens.json`

## Running the Application

### Development Mode

**Terminal 1 - Backend:**
```bash
cd backend
source venv/bin/activate
uvicorn server:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm start
```

Access the UI at: `http://localhost:3000`

### Production Mode

**Backend:**
```bash
cd backend
source venv/bin/activate
uvicorn server:app --host 0.0.0.0 --port 8000 --workers 4
```

**Frontend:**
```bash
cd frontend
npm run build
# Serve the build folder with nginx or similar
```

## Docker Deployment (Optional)

Create `Dockerfile` in backend directory:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:
```bash
docker build -t trading-bot-backend .
docker run -p 8000:8000 -v $(pwd)/data:/app/data trading-bot-backend
```

## Verification Steps

After deployment, verify the following:

### 1. Backend Health Check
```bash
curl http://localhost:8000/api/
# Should return: {"message": "Solana Trading Bot API"}
```

### 2. Data Persistence
```bash
# Start the bot, create some positions, then restart
# Check that data persists:
ls -la backend/data/
# Should show JSON files
```

### 3. Thread Safety
Monitor logs for any race condition indicators:
```bash
# In backend logs, should NOT see:
# - Duplicate sell attempts
# - Position already closing errors
```

### 4. Error Handling
Test bot control in UI:
- Start bot with valid config → Success message
- Start bot without config → Specific error message

## Migration from Previous Version

If migrating from the old in-memory version:

1. **Backup old data** (if you had any persistence mechanism)
2. **Deploy new code**
3. **First run will create fresh data files**
4. Old in-memory data will be lost (expected)

**Important:** There is no automatic migration from the old version as it had no persistence.

## Monitoring

### Log Files

Backend logs:
```bash
# View live logs
tail -f backend/logs/app.log  # If logging to file

# Or check systemd logs if using systemd
journalctl -u trading-bot -f
```

### Data Files

Monitor data file sizes:
```bash
watch -n 60 'ls -lh backend/data/'
```

### Health Checks

Set up health check endpoints:
- Backend: `http://localhost:8000/api/bot/status`
- Expected response includes `running` and `paper_trading` status

## Backup Strategy

### Automated Backups

Create a cron job for daily backups:

```bash
# Edit crontab
crontab -e

# Add daily backup at 2 AM
0 2 * * * cd /path/to/project && tar -czf backups/data_$(date +\%Y\%m\%d).tar.gz backend/data/
```

### Manual Backup

```bash
# Backup data directory
cp -r backend/data backend/data_backup_$(date +%Y%m%d_%H%M%S)

# Or create compressed archive
tar -czf data_backup_$(date +%Y%m%d_%H%M%S).tar.gz backend/data
```

## Troubleshooting

### Issue: "Module not found" errors
**Solution:** Ensure virtual environment is activated and dependencies installed:
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### Issue: "Permission denied" on data files
**Solution:** Ensure proper permissions:
```bash
chmod -R 755 backend/data
chown -R $USER:$USER backend/data
```

### Issue: Bot doesn't start
**Solution:** Check logs for specific error:
```bash
# Check backend logs
tail -f backend/logs/app.log

# Check if MongoDB is running
systemctl status mongodb
```

### Issue: Data not persisting
**Solution:** 
1. Check if data directory exists and is writable
2. Verify file permissions
3. Check backend logs for file I/O errors

### Issue: WebSocket disconnects frequently
**Solution:**
1. Check CORS settings in backend
2. Verify WebSocket URL in frontend matches backend
3. Check for network issues or firewalls

## Performance Tuning

### Backend

For production, increase uvicorn workers:
```bash
uvicorn server:app --workers 4 --host 0.0.0.0 --port 8000
```

### Database

Ensure MongoDB has proper indexes:
```javascript
// In MongoDB shell
db.positions.createIndex({ "mint": 1 })
db.positions.createIndex({ "status": 1 })
```

### File I/O

Data files are small and write infrequently. No tuning needed unless:
- You have thousands of positions (unlikely)
- Very high-frequency trading

## Security Considerations

1. **Never commit `.env` files** - Already in `.gitignore`
2. **Protect private keys** - Store in environment variables, not code
3. **Use HTTPS in production** - Set up SSL/TLS
4. **Restrict CORS** - Set specific origins in production
5. **MongoDB authentication** - Enable auth in production
6. **Firewall rules** - Only expose necessary ports

## Systemd Service (Linux)

Create `/etc/systemd/system/trading-bot.service`:

```ini
[Unit]
Description=Trading Bot Backend
After=network.target mongodb.service

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/project/backend
Environment="PATH=/path/to/project/backend/venv/bin"
ExecStart=/path/to/project/backend/venv/bin/uvicorn server:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable trading-bot
sudo systemctl start trading-bot
sudo systemctl status trading-bot
```

## Updates and Maintenance

### Updating Code

```bash
# Backup data first
cp -r backend/data backend/data_backup

# Pull latest code
git pull

# Update dependencies
cd backend
source venv/bin/activate
pip install -r requirements.txt

# Restart services
sudo systemctl restart trading-bot
```

### Cleaning Old Data

Closed positions are automatically limited to last 1000.
Seen tokens automatically limited to last 10,000.

To manually clean:
```bash
# Stop bot first
cd backend/data

# Backup
cp closed_positions.json closed_positions.json.bak

# Edit or truncate files as needed
```

## Support

For issues or questions:
1. Check the logs first
2. Verify all prerequisites are met
3. Review FIXES_SUMMARY.md for implementation details
4. Check GitHub issues for similar problems

## Change Log

See `FIXES_SUMMARY.md` for detailed list of all fixes and changes.
