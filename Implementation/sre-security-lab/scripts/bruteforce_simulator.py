#!/usr/bin/env python3
import requests
import threading
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

def worker(thread_id, duration, base_url):
    end_time = time.time() + duration
    count = 0
    while time.time() < end_time:
        try:
            requests.post(f"{base_url}/api/login", json={}, timeout=2)
            count += 1
        except:
            pass
        time.sleep(0.01)
    print(f"Thread {thread_id} finished, sent {count} requests")

def main():
    duration = 60
    threads = 50
    base_url = get_url()
    print(f"Target: {base_url}")
    print(f"Starting brute force simulation for {duration}s with {threads} threads...")
    threads_list = []
    for i in range(threads):
        t = threading.Thread(target=worker, args=(i, duration, base_url))
        t.start()
        threads_list.append(t)
    for t in threads_list:
        t.join()
    print("Done. Check classifier history.")

if __name__ == "__main__":
    main()
