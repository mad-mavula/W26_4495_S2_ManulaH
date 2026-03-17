#!/bin/bash

##################################################
# SRE Security Research Lab - Master Startup Script
# Handles: Fresh setup, daily startup, permanent baseline
##################################################

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
NAMESPACE="default"
LAB_DIR="$HOME/sre-security-lab"
BASELINE_FILE="$LAB_DIR/golden-baseline.json"

echo -e "${CYAN}"
echo "==========================================="
echo "🔬 SRE Security Research Lab Startup"
echo "==========================================="
echo -e "${NC}"

# Function to print status
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
    exit 1
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Check if this is first-time setup or daily startup
if [ "$1" == "--first-time" ]; then
    FIRST_TIME=true
    echo -e "${YELLOW}🆕 First-time setup mode${NC}"
else
    FIRST_TIME=false
    echo -e "${CYAN}🚀 Daily startup mode${NC}"
fi

echo ""

# Step 1: Minikube Setup
echo -e "${BLUE}1. Starting Minikube Cluster${NC}"
echo "-------------------------------------------"

minikube status > /dev/null 2>&1
if [ $? -ne 0 ]; then
    print_info "Starting Minikube with full monitoring stack..."
    minikube start \
        --driver=docker \
        --cpus=4 \
        --memory=6144 \
        --addons=metrics-server \
        --addons=dashboard \
        --addons=ingress
    print_status "Minikube started"
else
    print_status "Minikube already running"
fi

# Step 2: Prometheus Setup (if first time)
echo ""
echo -e "${BLUE}2. Monitoring Stack Setup${NC}"
echo "-------------------------------------------"

if ! kubectl get namespace monitoring > /dev/null 2>&1; then
    print_info "Installing Prometheus stack (this takes 2-3 minutes)..."
    helm repo add prometheus-community https://prometheus-community.github.io/helm-charts > /dev/null 2>&1 || true
    helm repo update > /dev/null 2>&1
    
    helm install monitoring prometheus-community/kube-prometheus-stack \
        --namespace monitoring \
        --create-namespace \
        --set prometheus.prometheusSpec.serviceMonitorSelectorNilUsesHelmValues=false \
        --wait --timeout=300s
    
    print_status "Prometheus stack installed"
else
    print_status "Monitoring stack already exists"
fi

# Step 3: Application Deployment
echo ""
echo -e "${BLUE}3. Deploying SRE Security Lab${NC}"
echo "-------------------------------------------"

cd "$LAB_DIR"

# Connect to Minikube Docker
eval $(minikube docker-env)
print_info "Connected to Minikube Docker"

# Build and deploy
print_info "Building and deploying applications..."
./scripts/deploy-kubectl.sh > deploy.log 2>&1
print_status "Applications deployed"

# Wait for pods to be ready
print_info "Waiting for pods to be ready (up to 5 minutes)..."
kubectl wait --for=condition=available --timeout=300s deployment/sre-backend
kubectl wait --for=condition=available --timeout=300s deployment/sre-frontend
print_status "All pods ready"

# Step 4: Baseline Management
echo ""
echo -e "${BLUE}4. Baseline Configuration${NC}"
echo "-------------------------------------------"

if [ "$FIRST_TIME" = true ] || [ ! -f "$BASELINE_FILE" ]; then
    echo -e "${YELLOW}📊 Creating permanent golden baseline...${NC}"
    
    # Generate normal traffic and collect baseline
    print_info "Starting traffic generation for baseline collection..."
    
    # Get service info
    MINIKUBE_IP=$(minikube ip)
    FRONTEND_PORT=$(kubectl get service sre-frontend-service -o jsonpath='{.spec.ports[0].nodePort}')
    
    # Test connectivity
    curl -s "http://$MINIKUBE_IP:$FRONTEND_PORT/api/health" > /dev/null || print_error "Backend not accessible"
    
    # Start background traffic
    cat > /tmp/baseline_traffic.sh << 'EOF'
#!/bin/bash
MINIKUBE_IP=$1
FRONTEND_PORT=$2
while true; do
  curl -s "http://$MINIKUBE_IP:$FRONTEND_PORT/api/health" > /dev/null
  curl -s "http://$MINIKUBE_IP:$FRONTEND_PORT/api/scenarios" > /dev/null
  sleep 0.5
done
EOF
    chmod +x /tmp/baseline_traffic.sh
    
    # Start traffic in background
    /tmp/baseline_traffic.sh "$MINIKUBE_IP" "$FRONTEND_PORT" &
    TRAFFIC_PID=$!
    
    print_info "Traffic started (PID: $TRAFFIC_PID). Collecting 5-minute baseline..."
    
    # Collect baseline in pod
    POD_NAME=$(kubectl get pods -l app=sre-backend -o jsonpath='{.items[0].metadata.name}')
    kubectl cp scripts/collect_baseline_fixed.py $POD_NAME:/app/
    
    # Run baseline collection
    kubectl exec -it $POD_NAME -- bash -c "cd /app && echo '1' | python collect_baseline_fixed.py"
    
    # Stop traffic
    kill $TRAFFIC_PID 2>/dev/null || true
    print_status "Baseline collection completed"
    
    # Copy baseline to host and save as golden baseline
    kubectl cp $POD_NAME:/tmp/baseline.json "$BASELINE_FILE"
    print_status "Golden baseline saved to $BASELINE_FILE"
    
    # Clean up
    rm -f /tmp/baseline_traffic.sh
    
else
    print_info "Using existing golden baseline from $BASELINE_FILE"
fi

# Step 5: Deploy Golden Baseline to Cluster
echo ""
echo -e "${BLUE}5. Deploying Permanent Baseline${NC}"
echo "-------------------------------------------"

# Create/update ConfigMap with golden baseline
kubectl create configmap sre-baseline --from-file=baseline.json="$BASELINE_FILE" --dry-run=client -o yaml | kubectl apply -f -
print_status "Baseline ConfigMap created"

# Restart pods to load new baseline
print_info "Restarting backend pods to load baseline..."
kubectl rollout restart deployment sre-backend
kubectl rollout status deployment sre-backend --timeout=300s
print_status "Pods restarted with golden baseline"

# Step 6: System Verification
echo ""
echo -e "${BLUE}6. System Verification${NC}"
echo "-------------------------------------------"

# Get access information
MINIKUBE_IP=$(minikube ip)
FRONTEND_PORT=$(kubectl get service sre-frontend-service -o jsonpath='{.spec.ports[0].nodePort}')

# Test endpoints
print_info "Testing system endpoints..."
curl -s "http://$MINIKUBE_IP:$FRONTEND_PORT/api/health" | grep -q "healthy" || print_error "Health check failed"
curl -s "http://$MINIKUBE_IP:$FRONTEND_PORT/api/scenarios" | grep -q "dos-attack" || print_error "Scenarios endpoint failed"

print_status "All endpoints responding correctly"

# Step 7: Start Anomaly Detector
echo ""
echo -e "${BLUE}7. Starting Research Components${NC}"
echo "-------------------------------------------"

# Port-forward for easy API access
print_info "Setting up port-forwarding for API access..."
POD_NAME=$(kubectl get pods -l app=sre-backend -o jsonpath='{.items[0].metadata.name}')

# Kill any existing port-forward
pkill -f "kubectl port-forward" 2>/dev/null || true
sleep 2

# Start new port-forward in background
kubectl port-forward pod/$POD_NAME 5000:5000 > /dev/null 2>&1 &
sleep 3

# Start anomaly detector
print_info "Starting anomaly detector..."
curl -s -X POST http://localhost:5000/api/detector/start > /dev/null
print_status "Anomaly detector started"

# Step 8: Final Setup Summary
echo ""
echo -e "${GREEN}"
echo "🎉 SRE Security Research Lab Ready!"
echo "==========================================="
echo -e "${NC}"
echo ""
echo -e "${CYAN}📊 Dashboard Access:${NC}"
echo "   Frontend: http://$MINIKUBE_IP:$FRONTEND_PORT"
echo "   Backend API: http://$MINIKUBE_IP:$FRONTEND_PORT/api"
echo ""
echo -e "${CYAN}🔧 Local API Access (port-forwarded):${NC}"
echo "   Health: curl http://localhost:5000/api/health"
echo "   Status: curl http://localhost:5000/api/status"
echo "   Detector: curl http://localhost:5000/api/detector/status"
echo ""
echo -e "${CYAN}🚨 Attack Simulation Scripts:${NC}"
echo "   DDoS: cd scripts && python ddos_simulator.py"
echo "   Brute Force: cd scripts && python bruteforce_simulator.py"
echo "   Misconfig: cd scripts && python misconfig_simulator.py"
echo ""
echo -e "${CYAN}📈 Monitoring:${NC}"
echo "   Prometheus: kubectl port-forward -n monitoring svc/monitoring-kube-prometheus-prometheus 9090:9090"
echo "   Grafana: kubectl port-forward -n monitoring svc/monitoring-grafana 3000:80"
echo ""
echo -e "${YELLOW}💡 Quick Commands:${NC}"
echo "   Check status: curl http://localhost:5000/api/detector/status"
echo "   View incidents: curl http://localhost:5000/api/classifier/history"
echo "   Stop detector: curl -X POST http://localhost:5000/api/detector/stop"
echo ""
print_status "Lab startup complete! Ready for security research experiments."

# Create a status file
cat > "$LAB_DIR/lab-status.txt" << EOF
SRE Security Lab Status - $(date)
=====================================
Minikube IP: $MINIKUBE_IP
Frontend Port: $FRONTEND_PORT
Golden Baseline: $BASELINE_FILE
Lab Directory: $LAB_DIR
Anomaly Detector: Running
Port-forward: localhost:5000 -> pod/$POD_NAME:5000

Quick Test Commands:
- curl http://localhost:5000/api/health
- curl http://localhost:5000/api/detector/status
- cd scripts && python bruteforce_simulator.py
EOF

echo ""
print_info "Lab status saved to $LAB_DIR/lab-status.txt"
