#!/bin/bash

# Deployment script for Kasa Monitor
# Copyright (C) 2025 Kasa Monitor Contributors

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DEPLOY_ENV="${DEPLOY_ENV:-production}"
DOCKER_REGISTRY="${DOCKER_REGISTRY:-}"
VERSION_FILE="$PROJECT_ROOT/version.json"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

check_dependencies() {
    log_step "Checking dependencies..."
    
    local deps=("docker" "docker-compose" "git")
    local missing=()
    
    for dep in "${deps[@]}"; do
        if ! command -v "$dep" &> /dev/null; then
            missing+=("$dep")
        fi
    done
    
    if [ ${#missing[@]} -gt 0 ]; then
        log_error "Missing dependencies: ${missing[*]}"
        return 1
    fi
    
    log_info "All dependencies satisfied"
}

get_version() {
    if [ -f "$VERSION_FILE" ]; then
        VERSION=$(python3 -c "import json; print(json.load(open('$VERSION_FILE'))['version'])")
    else
        VERSION="latest"
    fi
    echo "$VERSION"
}

update_version() {
    local new_version="$1"
    
    if [ -z "$new_version" ]; then
        # Auto-increment patch version
        local current_version=$(get_version)
        if [[ "$current_version" =~ ^([0-9]+)\.([0-9]+)\.([0-9]+)$ ]]; then
            local major="${BASH_REMATCH[1]}"
            local minor="${BASH_REMATCH[2]}"
            local patch="${BASH_REMATCH[3]}"
            new_version="$major.$minor.$((patch + 1))"
        else
            new_version="1.0.0"
        fi
    fi
    
    cat > "$VERSION_FILE" <<EOF
{
    "version": "$new_version",
    "updated_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
}
EOF
    
    log_info "Updated version to $new_version"
}

pre_deploy_checks() {
    log_step "Running pre-deployment checks..."
    
    # Check if .env file exists
    if [ ! -f "$PROJECT_ROOT/.env" ]; then
        log_error "Environment file (.env) not found"
        return 1
    fi
    
    # Run database migrations
    if [ -f "$PROJECT_ROOT/scripts/migration/migrate.py" ]; then
        log_info "Running database migrations..."
        python3 "$PROJECT_ROOT/scripts/migration/migrate.py" migrate
    fi
    
    # Backup database
    if [ -f "$PROJECT_ROOT/scripts/backup/backup_manager.sh" ]; then
        log_info "Creating database backup..."
        "$PROJECT_ROOT/scripts/backup/backup_manager.sh" --backup
    fi
    
    # Run tests if available
    if [ -f "$PROJECT_ROOT/test_endpoints.py" ]; then
        log_info "Running tests..."
        python3 "$PROJECT_ROOT/test_endpoints.py" || {
            log_warning "Tests failed, continue anyway? (y/n)"
            read -r response
            if [[ "$response" != "y" ]]; then
                return 1
            fi
        }
    fi
    
    log_info "Pre-deployment checks passed"
}

build_docker_images() {
    log_step "Building Docker images..."
    
    local version=$(get_version)
    
    # Build backend image
    log_info "Building backend image..."
    docker build -t kasa-monitor-backend:$version \
                 -t kasa-monitor-backend:latest \
                 -f "$PROJECT_ROOT/Dockerfile" \
                 "$PROJECT_ROOT"
    
    # Tag for registry if configured
    if [ -n "$DOCKER_REGISTRY" ]; then
        docker tag kasa-monitor-backend:$version \
                   "$DOCKER_REGISTRY/kasa-monitor-backend:$version"
        docker tag kasa-monitor-backend:latest \
                   "$DOCKER_REGISTRY/kasa-monitor-backend:latest"
    fi
    
    log_info "Docker images built successfully"
}

push_docker_images() {
    if [ -z "$DOCKER_REGISTRY" ]; then
        log_warning "No Docker registry configured, skipping push"
        return 0
    fi
    
    log_step "Pushing Docker images to registry..."
    
    local version=$(get_version)
    
    docker push "$DOCKER_REGISTRY/kasa-monitor-backend:$version"
    docker push "$DOCKER_REGISTRY/kasa-monitor-backend:latest"
    
    log_info "Docker images pushed successfully"
}

deploy_local() {
    log_step "Deploying to local environment..."
    
    cd "$PROJECT_ROOT"
    
    # Stop existing containers
    docker-compose down
    
    # Start new containers
    docker-compose up -d
    
    # Wait for services to be ready
    log_info "Waiting for services to start..."
    sleep 10
    
    # Check health
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        log_info "Application is healthy"
    else
        log_error "Health check failed"
        return 1
    fi
    
    log_info "Local deployment complete"
}

deploy_production() {
    log_step "Deploying to production environment..."
    
    cd "$PROJECT_ROOT"
    
    # Use production compose file
    local compose_file="docker-compose.prod.yml"
    
    if [ ! -f "$compose_file" ]; then
        log_error "Production compose file not found: $compose_file"
        return 1
    fi
    
    # Deploy with zero downtime
    log_info "Starting new containers..."
    docker-compose -f "$compose_file" up -d --no-deps --build
    
    # Wait for new containers to be ready
    sleep 10
    
    # Health check
    log_info "Running health check..."
    local max_attempts=30
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if curl -f http://localhost:8000/health > /dev/null 2>&1; then
            log_info "Health check passed"
            break
        fi
        
        attempt=$((attempt + 1))
        log_info "Waiting for application to be ready... ($attempt/$max_attempts)"
        sleep 2
    done
    
    if [ $attempt -eq $max_attempts ]; then
        log_error "Application failed to start"
        return 1
    fi
    
    # Remove old containers
    log_info "Cleaning up old containers..."
    docker-compose -f "$compose_file" rm -f
    
    log_info "Production deployment complete"
}

rollback() {
    log_step "Rolling back deployment..."
    
    # Restore database from backup
    if [ -f "$PROJECT_ROOT/scripts/backup/backup_manager.sh" ]; then
        log_info "Restoring database from backup..."
        local latest_backup=$(ls -t "$PROJECT_ROOT/backups"/db_backup_*.gz | head -1)
        if [ -n "$latest_backup" ]; then
            "$PROJECT_ROOT/scripts/backup/backup_manager.sh" --restore "$latest_backup"
        fi
    fi
    
    # Revert to previous Docker image
    local previous_version="$1"
    if [ -n "$previous_version" ]; then
        log_info "Reverting to version $previous_version..."
        docker-compose down
        docker run -d --name kasa-monitor \
                   -p 8000:8000 \
                   kasa-monitor-backend:$previous_version
    fi
    
    log_info "Rollback complete"
}

post_deploy() {
    log_step "Running post-deployment tasks..."
    
    # Clear caches
    log_info "Clearing caches..."
    docker exec kasa-monitor redis-cli FLUSHALL 2>/dev/null || true
    
    # Run smoke tests
    log_info "Running smoke tests..."
    local endpoints=("/health" "/api/devices" "/metrics")
    
    for endpoint in "${endpoints[@]}"; do
        if curl -f "http://localhost:8000$endpoint" > /dev/null 2>&1; then
            log_info "  $endpoint: OK"
        else
            log_warning "  $endpoint: FAILED"
        fi
    done
    
    # Send deployment notification
    if [ -n "$SLACK_WEBHOOK" ]; then
        log_info "Sending deployment notification..."
        local version=$(get_version)
        curl -X POST "$SLACK_WEBHOOK" \
             -H 'Content-Type: application/json' \
             -d "{\"text\":\"Kasa Monitor v$version deployed to $DEPLOY_ENV\"}" \
             2>/dev/null || true
    fi
    
    log_info "Post-deployment tasks complete"
}

# Main script logic
main() {
    local command="$1"
    
    case "$command" in
        deploy)
            check_dependencies
            pre_deploy_checks
            build_docker_images
            
            if [ "$DEPLOY_ENV" = "production" ]; then
                push_docker_images
                deploy_production
            else
                deploy_local
            fi
            
            post_deploy
            
            log_info "Deployment successful!"
            ;;
            
        build)
            check_dependencies
            build_docker_images
            ;;
            
        push)
            push_docker_images
            ;;
            
        rollback)
            rollback "$2"
            ;;
            
        version)
            if [ -n "$2" ]; then
                update_version "$2"
            else
                echo "Current version: $(get_version)"
            fi
            ;;
            
        status)
            log_info "Deployment Status:"
            echo "  Environment: $DEPLOY_ENV"
            echo "  Version: $(get_version)"
            echo "  Registry: ${DOCKER_REGISTRY:-none}"
            
            # Check running containers
            echo ""
            echo "Running Containers:"
            docker-compose ps
            ;;
            
        --help|-h|*)
            echo "Kasa Monitor Deployment Script"
            echo ""
            echo "Usage: $0 [command] [options]"
            echo ""
            echo "Commands:"
            echo "  deploy          Full deployment process"
            echo "  build           Build Docker images"
            echo "  push            Push images to registry"
            echo "  rollback [ver]  Rollback to previous version"
            echo "  version [ver]   Show/set version"
            echo "  status          Show deployment status"
            echo "  --help, -h      Show this help message"
            echo ""
            echo "Environment Variables:"
            echo "  DEPLOY_ENV      Deployment environment (default: production)"
            echo "  DOCKER_REGISTRY Docker registry URL"
            echo "  SLACK_WEBHOOK   Slack webhook for notifications"
            ;;
    esac
}

# Run main function
main "$@"