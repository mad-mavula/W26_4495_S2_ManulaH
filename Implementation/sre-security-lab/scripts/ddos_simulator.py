#!/usr/bin/env python3
"""
Enhanced DDoS simulator to generate high request rate, CPU load,
and occasional errors.
"""

import requests
import threading
import time
import random
import sys
import subprocess

def get_service_url():
    result = subprocess.run(['minikube', 'ip'], capture_output=True, text=True)
    minikube_ip = result.stdout.strip()
    result = subprocess.run(
        ['kubectl', 'get', 'service', 'sre-frontend-service',
         '-o', 'jsonpath={.spec.ports[0].nodePort}'],
        capture_output=True, text=True
    )
    port = result.stdout.strip()
    return f"http://{minikube_ip}:{port}"

def worker(thread_id, duration, base_url):
    endpoints = [
        '/api/health',
        '/api/scenarios',
        '/api/simulate/dos-attack',
        '/api/simulate/brute-force',
        '/api/simulate/config-error',
    ]
    end_time = time.time() + duration
    count = 0
    while time.time() < end_time:
        # Randomly pick an endpoint
        ep = random.choice(endpoints)
        try:
            requests.get(f"{base_url}{ep}", timeout=2)
            count += 1
        except:
            pass
        # Very short sleep to allow high concurrency
        time.sleep(0.005)
    print(f"Thread {thread_id} finished, sent {count} requests")

def main():
    duration = 120          # seconds
    threads = 200           # high concurrency
    base_url = get_service_url()
    print(f"Target URL: {base_url}")
    print(f"Generating high load for {duration} seconds with {threads} threads...")

    threads_list = []
    for i in range(threads):
        t = threading.Thread(target=worker, args=(i, duration, base_url))
        t.start()
        threads_list.append(t)

    for t in threads_list:
        t.join()

    print("Load test completed.")

if __name__ == "__main__":
    main()
