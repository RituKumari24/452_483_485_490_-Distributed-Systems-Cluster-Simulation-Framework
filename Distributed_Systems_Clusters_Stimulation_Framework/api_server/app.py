# api_server/app.py
from flask import Flask, request, jsonify
import time
from threading import Thread
import uuid
import docker
import os
import datetime

from api_server.node_manager import NodeManager
from api_server.pod_scheduler import PodScheduler
from api_server.health_monitor import HealthMonitor
from api_server.resource_monitor import ResourceMonitor

app = Flask(__name__)

@app.template_filter('timestamp_to_time')
def timestamp_to_time(timestamp):
    dt = datetime.datetime.fromtimestamp(timestamp)
    return dt.strftime('%H:%M:%S')

# Initializing components
node_manager = NodeManager()
pod_scheduler = PodScheduler(node_manager)
health_monitor = HealthMonitor(node_manager)
resource_monitor = ResourceMonitor(node_manager)

# Connectting the pod scheduler to the health monitor
health_monitor.set_pod_scheduler(pod_scheduler)

# Start background monitoring threads
health_monitor.start_monitoring()
resource_monitor.start_monitoring()

# Docker network for the cluster
DOCKER_NETWORK = "distributed_systems_clusters_stimulation_framework_cluster_network"

@app.route('/')
def home():
    return jsonify({"message": "Distributed Cluster API Server is running"})

@app.route('/api/nodes', methods=['GET'])
def get_nodes():
    """List all nodes and their status"""
    nodes = node_manager.get_all_nodes()
    return jsonify({"nodes": nodes})

@app.route('/api/nodes/add', methods=['POST'])
def add_node():
    """Add a new node to the cluster"""
    data = request.get_json()
    cpu_cores = data.get("cpu_cores")
    if not cpu_cores:
        return jsonify({"error": "Missing CPU cores value"}), 400

    try:
        # Convert to integer
        cpu_cores = int(cpu_cores)
        if cpu_cores <= 0:
            return jsonify({"error": "CPU cores must be positive"}), 400

        # Generate node ID
        node_id = f"node-{str(uuid.uuid4())[:8]}"

        # Launch Docker container for the node
        client = docker.from_env()
        container = client.containers.run(
            "node-image",
            name=node_id,
            detach=True,
            environment={
                "NODE_ID": node_id,
                "CPU_CORES": str(cpu_cores),
                "API_SERVER": "http://api_server:5000"
            },
            network=DOCKER_NETWORK,
            restart_policy={"Name": "on-failure"},
        )

        # Register node
        node_manager.add_node(node_id, cpu_cores)

        return jsonify({
            "message": "Node added successfully",
            "node_id": node_id,
            "cpu_cores": cpu_cores,
            "container_id": container.id
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/nodes/register', methods=['POST'])
def register_node():
    """Register a node with the API server"""
    data = request.get_json()
    node_id = data.get("node_id")
    cpu_cores = data.get("cpu_cores")
    
    if not node_id or not cpu_cores:
        return jsonify({"error": "Missing node_id or cpu_cores"}), 400
    
    node_manager.register_node(node_id, int(cpu_cores))
    return jsonify({"message": f"Node {node_id} registered successfully"}), 200

@app.route('/api/nodes/heartbeat', methods=['POST'])
def receive_heartbeat():
    """Receive heartbeat from a node"""
    data = request.get_json()
    node_id = data.get("node_id")
    pod_metrics = data.get("pod_metrics", {})
    
    if not node_id:
        return jsonify({"error": "Missing node_id"}), 400
    
    # Update node heartbeat
    success = health_monitor.process_heartbeat(node_id)
    if not success:
        return jsonify({"error": f"Node {node_id} not found"}), 404
    
    # Process resource metrics
    if pod_metrics:
        print(f"Received metrics from node {node_id}: {pod_metrics}")
        resource_monitor.update_pod_metrics(node_id, pod_metrics)
    
    return jsonify({"status": "heartbeat acknowledged"}), 200

@app.route('/api/nodes/remove', methods=['POST'])
def remove_node():
    """Remove a node from the cluster"""
    data = request.get_json()
    node_id = data.get("node_id")
    
    if not node_id:
        return jsonify({"error": "Missing node_id"}), 400
    
    try:
        # First update node status to failed to trigger pod rescheduling
        node_manager.update_node_status(node_id, "failed")
        
        # Reschedule pods from the failed node
        result = pod_scheduler.reschedule_pods_from_node(node_id)
        
        # Remove the node from cluster
        removed = node_manager.remove_node(node_id)
        if not removed:
            return jsonify({"error": f"Node {node_id} not found"}), 404
        
        # Stop and remove the Docker container
        client = docker.from_env()
        try:
            container = client.containers.get(node_id)
            container.stop()
            container.remove()
        except docker.errors.NotFound:
            pass  # Container might already be gone
        
        return jsonify({
            "message": f"Node {node_id} removed successfully",
            "rescheduled_pods": result.get("rescheduled", []),
            "failed_pods": result.get("failed", [])
        }), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/pods/launch', methods=['POST'])
def launch_pod():
    """Launch a new pod with specified CPU requirements"""
    data = request.get_json()
    cpu_req = data.get("cpu_cores")
    
    if not cpu_req:
        return jsonify({"error": "Missing CPU requirement"}), 400
    
    try:
        cpu_req = int(cpu_req)
        pod_id = f"pod-{str(uuid.uuid4())[:8]}"
        
        # Schedule the pod
        result = pod_scheduler.schedule_pod(pod_id, cpu_req)
        
        if not result["success"]:
            return jsonify({"error": result["message"]}), 400
        
        return jsonify({
            "message": "Pod launched successfully",
            "pod_id": pod_id,
            "node_id": result["node_id"],
            "cpu_cores": cpu_req
        }), 201
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/pods', methods=['GET'])
def get_pods():
    """Get all pods in the cluster"""
    pods = pod_scheduler.get_all_pods()
    return jsonify({"pods": pods})

@app.route('/api/pods/metrics', methods=['GET'])
def get_pod_metrics():
    """Get resource usage metrics for all pods"""
    metrics = resource_monitor.get_all_pod_metrics()
    return jsonify({"metrics": metrics})

@app.route('/api/pods/unschedule', methods=['POST'])
def unschedule_pod():
    """Unschedule a pod from a node"""
    data = request.get_json()
    pod_id = data.get("pod_id")
    
    if not pod_id:
        return jsonify({"error": "Missing pod_id"}), 400
    
    success = pod_scheduler.unschedule_pod(pod_id)
    
    if success:
        return jsonify({"message": f"Pod {pod_id} unscheduled successfully"}), 200
    else:
        return jsonify({"error": f"Pod {pod_id} not found or could not be unscheduled"}), 404

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
