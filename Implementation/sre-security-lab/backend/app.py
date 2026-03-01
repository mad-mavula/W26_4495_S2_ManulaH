from flask import Flask, jsonify, request
from flask_cors import CORS
from prometheus_client import generate_latest, Counter, Histogram, REGISTRY
import json
import time
import numpy as np
import requests
import os
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# ============================================
# BASELINE CALCULATOR CLASS
# ============================================

class BaselineCalculator:
    """
    Calculates and stores baseline metrics for normal system behavior.
    Runs in background, collects data every hour, updates baseline file.
    """
    
    def __init__(self, prometheus_url: str = "http://monitoring-kube-prometheus-prometheus.monitoring:9090"):
        self.prometheus_url = prometheus_url
        self.baseline_file = "/app/data/baseline.json"
        self.is_running = False
        self.thread = None
        
    def query_prometheus(self, query: str) -> Optional[float]:
        """Execute a Prometheus query and return the average value"""
        try:
            response = requests.get(
                f"{self.prometheus_url}/api/v1/query",
                params={"query": query},
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                if data['data']['result']:
                    value = float(data['data']['result'][0]['value'][1])
                    return value
            return None
        except Exception as e:
            print(f"Error querying Prometheus: {e}")
            return None
    
    def collect_current_metrics(self) -> Dict:
        """Collect current metrics from Prometheus"""
        metrics = {}
        
        queries = {
            'request_rate': 'sum(rate(http_requests_total[5m]))',
            'error_rate': 'sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m])) * 100',
            'latency_p95': 'histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))',
            'latency_p99': 'histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))',
            'cpu_usage': 'sum(rate(process_cpu_seconds_total[5m]))',
            'memory_usage': 'sum(process_resident_memory_bytes)',
            'auth_failures': 'sum(rate(http_requests_total{status="401"}[5m]))',
        }
        
        for name, query in queries.items():
            value = self.query_prometheus(query)
            if value is not None:
                metrics[name] = value
            else:
                metrics[name] = 0.0
                
        return metrics
    
    def calculate_baseline(self, samples: List[Dict]) -> Dict:
        """Calculate baseline statistics from collected samples"""
        if not samples:
            return {}
        
        baseline = {}
        metrics_keys = samples[0].keys()
        
        for key in metrics_keys:
            values = [sample[key] for sample in samples if key in sample]
            if values:
                baseline[key] = {
                    'mean': sum(values) / len(values),
                    'min': min(values),
                    'max': max(values),
                    'std_dev': (sum((x - (sum(values) / len(values))) ** 2 for x in values) / len(values)) ** 0.5 if len(values) > 1 else 0,
                    'samples': len(values)
                }
        
        return baseline
    
    def collect_baseline_data(self, duration_minutes: int = 60) -> List[Dict]:
        """Collect metrics over a period of time for baseline calculation"""
        print(f"Collecting baseline data for {duration_minutes} minutes...")
        samples = []
        end_time = time.time() + (duration_minutes * 60)
        
        while time.time() < end_time:
            metrics = self.collect_current_metrics()
            metrics['timestamp'] = time.time()
            samples.append(metrics)
            print(f"  Collected sample {len(samples)}")
            time.sleep(60)
            
        return samples
    
    def save_baseline(self, baseline: Dict):
        """Save baseline to file"""
        os.makedirs(os.path.dirname(self.baseline_file), exist_ok=True)
        
        baseline_data = {
            'timestamp': time.time(),
            'baseline': baseline,
            'metadata': {
                'version': '1.0',
                'description': 'SRE Security Research Baseline'
            }
        }
        
        with open(self.baseline_file, 'w') as f:
            json.dump(baseline_data, f, indent=2)
        
        print(f"Baseline saved to {self.baseline_file}")
    
    def load_baseline(self) -> Optional[Dict]:
        """Load baseline from file"""
        if os.path.exists(self.baseline_file):
            with open(self.baseline_file, 'r') as f:
                data = json.load(f)
                return data.get('baseline', {})
        return None
    
    def get_current_deviation(self, current_metrics: Dict) -> Dict:
        """Calculate deviation of current metrics from baseline"""
        baseline = self.load_baseline()
        if not baseline:
            return {}
        
        deviations = {}
        for metric, value in current_metrics.items():
            if metric in baseline:
                b = baseline[metric]
                if b['mean'] != 0:
                    deviation_pct = ((value - b['mean']) / b['mean']) * 100
                    deviations[metric] = {
                        'current': value,
                        'baseline_mean': b['mean'],
                        'deviation_percent': deviation_pct,
                        'is_anomaly': abs(deviation_pct) > (b['std_dev'] * 3) if b['std_dev'] > 0 else abs(deviation_pct) > 50
                    }
        
        return deviations

# ============================================
# ANOMALY DETECTOR CLASS
# ============================================

class AnomalyDetector:
    """
    Continuously monitors metrics and triggers classification
    when anomalies are detected.
    """
    
    def __init__(self, check_interval: int = 15):
        """
        Initialize the anomaly detector.
        
        Args:
            check_interval: Seconds between metric checks (default: 15)
        """
        self.check_interval = check_interval
        self.baseline_calc = None  # Will be set later
        self.is_running = False
        self.thread = None
        self.callback = None
        self.anomaly_history = []
        self.current_anomaly = None
        self.anomaly_start_time = None
        self.consecutive_anomalies = 0
        self.anomaly_threshold = 2  # Need 2 consecutive checks to confirm
        
        # Anomaly sensitivity thresholds (percentage deviation)
        self.sensitivity = {
            'request_rate': 50,    # 50% deviation
            'error_rate': 100,      # 100% deviation (2x)
            'latency_p95': 100,     # 100% deviation
            'latency_p99': 100,     # 100% deviation
            'cpu_usage': 30,        # 30% deviation
            'memory_usage': 20,      # 20% deviation
            'auth_failures': 200     # 200% deviation (3x)
        }
        
    def set_baseline_calculator(self, baseline_calc):
        """Set the baseline calculator instance"""
        self.baseline_calc = baseline_calc
        
    def set_callback(self, callback_function):
        """
        Set the function to call when anomaly is confirmed.
        This will be your classification engine.
        """
        self.callback = callback_function
        
    def check_metrics(self) -> Dict:
        """
        Check current metrics against baseline.
        Returns anomaly info if detected.
        """
        if not self.baseline_calc:
            return {'anomaly_count': 0, 'anomalous_metrics': {}}
            
        current_metrics = self.baseline_calc.collect_current_metrics()
        deviations = self.baseline_calc.get_current_deviation(current_metrics)
        
        # Find which metrics are anomalous based on sensitivity
        anomalous_metrics = {}
        for metric, data in deviations.items():
            if data and 'deviation_percent' in data:
                dev_pct = abs(data['deviation_percent'])
                sensitivity = self.sensitivity.get(metric, 50)
                
                if dev_pct > sensitivity:
                    anomalous_metrics[metric] = {
                        'deviation': data['deviation_percent'],
                        'current': data['current'],
                        'baseline': data['baseline_mean']
                    }
        
        return {
            'timestamp': time.time(),
            'all_metrics': current_metrics,
            'deviations': deviations,
            'anomalous_metrics': anomalous_metrics,
            'anomaly_count': len(anomalous_metrics)
        }
    
    def detect_anomalies(self) -> Optional[Dict]:
        """
        Run one detection cycle. Returns anomaly info if confirmed.
        """
        result = self.check_metrics()
        
        if result['anomaly_count'] > 0:
            self.consecutive_anomalies += 1
            
            if self.current_anomaly is None:
                # New anomaly starting
                self.current_anomaly = {
                    'start_time': time.time(),
                    'metrics': result['anomalous_metrics'],
                    'all_metrics': result['all_metrics'],
                    'deviations': result['deviations']
                }
                self.anomaly_start_time = time.time()
            
            # Check if anomaly is confirmed (consecutive detections)
            if self.consecutive_anomalies >= self.anomaly_threshold:
                confirmed_anomaly = {
                    'id': f"anomaly_{int(time.time())}",
                    'start_time': self.anomaly_start_time,
                    'detected_time': time.time(),
                    'duration': time.time() - self.anomaly_start_time,
                    'metrics': result['anomalous_metrics'],
                    'all_metrics': result['all_metrics'],
                    'deviations': result['deviations'],
                    'anomaly_count': result['anomaly_count']
                }
                
                # Add to history
                self.anomaly_history.append(confirmed_anomaly)
                
                # Keep history manageable (last 100)
                if len(self.anomaly_history) > 100:
                    self.anomaly_history = self.anomaly_history[-100:]
                
                return confirmed_anomaly
        else:
            # No anomalies detected
            self.consecutive_anomalies = 0
            self.current_anomaly = None
            self.anomaly_start_time = None
            
        return None
    
    def monitoring_loop(self):
        """Main monitoring loop running in background thread"""
        print(f"🚀 Anomaly detector started (checking every {self.check_interval}s)")
        
        while self.is_running:
            try:
                anomaly = self.detect_anomalies()
                
                if anomaly and self.callback:
                    # Trigger the classification engine
                    print(f"⚠️ Anomaly detected! Triggering classification...")
                    self.callback(anomaly)
                elif anomaly:
                    print(f"⚠️ Anomaly detected: {anomaly['anomaly_count']} metrics affected")
                
            except Exception as e:
                print(f"Error in anomaly detection: {e}")
            
            # Wait for next check
            time.sleep(self.check_interval)
    
    def start(self):
        """Start the anomaly detector in background thread"""
        if not self.baseline_calc or not self.baseline_calc.load_baseline():
            print("❌ Cannot start anomaly detector: No baseline found!")
            print("   Please run baseline collection first.")
            return False
        
        self.is_running = True
        self.thread = threading.Thread(target=self.monitoring_loop)
        self.thread.daemon = True
        self.thread.start()
        print(f"✅ Anomaly detector running (interval: {self.check_interval}s)")
        return True
    
    def stop(self):
        """Stop the anomaly detector"""
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=5)
        print("🛑 Anomaly detector stopped")
    
    def get_status(self) -> Dict:
        """Get current detector status"""
        return {
            'is_running': self.is_running,
            'check_interval': self.check_interval,
            'consecutive_anomalies': self.consecutive_anomalies,
            'has_baseline': self.baseline_calc.load_baseline() is not None if self.baseline_calc else False,
            'current_anomaly': self.current_anomaly,
            'recent_history': self.anomaly_history[-5:] if self.anomaly_history else []
        }
    
    def get_anomaly_history(self, limit: int = 10) -> List[Dict]:
        """Get recent anomaly history"""
        return self.anomaly_history[-limit:] if self.anomaly_history else []

# Create singleton instances
baseline_calculator = BaselineCalculator()
anomaly_detector = AnomalyDetector()
anomaly_detector.set_baseline_calculator(baseline_calculator)

# Load baseline on startup
try:
    baseline = baseline_calculator.load_baseline()
    if baseline:
        print("✅ Baseline loaded successfully")
        # Auto-start anomaly detector if baseline exists
        anomaly_detector.start()
    else:
        print("⚠️ No baseline found. Run baseline collection first")
except Exception as e:
    print(f"⚠️ Error loading baseline: {e}")

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

@app.route('/metrics', methods=['GET'])
def metrics_alt():
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

@app.route('/api/realtime-metrics/<scenario_id>', methods=['GET'])
def realtime_metrics(scenario_id):
    """Fetch real metrics from Prometheus for the given scenario"""
    
    # Prometheus service URL inside the cluster
    PROMETHEUS_URL = "http://monitoring-kube-prometheus-prometheus.monitoring:9090"
    
    # Define queries for each scenario
    queries = {
        "dos-attack": {
            "request_rate": 'sum(rate(http_requests_total[1m]))',
            "cpu_usage": 'sum(rate(process_cpu_seconds_total[1m]))',
            "memory_usage": 'sum(process_resident_memory_bytes)',
            "error_rate": 'sum(rate(http_requests_total{status=~"5.."}[1m])) / sum(rate(http_requests_total[1m])) * 100'
        },
        "brute-force": {
            "request_rate": 'sum(rate(http_requests_total{method="POST"}[1m]))',
            "auth_failures": 'sum(rate(http_requests_total{status="401"}[1m]))',
            "success_rate": 'sum(rate(http_requests_total{status="200", method="POST"}[1m])) / sum(rate(http_requests_total{method="POST"}[1m])) * 100'
        },
        "config-error": {
            "request_rate": 'sum(rate(http_requests_total[1m]))',
            "error_rate": 'sum(rate(http_requests_total{status="500"}[1m])) / sum(rate(http_requests_total[1m])) * 100',
            "cpu_usage": 'sum(rate(process_cpu_seconds_total[1m]))'
        }
    }
    
    if scenario_id not in queries:
        return jsonify({"error": "Scenario not found"}), 404
    
    results = {}
    for metric_name, query in queries[scenario_id].items():
        try:
            response = requests.get(
                f"{PROMETHEUS_URL}/api/v1/query",
                params={"query": query},
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                if data['data']['result']:
                    # Extract the value from Prometheus response
                    value = data['data']['result'][0]['value'][1]
                    results[metric_name] = float(value)
                else:
                    results[metric_name] = 0
            else:
                results[metric_name] = 0
        except Exception as e:
            print(f"Error fetching {metric_name}: {e}")
            results[metric_name] = 0
    
    # Add analysis based on real metrics
    risk_level = "low"
    if scenario_id in ["dos-attack", "brute-force"]:
        if results.get('request_rate', 0) > 10:
            risk_level = "high"
        elif results.get('request_rate', 0) > 5:
            risk_level = "medium"
    
    return jsonify({
        "scenario": scenario_id,
        "type": "security" if scenario_id in ["dos-attack", "brute-force"] else "operational",
        "metrics": results,
        "simulation_id": f"real_{int(time.time())}",
        "timestamp": time.time(),
        "analysis": {
            "risk_level": risk_level,
            "recommendations": [
                "Check Grafana dashboard for detailed metrics",
                "Monitor resource usage",
                "Review logs for anomalies"
            ]
        }
    })

@app.route('/api/status', methods=['GET'])
def get_current_status():
    """Get current system status with deviation from baseline"""
    current_metrics = baseline_calculator.collect_current_metrics()
    deviations = baseline_calculator.get_current_deviation(current_metrics)
    
    # Check if any anomaly is detected
    anomalies = {}
    for metric, data in deviations.items():
        if data.get('is_anomaly', False):
            anomalies[metric] = data
    
    status = {
        'timestamp': time.time(),
        'has_baseline': baseline_calculator.load_baseline() is not None,
        'current_metrics': current_metrics,
        'deviations': deviations,
        'anomalies_detected': len(anomalies) > 0,
        'anomalies': anomalies
    }
    
    return jsonify(status)

# NEW: Anomaly Detector Status Endpoint
@app.route('/api/detector/status', methods=['GET'])
def detector_status():
    """Get anomaly detector status"""
    return jsonify(anomaly_detector.get_status())

# NEW: Anomaly Detector History Endpoint
@app.route('/api/detector/history', methods=['GET'])
def detector_history():
    """Get anomaly history"""
    limit = request.args.get('limit', default=10, type=int)
    return jsonify(anomaly_detector.get_anomaly_history(limit))

# NEW: Start/Stop Detector Endpoints (Optional)
@app.route('/api/detector/start', methods=['POST'])
def start_detector():
    """Manually start the anomaly detector"""
    if anomaly_detector.start():
        return jsonify({"status": "started", "message": "Anomaly detector started"})
    return jsonify({"status": "error", "message": "Failed to start (no baseline?)"}), 400

@app.route('/api/detector/stop', methods=['POST'])
def stop_detector():
    """Stop the anomaly detector"""
    anomaly_detector.stop()
    return jsonify({"status": "stopped", "message": "Anomaly detector stopped"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
