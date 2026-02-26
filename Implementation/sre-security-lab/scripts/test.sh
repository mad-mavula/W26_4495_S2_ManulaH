#!/bin/bash

echo "================================================"
echo "🧪 SRE Security Lab - Test Script"
echo "================================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counter for tests
PASSED=0
TOTAL=0

# Function to print test result
print_result() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ PASS: $2${NC}"
        PASSED=$((PASSED+1))
    else
        echo -e "${RED}❌ FAIL: $2${NC}"
    fi
    TOTAL=$((TOTAL+1))
}

echo -e "${YELLOW}1. Checking Minikube Status${NC}"
echo "----------------------------------------"
minikube status > /dev/null 2>&1
print_result $? "Minikube is running"

echo ""

echo -e "${YELLOW}2. Checking Kubernetes Nodes${NC}"
echo "----------------------------------------"
NODES=$(kubectl get nodes | grep Ready | wc -l)
if [ $NODES -ge 1 ]; then
    print_result 0 "Kubernetes nodes are ready"
else
    print_result 1 "Kubernetes nodes not ready"
fi

echo ""

echo -e "${YELLOW}3. Checking Research Namespace${NC}"
echo "----------------------------------------"
kubectl get namespace research > /dev/null 2>&1
if [ $? -eq 0 ]; then
    print_result 0 "Research namespace exists"
else
    echo -e "${BLUE}Creating research namespace...${NC}"
    kubectl create namespace research
    print_result $? "Research namespace created"
fi

echo ""

echo -e "${YELLOW}4. Checking Backend Deployment${NC}"
echo "----------------------------------------"
kubectl get deployment sre-backend  > /dev/null 2>&1
if [ $? -eq 0 ]; then
    print_result 0 "Backend deployment exists"
    
    READY=$(kubectl get deployment sre-backend  -o jsonpath='{.status.readyReplicas}')
    if [ "$READY" -ge 1 ]; then
        print_result 0 "Backend pods are ready ($READY replicas)"
    else
        print_result 1 "Backend pods not ready"
    fi
else
    print_result 1 "Backend deployment not found"
fi

echo ""

echo -e "${YELLOW}5. Checking Frontend Deployment${NC}"
echo "----------------------------------------"
kubectl get deployment sre-frontend  > /dev/null 2>&1
if [ $? -eq 0 ]; then
    print_result 0 "Frontend deployment exists"
    
    READY=$(kubectl get deployment sre-frontend  -o jsonpath='{.status.readyReplicas}')
    if [ "$READY" -ge 1 ]; then
        print_result 0 "Frontend pods are ready ($READY replicas)"
    else
        print_result 1 "Frontend pods not ready"
    fi
else
    print_result 1 "Frontend deployment not found"
fi

echo ""

echo -e "${YELLOW}6. Testing Backend API Health${NC}"
echo "----------------------------------------"
# Port-forward to access backend
kubectl port-forward  service/sre-backend-service 5000:80 > /dev/null 2>&1 &
PF_PID=$!
sleep 3

curl -s http://localhost:5000/api/health > /dev/null
if [ $? -eq 0 ]; then
    print_result 0 "Backend health endpoint responding"
    
    # Get health response
    HEALTH=$(curl -s http://localhost:5000/api/health)
    echo -e "${BLUE}   Health: $HEALTH${NC}"
else
    print_result 1 "Backend health endpoint not responding"
fi

# Kill port-forward
kill $PF_PID 2>/dev/null

echo ""

echo -e "${YELLOW}7. Testing Scenarios Endpoint${NC}"
echo "----------------------------------------"
kubectl port-forward  service/sre-backend-service 5000:80 > /dev/null 2>&1 &
PF_PID=$!
sleep 3

SCENARIOS=$(curl -s http://localhost:5000/api/scenarios)
if [ $? -eq 0 ] && [ ! -z "$SCENARIOS" ]; then
    print_result 0 "Scenarios endpoint responding"
    
    # Count scenarios
    COUNT=$(echo $SCENARIOS | grep -o '"id"' | wc -l)
    echo -e "${BLUE}   Found $COUNT scenarios:${NC}"
    echo $SCENARIOS | grep -o '"name":"[^"]*"' | sed 's/"name":"//g' | sed 's/"//g' | while read name; do
        echo -e "${BLUE}     • $name${NC}"
    done
else
    print_result 1 "Scenarios endpoint not responding"
fi

kill $PF_PID 2>/dev/null

echo ""

echo -e "${YELLOW}8. Getting Access Information${NC}"
echo "----------------------------------------"
MINIKUBE_IP=$(minikube ip)
FRONTEND_PORT=$(kubectl get service sre-frontend-service  -o jsonpath='{.spec.ports[0].nodePort}' 2>/dev/null)

if [ ! -z "$FRONTEND_PORT" ]; then
    print_result 0 "Frontend service available"
    echo -e "${GREEN}   📊 Frontend Dashboard: http://$MINIKUBE_IP:$FRONTEND_PORT${NC}"
    echo -e "${GREEN}   🔌 Backend API: http://$MINIKUBE_IP:$FRONTEND_PORT/api${NC}"
    echo -e "${GREEN}   ❤️  Health Check: http://$MINIKUBE_IP:$FRONTEND_PORT/api/health${NC}"
else
    print_result 1 "Frontend service not found"
fi

echo ""

echo -e "${YELLOW}9. Checking Metrics Collection${NC}"
echo "----------------------------------------"
kubectl top pods  > /dev/null 2>&1
if [ $? -eq 0 ]; then
    print_result 0 "Metrics server is collecting data"
    echo -e "${BLUE}   Resource usage:${NC}"
    kubectl top pods  | head -3
else
    print_result 1 "Metrics server not available"
fi

echo ""

echo -e "${YELLOW}10. Testing Ingress (if enabled)${NC}"
echo "----------------------------------------"
kubectl get ingress  > /dev/null 2>&1
if [ $? -eq 0 ]; then
    INGRESS_HOST=$(kubectl get ingress  -o jsonpath='{.items[0].spec.rules[0].host}' 2>/dev/null)
    if [ ! -z "$INGRESS_HOST" ]; then
        print_result 0 "Ingress configured"
        echo -e "${GREEN}   🌐 Ingress URL: http://$INGRESS_HOST${NC}"
    else
        echo -e "${YELLOW}   ⚠️  Ingress exists but no host configured${NC}"
    fi
else
    echo -e "${YELLOW}   ⚠️  Ingress not enabled${NC}"
fi

echo ""
echo "================================================"
echo -e "${GREEN}✅ Tests Completed: $PASSED/$TOTAL passed${NC}"
echo "================================================"

if [ $PASSED -eq $TOTAL ]; then
    echo -e "${GREEN}🎉 All systems ready for research experiments!${NC}"
    echo ""
    echo "Next steps for your research:"
    echo "1. Run attack simulations: ./scripts/simulate_attacks.py"
    echo "2. Collect metrics from Prometheus"
    echo "3. Test classification framework"
    echo "4. Document results in /docs/results/"
else
    echo -e "${YELLOW}⚠️  Some components need attention before proceeding${NC}"
fi
