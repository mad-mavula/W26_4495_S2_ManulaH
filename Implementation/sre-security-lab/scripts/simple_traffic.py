#!/usr/bin/env python3
import requests
import time
import random

BASE_URL = "http://localhost:5000/api"

print("🚀 Starting traffic generator WITH ERRORS...")
print("Press Ctrl+C to stop")
print("-" * 50)

endpoints = ["/health", "/scenarios"]
scenarios = ["dos-attack", "brute-force", "config-error"]
error_endpoints = ["/error-test", "/crash", "/timeout", "/internal-error", "/database"]

request_count = 0
error_count = 0

while True:
    try:
        # 70% Normal traffic - successful requests
        if random.random() < 0.7:
            # Normal traffic to health and scenarios
            for endpoint in endpoints:
                try:
                    response = requests.get(f"{BASE_URL}{endpoint}", timeout=2)
                    print(f"✅ GET {endpoint} - {response.status_code}")
                    request_count += 1
                except:
                    print(f"❌ GET {endpoint} - Failed")
                time.sleep(0.3)
        
        # 20% Simulation traffic - still successful
        elif random.random() < 0.66:  # 20% of total (0.3 * 0.66 ≈ 0.2)
            scenario = random.choice(scenarios)
            try:
                response = requests.post(f"{BASE_URL}/simulate/{scenario}", timeout=2)
                print(f"🔄 POST /simulate/{scenario} - {response.status_code}")
                request_count += 1
            except:
                print(f"❌ POST /simulate/{scenario} - Failed")
        
        # 10% ERROR traffic - generate 5xx errors
        else:
            # Hit non-existent endpoints to generate 404s (4xx) or other errors
            error_endpoint = random.choice(error_endpoints)
            
            # Randomly choose error type
            error_type = random.choice(["404", "500", "503", "504"])
            
            if error_type == "404":
                # 404 Not Found - this will be 4xx, not 5xx
                url = f"{BASE_URL}{error_endpoint}"
                try:
                    response = requests.get(url, timeout=2)
                    print(f"⚠️ GET {error_endpoint} - {response.status_code}")
                    request_count += 1
                except:
                    print(f"⚠️ GET {error_endpoint} - Failed (maybe 500)")
                    error_count += 1
                    request_count += 1
                    
            elif error_type == "500":
                # Force a 500 error by causing an exception
                try:
                    # Send malformed data to cause server error
                    response = requests.post(
                        f"{BASE_URL}/simulate/{random.choice(scenarios)}",
                        json={"malformed": "data" * 10000},  # Large payload
                        timeout=1
                    )
                    print(f"🔥 POST with malformed data - {response.status_code}")
                    if response.status_code >= 500:
                        error_count += 1
                    request_count += 1
                except requests.exceptions.Timeout:
                    print(f"⏱️ Timeout error - 504 Gateway Timeout")
                    error_count += 1
                    request_count += 1
                except:
                    print(f"💥 Connection error - 502 Bad Gateway")
                    error_count += 1
                    request_count += 1
                    
            elif error_type == "503":
                # Overwhelm the server with concurrent requests
                try:
                    for i in range(5):  # Send 5 requests quickly
                        requests.get(f"{BASE_URL}/health", timeout=0.1)
                    print(f"⚡ Rapid requests - possible 503")
                    request_count += 5
                except:
                    print(f"💫 Server overwhelmed - 503 Service Unavailable")
                    error_count += 1
                    
            else:  # 504
                # Cause timeout
                try:
                    response = requests.get(f"{BASE_URL}/health", timeout=0.01)  # Very short timeout
                except requests.exceptions.Timeout:
                    print(f"⏰ Timeout - 504 Gateway Timeout")
                    error_count += 1
                    request_count += 1
                except:
                    pass
        
        # Print error rate every 20 requests
        if request_count % 20 == 0 and request_count > 0:
            error_rate = (error_count / request_count) * 100
            print(f"\n📊 Current error rate: {error_rate:.1f}% ({error_count}/{request_count})")
            print("-" * 50)
        
        # Random delay between 0.1 and 0.5 seconds
        time.sleep(random.uniform(0.1, 0.5))
        
    except KeyboardInterrupt:
        print(f"\n\n📊 Final Statistics:")
        print(f"   Total requests: {request_count}")
        print(f"   Total errors: {error_count}")
        print(f"   Error rate: {(error_count/request_count)*100:.1f}%")
        print("\nStopping...")
        break
    except Exception as e:
        print(f"Error in script: {e}")
        time.sleep(1)
