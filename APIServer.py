from flask import Flask, request, jsonify
import time
from threading import Thread

app = Flask(__name__)

# In-memory storage for nodes and pods
nodes = {}       # node_id -> {cpu_cores, status, last_heartbeat, pods}
pods = {}        # pod_id -> {node}
node_load = {}   # node_id -> number of pods assigned

@app.route('/add_node', methods=['POST'])
def add_node():
    data = request.get_json()
    cpu_cores = data.get("cpu_cores")

    if not cpu_cores:
        return jsonify({"error": "Missing CPU cores value"}), 400

    try:
        import docker
        import uuid

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
            network="your_network_name",  # replace with actual network
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

# Background thread to check heartbeats
def monitor_nodes():
    while True:
        current_time = time.time()
        for node_id, info in list(nodes.items()):
            if current_time - info.get("last_heartbeat", 0) > 30:
                nodes[node_id]["status"] = "unreachable"
        time.sleep(10)

Thread(target=monitor_nodes, daemon=True).start()

# Route: Register a node
@app.route('/register_node', methods=['POST'])
def register_node():
    data = request.get_json()
    node_id = data.get("node_id")
    cpu_cores = data.get("cpu_cores")

    if not node_id or not cpu_cores:
        return jsonify({"error": "Missing node_id or cpu_cores"}), 400

    nodes[node_id] = {
        "cpu_cores": cpu_cores,
        "last_heartbeat": time.time(),
        "pods": [],
        "status": "healthy"
    }
    node_load[node_id] = 0
    return jsonify({"message": f"Node {node_id} registered successfully."}), 200

# Route: Get all nodes
@app.route('/nodes', methods=['GET'])
def get_nodes():
    return jsonify({"nodes": list(nodes.keys())})

# Route: Schedule pod to least-loaded node
@app.route('/schedule_pod', methods=['POST'])
def schedule_pod():
    data = request.json
    pod_id = data.get('pod_id')
    if not pod_id:
        return jsonify({"error": "pod_id is required"}), 400

    available_nodes = {k: v for k, v in nodes.items() if v["status"] == "healthy"}
    if not available_nodes:
        return jsonify({"error": "No available healthy nodes"}), 400

    # Find node with least pods
    node_id = min(node_load, key=node_load.get)
    pods[pod_id] = {"node": node_id}
    node_load[node_id] += 1
    nodes[node_id]["pods"].append(pod_id)

    return jsonify({"message": f"Pod {pod_id} scheduled on Node {node_id}"}), 200

# Route: Get pod status
@app.route('/pod_status', methods=['GET'])
def pod_status():
    pod_id = request.args.get('pod_id')
    if pod_id not in pods:
        return jsonify({"error": "Pod not found"}), 404
    return jsonify({"pod_id": pod_id, "node": pods[pod_id]["node"]})

# Route: Remove a node
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

# Route: Receive heartbeat
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

# Run Flask app
if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=5000)

