#nodemanager.py
import time
from threading import Lock
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NodeManager:
    def __init__(self):
        self.nodes = {}  # node_id -> {cpu_cores, available_cores, status, last_heartbeat, pods}
        self.lock = Lock()  # For thread safety
    
    def add_node(self, node_id, cpu_cores):
        """Add a new node to the cluster"""
        with self.lock:
            logger.info(f"Adding new node {node_id} with {cpu_cores} CPU cores")
            self.nodes[node_id] = {
                "cpu_cores": cpu_cores,
                "available_cores": cpu_cores,
                "status": "initializing",
                "last_heartbeat": time.time(),
                "pods": []
            }
            return True
    
    def register_node(self, node_id, cpu_cores):
        """Register a node that's started up"""
        with self.lock:
            if node_id in self.nodes:
                # Update node details if already exists
                logger.info(f"Node {node_id} already exists, updating status to healthy")
                self.nodes[node_id]["status"] = "healthy"
                self.nodes[node_id]["last_heartbeat"] = time.time()
                return True
            else:
                # Create new node entry
                logger.info(f"Registering new node {node_id} with {cpu_cores} CPU cores")
                self.nodes[node_id] = {
                    "cpu_cores": cpu_cores,
                    "available_cores": cpu_cores,
                    "status": "healthy",
                    "last_heartbeat": time.time(),
                    "pods": []
                }
                return True
    
    def remove_node(self, node_id):
        """Remove a node from the cluster"""
        with self.lock:
            if node_id not in self.nodes:
                logger.warning(f"Attempted to remove non-existent node {node_id}")
                return False
            
            # Remove node
            logger.info(f"Removing node {node_id} from cluster")
            node_info = self.nodes.pop(node_id)
            return True
    
    def update_node_status(self, node_id, status):
        """Update a node's status"""
        with self.lock:
            if node_id not in self.nodes:
                logger.warning(f"Attempted to update status of non-existent node {node_id}")
                return False
            
            logger.info(f"Updating node {node_id} status to {status}")
            self.nodes[node_id]["status"] = status
            return True
    
    def update_heartbeat(self, node_id):
        """Update a node's last heartbeat time"""
        with self.lock:
            if node_id not in self.nodes:
                logger.warning(f"Received heartbeat from non-existent node {node_id}")
                return False
            
            logger.debug(f"Updated heartbeat for node {node_id}")
            self.nodes[node_id]["last_heartbeat"] = time.time()
            self.nodes[node_id]["status"] = "healthy"
            return True
    
    def allocate_resources(self, node_id, cpu_cores):
        """Allocate CPU resources on a node"""
        with self.lock:
            if node_id not in self.nodes:
                logger.warning(f"Attempted to allocate resources on non-existent node {node_id}")
                return False
            
            node = self.nodes[node_id]
            if node["available_cores"] < cpu_cores:
                logger.warning(f"Node {node_id} has insufficient resources: requested {cpu_cores}, available {node['available_cores']}")
                return False
            
            logger.info(f"Allocating {cpu_cores} cores on node {node_id}")
            node["available_cores"] -= cpu_cores
            return True
    
    def release_resources(self, node_id, cpu_cores):
        """Release CPU resources on a node"""
        with self.lock:
            if node_id not in self.nodes:
                logger.warning(f"Attempted to release resources on non-existent node {node_id}")
                return False
            
            node = self.nodes[node_id]
            logger.info(f"Releasing {cpu_cores} cores on node {node_id}")
            node["available_cores"] += cpu_cores
            
            # Ensure we don't exceed total cores
            if node["available_cores"] > node["cpu_cores"]:
                logger.warning(f"Available cores exceeded total cores on node {node_id}, capping at {node['cpu_cores']}")
                node["available_cores"] = node["cpu_cores"]
            
            return True
    
    def add_pod_to_node(self, node_id, pod_id):
        """Add a pod to a node"""
        with self.lock:
            if node_id not in self.nodes:
                logger.warning(f"Attempted to add pod to non-existent node {node_id}")
                return False
            
            logger.info(f"Adding pod {pod_id} to node {node_id}")
            if pod_id in self.nodes[node_id]["pods"]:
                logger.warning(f"Pod {pod_id} already exists on node {node_id}")
                return True
                
            self.nodes[node_id]["pods"].append(pod_id)
            return True
    
    def remove_pod_from_node(self, node_id, pod_id):
        """Remove a pod from a node"""
        with self.lock:
            if node_id not in self.nodes:
                logger.warning(f"Attempted to remove pod from non-existent node {node_id}")
                return False
            
            if pod_id in self.nodes[node_id]["pods"]:
                logger.info(f"Removing pod {pod_id} from node {node_id}")
                self.nodes[node_id]["pods"].remove(pod_id)
                return True
            else:
                logger.warning(f"Pod {pod_id} not found on node {node_id}")
                return False
    
    def get_node(self, node_id):
        """Get information about a specific node"""
        with self.lock:
            node_info = self.nodes.get(node_id)
            if not node_info:
                logger.warning(f"Attempted to get info for non-existent node {node_id}")
            return node_info
    
    def get_all_nodes(self):
        """Get information about all nodes"""
        with self.lock:
            # Create a copy to avoid concurrent modification issues
            return {nid: info.copy() for nid, info in self.nodes.items()}
    
    def get_healthy_nodes(self):
        """Get all healthy nodes"""
        with self.lock:
            healthy = {nid: info.copy() for nid, info in self.nodes.items() 
                   if info["status"] == "healthy"}
            logger.debug(f"Found {len(healthy)} healthy nodes")
            return healthy
