#!/bin/bash

echo "=== SRE Security Lab Deployment (Using kubectl) ==="
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

# 3. Deploy to Kubernetes
echo ""
echo "3. Deploying to Kubernetes..."
cd ~/sre-security-lab

echo " Deploying backend components..."
kubectl apply -f k8s/backend/configmap.yaml
kubectl apply -f k8s/backend/deployment.yaml
kubectl apply -f k8s/backend/service.yaml

echo " Deploying frontend components..."
kubectl apply -f k8s/frontend/deployment.yaml
kubectl apply -f k8s/frontend/service.yaml

# Optional: Deploy ingress
if [ -f "k8s/ingress/ingress.yaml" ]; then
  echo " Deploying ingress..."
  kubectl apply -f k8s/ingress/ingress.yaml
fi

# 4. Wait for deployments
echo ""
echo "4. Waiting for pods to be ready..."
echo " Waiting for backend pods..."
kubectl wait --for=condition=available --timeout=300s deployment/sre-backend

echo " Waiting for frontend pods..."
kubectl wait --for=condition=available --timeout=300s deployment/sre-frontend

# 5. Get access information
echo ""
echo "5. Deployment complete! Getting access information..."

MINIKUBE_IP=$(minikube ip)
FRONTEND_PORT=$(kubectl get service sre-frontend-service -o jsonpath='{.spec.ports[0].nodePort}')

echo ""
echo "================================================"
echo " ACCESS INFORMATION"
echo "================================================"
echo ""
echo "Kubernetes Architecture: Minikube with Docker driver"
echo "Minikube IP Address: $MINIKUBE_IP"
echo "Frontend NodePort: $FRONTEND_PORT"
echo ""
echo "=== DIRECT ACCESS ==="
echo "Frontend Dashboard: http://$MINIKUBE_IP:$FRONTEND_PORT"
echo "Backend API: http://$MINIKUBE_IP:$FRONTEND_PORT/api"
echo "Backend Health: http://$MINIKUBE_IP:$FRONTEND_PORT/api/health"
echo ""
echo "=== KUBERNETES RESOURCES ==="
echo "Pods:"
kubectl get pods -l research=sre-security
echo ""
echo "Services:"
kubectl get services -l research=sre-security
