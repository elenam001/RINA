# hybrid_network.py
import asyncio
import socket
import time
import logging
from collections import deque
from rina.dif import DIF
from rina.ipcp import IPCP
from rina.application import Application
from rina.qos import QoS
from rina.flow import Flow

class TCPIPAdapter:
    """Adapter to connect TCP/IP to RINA network"""
    def __init__(self, host='127.0.0.1', port=8000):
        self.host = host
        self.port = port
        self.server = None
        self.connections = {}
        self.rina_ipcp = None
        self.packet_buffer = deque(maxlen=1000)
        self.stats = {
            'sent_packets': 0,
            'received_packets': 0,
            'bytes_sent': 0,
            'bytes_received': 0
        }
        
    async def start_server(self):
        """Start TCP server to accept connections"""
        self.server = await asyncio.start_server(
            self.handle_connection, self.host, self.port
        )
        logging.info(f"TCP/IP Adapter listening on {self.host}:{self.port}")
        
        # Start serving in a background task without awaiting it
        asyncio.create_task(self._serve_forever())

    async def _serve_forever(self):
        """Background task to keep the server running"""
        if self.server:
            async with self.server:
                await self.server.serve_forever()
        
    async def handle_connection(self, reader, writer):
        """Handle incoming TCP connection"""
        addr = writer.get_extra_info('peername')
        connection_id = f"{addr[0]}:{addr[1]}"
        self.connections[connection_id] = (reader, writer)
        logging.info(f"TCP Connection from {connection_id}")
        
        if self.rina_ipcp:
            # Allocate RINA flow and bridge
            try:
                flow_id = await self.allocate_rina_flow(connection_id)
                if flow_id:
                    await self.tcp_to_rina_bridge(connection_id, flow_id, reader, writer)
                else:
                    raise Exception("Failed to allocate RINA flow")
            except Exception as e:
                logging.error(f"Error bridging TCP to RINA: {str(e)}")
                writer.close()
                await writer.wait_closed()
            finally:
                if connection_id in self.connections:
                    del self.connections[connection_id]
        else:
            try:
                # Add timeout to prevent hanging on read
                while True:
                    try:
                        data = await asyncio.wait_for(reader.read(4096), timeout=2.0)
                        if not data:
                            break
                        self.stats['received_packets'] += 1
                        self.stats['bytes_received'] += len(data)
                        # Echo it back for simple testing
                        writer.write(data)
                        await writer.drain()
                        self.stats['sent_packets'] += 1
                        self.stats['bytes_sent'] += len(data)
                    except asyncio.TimeoutError:
                        logging.warning(f"Read timeout for {connection_id}")
                        break
            except Exception as e:
                logging.error(f"TCP connection error: {str(e)}")
            finally:
                try:
                    writer.close()
                    await asyncio.wait_for(writer.wait_closed(), timeout=1.0)
                except Exception as e:
                    logging.error(f"Error closing connection: {str(e)}")
                if connection_id in self.connections:
                    del self.connections[connection_id]
    
    async def allocate_rina_flow(self, connection_id, qos=None):
        """Allocate a flow in the RINA network"""
        if not self.rina_ipcp:
            return None
        
        # Find a destination IPCP in the RINA network
        dest_ipcp = next(iter(self.rina_ipcp.neighbors), None)
        if not dest_ipcp:
            logging.error("No destination IPCP available in RINA network")
            return None
        
        # Allocate flow to the destination IPCP
        try:
            flow_id = await self.rina_ipcp.allocate_flow(dest_ipcp, port=5000, qos=qos)
            if flow_id:
                logging.info(f"Allocated RINA flow {flow_id} for TCP connection {connection_id}")
                return flow_id
            else:
                logging.error(f"Failed to allocate RINA flow for TCP connection {connection_id}")
                return None
        except Exception as e:
            logging.error(f"Error allocating RINA flow: {str(e)}")
            return None
    
    async def tcp_to_rina_bridge(self, connection_id, flow_id, reader, writer):
        """Bridge data between TCP and RINA networks"""
        # Start two tasks: TCP → RINA and RINA → TCP
        tcp_to_rina = asyncio.create_task(self._forward_tcp_to_rina(connection_id, flow_id, reader))
        rina_to_tcp = asyncio.create_task(self._forward_rina_to_tcp(connection_id, flow_id, writer))
        
        # Wait for either task to complete (connection closed or error)
        done, pending = await asyncio.wait(
            [tcp_to_rina, rina_to_tcp],
            return_when=asyncio.FIRST_COMPLETED
        )
        
        # Cancel the other task
        for task in pending:
            task.cancel()
        
        # Wait for cancellation to complete
        try:
            await asyncio.gather(*pending, return_exceptions=True)
        except asyncio.CancelledError:
            pass
    
    async def _forward_tcp_to_rina(self, connection_id, flow_id, reader):
        """Forward data from TCP to RINA"""
        try:
            while True:
                data = await reader.read(4096)
                if not data:
                    break
                self.stats['received_packets'] += 1
                self.stats['bytes_received'] += len(data)
                
                # Forward to RINA network
                await self.rina_ipcp.send_data(flow_id, data)
                logging.debug(f"TCP→RINA: {len(data)} bytes from {connection_id} to flow {flow_id}")
        except Exception as e:
            logging.error(f"TCP→RINA forwarding error: {str(e)}")
    
    async def _forward_rina_to_tcp(self, connection_id, flow_id, writer):
        """Forward data from RINA to TCP"""
        flow = self.rina_ipcp.flows.get(flow_id)
        if not flow:
            logging.error(f"No flow object found for ID {flow_id}")
            return
        
        # Register a callback to be notified when data arrives on this flow
        flow.tcp_adapter_queue = asyncio.Queue()
        
        # Original receive_data method to store for restoration
        original_receive_data = flow.receive_data
        
        # Override receive_data to capture data for TCP
        async def intercept_receive_data(packet):
            await original_receive_data(packet)
            if not isinstance(packet, dict) or not packet.get("is_ack", False):
                if isinstance(packet, dict) and "data" in packet:
                    data = packet["data"]
                else:
                    data = packet
                await flow.tcp_adapter_queue.put(data)
        
        flow.receive_data = intercept_receive_data
        
        try:
            while not writer.is_closing():
                try:
                    data = await asyncio.wait_for(flow.tcp_adapter_queue.get(), timeout=1.0)
                    if not data:
                        continue
                    
                    writer.write(data)
                    await writer.drain()
                    self.stats['sent_packets'] += 1
                    self.stats['bytes_sent'] += len(data)
                    logging.debug(f"RINA→TCP: {len(data)} bytes from flow {flow_id} to {connection_id}")
                except asyncio.TimeoutError:
                    # Just check if the connection is still alive
                    if writer.is_closing():
                        break
                except Exception as e:
                    logging.error(f"RINA→TCP forwarding error: {str(e)}")
                    break
        finally:
            # Restore original receive_data method
            flow.receive_data = original_receive_data
            if hasattr(flow, 'tcp_adapter_queue'):
                delattr(flow, 'tcp_adapter_queue')
            
            if not writer.is_closing():
                writer.close()
                await writer.wait_closed()
    
    async def connect_to_rina(self, rina_ipcp):
        """Connect this adapter to a RINA IPCP"""
        self.rina_ipcp = rina_ipcp
        logging.info(f"TCP/IP Adapter connected to RINA IPCP {rina_ipcp.id}")
    
    async def disconnect_from_rina(self):
        """Disconnect from RINA network"""
        self.rina_ipcp = None
        logging.info("TCP/IP Adapter disconnected from RINA network")
    
    async def close(self):
        """Stop the TCP server and close all connections"""
        if self.server:
            self.server.close()
            try:
                await asyncio.wait_for(self.server.wait_closed(), timeout=2.0)
            except asyncio.TimeoutError:
                logging.warning("Timeout waiting for server to close")
        
        for conn_id, (reader, writer) in list(self.connections.items()):
            try:
                writer.close()
                await asyncio.wait_for(writer.wait_closed(), timeout=1.0)
            except Exception as e:
                logging.error(f"Error closing connection {conn_id}: {str(e)}")
        self.connections.clear()
        
        logging.info("TCP/IP Adapter closed")

class RINATCPApplication(Application):
    """RINA Application that can communicate with TCP/IP"""
    def __init__(self, name, ipcp, tcp_adapter=None):
        super().__init__(name, ipcp)
        self.tcp_adapter = tcp_adapter
        self.tcp_connections = {}
    
    async def connect_to_tcp(self, host, port):
        """Establish a TCP connection from RINA"""
        try:
            reader, writer = await asyncio.open_connection(host, port)
            conn_id = f"{host}:{port}"
            self.tcp_connections[conn_id] = (reader, writer)
            logging.info(f"RINA app {self.name} connected to TCP {conn_id}")
            return conn_id
        except Exception as e:
            logging.error(f"Failed to connect to TCP {host}:{port}: {str(e)}")
            return None
    
    async def on_data(self, data):
        """Override to handle data from RINA that might go to TCP"""
        await super().on_data(data)
        
        # If we're connected to TCP endpoints, we could forward the data
        for conn_id, (reader, writer) in self.tcp_connections.items():
            try:
                writer.write(data)
                await writer.drain()
                logging.debug(f"RINA App {self.name} forwarded {len(data)} bytes to TCP {conn_id}")
            except Exception as e:
                logging.error(f"Error forwarding to TCP {conn_id}: {str(e)}")
    
    async def send_to_tcp(self, conn_id, data):
        """Send data to a specific TCP connection"""
        if conn_id in self.tcp_connections:
            reader, writer = self.tcp_connections[conn_id]
            try:
                writer.write(data)
                await writer.drain()
                logging.debug(f"Sent {len(data)} bytes to TCP {conn_id}")
                return True
            except Exception as e:
                logging.error(f"Error sending to TCP {conn_id}: {str(e)}")
                return False
        else:
            logging.warning(f"No TCP connection {conn_id}")
            return False
    
    async def disconnect_tcp(self, conn_id):
        """Close a TCP connection"""
        if conn_id in self.tcp_connections:
            reader, writer = self.tcp_connections[conn_id]
            writer.close()
            await writer.wait_closed()
            del self.tcp_connections[conn_id]
            logging.info(f"Closed TCP connection {conn_id}")
            return True
        return False
    
    async def close_all_tcp(self):
        """Close all TCP connections"""
        for conn_id in list(self.tcp_connections.keys()):
            await self.disconnect_tcp(conn_id)

class HybridNetwork:
    """Manager for the hybrid TCP/IP and RINA network"""
    def __init__(self):
        self.rina_difs = {}
        self.tcp_adapters = {}
        self.rina_apps = {}
        self.tcp_apps = {}
    
    async def create_rina_dif(self, name, layer, max_bandwidth=1000):
        """Create a RINA DIF"""
        dif = DIF(name=name, layer=layer, max_bandwidth=max_bandwidth)
        self.rina_difs[name] = dif
        return dif
    
    async def create_rina_ipcp(self, ipcp_id, dif_name):
        """Create a RINA IPCP in a specified DIF"""
        if dif_name not in self.rina_difs:
            logging.error(f"DIF {dif_name} not found")
            return None
        
        dif = self.rina_difs[dif_name]
        ipcp = IPCP(ipcp_id=ipcp_id, dif=dif)
        dif.add_ipcp(ipcp)
        return ipcp
    
    async def create_tcp_adapter(self, name, host='127.0.0.1', port=8000):
        """Create a TCP/IP adapter"""
        adapter = TCPIPAdapter(host=host, port=port)
        self.tcp_adapters[name] = adapter
        return adapter
    
    async def connect_adapter_to_rina(self, adapter_name, ipcp_id, dif_name):
        """Connect a TCP/IP adapter to a RINA IPCP"""
        if adapter_name not in self.tcp_adapters:
            logging.error(f"TCP Adapter {adapter_name} not found")
            return False
        
        if dif_name not in self.rina_difs:
            logging.error(f"DIF {dif_name} not found")
            return False
        
        dif = self.rina_difs[dif_name]
        ipcp = dif.get_ipcp(ipcp_id)
        if not ipcp:
            logging.error(f"IPCP {ipcp_id} not found in DIF {dif_name}")
            return False
        
        adapter = self.tcp_adapters[adapter_name]
        await adapter.connect_to_rina(ipcp)
        return True
    
    async def start_tcp_adapters(self):
        """Start all TCP adapters"""
        for name, adapter in self.tcp_adapters.items():
            await adapter.start_server()
            logging.info(f"Started TCP adapter: {name}")  # Add logging
    
    async def create_hybrid_application(self, name, ipcp, adapter_name=None):
        """Create an application that can work with both RINA and TCP/IP"""
        tcp_adapter = None
        if adapter_name and adapter_name in self.tcp_adapters:
            tcp_adapter = self.tcp_adapters[adapter_name]
        
        app = RINATCPApplication(name=name, ipcp=ipcp, tcp_adapter=tcp_adapter)
        self.rina_apps[name] = app
        return app 
    
    async def shutdown(self):
        """Shutdown the entire hybrid network"""
        logging.info("Starting hybrid network shutdown...")
        
        # Close all RINA apps TCP connections
        for name, app in self.rina_apps.items():
            logging.info(f"Closing TCP connections for RINA app: {name}")
            await app.close_all_tcp()
        
        # Close all TCP adapters
        for name, adapter in self.tcp_adapters.items():
            logging.info(f"Closing TCP adapter: {name}")
            await adapter.close()
        
        # Clean up RINA flows
        for name, dif in self.rina_difs.items():
            logging.info(f"Cleaning up DIF: {name}")
            for ipcp in dif.get_ipcps():
                flow_ids = list(ipcp.flows.keys())
                for flow_id in flow_ids:
                    logging.info(f"Deallocating flow: {flow_id}")
                    try:
                        await asyncio.wait_for(ipcp.deallocate_flow(flow_id), timeout=2.0)
                    except Exception as e:
                        logging.error(f"Error deallocating flow {flow_id}: {str(e)}")
        
        logging.info("Hybrid network shutdown complete")