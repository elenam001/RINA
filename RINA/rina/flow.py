# Fixed flow.py - focusing on state machine and resource management

import asyncio
from enum import Enum, auto
import time

class Flow:
    def __init__(self, flow_id, src_ipcp, dest_ipcp, port, qos=None):
        self.id = flow_id
        self.src_ipcp = src_ipcp
        self.dest_ipcp = dest_ipcp
        self.port = port
        self.qos = qos
        self.state_machine = None
        self.lower_flow_id = None
        self.retry_count = 0
        self.stats = {
            'sent_packets': 0,
            'received_packets': 0,
            'start_time': None,
            'end_time': None
        }
        
    async def _commit_resources(self):
        """Commit resources in both source and destination DIFs"""
        if self.qos and self.qos.bandwidth:
            # Ensure both DIFs have sufficient bandwidth
            src_allocation = self.src_ipcp.dif.allocate_bandwidth(self.qos.bandwidth)
            
            # If source and destination are in different DIFs, allocate in both
            dest_allocation = True
            if self.dest_ipcp.dif != self.src_ipcp.dif:
                dest_allocation = self.dest_ipcp.dif.allocate_bandwidth(self.qos.bandwidth)
                
            # If either allocation fails, roll back and return failure
            if not src_allocation or not dest_allocation:
                if src_allocation:
                    self.src_ipcp.dif.release_bandwidth(self.qos.bandwidth)
                if dest_allocation and self.dest_ipcp.dif != self.src_ipcp.dif:
                    self.dest_ipcp.dif.release_bandwidth(self.qos.bandwidth)
                return False
            
        # Handle lower layer flow allocation if needed
        if self.src_ipcp.lower_ipcp:
            self.lower_flow_id = await self.src_ipcp.lower_ipcp.allocate_flow(
                self.dest_ipcp.lower_ipcp,
                self.port,
                self.qos
            )
            if not self.lower_flow_id:
                # Roll back resource allocations
                if self.qos and self.qos.bandwidth:
                    self.src_ipcp.dif.release_bandwidth(self.qos.bandwidth)
                    if self.dest_ipcp.dif != self.src_ipcp.dif:
                        self.dest_ipcp.dif.release_bandwidth(self.qos.bandwidth)
                return False
            
        # Successfully committed resources
        self.stats["start_time"] = time.time()
        return True
        
    async def _release_resources(self):
        """Release all allocated resources"""
        if self.qos and self.qos.bandwidth:
            self.src_ipcp.dif.release_bandwidth(self.qos.bandwidth)
            if self.dest_ipcp.dif != self.src_ipcp.dif:
                self.dest_ipcp.dif.release_bandwidth(self.qos.bandwidth)
            
        if self.lower_flow_id:
            await self.src_ipcp.lower_ipcp.deallocate_flow(self.lower_flow_id)
            
        self.stats["end_time"] = time.time()
        self.state_machine.state = FlowAllocationFSM.State.CLOSED
        

class FlowAllocationFSM:
    class State(Enum):
        INITIALIZED = auto()
        REQUEST_SENT = auto()
        ALLOCATED = auto()
        ACTIVE = auto()
        DEALLOCATING = auto()
        CLOSED = auto()

    def __init__(self, flow):
        self.flow = flow
        self.state = self.State.INITIALIZED
        self.timeout_task = None

    async def handle_event(self, event):
        if self.state == self.State.INITIALIZED and event == "start_allocation":
            await self.start_allocation()
        elif self.state == self.State.REQUEST_SENT and event == "allocation_confirmed":
            await self.confirm_allocation()
        elif self.state == self.State.REQUEST_SENT and event == "allocation_timeout":
            await self.handle_timeout()
        elif event == "deallocate":
            await self.deallocate()

    async def start_allocation(self):
        self.state = self.State.REQUEST_SENT
        self.timeout_task = asyncio.create_task(self.allocation_timeout())
        # Simplified for testing - just approve
        await self.confirm_allocation()

    async def allocation_timeout(self, timeout=5.0):
        await asyncio.sleep(timeout)
        if self.state == self.State.REQUEST_SENT:
            await self.handle_event("allocation_timeout")

    async def confirm_allocation(self):
        if self.timeout_task and not self.timeout_task.done():
            self.timeout_task.cancel()
        self.state = self.State.ACTIVE

    async def handle_timeout(self):
        if self.flow.retry_count < 3:
            self.flow.retry_count += 1
            await self.start_allocation()
        else:
            await self.deallocate()

    async def deallocate(self):
        if self.state not in [self.State.CLOSED, self.State.DEALLOCATING]:
            self.state = self.State.DEALLOCATING
            # Cancel timeout task if it exists
            if self.timeout_task and not self.timeout_task.done():
                self.timeout_task.cancel()
            await self.flow._release_resources()
            self.state = self.State.CLOSED