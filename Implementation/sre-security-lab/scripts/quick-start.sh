#!/bin/bash

##################################################
# SRE Security Research Lab - Daily Quick Start
# Fast startup for daily research work
##################################################

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}"
echo "========================================"
echo "⚡ SRE Security Lab - Quick Start"
echo "========================================"
echo -e "${NC}"

LAB_DIR="$HOME/sre-security-lab"
cd "$LAB_DIR"

print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# 1. Check/Start Minikube
echo "1. Checking Minikube..."
if ! minikube status > /dev/null 2>&1; then
    print_info "Starting Minikube..."
    minikube start --driver=docker --cpus=4 --memory=6144
else
    print_status "Minikube running"
fi

# 2. Quick Deploy
echo ""
echo "2. Deploying applications..."
eval $(minikube docker-env)
./scripts/deploy-kubectl.sh > /dev/null 2>&1
print_status "Applications deployed"

# 3. Wait for ready
print_info "Waiting for pods..."
kubectl wait --for=condition=available --timeout=180s deployment/sre-backend > /dev/null 2>&1
print_status "Backend ready"

# 4. Setup port-forward and start detector
echo ""
echo "3. Starting research components..."
POD_NAME=$(kubectl get pods -l app=sre-backend -o jsonpath='{.items[0].metadata.name}')
pkill -f "kubectl port-forward" 2>/dev/null || true
sleep 2
kubectl port-forward pod/$POD_NAME 5000:5000 > /dev/null 2>&1 &
sleep 3

# Start detector
curl -s -X POST http://localhost:5000/api/detector/start > /dev/null
print_status "Anomaly detector started"

# 5. Get access info
MINIKUBE_IP=$(minikube ip)
FRONTEND_PORT=$(kubectl get service sre-frontend-service -o jsonpath='{.spec.ports[0].nodePort}')

echo ""
echo -e "${CYAN}🚀 Quick Start Complete!${NC}"
echo "================================"
echo ""
echo "📊 Dashboard: http://$MINIKUBE_IP:$FRONTEND_PORT"
echo "🔧 API: http://localhost:5000/api/health"
echo ""
echo -e "${GREEN}Ready for experiments! 🧪${NC}"
echo ""
echo "Next steps:"
echo "• cd scripts && python bruteforce_simulator.py"
echo "• curl http://localhost:5000/api/detector/status"
echo ""
