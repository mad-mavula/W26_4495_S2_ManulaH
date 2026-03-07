#!/usr/bin/env python3
import requests
import time
import subprocess

def get_url():
    result = subprocess.run(['minikube', 'ip'], capture_output=True, text=True)
    minikube_ip = result.stdout.strip()
    result = subprocess.run(
        ['kubectl', 'get', 'service', 'sre-frontend-service',
         '-o', 'jsonpath={.spec.ports[0].nodePort}'],
        capture_output=True, text=True
    )
    port = result.stdout.strip()
    return f"http://{minikube_ip}:{port}"

def main():
    base_url = get_url()
    url = f"{base_url}/api/broken"
    print(f"Target: {url}")
    print("Sending 500 requests...")
    for i in range(500):
        try:
            requests.get(url, timeout=2)
        except:
            pass
        time.sleep(0.02)
    print("Done. Check classifier history.")

if __name__ == "__main__":
    main()
