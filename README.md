# MongoDB Backup & Restore Script

Python script for backing up and restoring MongoDB between servers using an SSH tunnel. This script allows you to safely back up a MongoDB database from a production server and restore it to a replica server.

## 🚀 Features

- **SSH Tunnel**: Secure connection using SSH tunnel to access remote MongoDB
- **Selective Restore**: Restore all databases except the `admin` database
- **Logging**: Complete logging system with daily rotation and automatic cleanup
- **Error Handling**: Comprehensive error handling
- **Configuration File**: Separate configuration for security
- **Connection Testing**: Test SSH connection before starting the process
- **Cleanup**: Automatically clean up SSH tunnel and temporary files

## 📋 Prerequisites

### Required Software

- Python 3.6+
- MongoDB Tools (`mongodump`, `mongorestore`)
- SSH client
- `netcat` (`nc`) for connection testing

### Install MongoDB Tools

**Ubuntu/Debian:**

```bash
sudo apt-get install mongodb-database-tools
```

**CentOS/RHEL:**

```bash
sudo yum install mongodb-database-tools
```

**MacOS:**

```bash
brew install mongodb/brew/mongodb-database-tools
```

## 🔧 Installation & Configuration

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/mongodb-backup-restore.git
cd mongodb-backup-restore
```

### 2. Setup Configuration

```bash
# Copy the example configuration file
cp config.example.json config.json

# Edit the configuration file to suit your environment
nano config.json
```

### 3. Configuration File (`config.json`)

Edit the `config.json` file with your server details:

```json
{
  "ssh": {
    "user": "your-ssh-username",
    "host": "your-production-server-ip"
  },
  "mongodb": {
    "remote_port": 27017,
    "local_port": 27017,
    "local_tunnel_port": 27018,
    "local_restore_uri": "mongodb://username:password@localhost:27017/?authSource=admin"
  },
  "backup": {
    "dump_path": "backup-db"
  },
  "logging": {
    "log_dir": "log-mongo",
    "retention_days": 15
  }
}
```

**Configuration Parameters:**

- `ssh.user`: SSH username for the production server
- `ssh.host`: IP address or hostname of the production server
- `mongodb.remote_port`: MongoDB port on the production server (default: 27017)
- `mongodb.local_port`: MongoDB port on the local server (default: 27017)
- `mongodb.local_tunnel_port`: Local port used for SSH tunnel (default: 27018)
- `mongodb.local_restore_uri`: Local MongoDB URI with credentials
- `backup.dump_path`: Directory to temporarily store backup files
- `logging.log_dir`: Directory for log files
- `logging.retention_days`: Number of days to retain log files

### 4. Setup SSH Key Authentication (Recommended)

```bash
# Generate SSH key pair if you don't have one
ssh-keygen -t rsa -b 4096 -C "your_email@example.com"

# Copy the public key to the production server
ssh-copy-id your-ssh-username@your-production-server-ip
```

## 🎯 Usage

### Run the Script

```bash
python3 mongo-backup-restore.py
```

### Configuration Checklist

Before running the script, make sure:

1. SSH connection to the production server works without a password
2. MongoDB tools are installed
3. `local_tunnel_port` is not already in use by another application
4. Local MongoDB user has write permissions

### Sample Output

```
2024-01-15 10:30:00,123 - INFO - ============================================================
2024-01-15 10:30:00,124 - INFO - STARTING MONGODB BACKUP AND RESTORE PROCESS
2024-01-15 10:30:00,125 - INFO - Source: max@192.168.1.100:27017
2024-01-15 10:30:00,126 - INFO - Target: localhost:27017
2024-01-15 10:30:00,127 - INFO - ============================================================
2024-01-15 10:30:00,128 - INFO - Testing SSH connection...
2024-01-15 10:30:01,200 - INFO - SSH connection test successful
2024-01-15 10:30:01,201 - INFO - Opening SSH tunnel...
2024-01-15 10:30:06,300 - INFO - SSH tunnel established and accessible
2024-01-15 10:30:06,301 - INFO - Starting: mongodump from remote
...
2024-01-15 10:35:20,500 - INFO - ALL BACKUP AND RESTORE PROCESSES COMPLETED SUCCESSFULLY!
```

## 📁 Directory Structure

```
mongodb-backup-restore/
├── mongo-backup-restore.py    # Main script
├── config.example.json        # Configuration template
├── config.json                # Actual configuration (not committed to Git)
├── .gitignore                 # Git ignore rules
├── README.md                  # This documentation
├── backup-db/                 # Temporary backup directory
└── log-mongo/                 # Log files directory
    ├── mongo-backup-2024-01-15.log
    ├── mongo-backup-2024-01-16.log
    └── ...
```

## 🔐 Security

### Files Not Committed to Git

- `config.json` - Contains credentials and IPs
- `backup-db/` - Temporary backup directory
- `log-mongo/` - Logs that may contain sensitive info

### Best Practices

1. **Do not commit `config.json`** to version control
2. **Use SSH key authentication** for passwordless secure access
3. **Change default MongoDB passwords**
4. **Restrict SSH access** to known IPs only
5. **Back up `config.json`** securely and separately

## 🛠️ Troubleshooting

### SSH Connection Failed

```bash
# Test manual SSH connection
ssh your-ssh-username@your-production-server-ip

# Check SSH config
cat ~/.ssh/config
```

### MongoDB Connection Issues

```bash
# Test local MongoDB connection
mongo mongodb://localhost:27017

# Check MongoDB service status
sudo systemctl status mongod
```

### Port Already in Use

```bash
# Check if port is in use
netstat -tulpn | grep :27018

# Kill existing SSH tunnels
pkill -f "ssh.*your-production-server-ip"
```

### Permission Denied

```bash
# Check MongoDB user permissions
mongo mongodb://localhost:27017
> use admin
> db.runCommand({usersInfo: "your-username"})
```

## 📝 Logging

The script uses a logging system with:

- **Daily rotation**: A new log file is created daily
- **Automatic cleanup**: Old logs deleted based on `retention_days`
- **Dual output**: Logs written to file and printed to console

### Log Format

```
2024-01-15 10:30:00,123 - INFO - Log message
2024-01-15 10:30:01,124 - ERROR - Error message
```

### Log File Location

```
log-mongo/
├── mongo-backup-2024-01-15.log
├── mongo-backup-2024-01-16.log
└── mongo-backup-2024-01-17.log
```
