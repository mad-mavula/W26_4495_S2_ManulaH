# backend/src/baseline.py
"""
Baseline Calculator for SRE Security Research
Collects normal traffic patterns and establishes baseline metrics
"""

import json
import time
import os
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import threading

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
                    # Get the value from the first result
                    value = float(data['data']['result'][0]['value'][1])
                    return value
            return None
        except Exception as e:
            print(f"Error querying Prometheus: {e}")
            return None
    
    def collect_current_metrics(self) -> Dict:
        """Collect current metrics from Prometheus"""
        metrics = {}
        
        # Define queries for each metric
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
            time.sleep(60)  # Collect every minute
            
        return samples
    
    def save_baseline(self, baseline: Dict):
        """Save baseline to file"""
        # Ensure directory exists
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
                        'is_anomaly': abs(deviation_pct) > (b['std_dev'] * 2)  # 2 sigma threshold
                    }
        
        return deviations
    
    def run_baseline_collection(self, duration_minutes: int = 60):
        """Main function to collect and save baseline"""
        print(f"Starting baseline collection for {duration_minutes} minutes")
        samples = self.collect_baseline_data(duration_minutes)
        baseline = self.calculate_baseline(samples)
        self.save_baseline(baseline)
        print("Baseline collection complete!")
        return baseline
    
    def start_background_monitoring(self, interval_hours: int = 1):
        """Start background thread to update baseline periodically"""
        def monitor_loop():
            while self.is_running:
                print(f"Running scheduled baseline update (every {interval_hours} hours)")
                self.run_baseline_collection(30)  # Collect for 30 minutes
                time.sleep(interval_hours * 3600)
        
        self.is_running = True
        self.thread = threading.Thread(target=monitor_loop)
        self.thread.daemon = True
        self.thread.start()
        print("Background baseline monitoring started")
    
    def stop_background_monitoring(self):
        """Stop the background monitoring thread"""
        self.is_running = False
        if self.thread:
            self.thread.join()
        print("Background monitoring stopped")

# Singleton instance
_baseline_instance = None

def get_baseline_calculator():
    """Get or create the baseline calculator singleton"""
    global _baseline_instance
    if _baseline_instance is None:
        _baseline_instance = BaselineCalculator()
    return _baseline_instance

# If run directly, collect baseline
if __name__ == "__main__":
    calculator = BaselineCalculator()
    print("Starting baseline collection...")
    print("Make sure you're generating normal traffic during this period!")
    calculator.run_baseline_collection(15)  # Collect for 15 minutes for testing
