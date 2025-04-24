from collections import deque
import pytest
import pytest_asyncio
import asyncio
import time
import statistics
import json
import random
import socket
from contextlib import AsyncExitStack
import logging
import network_conditions

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Global metrics dictionary to store test results
metrics = {}

class TCPNetworkConditions(network_conditions.NetworkConditions):
    """Network conditions simulator for TCP connections"""
    
    async def process_packet(self, data, writer, flow_id=None):
        """Process a TCP packet with network conditions applied"""
        await self.queue.put((data, writer, None))
    
    async def _delayed_delivery(self, delay, packet, writer, flow_id):
        """Deliver a TCP packet after the specified delay"""
        await asyncio.sleep(delay)
        try:
            if writer and not writer.is_closing():
                writer.write(packet)
                await writer.drain()
        except Exception as e:
            print(f"Error delivering TCP packet: {str(e)}")

class TCPServer:
    """Simple TCP echo server for testing"""
    def __init__(self, host="127.0.0.1", port=0):
        self.host = host
        self.port = port
        self.server = None
        self.clients = set()
        
    async def start(self):
        self.server = await asyncio.start_server(
            self.handle_client, self.host, self.port
        )
        addr = self.server.sockets[0].getsockname()
        self.port = addr[1]  # Get actual port in case it was 0
        logging.info(f"TCP server started on {self.host}:{self.port}")
        
    async def handle_client(self, reader, writer):
        addr = writer.get_extra_info('peername')
        self.clients.add(writer)
        logging.info(f"Client connected: {addr}")
        
        try:
            while True:
                data = await reader.read(65536)  # Large buffer to handle various packet sizes
                if not data:
                    break
                writer.write(data)  # Echo back the data
                await writer.drain()
        except Exception as e:
            logging.error(f"Error handling client {addr}: {str(e)}")
        finally:
            if writer in self.clients:
                self.clients.remove(writer)
            writer.close()
            await writer.wait_closed()
            logging.info(f"Client disconnected: {addr}")
    
    async def stop(self):
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            
            # Close all client connections
            for writer in self.clients:
                writer.close()
                await writer.wait_closed()
            self.clients.clear()
            logging.info("TCP server stopped")


class TCPNetwork:
    """Manages TCP servers and clients with simulated network conditions"""
    def __init__(self):
        self.servers = {}
        self.network_conditions = {}
        
    async def create_tcp_server(self, name, host="127.0.0.1", port=0):
        """Create a TCP server with the given parameters"""
        server = TCPServer(host=host, port=port)
        await server.start()
        self.servers[name] = server
        return server
    
    async def set_network_conditions(self, server_name, conditions):
        """Apply network conditions to a TCP server"""
        if server_name not in self.servers:
            raise ValueError(f"Server {server_name} does not exist")
        
        # Create a proxy server to apply network conditions
        original_server = self.servers[server_name]
        proxy_port = original_server.port + 1000  # Use a different port for the proxy
        
        # Create network conditions simulator
        net_cond = TCPNetworkConditions(**conditions)
        await net_cond.start()
        
        # Create a proxy server that will apply the network conditions
        class TCPProxy:
            def __init__(self, target_host, target_port, proxy_port, net_cond):
                self.target_host = target_host
                self.target_port = target_port
                self.proxy_port = proxy_port
                self.net_cond = net_cond
                self.server = None
                self.clients = set()
                
            async def start(self):
                self.server = await asyncio.start_server(
                    self.handle_client, "127.0.0.1", self.proxy_port
                )
                logging.info(f"TCP proxy started on 127.0.0.1:{self.proxy_port} -> {self.target_host}:{self.target_port}")
                
            async def handle_client(self, client_reader, client_writer):
                # Connect to target server
                try:
                    server_reader, server_writer = await asyncio.open_connection(
                        self.target_host, self.target_port
                    )
                except Exception as e:
                    logging.error(f"Failed to connect to target server: {str(e)}")
                    client_writer.close()
                    return
                
                # Bidirectional forwarding with network conditions
                self.clients.add((client_writer, server_writer))
                
                # Forward client -> server with network conditions
                async def forward_to_server():
                    try:
                        while True:
                            data = await client_reader.read(65536)
                            if not data:
                                break
                            
                            # Process packet through network conditions
                            await self.net_cond.process_packet(
                                data, 
                                server_writer,
                                None  # No flow_id for TCP
                            )
                    except Exception as e:
                        logging.error(f"Error forwarding to server: {str(e)}")
                    finally:
                        server_writer.close()
                
                # Forward server -> client with network conditions
                async def forward_to_client():
                    try:
                        while True:
                            data = await server_reader.read(65536)
                            if not data:
                                break
                            
                            # Direct forwarding from server to client
                            # (We only simulate conditions in one direction)
                            client_writer.write(data)
                            await client_writer.drain()
                    except Exception as e:
                        logging.error(f"Error forwarding to client: {str(e)}")
                    finally:
                        client_writer.close()
                
                # Start both forwarding tasks
                await asyncio.gather(
                    forward_to_server(),
                    forward_to_client(),
                    return_exceptions=True
                )
                
                # Clean up
                if (client_writer, server_writer) in self.clients:
                    self.clients.remove((client_writer, server_writer))
                
            async def stop(self):
                if self.server:
                    self.server.close()
                    await self.server.wait_closed()
                    
                    # Close all client connections
                    for client_writer, server_writer in self.clients:
                        client_writer.close()
                        server_writer.close()
                    self.clients.clear()
                    logging.info("TCP proxy stopped")
                    
                # Stop the network conditions
                await self.net_cond.stop()
        
        # Create and start the proxy
        proxy = TCPProxy(
            original_server.host,
            original_server.port,
            proxy_port,
            net_cond
        )
        await proxy.start()
        
        # Store the proxy in the network conditions dict
        self.network_conditions[server_name] = (proxy, net_cond)
        
        # Return the proxy port for clients to connect to
        return proxy_port
    
    async def shutdown(self):
        """Clean up all resources"""
        # Stop all servers
        for server in self.servers.values():
            await server.stop()
        
        # Stop all proxies and network conditions
        for proxy, net_cond in self.network_conditions.values():
            await proxy.stop()


@pytest_asyncio.fixture
async def tcp_network():
    """Create a clean TCP network for each test"""
    network = TCPNetwork()
    yield network
    await network.shutdown()


async def measure_tcp_metrics(tcp_port, packet_size, packet_count, 
                            inter_packet_delay=0.001):
    """Helper function to measure metrics for a TCP flow"""
    start_time = time.time()
    
    metrics = {
        "connection_setup_time_ms": 0,
        "packet_size": packet_size,
        "packet_count": packet_count,
        "latencies_ms": [],
        "rtts_ms": [],
        "jitter_ms": [],
        "sent": 0,
        "received": 0,
        "throughput_mbps": 0,
    }
    
    try:
        reader, writer = await asyncio.open_connection("127.0.0.1", tcp_port)
        connection_setup_time = time.time() - start_time
        metrics["connection_setup_time_ms"] = connection_setup_time * 1000
    except Exception as e:
        logging.error(f"Failed to connect to TCP server: {str(e)}")
        return metrics
    
    data = b"x" * packet_size
    last_latency = 0
    send_start_time = time.time()
    for i in range(packet_count):
        packet_send_time = time.time()
        writer.write(data)
        await writer.drain()
        metrics["sent"] += 1
        try:
            response = await asyncio.wait_for(reader.read(packet_size), timeout=5.0)
            if response:
                metrics["received"] += 1
                rtt = (time.time() - packet_send_time) * 1000  # ms
                metrics["rtts_ms"].append(rtt)
                latency = rtt / 2
                metrics["latencies_ms"].append(latency)
                if i > 0:
                    jitter = abs(latency - last_latency)
                    metrics["jitter_ms"].append(jitter)
                last_latency = latency
        except asyncio.TimeoutError:
            logging.warning(f"Timeout waiting for response to packet {i}")
        if inter_packet_delay > 0:
            await asyncio.sleep(inter_packet_delay)
    
    send_end_time = time.time()
    metrics["delivery_ratio"] = (metrics["received"] / metrics["sent"]) * 100 if metrics["sent"] > 0 else 0
    total_bits = metrics["sent"] * packet_size * 8
    duration = send_end_time - send_start_time
    metrics["throughput_mbps"] = total_bits / (duration * 1_000_000) if duration > 0 else 0
    if metrics["latencies_ms"]:
        metrics["avg_latency_ms"] = statistics.mean(metrics["latencies_ms"])
        metrics["min_latency_ms"] = min(metrics["latencies_ms"])
        metrics["max_latency_ms"] = max(metrics["latencies_ms"])
    
    if metrics["jitter_ms"]:
        metrics["avg_jitter_ms"] = statistics.mean(metrics["jitter_ms"])
        metrics["max_jitter_ms"] = max(metrics["jitter_ms"])
    
    if metrics["rtts_ms"]:
        metrics["avg_rtt_ms"] = statistics.mean(metrics["rtts_ms"])
        metrics["min_rtt_ms"] = min(metrics["rtts_ms"])
        metrics["max_rtt_ms"] = max(metrics["rtts_ms"])
    
    writer.close()
    await writer.wait_closed()
    
    return metrics


@pytest.mark.asyncio
async def test_tcp_basic_connectivity(tcp_network):
    """Test basic TCP connectivity"""
    server = await tcp_network.create_tcp_server("test_server", port=8001)
    
    reader, writer = await asyncio.open_connection("127.0.0.1", server.port)
    
    test_message = b"Hello from TCP"
    writer.write(test_message)
    await writer.drain()
    
    try:
        response = await asyncio.wait_for(reader.read(1024), timeout=2.0)
        assert response == test_message, f"Response mismatch: {response} != {test_message}"
        logging.info("Successfully sent and received data through TCP")
    except (asyncio.TimeoutError, AssertionError) as e:
        pytest.fail(f"TCP communication failed: {str(e)}")
    finally:
        writer.close()
        await writer.wait_closed()
    
    metrics["tcp_basic_connectivity"] = {"success": True}
    
    return True


@pytest.mark.asyncio
async def test_throughput_tcp_network(tcp_network):
    """Test throughput across different realistic network profiles in TCP"""
    results = {}
    packet_sizes = [64, 512, 1024, 4096]
    test_duration = 3.0  # seconds
    
    for profile_name, profile in network_conditions.NETWORK_PROFILES.items():
        print(f"\nTesting throughput on {profile_name} TCP network profile")
        results[profile_name] = {}
        
        for packet_size in packet_sizes:
            server_name = f"server_{profile_name}_{packet_size}"
            server = await tcp_network.create_tcp_server(server_name)
            
            # Apply network conditions and get the proxy port
            proxy_port = await tcp_network.set_network_conditions(server_name, profile)
            
            try:
                reader, writer = await asyncio.open_connection("127.0.0.1", proxy_port)
            except Exception as e:
                logging.error(f"Failed to connect to TCP server: {str(e)}")
                continue
                
            data = b"x" * packet_size
            start_time = time.time()
            packets_sent = 0
            packets_received = 0
            bytes_sent = 0
            
            print(f"  Sending {packet_size} byte packets for {test_duration}s...")
            try:
                while time.time() - start_time < test_duration:
                    writer.write(data)
                    await writer.drain()
                    packets_sent += 1
                    bytes_sent += packet_size
                    try:
                        response = await asyncio.wait_for(reader.read(packet_size), timeout=0.1)
                        if response:
                            packets_received += 1
                    except asyncio.TimeoutError:
                        pass  # Continue without waiting for response
                    if profile["bandwidth_mbps"]:
                        # Calculate theoretical time to send based on bandwidth
                        packet_time = (packet_size * 8) / (profile["bandwidth_mbps"] * 1_000_000)
                        await asyncio.sleep(packet_time * 0.5)  # Sleep slightly less than theoretical time
                    else:
                        await asyncio.sleep(0.001)  # Minimal sleep
            except Exception as e:
                logging.error(f"Error during throughput test: {str(e)}")
            finally:
                writer.close()
                await writer.wait_closed()
                
            elapsed = time.time() - start_time
            throughput_mbps = (bytes_sent * 8) / (elapsed * 1_000_000)
            packets_per_second = packets_sent / elapsed
            delivery_ratio = (packets_received / packets_sent * 100) if packets_sent > 0 else 0
            
            results[profile_name][packet_size] = {
                "throughput_mbps": throughput_mbps,
                "packets_sent": packets_sent,
                "packets_received": packets_received,
                "packets_per_second": packets_per_second,
                "delivery_ratio": delivery_ratio,
                "bytes_sent": bytes_sent,
                "elapsed_seconds": elapsed
            }
            
            print(f"  Packet size: {packet_size} bytes - Throughput: {throughput_mbps:.2f} Mbps "
                  f"({packets_per_second:.2f} packets/sec), PDR: {delivery_ratio:.2f}%")
    
    metrics["throughput_tcp_network"] = results
    return results


@pytest.mark.asyncio
async def test_latency_jitter_tcp(tcp_network):
    """Test latency and jitter across different network profiles in TCP"""
    results = {}
    packet_sizes = [64, 512, 1024]
    samples_per_size = 50
    
    for profile_name, profile in network_conditions.NETWORK_PROFILES.items():
        if profile_name in ["congested"] and samples_per_size > 20:
            current_samples = 20
        else:
            current_samples = samples_per_size
            
        print(f"\nTesting latency/jitter on {profile_name} TCP network profile ({current_samples} samples)")
        profile_results = {}
        
        for packet_size in packet_sizes:
            server_name = f"server_{profile_name}_{packet_size}"
            server = await tcp_network.create_tcp_server(server_name)
            
            # Apply network conditions and get the proxy port
            proxy_port = await tcp_network.set_network_conditions(server_name, profile)
            
            test_metrics = await measure_tcp_metrics(
                tcp_port=proxy_port,
                packet_size=packet_size,
                packet_count=current_samples,
                inter_packet_delay=0.05  # Increased to reduce congestion
            )
            
            profile_results[packet_size] = {
                "avg_latency_ms": test_metrics.get("avg_latency_ms", 0),
                "min_latency_ms": test_metrics.get("min_latency_ms", 0),
                "max_latency_ms": test_metrics.get("max_latency_ms", 0),
                "avg_jitter_ms": test_metrics.get("avg_jitter_ms", 0),
                "max_jitter_ms": test_metrics.get("max_jitter_ms", 0),
                "avg_rtt_ms": test_metrics.get("avg_rtt_ms", 0)
            }
            
            print(f"  Packet size: {packet_size} bytes - "
                  f"Latency: {test_metrics.get('avg_latency_ms', 0):.2f}ms "
                  f"(min: {test_metrics.get('min_latency_ms', 0):.2f}, "
                  f"max: {test_metrics.get('max_latency_ms', 0):.2f}), "
                  f"Jitter: {test_metrics.get('avg_jitter_ms', 0):.2f}ms, "
                  f"RTT: {test_metrics.get('avg_rtt_ms', 0):.2f}ms")
        
        results[profile_name] = profile_results
    
    # Store results in the global metrics dictionary
    metrics["latency_jitter_tcp"] = results
    return results


@pytest.mark.asyncio
async def test_packet_delivery_ratio_tcp(tcp_network):
    """Test PDR under different network profiles and loads in TCP"""
    results = {}
    
    # Parameters
    packet_sizes = [64, 1024]
    packets_per_test = 200
    
    # Test different network profiles
    for profile_name, profile in network_conditions.NETWORK_PROFILES.items():
        print(f"\nTesting packet delivery ratio on {profile_name} TCP network profile")
        profile_results = {}
        
        for packet_size in packet_sizes:
            server_name = f"server_{profile_name}_{packet_size}"
            server = await tcp_network.create_tcp_server(server_name)
            
            # Apply network conditions and get the proxy port
            proxy_port = await tcp_network.set_network_conditions(server_name, profile)
            
            # Measure metrics
            test_metrics = await measure_tcp_metrics(
                tcp_port=proxy_port,
                packet_size=packet_size,
                packet_count=packets_per_test,
                inter_packet_delay=0.02  # Give packets time to arrive
            )
            
            profile_results[packet_size] = {
                "sent": test_metrics["sent"],
                "received": test_metrics["received"],
                "delivery_ratio": test_metrics["delivery_ratio"]
            }
            
            print(f"  Packet size: {packet_size} bytes - "
                  f"PDR: {test_metrics['delivery_ratio']:.2f}% "
                  f"({test_metrics['received']}/{test_metrics['sent']} packets)")
        
        results[profile_name] = profile_results
    
    # Store results in the global metrics dictionary
    metrics["packet_delivery_ratio_tcp"] = results
    return results


@pytest.mark.asyncio
async def test_concurrent_tcp_connections(tcp_network):
    """Test scalability with concurrent TCP connections"""
    results = {}
    
    # Parameters
    connection_counts = [1, 5, 10, 25]
    
    # Create base server
    server = await tcp_network.create_tcp_server("concurrent_test_server")
    
    for connection_count in connection_counts:
        print(f"\nTesting {connection_count} concurrent TCP connections")
        
        start_time = time.time()
        connections = []
        success_count = 0
        data_success = 0
        
        # Establish connections
        for i in range(connection_count):
            try:
                reader, writer = await asyncio.open_connection("127.0.0.1", server.port)
                connections.append((reader, writer))
                success_count += 1
            except Exception as e:
                logging.error(f"Failed to establish TCP connection {i+1}: {str(e)}")
        
        establishment_time = time.time() - start_time
        
        # Send data through all connections
        test_data = b"test_data"
        for i, (reader, writer) in enumerate(connections):
            try:
                writer.write(test_data)
                await writer.drain()
                
                # Wait for response
                response = await asyncio.wait_for(reader.read(len(test_data)), timeout=2.0)
                if response == test_data:
                    data_success += 1
            except Exception as e:
                logging.error(f"Error sending/receiving data through connection {i+1}: {str(e)}")
        
        # Close all connections
        for reader, writer in connections:
            writer.close()
            await writer.wait_closed()
        
        results[connection_count] = {
            "target_connections": connection_count,
            "successful_connections": success_count,
            "establishment_time_seconds": establishment_time,
            "establishment_time_per_conn_ms": (establishment_time * 1000) / max(success_count, 1),
            "data_exchange_success_rate": (data_success / max(success_count, 1)) * 100
        }
        
        print(f"Results: {success_count}/{connection_count} connections established in {establishment_time:.2f}s "
              f"({results[connection_count]['establishment_time_per_conn_ms']:.2f}ms per connection)")
        print(f"Data exchange success rate: {results[connection_count]['data_exchange_success_rate']:.2f}%")
    
    # Store results in global metrics
    metrics["concurrent_tcp_connections"] = results
    return results


@pytest.fixture(scope="session", autouse=True)
def save_metrics():
    yield
    with open("tcp_metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)


if __name__ == "__main__":
    pytest.main(["-xvs", "test_tcp_network.py"])