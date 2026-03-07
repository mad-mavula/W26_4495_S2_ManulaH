#!/usr/bin/env python3
"""
Classification Engine for SRE Security Research
Implements detection for DDoS, brute force, and configuration errors.
"""

import time
from typing import Dict, List

class ClassificationEngine:
    def __init__(self):
        self.incident_history = []

    def classify(self, anomaly: Dict) -> Dict:
        metrics = anomaly.get('metrics', {})          # anomalous metrics with deviations
        all_metrics = anomaly.get('all_metrics', {})  # all current metrics
        deviations = anomaly.get('deviations', {})    # all deviations

        # Default values (no incident)
        incident_type = "normal"
        attack_guess = None
        severity = "P3"
        confidence = 0
        triggered_rules = []
        user_impact = ""

        # Helper to get deviation safely
        def dev(metric):
            return metrics.get(metric, {}).get('deviation', 0)

        # ------------------------------------------------------------------
        # DDoS detection rules (ordered from most specific to general)
        # ------------------------------------------------------------------

        # Rule 1: Resource saturation (traffic + CPU/memory)
        if 'request_rate' in metrics:
            req_dev = dev('request_rate')
            cpu_dev = dev('cpu_usage')
            mem_dev = dev('memory_usage')

            if req_dev > 200 and (cpu_dev > 50 or mem_dev > 30):
                incident_type = "security"
                attack_guess = "ddos"
                confidence = 90
                triggered_rules.append("Rule1: Resource saturation (traffic + CPU/memory)")

        # Rule 2: User impact (traffic + latency)
        if incident_type == "normal" and 'request_rate' in metrics:
            req_dev = dev('request_rate')
            lat_dev = max(dev('latency_p95'), dev('latency_p99'))
            if req_dev > 150 and lat_dev > 100:
                incident_type = "security"
                attack_guess = "ddos"
                confidence = 80
                triggered_rules.append("Rule2: User impact (traffic + latency)")

        # Rule 3: Service failure (traffic + error rate)
        if incident_type == "normal" and 'request_rate' in metrics and 'error_rate' in metrics:
            req_dev = dev('request_rate')
            err_dev = dev('error_rate')
            current_error = all_metrics.get('error_rate', 0)
            if req_dev > 150 and (err_dev > 200 or current_error > 5):
                incident_type = "security"
                attack_guess = "ddos"
                confidence = 75
                triggered_rules.append("Rule3: Service failure (traffic + error rate)")

        # ------------------------------------------------------------------
        # Brute force detection (security)
        # ------------------------------------------------------------------
        if incident_type == "normal" and 'auth_failures' in metrics:
            auth_dev = dev('auth_failures')
            current_auth = all_metrics.get('auth_failures', 0)
            # High deviation or significant absolute number of failures
            if auth_dev > 200 or current_auth > 10:
                incident_type = "security"
                attack_guess = "bruteforce"
                confidence = 85
                triggered_rules.append("Rule4: High authentication failures")
                # Optionally could also check request rate to login endpoint,
                # but we don't have separate login metrics yet.

        # ------------------------------------------------------------------
        # Configuration error (operational)
        # ------------------------------------------------------------------
        if incident_type == "normal" and 'error_rate' in metrics:
            err_dev = dev('error_rate')
            # Ensure CPU is NOT anomalous (or at least not high) to distinguish from DDoS
            cpu_anomaly = 'cpu_usage' in metrics and abs(dev('cpu_usage')) > 30
            if err_dev > 100 and not cpu_anomaly:
                incident_type = "operational"
                attack_guess = "misconfig"
                confidence = 70
                triggered_rules.append("Rule5: Error rate spike without CPU saturation")

        # ------------------------------------------------------------------
        # Severity based on error budget impact (SRE principle)
        # Also assign user impact based on incident type
        # ------------------------------------------------------------------
        if incident_type != "normal":
            err_rate = all_metrics.get('error_rate', 0)
            # Simulate error budget: assume SLO 99.9% (0.1% errors)
            if err_rate > 5:
                severity = "P1"
                user_impact = "Critical: High error rate, service may be unavailable."
            elif err_rate > 1:
                severity = "P2"
                user_impact = "High: Significant errors, degraded user experience."
            else:
                # No significant errors – set impact based on attack type
                if attack_guess == "bruteforce":
                    user_impact = "Multiple failed authentication attempts – potential account takeover."
                    severity = "P2"  # brute force is usually high priority
                elif attack_guess == "misconfig":
                    user_impact = "Configuration error causing service degradation."
                    severity = "P3"
                else:
                    # DDoS without errors
                    user_impact = "Medium: Increased traffic causing resource strain."
                    severity = "P3"

        # Build result
        result = {
            'incident_id': anomaly.get('id'),
            'timestamp': time.time(),
            'incident_type': incident_type,
            'attack_guess': attack_guess,
            'severity': severity,
            'confidence': confidence,
            'explanation': {
                'triggered_rules': triggered_rules,
                'metrics_involved': list(metrics.keys()),
                'user_impact': user_impact,
                'anomaly_data': anomaly
            }
        }

        self.incident_history.append(result)
        if len(self.incident_history) > 100:
            self.incident_history = self.incident_history[-100:]

        return result

    def get_history(self, limit: int = 10) -> List[Dict]:
        return self.incident_history[-limit:]

_classifier_instance = None

def get_classifier():
    global _classifier_instance
    if _classifier_instance is None:
        _classifier_instance = ClassificationEngine()
    return _classifier_instance
