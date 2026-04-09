#!/usr/bin/env python3
"""
Anomaly Detector for SRE Security Research
Continuously watches metrics, compares with baseline,
and triggers classification when anomalies are detected
"""

import time
import threading
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Callable
from baseline import get_baseline_calculator
from classifier import get_classifier

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
        self.baseline_calc = get_baseline_calculator()
        self.classifier = get_classifier()
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
        
    def set_callback(self, callback_function: Callable):
        """
        Set an optional callback function (alternative to using classifier).
        """
        self.callback = callback_function

    def set_baseline_calculator(self, calculator):
        """
        Set a custom baseline calculator (dependency injection).
        Overrides the default calculator obtained from get_baseline_calculator().
        """
        self.baseline_calc = calculator
        
    def check_metrics(self) -> Dict:
        """
        Check current metrics against baseline.
        Returns anomaly info if detected.
        """
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
        # Debug: print auth_failures from fresh metrics
        print(f"DEBUG check_metrics auth_failures: {result['all_metrics'].get('auth_failures')}")
        
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
                
                if anomaly:
                    # Anomaly confirmed – run classification
                    print(f"⚠️ Anomaly detected! Classifying...")
                    
                    # Use classifier (primary)
                    if self.classifier:
                        classification = self.classifier.classify(anomaly)
                        print(f"   Classification: {classification['incident_type']} - {classification.get('attack_guess','unknown')} "
                              f"(severity {classification['severity']}, confidence {classification['confidence']}%)")
                    # Fallback to callback if no classifier
                    elif self.callback:
                        self.callback(anomaly)
                    else:
                        print(f"   No classifier or callback set. Anomaly: {anomaly['anomaly_count']} metrics")
                
            except Exception as e:
                print(f"Error in anomaly detection: {e}")
            
            # Wait for next check
            time.sleep(self.check_interval)
    
    def reset(self):
        """Reset the detector's internal state (history, current anomaly, counters)."""
        print("🔄 Anomaly detector reset called")
        self.anomaly_history = []
        self.current_anomaly = None
        self.anomaly_start_time = None
        self.consecutive_anomalies = 0
    
    def start(self):
        """Start the anomaly detector in background thread"""
        if not self.baseline_calc.load_baseline():
            print("❌ Cannot start anomaly detector: No baseline found!")
            print("   Please run baseline collection first.")
            return False
        
        # Reset internal state to avoid carrying over old anomalies
        self.reset()
        
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
            'has_baseline': self.baseline_calc.load_baseline() is not None,
            'current_anomaly': self.current_anomaly,
            'recent_history': self.anomaly_history[-5:] if self.anomaly_history else []
        }
    
    def get_anomaly_history(self, limit: int = 10) -> List[Dict]:
        """Get recent anomaly history"""
        return self.anomaly_history[-limit:] if self.anomaly_history else []

# Singleton instance
_detector_instance = None

def get_anomaly_detector():
    """Get or create the anomaly detector singleton"""
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = AnomalyDetector()
    return _detector_instance

# If run directly, test the detector
if __name__ == "__main__":
    detector = AnomalyDetector(check_interval=5)
    
    def test_callback(anomaly):
        print("\n🔔 TEST CALLBACK TRIGGERED!")
        print(f"Anomaly: {anomaly['anomaly_count']} metrics")
        print(f"Metrics: {list(anomaly['metrics'].keys())}")
    
    detector.set_callback(test_callback)
    
    if detector.start():
        try:
            print("\n📊 Monitoring for 30 seconds...")
            time.sleep(30)
        finally:
            detector.stop()
    
    print("\n📈 Anomaly History:")
    for i, a in enumerate(detector.get_anomaly_history()):
        print(f"  {i+1}. {a['start_time']} - {a['anomaly_count']} metrics")
