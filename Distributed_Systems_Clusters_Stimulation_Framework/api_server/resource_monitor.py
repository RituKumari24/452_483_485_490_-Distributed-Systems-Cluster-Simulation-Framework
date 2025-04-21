import time
import threading
from threading import Lock
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ResourceMonitor:
    def __init__(self, node_manager):
        self.node_manager = node_manager
        self.lock = Lock()
        self.pod_metrics = {}  # pod_id -> {cpu_usage, memory_usage, timestamp}
        self.running = False
        self.monitor_thread = None
    
    def start_monitoring(self):
        """Start the resource monitoring thread"""
        with self.lock:
            if self.running:
                return False
            
            self.running = True
            self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.monitor_thread.start()
            logger.info("Resource monitoring started")
            return True
    
    def stop_monitoring(self):
        """Stop the resource monitoring thread"""
        with self.lock:
            if not self.running:
                return False
            
            self.running = False
            if self.monitor_thread:
                self.monitor_thread.join(timeout=5)
            return True
    
    def _monitor_loop(self):
        """Background loop to clean up stale metrics"""
        while self.running:
            try:
                self._cleanup_metrics()
                logger.debug(f"Current metrics: {self.pod_metrics}")
            except Exception as e:
                logger.error(f"Error in resource monitor: {e}")
            
            # Sleep for a bit
            time.sleep(60)  # Clean up once a minute
    
    def _cleanup_metrics(self):
        """Clean up metrics for pods that no longer exist"""
        with self.lock:
            # Get current time
            current_time = time.time()
            
            # Remove metrics older than 5 minutes
            stale_time = current_time - 300  # 5 minutes
            stale_pods = []
            
            for pod_id in list(self.pod_metrics.keys()):
                if self.pod_metrics[pod_id]["timestamp"] < stale_time:
                    stale_pods.append(pod_id)
                    
            for pod_id in stale_pods:
                logger.info(f"Removing stale metrics for pod {pod_id}")
                del self.pod_metrics[pod_id]
    
    def update_pod_metrics(self, node_id, pod_metrics):
        """Update metrics for pods on a node"""
        with self.lock:
            # Update timestamp for each pod
            current_time = time.time()
            
            for pod_id, metrics in pod_metrics.items():
                logger.info(f"Updating metrics for pod {pod_id} on node {node_id}: {metrics}")
                self.pod_metrics[pod_id] = {
                    "cpu_usage": metrics.get("cpu_usage", 0),
                    "memory_usage": metrics.get("memory_usage", 0),
                    "node_id": node_id,
                    "timestamp": current_time
                }
    
    def get_pod_metrics(self, pod_id):
        """Get metrics for a specific pod"""
        with self.lock:
            return self.pod_metrics.get(pod_id)
    
    def get_all_pod_metrics(self):
        """Get metrics for all pods"""
        with self.lock:
            logger.info(f"Retrieved all pod metrics: {self.pod_metrics}")
            return {pid: {k: v for k, v in info.items() if k != 'timestamp'} 
                   for pid, info in self.pod_metrics.items()}