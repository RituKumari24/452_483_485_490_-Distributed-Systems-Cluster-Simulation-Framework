from flask import Flask, request, jsonify
import time
import uuid
from threading import Thread

app = Flask(__name__)

# In-memory cluster data
nodes = {}       # node_id -> {cpu_cores, available_cpu, status, last_heartbeat, pods}
pods = {}        # pod_id -> {node, cpu}
node_load = {}   # node_id -> number of pods assigned

# ========== Route: Add node and launch Docker container ==========
@app.route('/add_node', methods=['POST'])
def add_node():
    data = request.get_json()
    cpu_cores = data.get("cpu_cores")

    if not cpu_cores:
        return jsonify({"error": "Missing CPU cores value"}), 400

    try:
        import docker

        node_id = f"node-{str(uuid.uuid4())[:8]}"
        client = docker.from_env()

        container = client.containers.run(
            "node-image",
            name=node_id,
            detach=True,
            environment={
                "NODE_ID": node_id,
                "CPU_CORES": str(cpu_cores)
            },
            network="cc_p2_backend",  # Update as per your docker network
            restart_policy={"Name": "on-failure"},
        )

        return jsonify({
            "message": "Node container launched",
            "node_id": node_id,
            "cpu_cores": cpu_cores,
            "container_id": container.id
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ========== Background Thread: Monitor node heartbeats ==========
def monitor_nodes():
    while True:
        current_time = time.time()
        for node_id, info in list(nodes.items()):
            last = info.get("last_heartbeat", 0)
            if current_time - last > 60 and info["status"] != "unreachable":
                print(f"❌ Node {node_id} marked as unreachable.")
                info["status"] = "unreachable"

                # Reschedule its pods
                for pod_id in info["pods"]:
                    pod_cpu = pods[pod_id]["cpu"]
                    print(f"🔁 Rescheduling pod {pod_id} needing {pod_cpu} CPU")

                    available_nodes = {
                        nid: n for nid, n in nodes.items()
                        if n["status"] == "healthy" and n["available_cpu"] >= pod_cpu
                    }

                    if available_nodes:
                        # Best-Fit strategy
                        best_node = None
                        min_leftover = float('inf')
                        for nid, ninfo in available_nodes.items():
                            leftover = ninfo["available_cpu"] - pod_cpu
                            if leftover < min_leftover:
                                min_leftover = leftover
                                best_node = nid

                        if best_node:
                            nodes[best_node]["available_cpu"] -= pod_cpu
                            nodes[best_node]["pods"].append(pod_id)
                            pods[pod_id]["node"] = best_node
                            print(f"✅ Pod {pod_id} rescheduled to {best_node}")
                    else:
                        pods[pod_id]["node"] = None  # unscheduled
                        print(f"⚠️ Pod {pod_id} could not be rescheduled.")

                # Reset failed node's pod list and available CPU
                info["pods"] = []
                info["available_cpu"] = 0

        time.sleep(10)

Thread(target=monitor_nodes, daemon=True).start()

# ========== Route: Register a node (called by node.py) ==========
@app.route('/register_node', methods=['POST'])
def register_node():
    data = request.get_json()
    node_id = data.get("node_id")
    cpu_cores = data.get("cpu_cores")

    if not node_id or not cpu_cores:
        return jsonify({"error": "Missing node_id or cpu_cores"}), 400

    nodes[node_id] = {
        "cpu_cores": int(cpu_cores),
        "available_cpu": int(cpu_cores),
        "last_heartbeat": time.time(),
        "pods": [],
        "status": "healthy"
    }
    node_load[node_id] = 0

    return jsonify({"message": f"Node {node_id} registered successfully."}), 200

@app.route('/list_nodes', methods=['GET'])
def list_nodes():
    return jsonify({
        node_id: {
            "status": info["status"],
            "cpu_cores": info["cpu_cores"],
            "available_cpu": info["available_cpu"],
            "pods": info["pods"],
            "last_heartbeat": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(info["last_heartbeat"]))
        }
        for node_id, info in nodes.items()
    })


# ========== Route: Receive heartbeat ==========
@app.route('/send_heartbeat', methods=['POST'])
def send_heartbeat():
    data = request.json
    print("💓 Received Heartbeat Data:", data, flush=True)

    node_id = data.get('node_id')
    if not node_id:
        return jsonify({"error": "Missing node_id"}), 400
    if node_id not in nodes:
        return jsonify({"error": f"Node {node_id} not registered"}), 400

    nodes[node_id]["last_heartbeat"] = time.time()
    nodes[node_id]["status"] = "healthy"
    return jsonify({"message": f"Heartbeat received from {node_id}"}), 200

# ========== Route: Schedule a pod using Best-Fit strategy ==========
@app.route('/schedule_pod', methods=['POST'])
def schedule_pod():
    data = request.json
    pod_id = data.get('pod_id')
    cpu_required = data.get('cpu')

    if not pod_id or cpu_required is None:
        return jsonify({"error": "pod_id and cpu required"}), 400

    cpu_required = int(cpu_required)

    available_nodes = {
        nid: info for nid, info in nodes.items()
        if info["status"] == "healthy" and info["available_cpu"] >= cpu_required
    }

    if not available_nodes:
        return jsonify({"error": "No healthy nodes with enough resources"}), 400

    # Best-Fit strategy
    best_node = None
    min_leftover = float('inf')

    for node_id, info in available_nodes.items():
        leftover = info["available_cpu"] - cpu_required
        if leftover < min_leftover:
            min_leftover = leftover
            best_node = node_id

    if best_node:
        nodes[best_node]["available_cpu"] -= cpu_required
        nodes[best_node]["pods"].append(pod_id)
        pods[pod_id] = {
            "node": best_node,
            "cpu": cpu_required
        }
        return jsonify({"message": f"Pod {pod_id} scheduled on Node {best_node}"}), 200

    return jsonify({"error": "No nodes could accommodate the pod"}), 400

# ========== Route: Get pod status ==========
@app.route('/pod_status', methods=['GET'])
def pod_status():
    pod_id = request.args.get('pod_id')
    if pod_id not in pods:
        return jsonify({"error": "Pod not found"}), 404
    return jsonify({"pod_id": pod_id, "node": pods[pod_id]["node"]})

# ========== Route: Get all nodes and their details ==========
@app.route('/nodes', methods=['GET'])
def get_nodes():
    return jsonify({"nodes": nodes})

# ========== Route: Remove a node ==========
@app.route('/remove_node', methods=['DELETE'])
def remove_node():
    data = request.json
    node_id = data.get('node_id')

    if not node_id or node_id not in nodes:
        return jsonify({"error": "Invalid node_id"}), 400

    for pod_id in nodes[node_id]["pods"]:
        pods[pod_id]["node"] = None  # Unschedule

    del nodes[node_id]
    del node_load[node_id]

    return jsonify({"message": f"Node {node_id} removed, pods unscheduled"}), 200

# ========== Run Flask app ==========
if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=5000)
