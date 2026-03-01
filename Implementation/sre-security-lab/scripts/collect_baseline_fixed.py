#!/usr/bin/env python3
"""
Script to collect baseline metrics for SRE Security Research
Run this during normal traffic periods to establish baseline
"""

import sys
import os
sys.path.append('/app/src')
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend', 'src'))
from baseline import BaselineCalculator

def main():
    print("=" * 60)
    print("SRE SECURITY RESEARCH - BASELINE COLLECTION")
    print("=" * 60)
    print("\nThis script will collect metrics to establish a 'normal' baseline.")
    print("Please ensure you're generating normal traffic during this period.")
    print("\nOptions:")
    print("  1. Quick test (5 minutes)")
    print("  2. Standard baseline (30 minutes)")
    print("  3. Full baseline (60 minutes)")
    
    choice = input("\nEnter choice (1-3): ").strip()
    
    durations = {
        '1': 5,
        '2': 30,
        '3': 60
    }
    
    duration = durations.get(choice, 30)
    
    print(f"\nCollecting baseline for {duration} minutes...")
    print("Please generate normal traffic using your React dashboard or curl commands.")
    
    calculator = BaselineCalculator()
    calculator.run_baseline_collection(duration)
    
    print("\n✅ Baseline collection complete!")
    print(f"Baseline saved to: {calculator.baseline_file}")
    
    # Show summary
    baseline = calculator.load_baseline()
    if baseline:
        print("\n📊 BASELINE SUMMARY:")
        for metric, stats in baseline.items():
            print(f"  {metric}: mean={stats['mean']:.3f}, std={stats['std_dev']:.3f}")

if __name__ == "__main__":
    main()
