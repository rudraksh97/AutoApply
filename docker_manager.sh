#!/usr/bin/env bash

# AutoApply Docker Manager
# Usage: ./docker_manager.sh [command]
# Commands: build, up, down, logs, restart, clean

# Configuration
DOCKER_USER="devhaxcodes"
# DOCKER_PASS="Docker@123" # Uncomment and set if you want automatic login, otherwise rely on local auth
# We will set these dynamically based on environment, but defaults are helpful
# BACKEND_Image="devhaxcodes/autoapply-backend"
# FRONTEND_Image="devhaxcodes/autoapply-frontend"
# NEW_FRONTEND_Image="devhaxcodes/autoapply-new-frontend"
# REVAMP_FRONTEND_Image="devhaxcodes/autoapply-frontend-revamp"

# Determine current environment
determine_env() {
    # If TAG is already set, use it
    if [ -n "$TAG" ]; then
        CURRENT_ENV=$TAG
        echo "✅ Environment set via variable to: $CURRENT_ENV"
        return
    fi

    echo "Select Environment:"
    echo "1) Development (dev)"
    echo "2) Production (prod)"
    read -p "Select [1-2, default: 1]: " env_choice

    case $env_choice in
        2|prod)
            export TAG="prod"
            ;;
        1|dev|*)
            export TAG="dev"
            ;;
    esac

    CURRENT_ENV=$TAG
    echo "✅ Environment set to: $CURRENT_ENV"
}

# Initial determination
determine_env

# Function to check for Docker Compose V2 and install if missing
ensure_compose_v2() {
    if docker compose version >/dev/null 2>&1; then
        COMPOSE_CMD="docker compose"
        return
    fi
    
    echo "⚠️  'docker compose' (v2) not found. Falling back to 'docker-compose' (v1)."
    echo "❌ If you see 'ContainerConfig' errors, you need Docker Compose V2."
    read -p "❓ Do you want to install Docker Compose V2 now? (y/N) " install_v2
    if [[ $install_v2 =~ ^[Yy]$ ]]; then
        echo "⬇️  Installing Docker Compose V2..."
        mkdir -p ~/.docker/cli-plugins/
        ARCH=$(uname -m)
        curl -SL https://github.com/docker/compose/releases/download/v2.24.5/docker-compose-linux-$ARCH -o ~/.docker/cli-plugins/docker-compose
        chmod +x ~/.docker/cli-plugins/docker-compose
        
        echo "✅ Installed. Testing..."
        if docker compose version >/dev/null 2>&1; then
            echo "🎉 Docker Compose V2 is working!"
            COMPOSE_CMD="docker compose"
            return
        else
            echo "❌ Installation failed or not picked up. Using old docker-compose..."
        fi
    fi
    
    COMPOSE_CMD="docker-compose"
}

# Image names with tags
BACKEND_Image="devhaxcodes/autoapply-backend:$TAG"
FRONTEND_Image="devhaxcodes/autoapply-frontend:$TAG"
NEW_FRONTEND_Image="devhaxcodes/autoapply-new-frontend:$TAG"
REVAMP_FRONTEND_Image="devhaxcodes/autoapply-frontend-revamp:$TAG"
# RSS Poller uses the same image as backend, but we can tag it if we wanted. 
# For now, we rely on the implementation where it reuses the backend image.
# However, for clarity in logs, we can define it. 
# NOTE: In docker-compose.yml we use the SAME image name for both backend and rss-poller.
# So pushing backend effectively pushes rss-poller's image. 


# Function to run docker compose command
compose_cmd() {
    # Ensure we have the right compose command (V2 preferred)
    if [ -z "$COMPOSE_CMD" ]; then
        ensure_compose_v2
    fi
    
    # Check if backend directory exists to determine if we are in a dev environment with source code
    # or a prod environment without source code. The .docker_env file overrides this.
    
    if [ "$CURRENT_ENV" == "prod" ]; then
        # Check if the command allows -f flag (up, down, logs, config, etc.)
        # build command doesn't make sense with prod.yml for image usage (though technically valid syntax)
        if [[ "$1" != "build" ]]; then
            $COMPOSE_CMD -f docker-compose.prod.yml "$@"
            return
        else
            # If in Prod mode and user asks to build
            if [ -f "docker-compose.yml" ]; then
                echo "ℹ️  Building in Production mode using dev config (docker-compose.yml)..."
                $COMPOSE_CMD -f docker-compose.yml build
                return
            else
                 echo "⚠️  Warning: 'build' command ignored in Production mode (images are pulled, not built) and no source config found."
                 return
            fi
        fi
    fi

    $COMPOSE_CMD "$@"
}

show_menu() {
    echo "======================================"
    echo "   AutoApply Docker Management Script"
    echo "======================================"
    echo "1) 🏗️  Build Images (docker compose build)"
    echo "2) 🚀 Run Containers (docker compose up)"
    echo "3) 🛑 Stop Containers (docker compose down)"
    echo "4) 📜 View Logs (docker compose logs -f)"
    echo "5) ♻️  Restart (down + up)"
    echo "6) 🧹 Clean Data (down -v)"
    echo "7) ⬆️  Push Images (Current Env: $CURRENT_ENV)"
    echo "8) ⬇️  Pull Images (Current Env: $CURRENT_ENV)"
    echo "9) 🚪 Exit"
    echo "10) 🌐 Switch Environment"
    # echo "10) 🛠️  Run in Dev Mode (hot-reload)" # Disabled: No docker-compose.dev.yml
    echo "======================================"
}

execute_choice() {
    case $1 in
        1|build)
            echo "🔨 Building images..."
            echo "ℹ️  Note: 'rss-poller' uses the same image as 'backend', so they build together."
            compose_cmd build
            ;;
        2|up)
            echo "🚀 Starting services..."
            compose_cmd up
            echo "✅ Services started."
            echo "   Frontend: http://localhost:3000"
            echo "   New Frontend: http://localhost:3001"
            echo "   Revamp Frontend: http://localhost:3002"
            echo "   Backend: http://localhost:8000"
            echo "   Services Running: API, RSS Poller, Job Processor"
            ;;
        3|down)
            echo "🛑 Stopping services..."
            compose_cmd down
            ;;
        4|logs)
            echo "📜 Showing logs (Ctrl+C to exit)..."
            compose_cmd logs -f
            ;;
        5|restart)
            echo "♻️  Restarting..."
            compose_cmd down
            sleep 1
            compose_cmd up
            ;;
        6|clean)
            echo "⚠️  WARNING: This will delete the database volume."
            read -p "Are you sure? (y/N) " confirm
            if [[ $confirm =~ ^[Yy]$ ]]; then
                compose_cmd down -v
                echo "🧹 cleaned."
            fi
            ;;
        7|push)
            # Check for DOCKER_PASS or manual login
            if [ -n "$DOCKER_PASS" ]; then
                echo "🔑 Logging into Docker Hub..."
                echo "$DOCKER_PASS" | docker login --username "$DOCKER_USER" --password-stdin
            else
                echo "ℹ️  Assuming already logged in or using credential helper."
            fi
            
            if [ "$CURRENT_ENV" == "prod" ] && [ -f "docker-compose.yml" ]; then
                 read -p "❓ You are in Production mode but have source code. Do you want to BUILD images first? (y/N) " build_confirm
                 if [[ $build_confirm =~ ^[Yy]$ ]]; then
                     echo "🔨 Building production images (Tag: $TAG) using docker-compose.yml..."
                     # Explicitly pass TAG=prod to the build command so docker-compose.yml picks it up
                     if docker compose version >/dev/null 2>&1; then
                        TAG=$TAG docker compose -f docker-compose.yml build
                    else
                        TAG=$TAG docker-compose -f docker-compose.yml build
                    fi
                 fi
            fi

            # Now push the images. They should exist locally with the correct tag ($TAG)
            
            echo "⬆️  Pushing Backend: $BACKEND_Image..."
            docker push "$BACKEND_Image"
            
            echo "⬆️  Pushing Frontend: $FRONTEND_Image..."
            docker push "$FRONTEND_Image"

            # Tag other images if they exist - actually if they are built they are already tagged
            echo "⬆️  Pushing New Frontend: $NEW_FRONTEND_Image..."
            docker push "$NEW_FRONTEND_Image"

            echo "⬆️  Pushing Revamp Frontend: $REVAMP_FRONTEND_Image..."
            docker push "$REVAMP_FRONTEND_Image"

            echo "✅ Done!"
            ;;
        8|pull)
            if [ -n "$DOCKER_PASS" ]; then
                echo "🔑 Logging into Docker Hub..."
                echo "$DOCKER_PASS" | docker login --username "$DOCKER_USER" --password-stdin
            fi

            echo "⬇️  Pulling Backend: $BACKEND_Image..."
            docker pull "$BACKEND_Image"
            
            echo "⬇️  Pulling Frontend: $FRONTEND_Image..."
            docker pull "$FRONTEND_Image"

            echo "⬇️  Pulling New Frontend: $NEW_FRONTEND_Image..."
            docker pull "$NEW_FRONTEND_Image"

            echo "⬇️  Pulling Revamp Frontend: $REVAMP_FRONTEND_Image..."
            docker pull "$REVAMP_FRONTEND_Image"
            
            echo "✅ Done! To run these, you may need to adjust docker-compose.yml to use 'image:' instead of 'build:', or manually tag them."
            ;;
        9)
            exit 0
            ;;
        10)
            echo "ℹ️  Environment switching via menu is disabled."
            echo "   Please set the TAG environment variable instead: export TAG=prod"
            read -p "Press Enter to continue..."
            ;;
        # 10|dev)
        #     echo "🛠️  Starting in Dev Mode..."
        #     # ...
        #     ;;
        *)
            echo "❌ Invalid option."
            ;;
    esac
}

# Main logic
if [ -z "$1" ]; then
    # Interactive mode
    show_menu
    read -p "Select an option [1-10]: " choice
    execute_choice "$choice"
else
    # CLI mode
    execute_choice "$1"
fi
