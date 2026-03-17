#!/bin/bash

##################################################
# SRE Security Research Lab - Baseline Reset
# Recreates the golden baseline when needed
##################################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${YELLOW}"
echo "========================================"
echo "🔄 SRE Security Lab - Baseline Reset"
echo "========================================"
echo -e "${NC}"

LAB_DIR="$HOME/sre-security-lab"
BASELINE_FILE="$LAB_DIR/golden-baseline.json"

print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
    exit 1
}

# Check if system is running
kubectl get pods -l app=sre-backend > /dev/null 2>&1 || print_error "Backend pods not running. Run lab-startup.sh first."

cd "$LAB_DIR"

echo ""
print_warning "This will recreate your golden baseline!"
print_info "Current baseline: $BASELINE_FILE"

if [ -f "$BASELINE_FILE" ]; then
    echo ""
    echo "Current baseline info:"
    echo "Created: $(stat -f %SB "$BASELINE_FILE" 2>/dev/null || stat -c %y "$BASELINE_FILE")"
    echo "Size: $(wc -c < "$BASELINE_FILE") bytes"
fi

echo ""
read -p "Continue with baseline reset? (y/N): " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

# Backup existing baseline
if [ -f "$BASELINE_FILE" ]; then
    BACKUP_FILE="${BASELINE_FILE}.backup.$(date +%s)"
    cp "$BASELINE_FILE" "$BACKUP_FILE"
    print_info "Backed up existing baseline to $BACKUP_FILE"
fi

echo ""
echo -e "${CYAN}Starting baseline reset process...${NC}"
echo ""

# 1. Stop any running detector
print_info "Stopping anomaly detector..."
curl -s -X POST http://localhost:5000/api/detector/stop > /dev/null 2>&1 || true

# 2. Get service info
MINIKUBE_IP=$(minikube ip)
FRONTEND_PORT=$(kubectl get service sre-frontend-service -o jsonpath='{.spec.ports[0].nodePort}')

# Test connectivity
curl -s "http://$MINIKUBE_IP:$FRONTEND_PORT/api/health" > /dev/null || print_error "Backend not accessible"

# 3. Generate clean traffic
print_info "Starting clean traffic generation..."

# Create traffic script
cat > /tmp/reset_traffic.sh << 'EOF'
#!/bin/bash
MINIKUBE_IP=$1
FRONTEND_PORT=$2
echo "Generating normal traffic for baseline..."
for i in {1..600}; do  # 10 minutes of traffic
  curl -s "http://$MINIKUBE_IP:$FRONTEND_PORT/api/health" > /dev/null
  curl -s "http://$MINIKUBE_IP:$FRONTEND_PORT/api/scenarios" > /dev/null
  echo -ne "\rTraffic sample: $i/600"
  sleep 1
done
echo ""
EOF
chmod +x /tmp/reset_traffic.sh

# Start traffic in background
/tmp/reset_traffic.sh "$MINIKUBE_IP" "$FRONTEND_PORT" &
TRAFFIC_PID=$!

print_info "Traffic started (PID: $TRAFFIC_PID). Collecting 10-minute baseline..."

# 4. Collect new baseline
POD_NAME=$(kubectl get pods -l app=sre-backend -o jsonpath='{.items[0].metadata.name}')
kubectl cp scripts/collect_baseline_fixed.py $POD_NAME:/app/

# Wait a bit for traffic to stabilize
sleep 30

# Run baseline collection (10 minutes)
print_info "Running baseline collection (this will take 10 minutes)..."
kubectl exec $POD_NAME -- bash -c "cd /app && echo '2' | python collect_baseline_fixed.py" || print_error "Baseline collection failed"

# Stop traffic
kill $TRAFFIC_PID 2>/dev/null || true
wait $TRAFFIC_PID 2>/dev/null || true
print_status "Traffic generation stopped"

# 5. Copy new baseline
kubectl cp $POD_NAME:/tmp/baseline.json "$BASELINE_FILE"
print_status "New golden baseline saved"

# 6. Deploy to cluster
kubectl create configmap sre-baseline --from-file=baseline.json="$BASELINE_FILE" --dry-run=client -o yaml | kubectl apply -f -
print_status "Baseline ConfigMap updated"

# 7. Restart pods
print_info "Restarting backend pods to load new baseline..."
kubectl rollout restart deployment sre-backend
kubectl rollout status deployment sre-backend --timeout=300s
print_status "Pods restarted"

# 8. Restart port-forward and detector
print_info "Restarting research components..."
POD_NAME=$(kubectl get pods -l app=sre-backend -o jsonpath='{.items[0].metadata.name}')

pkill -f "kubectl port-forward" 2>/dev/null || true
sleep 3

kubectl port-forward pod/$POD_NAME 5000:5000 > /dev/null 2>&1 &
sleep 3

curl -s -X POST http://localhost:5000/api/detector/start > /dev/null
print_status "Anomaly detector restarted"

# 9. Verify new baseline
echo ""
echo -e "${CYAN}Verifying new baseline...${NC}"
NEW_SIZE=$(wc -c < "$BASELINE_FILE")
echo "New baseline size: $NEW_SIZE bytes"
echo "Created: $(date)"

# Test baseline loading
BASELINE_STATUS=$(curl -s http://localhost:5000/api/detector/status | grep -o '"has_baseline":[^,]*' | cut -d: -f2)
if [ "$BASELINE_STATUS" = "true" ]; then
    print_status "New baseline loaded successfully"
else
    print_warning "Baseline may not be loaded properly"
fi

# Cleanup
rm -f /tmp/reset_traffic.sh

echo ""
echo -e "${GREEN}"
echo "🎉 Baseline Reset Complete!"
echo "=========================="
echo -e "${NC}"
echo ""
print_info "New golden baseline ready for research experiments"
print_info "You can now run attack simulations to test detection accuracy"
echo ""
echo "Next steps:"
echo "• cd scripts && python bruteforce_simulator.py"
echo "• curl http://localhost:5000/api/detector/status"
echo ""
