import asyncio
import random
import time

from rina.application import Application
from rina.dif import DIF
from rina.ipcp import IPCP


class NetworkConditions:
    """Class to simulate realistic network conditions"""
    def __init__(self, 
                 latency_ms=0, 
                 jitter_ms=0, 
                 packet_loss_rate=0, 
                 bandwidth_mbps=None,
                 corruption_rate=0,
                 reordering_rate=0):
        self.latency_ms = latency_ms
        self.jitter_ms = jitter_ms
        self.packet_loss_rate = packet_loss_rate
        self.bandwidth_mbps = bandwidth_mbps
        self.corruption_rate = corruption_rate
        self.reordering_rate = reordering_rate
        self.queue = asyncio.Queue()
        self.processing_task = None
        self.last_packet_time = 0
        self.bytes_sent = 0
        self.start_time = None
        self.reorder_buffer = []
        
    async def start(self):
        """Start processing packets"""
        self.processing_task = asyncio.create_task(self._process_queue())
        self.start_time = time.time()
    
    async def stop(self):
        """Stop processing packets"""
        if self.processing_task:
            self.processing_task.cancel()
            try:
                await self.processing_task
            except asyncio.CancelledError:
                pass
    
    async def process_packet(self, packet, dest_ipcp, flow_id):
        """Process a packet according to defined network conditions"""
        await self.queue.put((packet, dest_ipcp, flow_id))
        
    async def _process_queue(self):
        """Internal task that processes the packet queue"""
        while True:
            packet, dest_ipcp, flow_id = await self.queue.get()
            
            # Apply bandwidth limitation
            if self.bandwidth_mbps:
                packet_size_bits = len(packet) * 8
                theoretical_time = packet_size_bits / (self.bandwidth_mbps * 1_000_000)
                self.bytes_sent += len(packet)
                
                # Calculate elapsed time and if we're sending too fast, delay
                elapsed = time.time() - self.start_time
                expected_elapsed = (self.bytes_sent * 8) / (self.bandwidth_mbps * 1_000_000)
                if expected_elapsed > elapsed:
                    await asyncio.sleep(expected_elapsed - elapsed)
            
            # Simulate packet loss
            if random.random() < self.packet_loss_rate:
                # Packet lost, don't deliver
                self.queue.task_done()
                continue
                
            # Simulate packet corruption
            if random.random() < self.corruption_rate:
                # Corrupt the packet data
                if isinstance(packet, bytes) and len(packet) > 0:
                    pos = random.randrange(len(packet))
                    # XOR a byte to corrupt it
                    corrupt_byte = packet[pos] ^ random.randint(1, 255)
                    packet = packet[:pos] + bytes([corrupt_byte]) + packet[pos+1:]
            
            # Apply base latency + jitter
            latency = self.latency_ms / 1000  # Convert to seconds
            if self.jitter_ms > 0:
                # Add random jitter within defined range
                jitter = random.uniform(-self.jitter_ms/1000, self.jitter_ms/1000)
                latency += jitter
            
            # Handle packet reordering
            if random.random() < self.reordering_rate:
                # Add to reorder buffer with shorter delay
                reorder_delay = latency * 0.5
                asyncio.create_task(self._delayed_delivery(reorder_delay, packet, dest_ipcp, flow_id))
            else:
                # Normal delivery path
                await self._delayed_delivery(latency, packet, dest_ipcp, flow_id)
            
            self.queue.task_done()
    
    async def _delayed_delivery(self, delay, packet, dest_ipcp, flow_id):
        """Deliver a packet after the specified delay"""
        await asyncio.sleep(delay)
        try:
            # Check if the flow exists before delivering
            if hasattr(dest_ipcp, 'flows') and flow_id in dest_ipcp.flows:
                # Make sure the packet is properly formatted if it's not already a dict
                if not isinstance(packet, dict) and isinstance(packet, bytes):
                    formatted_packet = {
                        "seq_num": dest_ipcp.flows[flow_id].recv_base,
                        "is_ack": False,
                        "data": packet
                    }
                    await dest_ipcp.receive_data(formatted_packet, flow_id)
                else:
                    await dest_ipcp.receive_data(packet, flow_id)
            else:
                # Silently drop packet instead of printing error (this is expected in network conditions)
                pass
        except Exception as e:
            # Log the error but don't crash
            print(f"Error delivering packet: {str(e)}")


class RealisticNetwork:
    """Manages a realistic network with multiple DIFs and network conditions"""
    def __init__(self):
        self.difs = {}
        self.ipcps = {}
        self.applications = {}
        self.network_conditions = {}
        
    async def create_dif(self, name, layer=0, max_bandwidth=1000):
        """Create a DIF with the given parameters"""
        dif = DIF(name=name, layer=layer, max_bandwidth=max_bandwidth)
        self.difs[name] = dif
        return dif
        
    async def create_ipcp(self, ipcp_id, dif_name):
        """Create an IPCP and associate it with a DIF"""
        if dif_name not in self.difs:
            raise ValueError(f"DIF {dif_name} does not exist")
        
        ipcp = IPCP(ipcp_id=ipcp_id, dif=self.difs[dif_name])
        self.ipcps[ipcp_id] = ipcp
        return ipcp
        
    async def create_application(self, app_name, ipcp_id, port=None):
        """Create an application and bind it to an IPCP"""
        if ipcp_id not in self.ipcps:
            raise ValueError(f"IPCP {ipcp_id} does not exist")
            
        app = Application(name=app_name, ipcp=self.ipcps[ipcp_id])
        if port:
            await app.bind(port)
        self.applications[app_name] = app
        return app
    
    async def set_network_conditions(self, src_ipcp_id, dst_ipcp_id, conditions):
        """Set network conditions between two IPCPs"""
        if src_ipcp_id not in self.ipcps or dst_ipcp_id not in self.ipcps:
            raise ValueError("One or both IPCPs do not exist")
            
        # Store original send_data method
        src_ipcp = self.ipcps[src_ipcp_id]
        original_send_data = src_ipcp.send_data
        
        # Create network condition
        net_cond = NetworkConditions(**conditions)
        await net_cond.start()
        
        # Replace send_data with our interceptor
        async def intercepted_send_data(flow_id, data):
            if flow_id in src_ipcp.flows:
                flow = src_ipcp.flows[flow_id]
                dst_ipcp = flow.dest_ipcp
                
                if dst_ipcp == self.ipcps[dst_ipcp_id]:
                    await net_cond.process_packet(data, dst_ipcp, flow_id)
                    return True
                else:
                    # Use the original method for other flows
                    return await original_send_data(flow_id, data)
            else:
                print(f"Flow {flow_id} not found in source IPCP {src_ipcp_id}")
                return False
                
        src_ipcp.send_data = intercepted_send_data
        # Store for cleanup
        self.network_conditions[(src_ipcp_id, dst_ipcp_id)] = (src_ipcp, original_send_data, net_cond)
        return net_cond
        
    async def cleanup(self):
        """Clean up all resources"""
        # Restore original send_data methods
        for (src_id, dst_id), (src_ipcp, original_send_data, net_cond) in self.network_conditions.items():
            src_ipcp.send_data = original_send_data
            await net_cond.stop()
            
        # Clean up flows
        for ipcp in self.ipcps.values():
            for flow_id in list(ipcp.flows.keys()):
                try:
                    await ipcp.deallocate_flow(flow_id)
                except:
                    pass



# Define realistic network condition profiles
NETWORK_PROFILES = {
    "perfect": {
        "latency_ms": 0,
        "jitter_ms": 0, 
        "packet_loss_rate": 0,
        "bandwidth_mbps": None,
        "corruption_rate": 0,
        "reordering_rate": 0
    },
    "lan": {
        "latency_ms": 2,
        "jitter_ms": 1,
        "packet_loss_rate": 0.001,
        "bandwidth_mbps": 1000,
        "corruption_rate": 0.0001,
        "reordering_rate": 0.001
    },
    "wifi": {
        "latency_ms": 5,
        "jitter_ms": 3,
        "packet_loss_rate": 0.005,
        "bandwidth_mbps": 100,
        "corruption_rate": 0.001,
        "reordering_rate": 0.002
    },
    "congested": {
        "latency_ms": 100,
        "jitter_ms": 40,
        "packet_loss_rate": 0.05,
        "bandwidth_mbps": 10,
        "corruption_rate": 0.005,
        "reordering_rate": 0.01
    }
}
