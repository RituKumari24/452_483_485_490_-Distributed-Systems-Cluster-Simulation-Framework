# web_interface/app.py
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import requests
import os
import json
import logging
import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.template_filter('timestamp_to_time')
def timestamp_to_time(timestamp):
    dt = datetime.datetime.fromtimestamp(timestamp)
    return dt.strftime('%H:%M:%S')

app.secret_key = os.getenv("SECRET_KEY", "dev_key_for_flask_session")

API_SERVER = os.getenv("API_SERVER", "http://api_server:5000")

@app.route('/')
def index():
    """Dashboard page"""
    # Get node count
    nodes_response = requests.get(f"{API_SERVER}/api/nodes")
    if nodes_response.status_code != 200:
        flash("Failed to connect to API server", "danger")
        node_count = 0
        nodes = {}
    else:
        nodes = nodes_response.json().get("nodes", {})
        node_count = len(nodes)
    
    # Get pod count
    pods_response = requests.get(f"{API_SERVER}/api/pods")
    if pods_response.status_code != 200:
        flash("Failed to fetch pods", "danger")
        pod_count = 0
    else:
        pods = pods_response.json().get("pods", {})
        pod_count = len(pods)
    
    return render_template('index.html', node_count=node_count, pod_count=pod_count, nodes=nodes)

@app.route('/nodes')
def nodes():
    """Nodes management page"""
    response = requests.get(f"{API_SERVER}/api/nodes")
    if response.status_code != 200:
        flash("Failed to fetch nodes", "danger")
        nodes = {}
    else:
        nodes = response.json().get("nodes", {})
    
    return render_template('nodes.html', nodes=nodes)

@app.route('/nodes/add', methods=['GET', 'POST'])
def add_node():
    """Add a new node"""
    if request.method == 'POST':
        cpu_cores = request.form.get('cpu_cores')
        
        if not cpu_cores:
            flash("CPU cores must be specified", "danger")
            return redirect(url_for('add_node'))
        
        try:
            # Validate CPU cores is a positive integer
            cpu_cores = int(cpu_cores)
            if cpu_cores <= 0:
                flash("CPU cores must be a positive number", "danger")
                return redirect(url_for('add_node'))
            
            # Send request to API server
            response = requests.post(
                f"{API_SERVER}/api/nodes/add", 
                json={"cpu_cores": cpu_cores}
            )
            
            if response.status_code == 201:
                flash("Node added successfully", "success")
                return redirect(url_for('nodes'))
            else:
                flash(f"Failed to add node: {response.json().get('error', 'Unknown error')}", "danger")
                return redirect(url_for('add_node'))
        
        except ValueError:
            flash("CPU cores must be a number", "danger")
            return redirect(url_for('add_node'))
        except Exception as e:
            flash(f"An error occurred: {str(e)}", "danger")
            return redirect(url_for('add_node'))
    
    return render_template('add_node.html')

@app.route('/nodes/delete', methods=['POST'])
def delete_node():
    """Delete a node"""
    node_id = request.form.get('node_id')
    
    if not node_id:
        flash("Node ID must be specified", "danger")
        return redirect(url_for('nodes'))
    
    try:
        # Send request to API server
        response = requests.delete(
            f"{API_SERVER}/api/nodes/remove", 
            json={"node_id": node_id}
        )
        
        if response.status_code == 200:
            result = response.json()
            rescheduled = result.get("rescheduled_pods", [])
            failed = result.get("failed_pods", [])
            
            if failed:
                flash(f"Node removed, but {len(failed)} pods could not be rescheduled: {', '.join(failed)}", "warning")
            elif rescheduled:
                flash(f"Node removed and {len(rescheduled)} pods were rescheduled successfully", "success")
            else:
                flash("Node removed successfully", "success")
        else:
            flash(f"Failed to remove node: {response.json().get('error', 'Unknown error')}", "danger")
        
        return redirect(url_for('nodes'))
    
    except Exception as e:
        flash(f"An error occurred: {str(e)}", "danger")
        return redirect(url_for('nodes'))

@app.route('/pods')
def pods():
    """Pods management page"""
    try:
        # Get all pods
        pods_response = requests.get(f"{API_SERVER}/api/pods")
        if pods_response.status_code != 200:
            flash("Failed to fetch pods", "danger")
            pods = {}
        else:
            pods = pods_response.json().get("pods", {})
            logger.info(f"Retrieved pods: {pods}")
        
        # Get pod metrics
        metrics_response = requests.get(f"{API_SERVER}/api/pods/metrics")
        if metrics_response.status_code != 200:
            flash("Failed to fetch pod metrics", "warning")
            metrics = {}
        else:
            metrics = metrics_response.json().get("metrics", {})
            logger.info(f"Retrieved pod metrics: {metrics}")
        
        return render_template('pods.html', pods=pods, metrics=metrics)
    except Exception as e:
        flash(f"An error occurred: {str(e)}", "danger")
        logger.error(f"Error in pods view: {str(e)}")
        return render_template('pods.html', pods={}, metrics={})

@app.route('/pods/launch', methods=['GET', 'POST'])
def launch_pod():
    """Launch a new pod"""
    if request.method == 'POST':
        cpu_cores = request.form.get('cpu_cores')
        
        if not cpu_cores:
            flash("CPU cores must be specified", "danger")
            return redirect(url_for('launch_pod'))
        
        try:
            # Validate CPU cores is a positive integer
            cpu_cores = int(cpu_cores)
            if cpu_cores <= 0:
                flash("CPU cores must be a positive number", "danger")
                return redirect(url_for('launch_pod'))
            
            # Send request to API server
            response = requests.post(
                f"{API_SERVER}/api/pods/launch", 
                json={"cpu_cores": cpu_cores}
            )
            
            if response.status_code == 201:
                result = response.json()
                flash(f"Pod {result.get('pod_id')} launched successfully on node {result.get('node_id')}", "success")
                return redirect(url_for('pods'))
            else:
                flash(f"Failed to launch pod: {response.json().get('error', 'Unknown error')}", "danger")
                return redirect(url_for('launch_pod'))
        
        except ValueError:
            flash("CPU cores must be a number", "danger")
            return redirect(url_for('launch_pod'))
        except Exception as e:
            flash(f"An error occurred: {str(e)}", "danger")
            return redirect(url_for('launch_pod'))
    
    # Get available nodes for the dropdown
    response = requests.get(f"{API_SERVER}/api/nodes")
    if response.status_code != 200:
        flash("Failed to fetch available nodes", "warning")
        nodes = {}
    else:
        nodes = response.json().get("nodes", {})
    
    return render_template('launch_pod.html', nodes=nodes)

@app.route('/pods/delete', methods=['POST'])
def delete_pod():
    """Delete a pod"""
    data = request.get_json()
    pod_id = data.get('pod_id')
    
    if not pod_id:
        return jsonify({"success": False, "message": "Pod ID must be specified"})
    
    try:
        # Send request to API server to unschedule the pod
        response = requests.post(
            f"{API_SERVER}/api/pods/unschedule", 
            json={"pod_id": pod_id}
        )
        
        if response.status_code == 200:
            return jsonify({"success": True, "message": "Pod deleted successfully"})
        else:
            error_msg = response.json().get('error', 'Unknown error')
            return jsonify({"success": False, "message": f"Failed to delete pod: {error_msg}"})
    
    except Exception as e:
        return jsonify({"success": False, "message": f"An error occurred: {str(e)}"})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)