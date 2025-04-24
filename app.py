import streamlit as st
import requests
from datetime import datetime

import pandas as pd
import matplotlib.pyplot as plt
import io
import base64

BASE_URL = 'http://127.0.0.1:5000'

st.set_page_config(page_title="Kubernetes-like Simulator", layout="centered")
st.title("🚀 Kubernetes-like Cluster Simulator")
st.markdown("Manage your cluster nodes and pods using a friendly interface!")

# Check API server status
def is_api_running():
    try:
        requests.get(f'{BASE_URL}/cluster/status')
        return True
    except:
        return False

if not is_api_running():
    st.error("❌ Cannot connect to the API server. Please start it using `python api_server.py`.")
    st.stop()

# Section: Add Node
st.subheader("🧱 Add Node")
cpu_capacity = st.slider("Select CPU capacity", min_value=1, max_value=16, value=4)
if st.button("Add Node"):
    res = requests.post(f"{BASE_URL}/nodes", json={"cpu_capacity": cpu_capacity})
    if res.status_code == 200:
        st.session_state["node_added"] = True
        st.rerun()
    else:
        st.error(f"❌ Failed to add node: {res.text}")

if "node_added" in st.session_state:
    st.success("✅ Node added successfully!")
    del st.session_state["node_added"]

# Section: Create Pod
st.subheader("📦 Create Pod")
cpu_required = st.slider("CPU required for pod", min_value=1, max_value=8, value=2)
if st.button("Create Pod"):
    res = requests.post(f"{BASE_URL}/pods", json={"cpu_required": cpu_required})
    if res.status_code == 200:
        st.session_state["pod_created"] = True
        st.rerun()
    else:
        st.error(f"❌ Failed to create pod: {res.text}")

if "pod_created" in st.session_state:
    st.success("✅ Pod created successfully!")
    del st.session_state["pod_created"]

# Refresh Button
refresh_clicked = st.button("🔄 Refresh Cluster Status")

# Get Cluster Status
status_res = requests.get(f"{BASE_URL}/cluster/status")
cluster_data = status_res.json() if status_res.status_code == 200 else {}

# Display Nodes
st.subheader("📊 Cluster Status")
nodes = cluster_data.get("nodes", {})
pods = cluster_data.get("pods", {})

if not nodes:
    st.warning("⚠️ No nodes available in the cluster.")
else:
    st.markdown(f"🧮 Total Nodes: **{len(nodes)}**")
    for node_id, info in nodes.items():
        status = info['status']
        status_icon = "🟢" if status == 'healthy' else "🔴"
        heartbeat_time = datetime.fromisoformat(info["last_heartbeat"]).strftime("%Y-%m-%d %H:%M:%S")
        st.markdown(f"""
        {status_icon} **Node ID**: `{node_id[:8]}`
        - **Status**: `{status.capitalize()}`
        - **CPU Availability**: `{info['cpu_available']} / {info['cpu_capacity']}`
        - **Last Heartbeat**: `{heartbeat_time}`
        - **Pods Running**: `{len(info['pods'])}`
        """)
        st.markdown("---")

# Display Pods
st.subheader("📦 Pods Overview")
orphaned_pods = []  # Define orphaned_pods list

if pods:
    st.markdown(f"🧮 Total Pods: **{len(pods)}**")
    
    # Check for orphaned pods
    for pod_id, pod_info in pods.items():
        if pod_info['node_id'] not in nodes:
            orphaned_pods.append(pod_id)
            continue  # Skip orphaned pods in the normal list display
    
    # Display normal pods
    for pod_id, pod_info in pods.items():
        if pod_id not in orphaned_pods:
            st.markdown(f"""
            🔹 **Pod ID**: `{pod_id[:8]}`
            - Assigned to Node: `{pod_info['node_id'][:8]}`
            - CPU Required: `{pod_info['cpu_required']}`
            - Created At: `{pod_info['created_at']}`
            """)
            st.markdown("----")
else:
    st.info("No pods are currently scheduled.")

if orphaned_pods:
    st.info(f"ℹ️ {len(orphaned_pods)} pod(s) were reassigned to new nodes after their original node(s) went offline.")


st.subheader("📈 Pod Resource Monitoring")
if pods:
    pod_ids = list(pods.keys())
    if pod_ids:
        selected_pod = st.selectbox("Select Pod to view metrics", pod_ids, key="pod_metrics_select")
        
        metrics_res = requests.get(f"{BASE_URL}/pods/{selected_pod}/metrics")
        if metrics_res.status_code == 200:
            pod_metrics = metrics_res.json()
            
            # Display average metrics
            avg_metrics = pod_metrics.get('averages', {})
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric(
                    "Avg CPU Usage", 
                    f"{avg_metrics.get('cpu', 0):.1f}%",
                    delta=None
                )
            
            with col2:
                st.metric(
                    "Avg Memory", 
                    f"{avg_metrics.get('memory', 0):.1f} MB",
                    delta=None
                )
            
            with col3:
                st.metric(
                    "Avg Network I/O", 
                    f"{avg_metrics.get('network', 0):.1f} KB/s",
                    delta=None
                )
            
            # Get the metrics history
            metrics_history = pod_metrics.get('metrics', {})
            
            # Plot metrics if we have data
            if metrics_history and all(len(metrics_history.get(k, [])) > 0 for k in ['cpu_usage', 'memory_usage', 'network_io']):
                st.subheader("Resource Usage History")
                
                # Create a figure with 3 subplots
                fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 10))
                
                # Plot CPU usage
                cpu_data = metrics_history.get('cpu_usage', [])
                ax1.plot(cpu_data, 'b-')
                ax1.set_title('CPU Usage (%)')
                ax1.set_ylim(0, 110)
                
                # Plot memory usage
                memory_data = metrics_history.get('memory_usage', [])
                ax2.plot(memory_data, 'g-')
                ax2.set_title('Memory Usage (MB)')
                
                # Plot network I/O
                network_data = metrics_history.get('network_io', [])
                ax3.plot(network_data, 'r-')
                ax3.set_title('Network I/O (KB/s)')
                
                plt.tight_layout()
                st.pyplot(fig)
            else:
                st.info("Collecting metrics data... Please wait a moment.")
        else:
            st.error("Failed to fetch pod metrics")
else:
    st.info("No pods available to monitor.")

# Node Resource Usage
st.subheader("📊 Node Resource Usage")
if nodes:
    node_ids_list = list(nodes.keys())
    selected_node = st.selectbox("Select Node to view resource usage", node_ids_list, key="node_usage_select")
    
    usage_res = requests.get(f"{BASE_URL}/nodes/{selected_node}/resource-usage")
    if usage_res.status_code == 200:
        node_usage = usage_res.json()
        usage_data = node_usage.get('resource_usage', {})
        capacity = node_usage.get('capacity', {})
        
        # Display node usage metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            cpu_usage = usage_data.get('cpu', 0)
            cpu_capacity = capacity.get('cpu', 1)  # Avoid division by zero
            cpu_percent = (cpu_usage / cpu_capacity) * 100
            st.metric(
                "CPU Usage", 
                f"{cpu_usage:.1f}/{cpu_capacity} cores",
                f"{cpu_percent:.1f}%"
            )
        
        with col2:
            st.metric(
                "Memory Usage", 
                f"{usage_data.get('memory', 0):.1f} MB",
                None
            )
        
        with col3:
            st.metric(
                "Network I/O", 
                f"{usage_data.get('network', 0):.1f} KB/s",
                None
            )
        
        with col4:
            st.metric(
                "Pods Running", 
                f"{usage_data.get('pod_count', 0)}",
                None
            )
        
        # Create a gauge chart for CPU utilization
        fig, ax = plt.subplots(figsize=(8, 2))
        cpu_util = cpu_usage / cpu_capacity
        ax.barh(0, cpu_util, height=0.5, color='blue')
        ax.barh(0, 1, height=0.5, color='lightgray', alpha=0.3)
        ax.set_xlim(0, 1)
        ax.set_yticks([])
        ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
        ax.set_xticklabels(['0%', '25%', '50%', '75%', '100%'])
        ax.set_title(f'CPU Utilization: {cpu_percent:.1f}%')
        st.pyplot(fig)
    else:
        st.error("Failed to fetch node resource usage")
else:
    st.info("No nodes available to monitor.")

# Remove Node
st.subheader("🗑️ Remove Node")
node_ids = list(nodes.keys())
if node_ids:
    node_to_remove = st.selectbox("Select Node to remove", node_ids)
    if st.button("Remove Node"):
        res = requests.delete(f"{BASE_URL}/nodes/{node_to_remove}")
        if res.status_code == 200:
            st.session_state["node_removed"] = True
            st.rerun()
        else:
            st.error(f"❌ Failed to remove node: {res.text}")
else:
    st.info("No nodes to remove.")

if "node_removed" in st.session_state:
    st.success("✅ Node removed successfully!")
    del st.session_state["node_removed"]

# Simulate Node Failure
st.subheader("💥 Simulate Node Failure")
if node_ids:
    node_to_fail = st.selectbox("Select Node to simulate failure", node_ids, key="fail_node_select")
    if st.button("Simulate Failure"):
        res = requests.post(f"{BASE_URL}/nodes/{node_to_fail}/fail")
        if res.status_code == 200:
            st.session_state["node_failed"] = True
            st.rerun()
        else:
            st.error(f"❌ Failed to simulate node failure: {res.text}")
else:
    st.info("No nodes available to simulate failure.")

if "node_failed" in st.session_state:
    st.warning("⚠️ Node failure simulated. Cluster will now try to recover pods!")
    del st.session_state["node_failed"]
