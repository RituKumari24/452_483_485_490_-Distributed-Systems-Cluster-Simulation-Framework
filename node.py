import requests
import time
import os

NODE_ID = os.getenv("NODE_ID", "default_node")
CPU_CORES = int(os.getenv("CPU_CORES", "2"))
API_SERVER = "http://apiserver:5000"

# Register the node first
try:
    res = requests.post(f"{API_SERVER}/register_node", json={
        "node_id": NODE_ID,
        "cpu_cores": CPU_CORES
    }, timeout=5)
    print(f"✅ Registered node {NODE_ID}: {res.json()}", flush=True)
except Exception as e:
    print(f"❌ Failed to register node {NODE_ID}: {e}", flush=True)

# Send heartbeat in a loop
while True:
    try:
        response = requests.post(f"{API_SERVER}/send_heartbeat", json={"node_id": NODE_ID}, timeout=5)
        print(f"✅ Heartbeat sent from {NODE_ID}: {response.json()}", flush=True)
    except requests.ConnectionError:
        print(f"❌ API server is down. {NODE_ID} retrying...", flush=True)
    except Exception as e:
        print(f"❌ Error sending heartbeat from {NODE_ID}: {e}", flush=True)

    time.sleep(10)

