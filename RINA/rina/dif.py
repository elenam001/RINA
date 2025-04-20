import logging


class DIF:
    def __init__(self, name, layer, lower_dif=None, max_bandwidth=1000):
        self.name = name 
        self.layer = layer
        self.ipcps = {} 
        self.lower_dif = lower_dif
        self.max_bandwidth = max_bandwidth
        self.allocated_bandwidth = 0
        self.allocated_flows = {}
        self.monitoring = {
            "bandwidth_usage": [],
            "packet_loss": 0,
            "latency": [],
        }

    def add_ipcp(self, ipcp):
        self.ipcps[ipcp.id] = ipcp

    def remove_ipcp(self, ipcp_id):
        if ipcp_id in self.ipcps:
            del self.ipcps[ipcp_id]

    def get_ipcp(self, ipcp_id):
        return self.ipcps.get(ipcp_id)

    def get_ipcps(self):
        return self.ipcps.values()
    
    def get_lower_dif(self):
        return self.lower_dif
    
    def allocate_bandwidth(self, bandwidth):
        """Allocate bandwidth from the DIF's capacity"""
        if bandwidth is None:
            return True
        if self.allocated_bandwidth + bandwidth <= self.max_bandwidth:
            self.allocated_bandwidth += bandwidth
            logging.debug(f"DIF {self.name}: Allocated {bandwidth} bandwidth, total now: {self.allocated_bandwidth}/{self.max_bandwidth}")
            return True
        else:
            logging.debug(f"DIF {self.name}: Cannot allocate {bandwidth} bandwidth, available: {self.max_bandwidth - self.allocated_bandwidth}")
            return False

    def release_bandwidth(self, bandwidth):
        """Release previously allocated bandwidth"""
        if bandwidth is None:
            return
        self.allocated_bandwidth = max(0, self.allocated_bandwidth - bandwidth)
        logging.debug(f"DIF {self.name}: Released {bandwidth} bandwidth, total now: {self.allocated_bandwidth}/{self.max_bandwidth}")

    def list_allocated_flows(self):
        return [flow.id for flow in self.allocated_flows.values()]