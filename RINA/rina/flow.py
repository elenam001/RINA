import asyncio
from enum import Enum, auto
import time
from collections import deque
from .sequence import SequenceNumber

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
        self.window_size = 64
        self.timeout = 0.5
        self.sequence_gen = SequenceNumber()
        self.send_base = 0    
        self.next_seq_num = 0 
        self.recv_base = 0
        self.unacked_packets = {}
        self.out_of_order_buffer = {}
        self.window_lock = asyncio.Lock()
        self.ack_received = asyncio.Event()
        self.retransmission_task = None
        
    async def _commit_resources(self):
        """Commit resources in both source and destination DIFs"""
        if self.qos and self.qos.bandwidth:
            src_allocation = self.src_ipcp.dif.allocate_bandwidth(self.qos.bandwidth)
            dest_allocation = True
            if self.dest_ipcp.dif != self.src_ipcp.dif:
                dest_allocation = self.dest_ipcp.dif.allocate_bandwidth(self.qos.bandwidth)
            if not src_allocation or not dest_allocation:
                if src_allocation:
                    self.src_ipcp.dif.release_bandwidth(self.qos.bandwidth)
                if dest_allocation and self.dest_ipcp.dif != self.src_ipcp.dif:
                    self.dest_ipcp.dif.release_bandwidth(self.qos.bandwidth)
                return False
        if self.src_ipcp.lower_ipcp:
            self.lower_flow_id = await self.src_ipcp.lower_ipcp.allocate_flow(
                self.dest_ipcp.lower_ipcp,
                self.port,
                self.qos
            )
            if not self.lower_flow_id:
                if self.qos and self.qos.bandwidth:
                    self.src_ipcp.dif.release_bandwidth(self.qos.bandwidth)
                    if self.dest_ipcp.dif != self.src_ipcp.dif:
                        self.dest_ipcp.dif.release_bandwidth(self.qos.bandwidth)
                return False
        self.stats["start_time"] = time.time()
        self.retransmission_task = asyncio.create_task(self._retransmission_loop())
        
        return True
        
    async def _release_resources(self):
        """Release all allocated resources"""
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
                    for seq_num, (data, timestamp) in list(self.unacked_packets.items()):
                        if now - timestamp > self.timeout:
                            retransmit_packets.append((seq_num, data))
                for seq_num, data in retransmit_packets:
                    #print(qui)
                    await self._send_packet(data, seq_num, is_retransmission=True)
                    self.stats["retransmitted_packets"] += 1
                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            pass
    
    async def _send_packet(self, data, seq_num=None, is_retransmission=False, already_stored=False):
        """Internal method to send a packet with sequence number"""
        if seq_num is None:
            seq_num = self.sequence_gen.next()
        packet = {
            "seq_num": seq_num,
            "is_ack": False,
            "data": data
        }
        if not already_stored and not is_retransmission:
            async with self.window_lock:
                self.unacked_packets[seq_num] = (data, time.time())
        self.stats['sent_packets'] += 1
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
            await self.dest_ipcp.receive_data(packet, self.id)
    
    async def send_data(self, data):
        """Send data with flow control"""
        if self.state_machine.state != FlowAllocationFSM.State.ACTIVE:
            raise ConnectionError("Flow not in active state")
        async with self.window_lock:
            while len(self.unacked_packets) >= self.window_size:
                self.window_lock.release()
                lock_reacquired = False
                try:
                    await asyncio.wait_for(self.ack_received.wait(), timeout=self.timeout)
                    self.ack_received.clear()
                except asyncio.TimeoutError:
                    print("Timeout waiting for ACKs, retrying...")
                finally:
                    await self.window_lock.acquire()
                    lock_reacquired = True
            seq_num = self.sequence_gen.next()
            self.unacked_packets[seq_num] = (data, time.time())
        await self._send_packet(data, seq_num, already_stored=True)
        return seq_num
    
    async def receive_data(self, packet):
        """Process received data or acknowledgment packets"""
        if not isinstance(packet, dict):
            print("Malformed packet")
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
            print("Received ACK with no sequence number")
            return
        self.stats['ack_packets'] += 1
        async with self.window_lock:
            before_count = len(self.unacked_packets)
            if ack_seq in self.unacked_packets:
                del self.unacked_packets[ack_seq]
            after_count = len(self.unacked_packets)
        self.ack_received.set()
    
    async def _handle_data_packet(self, packet):
        """Process a data packet and send acknowledgment"""
        seq_num = packet.get("seq_num")
        data = packet.get("data")
        
        if seq_num is None or data is None:
            print("Data packet with missing fields")
            return
        if seq_num == self.recv_base:
            await self.dest_ipcp.deliver_to_application(self.port, data)
            self.recv_base = (self.recv_base + 1) % (2**16)
            while self.recv_base in self.out_of_order_buffer:
                buffered_data = self.out_of_order_buffer.pop(self.recv_base)
                await self.dest_ipcp.deliver_to_application(self.port, buffered_data)
                self.recv_base = (self.recv_base + 1) % (2**16)
        elif self.sequence_gen.is_in_window(seq_num, self.recv_base, self.window_size):
            self.out_of_order_buffer[seq_num] = data
        ack_packet = {
            "is_ack": True,
            "ack_seq_num": (self.recv_base - 1) % (2**16)
        }
        await self.send_ack(ack_packet)
    
    async def send_ack(self, ack_packet):
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
            await self.src_ipcp.receive_data(ack_packet, self.id)

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
            if self.timeout_task and not self.timeout_task.done():
                self.timeout_task.cancel()
            await self.flow._release_resources()
            self.state = self.State.CLOSED