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