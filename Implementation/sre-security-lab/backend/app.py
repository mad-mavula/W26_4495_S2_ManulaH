from flask import Flask, jsonify, request
from flask_cors import CORS
from prometheus_client import generate_latest, Counter, Histogram, REGISTRY
import json
import time
import numpy as np

app = Flask(__name__)
CORS(app)

# Prometheus metrics
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP Requests', ['method', 'endpoint', 'status'])
REQUEST_LATENCY = Histogram('http_request_duration_seconds', 'HTTP request latency', ['endpoint'])

# Load scenarios
with open('scenarios/scenarios.json', 'r') as f:
    scenarios = json.load(f)

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy", "timestamp": time.time()})

@app.route('/api/metrics', methods=['GET'])
def metrics():
    return generate_latest(REGISTRY), 200, {'Content-Type': 'text/plain'}

@app.route('/api/scenarios', methods=['GET'])
def get_scenarios():
    REQUEST_COUNT.labels(method='GET', endpoint='/scenarios', status='200').inc()
    with REQUEST_LATENCY.labels(endpoint='/scenarios').time():
        return jsonify(scenarios)

@app.route('/api/simulate/<scenario_id>', methods=['POST'])
def simulate_scenario(scenario_id):
    REQUEST_COUNT.labels(method='POST', endpoint='/simulate', status='200').inc()
    with REQUEST_LATENCY.labels(endpoint='/simulate').time():
        scenario = next((s for s in scenarios if s['id'] == scenario_id), None)
        if not scenario:
            return jsonify({"error": "Scenario not found"}), 404
        
        # Simulate some processing
        time.sleep(0.1)
        
        # Add simulation results
        result = {
            "scenario": scenario['name'],
            "type": scenario['type'],
            "metrics": scenario['metrics'],
            "simulation_id": f"sim_{int(time.time())}",
            "timestamp": time.time(),
            "analysis": {
                "risk_level": "high" if scenario['type'] == 'security' else "medium",
                "recommendations": ["Increase monitoring", "Review logs", "Check resource usage"]
            }
        }
        return jsonify(result)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)