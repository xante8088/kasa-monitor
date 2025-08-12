#!/bin/bash

# Docker Network Helper Script
# Automatically finds an available subnet for docker-compose networks
# 
# Usage:
#   ./docker-network-helper.sh                  # Check for available subnet
#   ./docker-network-helper.sh --generate       # Generate docker-compose with available network
#   ./docker-network-helper.sh --subnet 172.30  # Check if specific subnet is available

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to check if a subnet is in use
is_subnet_in_use() {
    local subnet=$1
    docker network ls --format '{{.Name}}' | while read network; do
        if [ "$network" != "none" ] && [ "$network" != "host" ]; then
            docker network inspect "$network" 2>/dev/null | grep -q "\"Subnet\": \"${subnet}" && return 0
        fi
    done
    return 1
}

# Function to find an available subnet
find_available_subnet() {
    local base_subnet="${1:-172}"
    
    echo -e "${BLUE}Searching for available Docker network subnet...${NC}"
    
    # Common private subnet ranges to try
    local subnets=(
        "${base_subnet}.20.0.0/16"
        "${base_subnet}.21.0.0/16"
        "${base_subnet}.22.0.0/16"
        "${base_subnet}.23.0.0/16"
        "${base_subnet}.24.0.0/16"
        "${base_subnet}.25.0.0/16"
        "${base_subnet}.26.0.0/16"
        "${base_subnet}.27.0.0/16"
        "${base_subnet}.28.0.0/16"
        "${base_subnet}.29.0.0/16"
        "${base_subnet}.30.0.0/16"
        "10.10.0.0/16"
        "10.11.0.0/16"
        "10.12.0.0/16"
        "192.168.100.0/24"
        "192.168.200.0/24"
    )
    
    for subnet in "${subnets[@]}"; do
        if ! is_subnet_in_use "$subnet"; then
            echo -e "${GREEN}✓ Found available subnet: ${subnet}${NC}"
            echo "$subnet"
            return 0
        fi
    done
    
    echo -e "${RED}✗ No available subnet found in common ranges${NC}"
    return 1
}

# Function to list all Docker networks and their subnets
list_docker_networks() {
    echo -e "${BLUE}Current Docker networks:${NC}"
    echo "----------------------------------------"
    
    docker network ls --format 'table {{.Name}}\t{{.Driver}}' | while read line; do
        if [[ $line == *"NAME"* ]]; then
            echo "$line	SUBNET"
        elif [[ $line != *"none"* ]] && [[ $line != *"host"* ]]; then
            network_name=$(echo "$line" | awk '{print $1}')
            subnet=$(docker network inspect "$network_name" 2>/dev/null | grep -oP '"Subnet": "\K[^"]+' | head -1 || echo "N/A")
            echo "$line	$subnet"
        fi
    done
    echo "----------------------------------------"
}

# Function to generate docker-compose with available network
generate_docker_compose() {
    local subnet=$(find_available_subnet)
    
    if [ -z "$subnet" ]; then
        echo -e "${RED}Failed to find available subnet${NC}"
        exit 1
    fi
    
    local gateway="${subnet%.*}.1"
    gateway="${gateway%.0/16}.0.1"
    
    if [ -f "docker-compose.yml" ]; then
        echo -e "${YELLOW}⚠ docker-compose.yml already exists${NC}"
        read -p "Do you want to create docker-compose.auto.yml instead? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 0
        fi
        output_file="docker-compose.auto.yml"
    else
        output_file="docker-compose.yml"
    fi
    
    echo -e "${BLUE}Generating ${output_file} with subnet ${subnet}...${NC}"
    
    # Copy sample file and update network configuration
    if [ -f "docker-compose.sample.yml" ]; then
        cp docker-compose.sample.yml "$output_file"
        
        # Update the subnet in the file using sed
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS sed syntax
            sed -i '' "s|subnet: 172.20.0.0/16|subnet: ${subnet}|g" "$output_file"
            sed -i '' "s|gateway: 172.20.0.1|gateway: ${gateway}|g" "$output_file"
        else
            # Linux sed syntax
            sed -i "s|subnet: 172.20.0.0/16|subnet: ${subnet}|g" "$output_file"
            sed -i "s|gateway: 172.20.0.1|gateway: ${gateway}|g" "$output_file"
        fi
        
        echo -e "${GREEN}✓ Generated ${output_file} with network configuration:${NC}"
        echo "  Subnet: ${subnet}"
        echo "  Gateway: ${gateway}"
        echo ""
        echo -e "${GREEN}You can now run: docker-compose up -d${NC}"
    else
        echo -e "${RED}✗ docker-compose.sample.yml not found${NC}"
        exit 1
    fi
}

# Function to validate Docker is running
check_docker() {
    if ! docker info >/dev/null 2>&1; then
        echo -e "${RED}✗ Docker is not running or not installed${NC}"
        echo "Please start Docker and try again"
        exit 1
    fi
}

# Function to show usage
show_usage() {
    cat << EOF
Docker Network Helper for Kasa Monitor

Usage: $0 [OPTIONS]

OPTIONS:
    -h, --help          Show this help message
    -l, --list          List all Docker networks and their subnets
    -g, --generate      Generate docker-compose.yml with available network
    -c, --check         Check for available subnet (default)
    -s, --subnet BASE   Check availability starting from BASE subnet (e.g., 172.30)
    
EXAMPLES:
    $0                      # Find an available subnet
    $0 --generate           # Create docker-compose.yml with available network
    $0 --list               # Show all Docker networks
    $0 --subnet 10.20       # Check for available subnet starting at 10.20.x.x

NOTES:
    - This script helps avoid Docker network conflicts
    - It automatically finds unused subnets for your containers
    - Generated configs are compatible with docker-compose v3.8+
    
EOF
}

# Main script logic
main() {
    check_docker
    
    case "${1:-}" in
        -h|--help)
            show_usage
            ;;
        -l|--list)
            list_docker_networks
            ;;
        -g|--generate)
            generate_docker_compose
            ;;
        -s|--subnet)
            if [ -z "${2:-}" ]; then
                echo -e "${RED}✗ Please provide a base subnet (e.g., 172.30)${NC}"
                exit 1
            fi
            find_available_subnet "$2"
            ;;
        -c|--check|"")
            find_available_subnet
            ;;
        *)
            echo -e "${RED}✗ Unknown option: $1${NC}"
            show_usage
            exit 1
            ;;
    esac
}

# Run main function
main "$@"