import asyncio
import logging
import uuid
from rina.flow import Flow, FlowAllocationFSM

class IPCP:
    def __init__(self, ipcp_id, dif, lower_ipcp=None):
        self.id = ipcp_id
        self.dif = dif
        self.lower_ipcp = lower_ipcp
        self.higher_ipcp = None
        self.neighbors = set()
        self.port_map = {}
        self.flows = {}
        self.pending_requests = {}
        
        if self.lower_ipcp:
            self.lower_ipcp.higher_ipcp = self
        
    async def enroll(self, neighbor_ipcp):
        """Enroll with a neighboring IPCP (simplified)."""
        self.neighbors.add(neighbor_ipcp)
        neighbor_ipcp.neighbors.add(self)
        print(f"IPCP {self.id} enrolled with {neighbor_ipcp.id}")

    async def allocate_flow(self, dest_ipcp, port, qos=None):
        """Allocate a flow between this IPCP and a destination IPCP."""
        try:
            flow_id = str(uuid.uuid4())
            flow = Flow(flow_id, self, dest_ipcp, port, qos)
            flow.state_machine = FlowAllocationFSM(flow)
            self.flows[flow_id] = flow
            dest_ipcp.flows[flow_id] = flow
            validation_result = await self._validate_flow_request(flow)
            if not validation_result:
                print(f"Flow request validation failed for flow {flow_id}")
                del self.flows[flow_id]
                if flow_id in dest_ipcp.flows:
                    del dest_ipcp.flows[flow_id]
                return None
            allocation_result = await self._handle_flow_request(flow)
            if not allocation_result:
                print(f"Flow allocation request rejected for flow {flow_id}")
                del self.flows[flow_id]
                if flow_id in dest_ipcp.flows:
                    del dest_ipcp.flows[flow_id]
                return None
            await flow.state_machine.handle_event("start_allocation")
            await flow._commit_resources()
            return flow_id
        except Exception as e:
            print(f"Flow allocation failed with exception: {str(e)}")
            return None
    
    async def deallocate_flow(self, flow_id):
        """Deallocate a flow and release its resources."""
        if flow_id in self.flows:
            flow = self.flows[flow_id]
            await flow.state_machine.handle_event("deallocate")
            del self.flows[flow_id]
            if flow_id in flow.dest_ipcp.flows:
                del flow.dest_ipcp.flows[flow_id]
                
            return True
        return False
    
    async def _validate_flow_request(self, flow):
        """Validate flow request parameters."""
        if flow.port in self.port_map and not self.port_map[flow.port].supports_multiple:
            pass
        if flow.qos and flow.qos.bandwidth is not None:
            available = self.dif.max_bandwidth - self.dif.allocated_bandwidth
            if flow.qos.bandwidth > available:
                print(f"Insufficient bandwidth: requested={flow.qos.bandwidth}, available={available}")
                return False
        return True
    
    async def _handle_flow_request(self, flow):
        """Process an incoming flow allocation request."""
        return True
    
    async def _send_flow_request(self, flow):
        """Send a flow allocation request to the destination IPCP."""
        try:
            return True
        except asyncio.TimeoutError:
            return False
            
    async def send_data(self, flow_id, data):
        """Send data through an allocated flow with flow control."""
        if flow_id not in self.flows:
            raise ValueError(f"Flow {flow_id} not found")
        flow = self.flows[flow_id]
        if flow.state_machine.state != FlowAllocationFSM.State.ACTIVE:
            raise ConnectionError("Flow not in active state")
        await flow.send_data(data)
            
    async def receive_data(self, data, flow_id):
        """Handle incoming data."""
        if flow_id in self.flows:
            flow = self.flows[flow_id]
            if isinstance(data, dict) and 'header' in data:
                if self.higher_ipcp:
                    await self.higher_ipcp.receive_data(
                        data['payload'], 
                        data['header']['flow_id']
                    )
                    return
                data = data['payload']
            await flow.receive_data(data)
        else:
            print(f"IPCP {self.id}: No flow found for ID {flow_id}")
    
    async def deliver_to_application(self, port, data):
        """Deliver data to the application at the specified port."""
        if port in self.port_map:
            flow = None
            for f in self.flows.values():
                f.stats['received_packets'] += 1
                flow = f
                break
            try:
                await asyncio.wait_for(self.port_map[port].on_data(data), timeout=0.1)
            except asyncio.TimeoutError:
                logging.debug(f"IPCP {self.id}: Timeout delivering to application on port {port}")