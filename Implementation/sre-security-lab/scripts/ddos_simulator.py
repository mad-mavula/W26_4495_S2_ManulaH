#!/usr/bin/env python3
import requests
import threading
import time
import random

def get_url():
    return "http://sre-frontend-service.default.svc.cluster.local"

def worker(thread_id, duration, base_url):
    endpoints = [
        '/api/health',
        '/api/scenarios',
    ]
    end_time = time.time() + duration
    count = 0
    while time.time() < end_time:
        ep = random.choice(endpoints)
        try:
            requests.get(f"{base_url}{ep}", timeout=2)
            count += 1
        except:
            pass
        time.sleep(0.05)   # slower rate
    print(f"Thread {thread_id} finished, sent {count} requests")

def main():
    duration = 30          # shorter
    threads = 10           # lower concurrency
    base_url = get_url()
    print(f"Target URL: {base_url}")
    print(f"Generating moderate load for {duration}s with {threads} threads...")
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
