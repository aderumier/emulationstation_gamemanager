# GameManager .deb Package Installation

## Quick Installation

### 1. Install the Package
```bash
sudo dpkg -i gamemanager_1.0-1_all.deb
```

### 2. Fix Dependencies (if needed)
```bash
sudo apt-get install -f
```

### 3. Start the Service
```bash
sudo systemctl start gamemanager
```

### 4. Enable Auto-start (optional)
```bash
sudo systemctl enable gamemanager
```

## Verification

### Check Service Status
```bash
sudo systemctl status gamemanager
```

### View Logs
```bash
sudo journalctl -u gamemanager -f
```

### Access the Application
Open your web browser and navigate to:
```
http://localhost:5000
```

## Configuration

### Main Configuration
Edit the configuration file:
```bash
sudo nano /opt/gamemanager/var/config/config.json
```

### Add Game ROMs
Place your game ROMs in:
```
/mnt/roms/
```

### Media Files
Media files will be stored in:
```
/mnt/roms/<system>/media/
```

## Management Commands

### Start Service
```bash
sudo systemctl start gamemanager
```

### Stop Service
```bash
sudo systemctl stop gamemanager
```

### Restart Service
```bash
sudo systemctl restart gamemanager
```

### Check Status
```bash
sudo systemctl status gamemanager
```

### View Logs
```bash
sudo journalctl -u gamemanager -f
```

## Uninstallation

### Remove Package
```bash
sudo dpkg -r gamemanager
```

The uninstaller will ask if you want to:
- Remove application data directories (configuration, logs, temporary data)
- Remove the gamemanager user account

**Note**: Your game ROMs and media files in `/mnt/roms/` will be preserved during uninstallation.

## File Locations

- **Application**: `/opt/gamemanager/`
- **Configuration**: `/opt/gamemanager/var/config/`
- **Game ROMs**: `/mnt/roms/`
- **Media Files**: `/mnt/roms/<system>/media/`
- **Logs**: `/opt/gamemanager/var/task_logs/`
- **Service File**: `/etc/systemd/system/gamemanager.service`

## Troubleshooting

### Service Won't Start
1. Check logs: `sudo journalctl -u gamemanager -f`
2. Verify dependencies: `sudo apt-get install -f`
3. Check permissions: `ls -la /opt/gamemanager/`

### Permission Issues
```bash
sudo chown -R gamemanager:gamemanager /opt/gamemanager
```

### Port Already in Use
Edit the configuration file and change the port:
```bash
sudo nano /opt/gamemanager/var/config/config.json
```

Change the port in the server section:
```json
"server": {
    "host": "0.0.0.0",
    "port": 5001
}
```

Then restart the service:
```bash
sudo systemctl restart gamemanager
```

## Support

For issues and support, please refer to:
- README.md in `/opt/gamemanager/`
- Documentation in `/usr/share/doc/gamemanager/`
