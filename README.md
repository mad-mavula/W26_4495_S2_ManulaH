## Repository Structure

- Implementation/ — Source code and experiments
- ReportsAndDocuments/ — Proposal, scope, and formal documents
- Misc/ — ChatGPT logs and supporting material

## Project Description

This research project implements a lightweight framework that uses Site Reliability Engineering (SRE) metrics to detect and prioritize security incidents in cloud-native systems. The framework correlates reliability signals—including latency, error rates, traffic patterns, and error budget consumption—to distinguish between security-driven incidents and operational failures.

**Key Features:**
- Complete Kubernetes environment on Minikube
- Flask backend with Prometheus metrics endpoint (`/api/metrics`)
- React dashboard with three incident scenarios (DDoS, Brute Force, Configuration Error)
- Rule-based classification engine that outputs incident type, severity, and explanations
- Prometheus monitoring stack with custom SRE queries
- Grafana visualizations for p99 latency, error rates, request rates, and saturation metrics

**Research Objective:**
To demonstrate that security incidents produce measurable patterns in reliability metrics that differ from operational failures, enabling better incident classification and prioritization without dedicated security tools.

**Technologies Used:**
- Ubuntu 22.04 (Host OS)
- Docker (Container Runtime)
- Minikube (Kubernetes)
- Python/Flask (Backend API)
- React/Material-UI (Frontend Dashboard)
- Prometheus + Grafana (Monitoring Stack)
- Helm (Package Management)

## Installation Instructions

Follow these steps to set up the complete environment and run the demo on your own machine.

### Prerequisites

| **Requirement** | **Minimum** | **Recommended** |
|-----------------|-------------|-----------------|
| RAM | 8GB | 16GB |
| CPU Cores | 2 | 4 |
| Disk Space | 20GB | 40GB |
| OS | Ubuntu 22.04 | Ubuntu 22.04 |
| Virtualization | Enabled in BIOS | Enabled in BIOS |

### 1. Clone the Repository

git clone https://github.com/your-username/sre-security-lab.git  
cd sre-security-lab  

### 2. Install Docker, Minikube, kubectl, and Helm

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh  
sudo sh get-docker.sh  
sudo usermod -aG docker $USER  
newgrp docker  

# Install Minikube
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64  
sudo install minikube-linux-amd64 /usr/local/bin/minikube  

# Install kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"  
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl  

# Install Helm
curl -fsSL -o get_helm.sh https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3  
chmod 700 get_helm.sh && ./get_helm.sh  

### 3. Start Minikube

minikube start --driver=docker --cpus=4 --memory=6144 --addons=metrics-server,dashboard,ingress  
eval $(minikube docker-env)  

### 4. Install the Prometheus Stack (kube-prometheus-stack)

helm repo add prometheus-community https://prometheus-community.github.io/helm-charts  
helm repo update  
helm install monitoring prometheus-community/kube-prometheus-stack \
  --namespace monitoring --create-namespace \
  --set prometheus.prometheusSpec.serviceMonitorSelectorNilUsesHelmValues=false  

### 5. Build and Deploy the Application

cd ~/sre-security-lab  
./scripts/deploy-kubectl.sh  

This script builds the Docker images (backend and frontend), loads them into Minikube, and applies the Kubernetes manifests.

### 6. Collect a Baseline (Normal Traffic)

Wait for all pods to be ready (kubectl get pods). Then:

kubectl exec -it deployment/sre-backend -- python /app/scripts/collect_baseline_fixed.py  

Choose option 1 (5 minutes). While the script runs, generate normal traffic (e.g., refresh the dashboard every few seconds). The baseline will be saved to /app/data/baseline.json and persist across restarts.

### 7. Start the Anomaly Detector (Auto-starts if baseline exists, but verify)

kubectl exec -it deployment/sre-backend -- curl -X POST http://localhost:5000/api/detector/start  

### 8. Access the Dashboard

minikube service sre-frontend-service  

## User Guide (Quick Demo)

- Run Brute Force Attack – Click the button; wait 15–30 seconds; a “bruteforce” incident with severity P2 (or P1) will appear in the Live Incidents panel.
- Run DDoS Attack – Click the button; a “ddos” incident with severity P3/P2/P1 will appear (depending on intensity).
- Reset Detector – Clears the anomaly detector’s internal state and the classifier history. Use between different attack types.
- Clear Live Incidents – Removes all incidents from the panel (does not affect the detector or baseline).

Note: The misconfiguration attack is not implemented in the final demo.

## Troubleshooting

- Pods not starting: Run kubectl describe pod <pod-name> to see errors. Ensure you built images with eval $(minikube docker-env).
- Baseline not found: Re-run the baseline collection script (step 6).
- 502 errors: Reduce attack intensity by editing ddos_simulator.py (set duration=20, threads=10) and rebuild the backend.

## Repository Structure

- backend/ – Flask application, classifier, anomaly detector, attack scripts
- frontend/ – React dashboard, nginx configuration
- k8s/ – Kubernetes deployment, service, and configmap manifests
- scripts/ – Deployment automation and lab management scripts
- ReportsAndDocuments/ – Final report and presentation slides
