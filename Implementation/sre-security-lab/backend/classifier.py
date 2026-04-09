#!/usr/bin/env python3
"""
Classification Engine for SRE Security Research
Severity based on attack intensity and user impact.
Only non-normal incidents are stored in history (no limit).
"""

import time
from typing import Dict, List

class ClassificationEngine:
    def __init__(self):
        self.incident_history = []

    def classify(self, anomaly: Dict) -> Dict:
        metrics = anomaly.get('metrics', {})
        all_metrics = anomaly.get('all_metrics', {})
        deviations = anomaly.get('deviations', {})

        incident_type = "normal"
        attack_guess = None
        confidence = 0
        triggered_rules = []
        user_impact = ""

        def dev(metric):
            return metrics.get(metric, {}).get('deviation', 0)

        # ----- Detection (unchanged) -----
        auth_failures = all_metrics.get('auth_failures', 0)
        if auth_failures > 5:
            incident_type = "security"
            attack_guess = "bruteforce"
            confidence = 85
            triggered_rules.append("Rule4: High authentication failures")

        if incident_type == "normal":
            def auth_is_high():
                return all_metrics.get('auth_failures', 0) > 10 or ('auth_failures' in metrics and dev('auth_failures') > 200)

            if not auth_is_high():
                if 'request_rate' in metrics:
                    req_dev = dev('request_rate')
                    if req_dev > 50 and (dev('cpu_usage') > 50 or dev('memory_usage') > 15):
                        incident_type = "security"
                        attack_guess = "ddos"
                        confidence = 90
                        triggered_rules.append("Rule1: Resource saturation")

                if incident_type == "normal" and 'request_rate' in metrics:
                    req_dev = dev('request_rate')
                    lat_dev = max(dev('latency_p95'), dev('latency_p99'))
                    if req_dev > 50 and lat_dev > 50:
                        incident_type = "security"
                        attack_guess = "ddos"
                        confidence = 80
                        triggered_rules.append("Rule2: User impact (latency)")

                if incident_type == "normal" and 'request_rate' in metrics and 'error_rate' in metrics:
                    req_dev = dev('request_rate')
                    err_dev = dev('error_rate')
                    current_error = all_metrics.get('error_rate', 0)
                    if req_dev > 50 and (err_dev > 50 or current_error > 1):
                        incident_type = "security"
                        attack_guess = "ddos"
                        confidence = 75
                        triggered_rules.append("Rule3: Service failure (errors)")

        if incident_type == "normal" and 'error_rate' in metrics:
            err_dev = dev('error_rate')
            cpu_anomaly = 'cpu_usage' in metrics and abs(dev('cpu_usage')) > 30
            if err_dev > 100 and not cpu_anomaly:
                incident_type = "operational"
                attack_guess = "misconfig"
                confidence = 70
                triggered_rules.append("Rule5: Error spike without CPU saturation")

        # ----- Severity based on attack type and intensity -----
        severity = "P3"
        err_rate = all_metrics.get('error_rate', 0)
        req_rate = all_metrics.get('request_rate', 0)
        baseline_req = deviations.get('request_rate', {}).get('baseline_mean', 1)
        req_factor = req_rate / baseline_req if baseline_req > 0 else 1
        cpu_usage = all_metrics.get('cpu_usage', 0)
        baseline_cpu = deviations.get('cpu_usage', {}).get('baseline_mean', 0.01)
        cpu_factor = cpu_usage / baseline_cpu if baseline_cpu > 0 else 1

        if attack_guess == "ddos":
            if req_factor > 20 or cpu_factor > 5 or err_rate > 5:
                severity = "P1"
                user_impact = "Critical: Extreme DDoS causing severe degradation or service unavailability."
            elif req_factor > 10 or cpu_factor > 3 or err_rate > 1:
                severity = "P2"
                user_impact = "High: Significant DDoS impact – degraded performance."
            else:
                severity = "P3"
                user_impact = "Medium: DDoS detected but limited user impact."

        elif attack_guess == "bruteforce":
            if auth_failures > 100 or err_rate > 5:
                severity = "P1"
                user_impact = "Critical: Massive brute force attack causing system strain."
            else:
                severity = "P2"
                user_impact = "High: Brute force attack detected – potential account takeover risk."

        elif attack_guess == "misconfig":
            if err_rate > 5:
                severity = "P1"
                user_impact = "Critical: Configuration error causing major outage."
            elif err_rate > 1:
                severity = "P2"
                user_impact = "High: Configuration error causing significant errors."
            else:
                severity = "P3"
                user_impact = "Medium: Configuration error causing service degradation."

        else:
            # Normal or unknown
            severity = "P3"
            user_impact = "Low: Anomaly detected but no significant user impact."

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

        # Only store non-normal incidents (security or operational) – no limit
        if incident_type != "normal":
            self.incident_history.append(result)

        return result

    def get_history(self, limit: int = 10) -> List[Dict]:
        # Return last 'limit' incidents (or all if limit is very large)
        if limit >= len(self.incident_history):
            return self.incident_history
        return self.incident_history[-limit:]

_classifier_instance = None

def get_classifier():
    global _classifier_instance
    if _classifier_instance is None:
        _classifier_instance = ClassificationEngine()
    return _classifier_instance
