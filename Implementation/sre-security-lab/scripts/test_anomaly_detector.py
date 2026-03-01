#!/usr/bin/env python3
"""
Test script for anomaly detector
"""

import sys
import os
import time
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend', 'src'))
from anomaly_detector import get_anomaly_detector

def classification_callback(anomaly):
    """This will be replaced by your actual classification engine"""
    print("\n" + "="*60)
    print("🔔 CLASSIFICATION ENGINE TRIGGERED!")
    print("="*60)
    print(f"Anomaly ID: {anomaly['id']}")
    print(f"Duration: {anomaly['duration']:.1f} seconds")
    print(f"Affected metrics: {list(anomaly['metrics'].keys())}")
    print("\nMetric Details:")
    for metric, data in anomaly['metrics'].items():
        print(f"  {metric}: {data['deviation']:.1f}% deviation")
    print("="*60 + "\n")

def main():
    print("="*60)
    print("ANOMALY DETECTOR TEST")
    print("="*60)
    
    # Create detector with 5-second checks
    detector = get_anomaly_detector()
    detector.check_interval = 5
    detector.anomaly_threshold = 2
    
    # Set callback
    detector.set_callback(classification_callback)
    
    # Start detector
    if not detector.start():
        print("❌ Failed to start detector. Run baseline collection first.")
        return
    
    print("\n📊 Monitoring for anomalies...")
    print("Press Ctrl+C to stop\n")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping detector...")
        detector.stop()
    
    # Show history
    print("\n📈 Anomaly History:")
    history = detector.get_anomaly_history()
    if history:
        for i, a in enumerate(history):
            print(f"  {i+1}. {time.ctime(a['start_time'])} - {a['anomaly_count']} metrics")
    else:
        print("  No anomalies detected during test period")

if __name__ == "__main__":
    main()
