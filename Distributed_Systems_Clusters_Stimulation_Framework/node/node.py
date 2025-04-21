# node/node.py
import os
import time
import requests
import random
import json
from threading import Thread
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get environment variables
NODE_ID = os.getenv("NODE_ID", f"node-{random.randint(1000, 9999)}")
CPU_CORES = int(os.getenv("CPU_CORES", "2"))
API_SERVER = os.getenv("API_SERVER", "http://api_server:5000")
HEARTBEAT_INTERVAL = 10  # seconds
REGISTRATION_RETRY_INTERVAL = 5  # seconds

class Node:
    def __init__(self):
        self.pods = []  # List of pod IDs
        self.pod_resources = {}  # pod_id -> cpu_cores
        self.running = True
        
        # Poll for pod assignments every 15 seconds
        self.pod_poll_thread = Thread(target=self._poll_for_pods, daemon=True)

    def register(self):
        """Register the node with the API server"""
        while self.running:
            try:
                response = requests.post(
                    f"{API_SERVER}/api/nodes/register",
                    json={
                        "node_id": NODE_ID,
                        "cpu_cores": CPU_CORES
                    },
                    timeout=5
                )
                if response.status_code == 200:
                    logger.info(f"Node {NODE_ID} registered successfully")
                    return True
                else:
                    logger.warning(f"Failed to register node: {response.text}")
            except Exception as e:
                logger.error(f"Error registering node: {str(e)}")
            
            logger.info(f"Retrying registration in {REGISTRATION_RETRY_INTERVAL} seconds...")
            time.sleep(REGISTRATION_RETRY_INTERVAL)
    
    def _poll_for_pods(self):
        """Poll the API server for pod assignments"""
        while self.running:
            try:
                response = requests.get(f"{API_SERVER}/api/nodes", timeout=5)
                if response.status_code == 200:
                    nodes = response.json().get("nodes", {})
                    if NODE_ID in nodes:
                        node_info = nodes[NODE_ID]
                        self.pods = node_info.get("pods", [])
                        
                        # For each pod, if we don't have resource info, generate it
                        for pod_id in self.pods:
                            if pod_id not in self.pod_resources:
                                response = requests.get(f"{API_SERVER}/api/pods", timeout=5)
                                if response.status_code == 200:
                                    all_pods = response.json().get("pods", {})
                                    if pod_id in all_pods:
                                        self.pod_resources[pod_id] = all_pods[pod_id].get("cpu_cores", 1)
                                    else:
                                        # Default to 1 core if not found
                                        self.pod_resources[pod_id] = 1
                        
                        logger.info(f"Updated pod assignments: {self.pods}")
                        logger.info(f"Pod resources: {self.pod_resources}")
            except Exception as e:
                logger.error(f"Error polling for pods: {str(e)}")
            
            time.sleep(15)

    def send_heartbeat(self):
        """Send heartbeat to the API server"""
        while self.running:
            try:
                pod_metrics = self._generate_pod_metrics()
                
                response = requests.post(
                    f"{API_SERVER}/api/nodes/heartbeat",
                    json={
                        "node_id": NODE_ID,
                        "pod_metrics": pod_metrics
                    },
                    timeout=5
                )
                
                if response.status_code == 200:
                    logger.debug(f"Heartbeat sent from {NODE_ID} with metrics: {pod_metrics}")
                else:
                    logger.warning(f"Failed to send heartbeat: {response.text}")
            
            except requests.exceptions.ConnectionError:
                logger.error("API server is down. Retrying...")
            except Exception as e:
                logger.error(f"Error sending heartbeat: {str(e)}")
            
            time.sleep(HEARTBEAT_INTERVAL)

    def _generate_pod_metrics(self):
        """Generate simulated resource metrics for pods"""
        metrics = {}
        for pod_id in self.pods:
            cpu_cores = self.pod_resources.get(pod_id, 1)
            metrics[pod_id] = {
                "cpu_usage": round(random.uniform(0.1, 0.9) * cpu_cores, 2),
                "memory_usage": random.randint(50, 500)
            }
        logger.info(f"Generated metrics for pods: {metrics}")
        return metrics

    def run(self):
        """Main node execution"""
        # Register with API server
        registration_thread = Thread(target=self.register, daemon=True)
        registration_thread.start()

        # Start heartbeat thread
        heartbeat_thread = Thread(target=self.send_heartbeat, daemon=True)
        heartbeat_thread.start()
        
        # Start pod polling thread
        self.pod_poll_thread.start()

        # Main loop
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutting down node...")
            self.running = False

if __name__ == "__main__":
    node = Node()
    node.run()