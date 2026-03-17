#!/bin/bash

##################################################
# SRE Security Research Lab - Attack Simulation Workflow
# Automated testing of security incident detection
##################################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

echo -e "${MAGENTA}"
echo "================================================"
echo "🚨 SRE Security Lab - Attack Simulation Suite"
echo "================================================"
echo -e "${NC}"

LAB_DIR="$HOME/sre-security-lab"
RESULTS_DIR="$LAB_DIR/experiment-results"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

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

print_attack() {
    echo -e "${RED}🔥 $1${NC}"
}

print_detect() {
    echo -e "${CYAN}🔔 $1${NC}"
}

# Create results directory
mkdir -p "$RESULTS_DIR"

# Check system status
echo "Checking system status..."
kubectl get pods -l app=sre-backend > /dev/null 2>&1 || print_error "Backend not running. Run lab-startup.sh first."
curl -s http://localhost:5000/api/health > /dev/null || print_error "API not accessible. Check port-forward."

# Get detector status
DETECTOR_STATUS=$(curl -s http://localhost:5000/api/detector/status | grep -o '"is_running":[^,]*' | cut -d: -f2)
if [ "$DETECTOR_STATUS" != "true" ]; then
    print_warning "Anomaly detector not running. Starting..."
    curl -s -X POST http://localhost:5000/api/detector/start > /dev/null
    sleep 5
fi

print_status "System ready for attack simulation"

# Show menu
echo ""
echo -e "${CYAN}Choose simulation type:${NC}"
echo "1. 🔥 DDoS Attack Test"
echo "2. 🔐 Brute Force Attack Test"  
echo "3. 🔧 Misconfiguration Test"
echo "4. 🧪 Full Test Suite (all attacks)"
echo "5. 📊 Quick Status Check"
echo ""
read -p "Enter choice (1-5): " choice

cd "$LAB_DIR/scripts"

case $choice in
    1)
        echo ""
        echo -e "${RED}════════════════════════════════════${NC}"
        echo -e "${RED}🔥 DDOS ATTACK SIMULATION${NC}"
        echo -e "${RED}════════════════════════════════════${NC}"
        
        # Clear previous incidents
        curl -s -X POST http://localhost:5000/api/detector/stop > /dev/null
        sleep 2
        curl -s -X POST http://localhost:5000/api/detector/start > /dev/null
        sleep 3
        
        print_info "Starting DDoS attack simulation (3000 threads, 120 seconds)..."
        print_warning "This will stress your system significantly!"
        
        # Start monitoring in background
        (
            while true; do
                STATUS=$(curl -s http://localhost:5000/api/detector/status 2>/dev/null || echo "{}")
                echo "$STATUS" | grep -q '"consecutive_anomalies"' && {
                    CONSECUTIVE=$(echo "$STATUS" | grep -o '"consecutive_anomalies":[0-9]*' | cut -d: -f2)
                    if [ "$CONSECUTIVE" -gt 0 ]; then
                        print_detect "Anomaly detected (consecutive: $CONSECUTIVE)"
                    fi
                }
                sleep 5
            done
        ) &
        MONITOR_PID=$!
        
        # Run attack
        print_attack "Launching DDoS simulation..."
        python ddos_simulator.py
        
        # Stop monitoring
        kill $MONITOR_PID 2>/dev/null || true
        
        # Wait and check results
        sleep 10
        print_info "Collecting results..."
        INCIDENTS=$(curl -s http://localhost:5000/api/classifier/history)
        echo "$INCIDENTS" > "$RESULTS_DIR/ddos_test_$TIMESTAMP.json"
        
        # Show summary
        DDOS_COUNT=$(echo "$INCIDENTS" | grep -o '"attack_guess":"ddos"' | wc -l)
        print_status "DDoS simulation complete. Detected $DDOS_COUNT DDoS incidents."
        ;;
        
    2)
        echo ""
        echo -e "${YELLOW}════════════════════════════════════${NC}"
        echo -e "${YELLOW}🔐 BRUTE FORCE ATTACK SIMULATION${NC}"
        echo -e "${YELLOW}════════════════════════════════════${NC}"
        
        # Clear previous incidents
        curl -s -X POST http://localhost:5000/api/detector/stop > /dev/null
        sleep 2
        curl -s -X POST http://localhost:5000/api/detector/start > /dev/null
        sleep 3
        
        print_info "Starting brute force attack simulation (50 threads, 60 seconds)..."
        
        # Start monitoring
        (
            while true; do
                STATUS=$(curl -s http://localhost:5000/api/detector/status 2>/dev/null || echo "{}")
                echo "$STATUS" | grep -q '"consecutive_anomalies"' && {
                    CONSECUTIVE=$(echo "$STATUS" | grep -o '"consecutive_anomalies":[0-9]*' | cut -d: -f2)
                    if [ "$CONSECUTIVE" -gt 0 ]; then
                        print_detect "Auth anomaly detected (consecutive: $CONSECUTIVE)"
                    fi
                }
                sleep 5
            done
        ) &
        MONITOR_PID=$!
        
        # Run attack
        print_attack "Launching brute force simulation..."
        python bruteforce_simulator.py
        
        # Stop monitoring
        kill $MONITOR_PID 2>/dev/null || true
        
        # Wait and check results
        sleep 10
        print_info "Collecting results..."
        INCIDENTS=$(curl -s http://localhost:5000/api/classifier/history)
        echo "$INCIDENTS" > "$RESULTS_DIR/bruteforce_test_$TIMESTAMP.json"
        
        # Show summary
        BRUTEFORCE_COUNT=$(echo "$INCIDENTS" | grep -o '"attack_guess":"bruteforce"' | wc -l)
        print_status "Brute force simulation complete. Detected $BRUTEFORCE_COUNT brute force incidents."
        ;;
        
    3)
        echo ""
        echo -e "${BLUE}════════════════════════════════════${NC}"
        echo -e "${BLUE}🔧 MISCONFIGURATION SIMULATION${NC}"
        echo -e "${BLUE}════════════════════════════════════${NC}"
        
        # Clear previous incidents
        curl -s -X POST http://localhost:5000/api/detector/stop > /dev/null
        sleep 2
        curl -s -X POST http://localhost:5000/api/detector/start > /dev/null
        sleep 3
        
        print_info "Starting misconfiguration simulation (500 error requests)..."
        
        # Start monitoring
        (
            while true; do
                STATUS=$(curl -s http://localhost:5000/api/detector/status 2>/dev/null || echo "{}")
                echo "$STATUS" | grep -q '"consecutive_anomalies"' && {
                    CONSECUTIVE=$(echo "$STATUS" | grep -o '"consecutive_anomalies":[0-9]*' | cut -d: -f2)
                    if [ "$CONSECUTIVE" -gt 0 ]; then
                        print_detect "Error rate anomaly detected (consecutive: $CONSECUTIVE)"
                    fi
                }
                sleep 5
            done
        ) &
        MONITOR_PID=$!
        
        # Run simulation
        print_attack "Launching misconfiguration simulation..."
        python misconfig_simulator.py
        
        # Stop monitoring
        kill $MONITOR_PID 2>/dev/null || true
        
        # Wait and check results
        sleep 10
        print_info "Collecting results..."
        INCIDENTS=$(curl -s http://localhost:5000/api/classifier/history)
        echo "$INCIDENTS" > "$RESULTS_DIR/misconfig_test_$TIMESTAMP.json"
        
        # Show summary
        MISCONFIG_COUNT=$(echo "$INCIDENTS" | grep -o '"attack_guess":"misconfig"' | wc -l)
        print_status "Misconfiguration simulation complete. Detected $MISCONFIG_COUNT misconfig incidents."
        ;;
        
    4)
        echo ""
        echo -e "${MAGENTA}════════════════════════════════════${NC}"
        echo -e "${MAGENTA}🧪 FULL TEST SUITE${NC}"
        echo -e "${MAGENTA}════════════════════════════════════${NC}"
        
        print_warning "This will run all attack simulations sequentially."
        print_info "Total estimated time: ~5 minutes"
        echo ""
        read -p "Continue with full test suite? (y/N): " -n 1 -r
        echo ""
        
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Cancelled."
            exit 0
        fi
        
        SUITE_RESULTS="$RESULTS_DIR/full_suite_$TIMESTAMP.json"
        echo "{\"suite_start\": \"$(date -Iseconds)\", \"tests\": []}" > "$SUITE_RESULTS"
        
        # Test 1: Brute Force (least disruptive first)
        echo ""
        print_attack "Test 1/3: Brute Force Attack"
        curl -s -X POST http://localhost:5000/api/detector/stop > /dev/null
        sleep 2
        curl -s -X POST http://localhost:5000/api/detector/start > /dev/null
        sleep 3
        
        python bruteforce_simulator.py > /dev/null 2>&1
        sleep 10
        INCIDENTS_BF=$(curl -s http://localhost:5000/api/classifier/history)
        BF_COUNT=$(echo "$INCIDENTS_BF" | grep -c '"attack_guess":"bruteforce"' || echo "0")
        print_status "Brute Force: $BF_COUNT detections"
        
        # Test 2: Misconfiguration
        echo ""
        print_attack "Test 2/3: Misconfiguration"
        curl -s -X POST http://localhost:5000/api/detector/stop > /dev/null
        sleep 2
        curl -s -X POST http://localhost:5000/api/detector/start > /dev/null
        sleep 3
        
        python misconfig_simulator.py > /dev/null 2>&1
        sleep 10
        INCIDENTS_MC=$(curl -s http://localhost:5000/api/classifier/history)
        MC_COUNT=$(echo "$INCIDENTS_MC" | grep -c '"attack_guess":"misconfig"' || echo "0")
        print_status "Misconfiguration: $MC_COUNT detections"
        
        # Test 3: DDoS (most resource intensive last)
        echo ""
        print_attack "Test 3/3: DDoS Attack (this may take 2+ minutes)"
        curl -s -X POST http://localhost:5000/api/detector/stop > /dev/null
        sleep 2
        curl -s -X POST http://localhost:5000/api/detector/start > /dev/null
        sleep 3
        
        python ddos_simulator.py > /dev/null 2>&1
        sleep 15  # DDoS needs more recovery time
        INCIDENTS_DD=$(curl -s http://localhost:5000/api/classifier/history)
        DD_COUNT=$(echo "$INCIDENTS_DD" | grep -c '"attack_guess":"ddos"' || echo "0")
        print_status "DDoS Attack: $DD_COUNT detections"
        
        # Create comprehensive report
        cat > "$SUITE_RESULTS" << EOF
{
  "suite_start": "$(date -Iseconds)",
  "suite_end": "$(date -Iseconds)",
  "summary": {
    "brute_force_detections": $BF_COUNT,
    "misconfiguration_detections": $MC_COUNT,
    "ddos_detections": $DD_COUNT,
    "total_tests": 3,
    "successful_detections": $((BF_COUNT + MC_COUNT + DD_COUNT))
  },
  "detailed_results": {
    "brute_force": $INCIDENTS_BF,
    "misconfiguration": $INCIDENTS_MC,  
    "ddos": $INCIDENTS_DD
  }
}
EOF
        
        echo ""
        echo -e "${GREEN}════════════════════════════════════${NC}"
        echo -e "${GREEN}📊 FULL SUITE RESULTS${NC}"
        echo -e "${GREEN}════════════════════════════════════${NC}"
        echo ""
        echo "🔐 Brute Force Detections: $BF_COUNT"
        echo "🔧 Misconfiguration Detections: $MC_COUNT"
        echo "🔥 DDoS Detections: $DD_COUNT"
        echo ""
        TOTAL_DETECTIONS=$((BF_COUNT + MC_COUNT + DD_COUNT))
        echo "📈 Total Detections: $TOTAL_DETECTIONS/3 attack types"
        echo "💾 Detailed results: $SUITE_RESULTS"
        ;;
        
    5)
        echo ""
        echo -e "${CYAN}════════════════════════════════════${NC}"
        echo -e "${CYAN}📊 SYSTEM STATUS CHECK${NC}"
        echo -e "${CYAN}════════════════════════════════════${NC}"
        
        # Check detector
        print_info "Checking anomaly detector..."
        DETECTOR_STATUS=$(curl -s http://localhost:5000/api/detector/status)
        echo "$DETECTOR_STATUS" | grep -q '"is_running":true' && print_status "Detector running" || print_warning "Detector not running"
        
        # Check baseline
        echo "$DETECTOR_STATUS" | grep -q '"has_baseline":true' && print_status "Baseline loaded" || print_warning "No baseline found"
        
        # Show recent incidents
        print_info "Recent incident history..."
        RECENT=$(curl -s http://localhost:5000/api/classifier/history | tail -n 10)
        INCIDENT_COUNT=$(echo "$RECENT" | grep -c '"incident_type"' || echo "0")
        print_info "Recent incidents: $INCIDENT_COUNT"
        
        # System health
        print_info "System health check..."
        curl -s http://localhost:5000/api/health | grep -q '"status":"healthy"' && print_status "Backend healthy" || print_warning "Backend issues"
        
        echo ""
        print_info "System ready for attack simulations"
        ;;
        
    *)
        print_error "Invalid choice"
        ;;
esac

echo ""
echo -e "${CYAN}📁 Results Directory: $RESULTS_DIR${NC}"
echo -e "${BLUE}🔍 View results: ls -la $RESULTS_DIR${NC}"
echo ""
print_status "Attack simulation workflow complete!"
