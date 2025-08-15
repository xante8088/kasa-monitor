#!/bin/bash

# Backup management script for Kasa Monitor
# Copyright (C) 2025 Kasa Monitor Contributors

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BACKUP_DIR="${BACKUP_DIR:-$PROJECT_ROOT/backups}"
DB_PATH="${DB_PATH:-$PROJECT_ROOT/kasa_monitor.db}"
MAX_BACKUPS="${MAX_BACKUPS:-30}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

create_backup_dir() {
    if [ ! -d "$BACKUP_DIR" ]; then
        log_info "Creating backup directory: $BACKUP_DIR"
        mkdir -p "$BACKUP_DIR"
    fi
}

backup_database() {
    local backup_file="$BACKUP_DIR/db_backup_${TIMESTAMP}.sqlite"
    
    log_info "Backing up database to: $backup_file"
    
    if [ ! -f "$DB_PATH" ]; then
        log_error "Database file not found: $DB_PATH"
        return 1
    fi
    
    # Create backup using sqlite3 backup command
    sqlite3 "$DB_PATH" ".backup '$backup_file'"
    
    # Compress backup
    log_info "Compressing backup..."
    gzip "$backup_file"
    backup_file="${backup_file}.gz"
    
    # Calculate checksum
    if command -v sha256sum &> /dev/null; then
        sha256sum "$backup_file" > "${backup_file}.sha256"
    elif command -v shasum &> /dev/null; then
        shasum -a 256 "$backup_file" > "${backup_file}.sha256"
    fi
    
    log_info "Backup created: $backup_file"
    
    # Verify backup
    verify_backup "$backup_file"
}

backup_config() {
    local backup_file="$BACKUP_DIR/config_backup_${TIMESTAMP}.tar.gz"
    
    log_info "Backing up configuration files to: $backup_file"
    
    # Create list of config files to backup
    local config_files=(
        ".env"
        "docker-compose.yml"
        "docker-compose.*.yml"
        "prometheus/prometheus.yml"
        "prometheus/alert_rules.yml"
        "grafana/dashboards/*.json"
        "version.json"
    )
    
    # Change to project root
    cd "$PROJECT_ROOT"
    
    # Create tar archive
    tar -czf "$backup_file" "${config_files[@]}" 2>/dev/null || true
    
    log_info "Configuration backup created: $backup_file"
}

backup_full() {
    local backup_file="$BACKUP_DIR/full_backup_${TIMESTAMP}.tar.gz"
    
    log_info "Creating full backup to: $backup_file"
    
    # Create temporary directory for staging
    local temp_dir=$(mktemp -d)
    
    # Copy database
    if [ -f "$DB_PATH" ]; then
        cp "$DB_PATH" "$temp_dir/kasa_monitor.db"
    fi
    
    # Copy configuration files
    cp -r "$PROJECT_ROOT/.env" "$temp_dir/" 2>/dev/null || true
    cp -r "$PROJECT_ROOT/docker-compose"*.yml "$temp_dir/" 2>/dev/null || true
    
    # Copy data directory if exists
    if [ -d "$PROJECT_ROOT/data" ]; then
        cp -r "$PROJECT_ROOT/data" "$temp_dir/"
    fi
    
    # Create archive
    cd "$temp_dir"
    tar -czf "$backup_file" .
    
    # Cleanup
    rm -rf "$temp_dir"
    
    log_info "Full backup created: $backup_file"
}

verify_backup() {
    local backup_file="$1"
    
    log_info "Verifying backup: $backup_file"
    
    if [ ! -f "$backup_file" ]; then
        log_error "Backup file not found: $backup_file"
        return 1
    fi
    
    # Check if file is valid gzip
    if [[ "$backup_file" == *.gz ]]; then
        if ! gzip -t "$backup_file" 2>/dev/null; then
            log_error "Backup file is corrupted: $backup_file"
            return 1
        fi
    fi
    
    log_info "Backup verification passed"
}

restore_database() {
    local backup_file="$1"
    
    if [ -z "$backup_file" ]; then
        log_error "No backup file specified"
        return 1
    fi
    
    if [ ! -f "$backup_file" ]; then
        log_error "Backup file not found: $backup_file"
        return 1
    fi
    
    log_warning "This will replace the current database. Continue? (y/n)"
    read -r response
    if [[ "$response" != "y" ]]; then
        log_info "Restore cancelled"
        return 0
    fi
    
    # Create backup of current database
    if [ -f "$DB_PATH" ]; then
        log_info "Backing up current database..."
        cp "$DB_PATH" "${DB_PATH}.before_restore_${TIMESTAMP}"
    fi
    
    # Decompress if needed
    local restore_file="$backup_file"
    if [[ "$backup_file" == *.gz ]]; then
        log_info "Decompressing backup..."
        restore_file="${backup_file%.gz}"
        gunzip -c "$backup_file" > "$restore_file"
    fi
    
    # Restore database
    log_info "Restoring database..."
    cp "$restore_file" "$DB_PATH"
    
    # Cleanup temporary file
    if [[ "$backup_file" == *.gz ]]; then
        rm "$restore_file"
    fi
    
    log_info "Database restored successfully"
}

cleanup_old_backups() {
    log_info "Cleaning up old backups (keeping last $MAX_BACKUPS)..."
    
    # Count database backups
    local db_backup_count=$(ls -1 "$BACKUP_DIR"/db_backup_*.gz 2>/dev/null | wc -l)
    
    if [ "$db_backup_count" -gt "$MAX_BACKUPS" ]; then
        local to_delete=$((db_backup_count - MAX_BACKUPS))
        log_info "Deleting $to_delete old database backups..."
        
        ls -1t "$BACKUP_DIR"/db_backup_*.gz | tail -n "$to_delete" | while read -r file; do
            log_info "Deleting: $(basename "$file")"
            rm "$file"
            rm -f "${file}.sha256"
        done
    fi
    
    # Count config backups
    local config_backup_count=$(ls -1 "$BACKUP_DIR"/config_backup_*.tar.gz 2>/dev/null | wc -l)
    
    if [ "$config_backup_count" -gt "$MAX_BACKUPS" ]; then
        local to_delete=$((config_backup_count - MAX_BACKUPS))
        log_info "Deleting $to_delete old config backups..."
        
        ls -1t "$BACKUP_DIR"/config_backup_*.tar.gz | tail -n "$to_delete" | while read -r file; do
            log_info "Deleting: $(basename "$file")"
            rm "$file"
        done
    fi
}

list_backups() {
    log_info "Available backups in $BACKUP_DIR:"
    
    echo -e "\nDatabase Backups:"
    ls -lh "$BACKUP_DIR"/db_backup_*.gz 2>/dev/null | awk '{print "  " $9 " (" $5 ")"}'
    
    echo -e "\nConfiguration Backups:"
    ls -lh "$BACKUP_DIR"/config_backup_*.tar.gz 2>/dev/null | awk '{print "  " $9 " (" $5 ")"}'
    
    echo -e "\nFull Backups:"
    ls -lh "$BACKUP_DIR"/full_backup_*.tar.gz 2>/dev/null | awk '{print "  " $9 " (" $5 ")"}'
}

schedule_backup() {
    log_info "Setting up automated backup schedule..."
    
    # Create cron job
    local cron_cmd="0 2 * * * $SCRIPT_DIR/backup_manager.sh --auto >/dev/null 2>&1"
    
    # Check if cron job already exists
    if crontab -l 2>/dev/null | grep -q "backup_manager.sh"; then
        log_warning "Backup cron job already exists"
    else
        # Add cron job
        (crontab -l 2>/dev/null; echo "$cron_cmd") | crontab -
        log_info "Backup scheduled daily at 2:00 AM"
    fi
}

# Main script logic
main() {
    local action="$1"
    
    case "$action" in
        --backup|-b)
            create_backup_dir
            backup_database
            cleanup_old_backups
            ;;
        --backup-config)
            create_backup_dir
            backup_config
            ;;
        --backup-full)
            create_backup_dir
            backup_full
            ;;
        --restore|-r)
            restore_database "$2"
            ;;
        --list|-l)
            list_backups
            ;;
        --cleanup)
            cleanup_old_backups
            ;;
        --schedule)
            schedule_backup
            ;;
        --auto)
            # Automated backup (called by cron)
            create_backup_dir
            backup_database
            backup_config
            cleanup_old_backups
            ;;
        --help|-h|*)
            echo "Kasa Monitor Backup Manager"
            echo ""
            echo "Usage: $0 [option]"
            echo ""
            echo "Options:"
            echo "  --backup, -b        Create database backup"
            echo "  --backup-config     Backup configuration files"
            echo "  --backup-full       Create full system backup"
            echo "  --restore, -r FILE  Restore database from backup"
            echo "  --list, -l          List available backups"
            echo "  --cleanup           Remove old backups"
            echo "  --schedule          Setup automated backup schedule"
            echo "  --auto              Run automated backup (for cron)"
            echo "  --help, -h          Show this help message"
            echo ""
            echo "Environment Variables:"
            echo "  BACKUP_DIR          Backup directory (default: ./backups)"
            echo "  DB_PATH             Database path (default: ./kasa_monitor.db)"
            echo "  MAX_BACKUPS         Maximum backups to keep (default: 30)"
            ;;
    esac
}

# Run main function
main "$@"