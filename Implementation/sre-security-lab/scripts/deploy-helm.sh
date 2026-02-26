#!/bin/bash

echo "=== SRE Security Lab Deployment (Using Helm) ==="
echo ""

# 1. Build Docker images locally
echo "1. Building Docker images..."
cd ~/sre-security-lab/backend
echo " Building backend image..."
docker build -t sre-backend:latest .

cd ~/sre-security-lab/frontend
echo " Building frontend image..."
docker build -t sre-frontend:latest .

echo " Docker images built successfully."
docker images | grep sre-

# 2. Load images to Minikube
echo ""
echo "2. Loading images to Minikube..."
minikube image load sre-backend:latest
minikube image load sre-frontend:latest

# 3. Update Helm dependencies
echo ""
echo "3. Updating Helm dependencies..."
cd ~/sre-security-lab/helm-charts/sre-lab
helm dependency update

# 4. Deploy with Helm
echo ""
echo "4. Deploying with Helm..."
helm upgrade --install sre-lab . \
  --namespace sre-lab \
  --create-namespace \
  --values values.yaml

# 5. Wait for deployments
echo ""
echo "5. Waiting for pods to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/sre-backend -n sre-lab
kubectl wait --for=condition=available --timeout=300s deployment/sre-frontend -n sre-lab

# 6. Get access information
echo ""
echo "6. Deployment complete! Getting access information..."

MINIKUBE_IP=$(minikube ip)
FRONTEND_PORT=$(kubectl get service sre-frontend-service -n sre-lab -o jsonpath='{.spec.ports[0].nodePort}')

echo ""
echo "================================================"
echo " ACCESS INFORMATION"
echo "================================================"
echo ""
echo "Deployment Method: Helm"
echo "Namespace: sre-lab"
echo "Minikube IP Address: $MINIKUBE_IP"
echo "Frontend NodePort: $FRONTEND_PORT"
echo ""
echo "=== DIRECT ACCESS ==="
echo "Frontend Dashboard: http://$MINIKUBE_IP:$FRONTEND_PORT"
echo "Backend API: http://$MINIKUBE_IP:$FRONTEND_PORT/api"
echo ""
echo "=== HELM RESOURCES ==="
echo "Releases:"
helm list -n sre-lab
echo ""
echo "Pods:"
kubectl get pods -n sre-lab -l research=sre-security
echo ""
echo "Services:"
kubectl get services -n sre-lab -l research=sre-security
