import asyncio
from enum import Enum, auto
import time
from collections import deque
from .sequence import SequenceNumber  # Import the new SequenceNumber class

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
            'ack_packets': 0,
            'retransmitted_packets': 0,
            'start_time': None,
            'end_time': None
        }
        
        # Flow control parameters
        self.window_size = 16  # Default window size
        self.timeout = 2.0     # Default timeout in seconds
        
        # Flow control state
        self.sequence_gen = SequenceNumber()
        self.send_base = 0     # Base of the sending window
        self.next_seq_num = 0  # Next sequence number to use
        self.recv_base = 0     # Base of the receiving window
        
        # Buffers for unacknowledged and out-of-order packets
        self.unacked_packets = {}  # seq_num -> (data, timestamp)
        self.out_of_order_buffer = {}  # seq_num -> data
        
        # Flow control locks and event
        self.window_lock = asyncio.Lock()
        self.ack_received = asyncio.Event()
        
        # Retransmission task
        self.retransmission_task = None
        
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
        
        # Start retransmission task
        self.retransmission_task = asyncio.create_task(self._retransmission_loop())
        
        return True
        
    async def _release_resources(self):
        """Release all allocated resources"""
        # Cancel retransmission task
        if self.retransmission_task and not self.retransmission_task.done():
            self.retransmission_task.cancel()
            try:
                await self.retransmission_task
            except asyncio.CancelledError:
                pass
            
        if self.qos and self.qos.bandwidth:
            self.src_ipcp.dif.release_bandwidth(self.qos.bandwidth)
            if self.dest_ipcp.dif != self.src_ipcp.dif:
                self.dest_ipcp.dif.release_bandwidth(self.qos.bandwidth)
            
        if self.lower_flow_id:
            await self.src_ipcp.lower_ipcp.deallocate_flow(self.lower_flow_id)
            
        self.stats["end_time"] = time.time()
        self.state_machine.state = FlowAllocationFSM.State.CLOSED
    
    async def _retransmission_loop(self):
        """Background task to handle retransmissions of unacknowledged packets"""
        try:
            while True:
                now = time.time()
                retransmit_packets = []
                
                async with self.window_lock:
                    # Find packets that have timed out
                    for seq_num, (data, timestamp) in list(self.unacked_packets.items()):
                        if now - timestamp > self.timeout:
                            retransmit_packets.append((seq_num, data))
                
                # Retransmit any timed-out packets
                for seq_num, data in retransmit_packets:
                    print(f"Retransmitting packet {seq_num} for flow {self.id}")
                    await self._send_packet(data, seq_num, is_retransmission=True)
                    self.stats["retransmitted_packets"] += 1
                
                # Wait for a bit before checking again
                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            # Task was cancelled, clean up and exit
            pass
    
    async def _send_packet(self, data, seq_num=None, is_retransmission=False):
        """Internal method to send a packet with sequence number"""
        if seq_num is None:
            seq_num = self.sequence_gen.next()
        
        # Prepare packet with sequence number
        packet = {
            "seq_num": seq_num,
            "is_ack": False,
            "data": data
        }
        
        # If not a retransmission, store in unacked packets
        if not is_retransmission:
            async with self.window_lock:
                self.unacked_packets[seq_num] = (data, time.time())
        
        # Update stats
        self.stats['sent_packets'] += 1
        
        # Handle encapsulation and sending through IPCP
        if self.lower_flow_id and self.src_ipcp.lower_ipcp:
            encapsulated = {
                "header": {
                    "flow_id": self.id,
                    "qos": self.qos.to_dict() if self.qos else None
                },
                "payload": packet
            }
            await self.src_ipcp.lower_ipcp.send_data(self.lower_flow_id, encapsulated)
        else:
            # Direct delivery
            await self.dest_ipcp.receive_data(packet, self.id)
    
    async def send_data(self, data):
        """Send data with flow control"""
        if self.state_machine.state != FlowAllocationFSM.State.ACTIVE:
            raise ConnectionError("Flow not in active state")
        
        print(f"Flow {self.id}: Attempting to send data of size {len(data)}")
        
        async with self.window_lock:
            print(f"Flow {self.id}: Acquired window lock, unacked: {len(self.unacked_packets)}/{self.window_size}")
            
            # Wait if window is full
            while len(self.unacked_packets) >= self.window_size:
                print(f"Flow {self.id}: Window full, waiting for ACKs...")
                # Release lock while waiting for acks
                self.window_lock.release()
                try:
                    # Wait for acknowledgments to make space in the window
                    await asyncio.wait_for(self.ack_received.wait(), timeout=self.timeout)
                    self.ack_received.clear()
                except asyncio.TimeoutError:
                    print(f"Flow {self.id}: Timeout waiting for ACKs, retrying...")
                    # Timeout occurred, continue anyway (will check window again)
                # Reacquire lock
                await self.window_lock.acquire()
                print(f"Flow {self.id}: Reacquired lock after waiting, unacked: {len(self.unacked_packets)}/{self.window_size}")
            
            # Send the packet
            seq_num = self.sequence_gen.next()
            print(f"Flow {self.id}: Sending packet with seq_num {seq_num}")
            await self._send_packet(data, seq_num)
            print(f"Flow {self.id}: Sent packet {seq_num}, window now: {len(self.unacked_packets)}/{self.window_size}")
            return seq_num
    
    async def receive_data(self, packet):
        """Process received data or acknowledgment packets"""
        if not isinstance(packet, dict):
            print(f"Warning: Received malformed packet on flow {self.id}")
            return
        
        if packet.get("is_ack", False):
            # This is an ACK packet
            await self._handle_ack(packet)
        else:
            # This is a data packet
            await self._handle_data_packet(packet)
    
    async def _handle_ack(self, ack_packet):
        """Process an acknowledgment packet"""
        ack_seq = ack_packet.get("ack_seq_num")
        if ack_seq is None:
            print(f"Flow {self.id}: Received ACK with no sequence number")
            return
        
        print(f"Flow {self.id}: Received ACK for seq {ack_seq}")
        self.stats['ack_packets'] += 1
        
        # Remove acknowledged packets from unacked_packets
        async with self.window_lock:
            before_count = len(self.unacked_packets)
            # Find all sequence numbers that are less than or equal to the ACK sequence number
            to_remove = [seq for seq in self.unacked_packets.keys() 
                        if (ack_seq >= seq) or (ack_seq < seq and ack_seq < self.send_base)]
            
            # Remove all acknowledged packets
            for seq in to_remove:
                del self.unacked_packets[seq]
            
            after_count = len(self.unacked_packets)
            print(f"Flow {self.id}: Removed {before_count - after_count} packets from unacked")
            
            # Update send_base if necessary
            if not self.unacked_packets:
                # If all packets are acknowledged, update send_base to next_seq_num
                self.send_base = self.next_seq_num
            else:
                # Otherwise, update to the smallest unacknowledged sequence number
                self.send_base = min(self.unacked_packets.keys())
        
        # Signal that space may be available in the window
        print(f"Flow {self.id}: Setting ack_received event")
        self.ack_received.set()
    
    async def _handle_data_packet(self, packet):
        """Process a data packet and send acknowledgment"""
        seq_num = packet.get("seq_num")
        data = packet.get("data")
        
        if seq_num is None or data is None:
            print(f"Warning: Received data packet with missing fields on flow {self.id}")
            return
        
        # Check if this is the expected sequence number
        if seq_num == self.recv_base:
            # Deliver the data to the application
            await self.dest_ipcp.deliver_to_application(self.port, data)
            
            # Update receive base
            self.recv_base = (self.recv_base + 1) % (2**16)
            
            # Check if we have buffered packets that can now be delivered
            while self.recv_base in self.out_of_order_buffer:
                buffered_data = self.out_of_order_buffer.pop(self.recv_base)
                await self.dest_ipcp.deliver_to_application(self.port, buffered_data)
                self.recv_base = (self.recv_base + 1) % (2**16)
        
        elif self.sequence_gen.is_in_window(seq_num, self.recv_base, self.window_size):
            # Packet is within receive window but not the next expected one
            # Buffer it for later delivery
            self.out_of_order_buffer[seq_num] = data
        
        # Otherwise, it's outside our window and we ignore it
        
        # Send ACK for the highest in-order packet received
        ack_packet = {
            "is_ack": True,
            "ack_seq_num": (self.recv_base - 1) % (2**16)  # ACK the last in-order packet
        }
        
        # Send the ACK packet back
        await self._send_ack(ack_packet)
    
    async def _send_ack(self, ack_packet):
        """Send an acknowledgment packet"""
        if self.lower_flow_id and self.src_ipcp.lower_ipcp:
            encapsulated = {
                "header": {
                    "flow_id": self.id,
                    "qos": self.qos.to_dict() if self.qos else None
                },
                "payload": ack_packet
            }
            await self.dest_ipcp.lower_ipcp.send_data(self.lower_flow_id, encapsulated)
        else:
            # Direct delivery back to source
            await self.src_ipcp.receive_data(ack_packet, self.id)

# Update to FlowAllocationFSM remains mostly the same
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