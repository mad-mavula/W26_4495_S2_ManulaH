#!/usr/bin/env python3
import requests
import threading
import time

def get_url():
    return "http://sre-frontend-service.default.svc.cluster.local"

def worker(thread_id, duration, base_url):
    end_time = time.time() + duration
    count = 0
    while time.time() < end_time:
        try:
            requests.post(f"{base_url}/api/login", json={}, timeout=2)
            count += 1
        except:
            pass
        time.sleep(0.05)
    print(f"Thread {thread_id} finished, sent {count} requests")

def main():
    duration = 30
    threads = 10
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
    print("Done.")

if __name__ == "__main__":
    main()
