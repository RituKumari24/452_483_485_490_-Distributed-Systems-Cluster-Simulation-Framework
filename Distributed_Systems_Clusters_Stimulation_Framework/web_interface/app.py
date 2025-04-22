# web_interface/app.py
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import requests
import os
import datetime

app = Flask(__name__)
app.secret_key = "distributed_cluster_secret"

# API server URL
API_SERVER = os.getenv("API_SERVER", "http://api_server:5000")

@app.route('/')
def index():
    """Dashboard page"""
    return render_template('index.html')

@app.route('/nodes')
def nodes():
    """Node management page"""
    try:
        response = requests.get(f"{API_SERVER}/api/nodes")
        nodes_data = response.json().get("nodes", {})
        return render_template('nodes.html', nodes=nodes_data)
    except Exception as e:
        flash(f"Error retrieving nodes: {str(e)}", "danger")
        return render_template('nodes.html', nodes={})

@app.route('/nodes/add', methods=['GET', 'POST'])
def add_node():
    """Add a new node"""
    if request.method == 'POST':
        cpu_cores = request.form.get('cpu_cores')
        try:
            response = requests.post(
                f"{API_SERVER}/api/nodes/add",
                json={"cpu_cores": cpu_cores}
            )
            
            if response.status_code == 201:
                data = response.json()
                flash(f"Node {data['node_id']} added successfully with {cpu_cores} CPU cores", "success")
            else:
                flash(f"Failed to add node: {response.json().get('error')}", "danger")
            
            return redirect(url_for('nodes'))
        except Exception as e:
            flash(f"Error adding node: {str(e)}", "danger")
            return redirect(url_for('nodes'))
    
    return render_template('add_node.html')

@app.route('/nodes/remove/<node_id>', methods=['POST'])
def remove_node(node_id):
    """Remove a node"""
    try:
        response = requests.delete(
            f"{API_SERVER}/api/nodes/remove",
            json={"node_id": node_id}
        )
        
        if response.status_code == 200:
            flash(f"Node {node_id} removed successfully", "success")
        else:
            flash(f"Failed to remove node: {response.json().get('error')}", "danger")
    except Exception as e:
        flash(f"Error removing node: {str(e)}", "danger")
    
    return redirect(url_for('nodes'))

@app.route('/pods')
def pods():
    """Pod management page"""
    try:
        # Get pods
        pods_response = requests.get(f"{API_SERVER}/api/pods")
        pods_data = pods_response.json().get("pods", {})
        
        # Get metrics
        metrics_response = requests.get(f"{API_SERVER}/api/pods/metrics")
        metrics_data = metrics_response.json().get("metrics", {})
        
        return render_template('pods.html', pods=pods_data, metrics=metrics_data)
    except Exception as e:
        flash(f"Error retrieving pods: {str(e)}", "danger")
        return render_template('pods.html', pods={}, metrics={})

@app.route('/pods/launch', methods=['GET', 'POST'])
def launch_pod():
    """Launch a new pod"""
    if request.method == 'POST':
        cpu_cores = request.form.get('cpu_cores')
        try:
            response = requests.post(
                f"{API_SERVER}/api/pods/launch",
                json={"cpu_cores": cpu_cores}
            )
            
            if response.status_code == 201:
                data = response.json()
                flash(f"Pod {data['pod_id']} launched successfully on node {data['node_id']}", "success")
            else:
                flash(f"Failed to launch pod: {response.json().get('error')}", "danger")
            
            return redirect(url_for('pods'))
        except Exception as e:
            flash(f"Error launching pod: {str(e)}", "danger")
            return redirect(url_for('pods'))
    
    return render_template('launch_pod.html')

@app.route('/api/data')
def get_api_data():
    """Get real-time data for dashboard"""
    try:
        # Get nodes data
        nodes_response = requests.get(f"{API_SERVER}/api/nodes")
        nodes_data = nodes_response.json().get("nodes", {})
        
        # Get pods data
        pods_response = requests.get(f"{API_SERVER}/api/pods")
        pods_data = pods_response.json().get("pods", {})
        
        # Get metrics data
        metrics_response = requests.get(f"{API_SERVER}/api/pods/metrics")
        metrics_data = metrics_response.json().get("metrics", {})
        
        # Process data for charts
        healthy_nodes = len([n for n in nodes_data.values() if n["status"] == "healthy"])
        failed_nodes = len([n for n in nodes_data.values() if n["status"] == "failed"])
        
        total_cpu = sum(n["cpu_cores"] for n in nodes_data.values())
        used_cpu = sum(n["cpu_cores"] - n["available_cores"] for n in nodes_data.values())
        
        # Return data as JSON
        return jsonify({
            "nodes_count": len(nodes_data),
            "pods_count": len(pods_data),
            "healthy_nodes": healthy_nodes,
            "failed_nodes": failed_nodes,
            "total_cpu": total_cpu,
            "used_cpu": used_cpu,
            "nodes": nodes_data,
            "pods": pods_data,
            "metrics": metrics_data
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.template_filter('timestamp_to_time')
def timestamp_to_time(timestamp):
    """Convert Unix timestamp to readable time"""
    dt = datetime.datetime.fromtimestamp(timestamp)
    return dt.strftime('%Y-%m-%d %H:%M:%S')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)
