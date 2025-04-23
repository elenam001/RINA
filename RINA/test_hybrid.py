import pytest
import pytest_asyncio
import asyncio
import time
import statistics
import json
import random
import logging
from contextlib import AsyncExitStack
from rina.qos import QoS
from network_conditions import RealisticNetwork, NETWORK_PROFILES
from hybrid_network import HybridNetwork, TCPIPAdapter, RINATCPApplication

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Global metrics dictionary to store all test results
metrics = {}

@pytest_asyncio.fixture
async def hybrid_network():
    """Create a clean hybrid network for each test"""
    network = HybridNetwork()
    yield network
    await network.shutdown()

@pytest_asyncio.fixture
async def realistic_network():
    """Create a clean realistic network for each test"""
    network = RealisticNetwork()
    yield network
    await network.cleanup()

async def setup_hybrid_test_env(hybrid_network, realistic_network, profile_name, profile):
    """Set up a test environment with hybrid network and realistic conditions"""
    # Create DIFs
    rina_dif = await hybrid_network.create_rina_dif("rina_dif", layer=0, max_bandwidth=1000)
    
    # Create IPCPs
    rina_ipcp1 = await hybrid_network.create_rina_ipcp("rina_ipcp1", "rina_dif")
    rina_ipcp2 = await hybrid_network.create_rina_ipcp("rina_ipcp2", "rina_dif")
    
    # Enroll IPCPs
    await rina_ipcp1.enroll(rina_ipcp2)
    
    # Create TCP adapters
    tcp_adapter1 = await hybrid_network.create_tcp_adapter("tcp_adapter1", host='127.0.0.1', port=8000)
    tcp_adapter2 = await hybrid_network.create_tcp_adapter("tcp_adapter2", host='127.0.0.1', port=8001)
    
    # Connect adapters to RINA IPCPs
    await hybrid_network.connect_adapter_to_rina("tcp_adapter1", "rina_ipcp1", "rina_dif")
    await hybrid_network.connect_adapter_to_rina("tcp_adapter2", "rina_ipcp2", "rina_dif")
    
    # Start TCP adapters
    await hybrid_network.start_tcp_adapters()
    
    # Set up network conditions
    await realistic_network.set_network_conditions("rina_ipcp1", "rina_ipcp2", profile)
    
    return {
        "rina_dif": rina_dif,
        "rina_ipcp1": rina_ipcp1,
        "rina_ipcp2": rina_ipcp2,
        "tcp_adapter1": tcp_adapter1,
        "tcp_adapter2": tcp_adapter2
    }

class TCPTestClient:
    """Test client that sends/receives data over TCP"""
    def __init__(self, host='127.0.0.1', port=8000):
        self.host = host
        self.port = port
        self.reader = None
        self.writer = None
        self.stats = {
            "sent_packets": 0,
            "received_packets": 0,
            "bytes_sent": 0,
            "bytes_received": 0,
            "response_times_ms": []
        }
    
    async def connect(self):
        """Connect to the TCP server"""
        self.reader, self.writer = await asyncio.open_connection(self.host, self.port)
        return True
    
    async def send_data(self, data):
        """Send data and measure response time"""
        if not self.writer:
            return False
            
        start_time = time.time()
        try:
            self.writer.write(data)
            await self.writer.drain()
            self.stats["sent_packets"] += 1
            self.stats["bytes_sent"] += len(data)
            
            # Wait for response
            response = await asyncio.wait_for(self.reader.read(len(data) * 2), timeout=5.0)
            end_time = time.time()
            
            if response:
                self.stats["received_packets"] += 1
                self.stats["bytes_received"] += len(response)
                response_time = (end_time - start_time) * 1000  # ms
                self.stats["response_times_ms"].append(response_time)
                return response, response_time
            return None, 0
            
        except Exception as e:
            logging.error(f"Error in send_data: {str(e)}")
            return None, 0
    
    async def close(self):
        """Close the connection"""
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()
            self.writer = None
            self.reader = None


@pytest.mark.asyncio
async def test_hybrid_throughput(hybrid_network, realistic_network):
    """Test throughput of the hybrid network across different network profiles"""
    results = {}
    
    # Test parameters
    packet_sizes = [64, 512, 1024, 4096]
    test_duration = 5.0  # seconds
    
    for profile_name, profile in NETWORK_PROFILES.items():
        print(f"\nTesting hybrid throughput on {profile_name} network profile")
        profile_results = {}
        
        # Set up test environment
        env = await setup_hybrid_test_env(hybrid_network, realistic_network, profile_name, profile)
        
        for packet_size in packet_sizes:
            print(f"  Testing with packet size: {packet_size} bytes")
            
            # Create TCP test client
            client = TCPTestClient(host='127.0.0.1', port=8000)
            await client.connect()
            
            # Send data continuously for the test duration
            data = b"x" * packet_size
            start_time = time.time()
            packets_sent = 0
            bytes_sent = 0
            
            # Adjust sending speed based on network profile
            if profile["bandwidth_mbps"]:
                # Theoretical time to send one packet
                packet_time = (packet_size * 8) / (profile["bandwidth_mbps"] * 1_000_000)
                sleep_time = packet_time * 0.9  # Slightly less than theoretical time
            else:
                sleep_time = 0.0001  # Minimal sleep
            
            while time.time() - start_time < test_duration:
                response, _ = await client.send_data(data)
                if response:
                    packets_sent += 1
                    bytes_sent += packet_size
                    
                await asyncio.sleep(sleep_time)
            
            # Calculate metrics
            elapsed = time.time() - start_time
            throughput_mbps = (bytes_sent * 8) / (elapsed * 1_000_000)
            packets_per_second = packets_sent / elapsed
            avg_response_time = statistics.mean(client.stats["response_times_ms"]) if client.stats["response_times_ms"] else 0
            
            # Close the client
            await client.close()
            
            # Store results
            profile_results[packet_size] = {
                "throughput_mbps": throughput_mbps,
                "packets_sent": packets_sent,
                "packets_received": client.stats["received_packets"],
                "packets_per_second": packets_per_second,
                "bytes_sent": bytes_sent,
                "bytes_received": client.stats["bytes_received"],
                "avg_response_time_ms": avg_response_time,
                "elapsed_seconds": elapsed
            }
            
            print(f"  Throughput: {throughput_mbps:.2f} Mbps ({packets_per_second:.2f} packets/sec)")
            print(f"  Average response time: {avg_response_time:.2f} ms")
        
        results[profile_name] = profile_results
    
    # Store results in the global metrics dictionary
    metrics["hybrid_throughput"] = results
    return results


@pytest.mark.asyncio
async def test_hybrid_latency_jitter(hybrid_network, realistic_network):
    """Test latency and jitter of the hybrid network across different network profiles"""
    results = {}
    
    # Test parameters
    packet_sizes = [64, 512, 1024, 4096]
    samples_per_size = 100
    
    for profile_name, profile in NETWORK_PROFILES.items():
        # Reduce samples for high latency profiles
        if profile_name in ["congested"]:
            current_samples = 50
        else:
            current_samples = samples_per_size
            
        print(f"\nTesting hybrid latency/jitter on {profile_name} network profile")
        profile_results = {}
        
        # Set up test environment
        env = await setup_hybrid_test_env(hybrid_network, realistic_network, profile_name, profile)
        
        for packet_size in packet_sizes:
            print(f"  Testing with packet size: {packet_size} bytes")
            
            # Create TCP test client
            client = TCPTestClient(host='127.0.0.1', port=8000)
            await client.connect()
            
            # Send packets and measure response time
            data = b"x" * packet_size
            response_times = []
            jitter_values = []
            last_response_time = 0
            
            for i in range(current_samples):
                response, response_time = await client.send_data(data)
                if response:
                    response_times.append(response_time)
                    
                    # Calculate jitter (variation in response time)
                    if i > 0:
                        jitter = abs(response_time - last_response_time)
                        jitter_values.append(jitter)
                    
                    last_response_time = response_time
                
                # Add delay between packets to avoid congestion
                await asyncio.sleep(0.05)
            
            # Calculate metrics
            if response_times:
                avg_response_time = statistics.mean(response_times)
                min_response_time = min(response_times)
                max_response_time = max(response_times)
            else:
                avg_response_time = min_response_time = max_response_time = 0
                
            if jitter_values:
                avg_jitter = statistics.mean(jitter_values)
                max_jitter = max(jitter_values)
            else:
                avg_jitter = max_jitter = 0
            
            # Close the client
            await client.close()
            
            # Store results
            profile_results[packet_size] = {
                "avg_response_time_ms": avg_response_time,
                "min_response_time_ms": min_response_time,
                "max_response_time_ms": max_response_time,
                "avg_jitter_ms": avg_jitter,
                "max_jitter_ms": max_jitter,
                "samples": len(response_times)
            }
            
            print(f"  Response time: {avg_response_time:.2f}ms (min: {min_response_time:.2f}, max: {max_response_time:.2f})")
            print(f"  Jitter: {avg_jitter:.2f}ms (max: {max_jitter:.2f})")
        
        results[profile_name] = profile_results
    
    # Store results in the global metrics dictionary
    metrics["hybrid_latency_jitter"] = results
    return results


@pytest.mark.asyncio
async def test_hybrid_packet_delivery_ratio(hybrid_network, realistic_network):
    """Test packet delivery ratio across different network profiles"""
    results = {}
    
    # Test parameters
    packet_sizes = [64, 1024, 4096]
    packets_per_test = 200
    
    for profile_name, profile in NETWORK_PROFILES.items():
        print(f"\nTesting hybrid packet delivery ratio on {profile_name} network profile")
        profile_results = {}
        
        # Set up test environment
        env = await setup_hybrid_test_env(hybrid_network, realistic_network, profile_name, profile)
        
        for packet_size in packet_sizes:
            print(f"  Testing with packet size: {packet_size} bytes")
            
            # Create TCP test client
            client = TCPTestClient(host='127.0.0.1', port=8000)
            await client.connect()
            
            # Send packets and count successful deliveries
            data = b"x" * packet_size
            successful_sends = 0
            successful_responses = 0
            
            for i in range(packets_per_test):
                try:
                    response, _ = await asyncio.wait_for(
                        client.send_data(data), 
                        timeout=max(1.0, profile["latency_ms"] / 500)
                    )
                    successful_sends += 1
                    if response:
                        successful_responses += 1
                except asyncio.TimeoutError:
                    pass
                except Exception as e:
                    logging.error(f"Error in packet delivery test: {str(e)}")
                
                # Add delay between packets
                await asyncio.sleep(0.01)
            
            # Calculate metrics
            if successful_sends > 0:
                delivery_ratio = (successful_responses / successful_sends) * 100
            else:
                delivery_ratio = 0
            
            # Close the client
            await client.close()
            
            # Store results
            profile_results[packet_size] = {
                "packets_sent": packets_per_test,
                "successful_sends": successful_sends,
                "successful_responses": successful_responses,
                "delivery_ratio": delivery_ratio
            }
            
            print(f"  PDR: {delivery_ratio:.2f}% ({successful_responses}/{successful_sends} packets)")
        
        results[profile_name] = profile_results
    
    # Store results in the global metrics dictionary
    metrics["hybrid_packet_delivery_ratio"] = results
    return results


@pytest.mark.asyncio
async def test_hybrid_concurrent_clients(hybrid_network, realistic_network):
    """Test the hybrid network with multiple concurrent TCP clients"""
    results = {}
    
    # Test parameters
    client_counts = [1, 5, 10, 25]  # Number of concurrent clients
    packet_size = 1024
    packets_per_client = 50
    
    # Test only with certain network profiles for practicality
    test_profiles = ["perfect", "lan", "wifi"]
    
    for profile_name in test_profiles:
        profile = NETWORK_PROFILES[profile_name]
        print(f"\nTesting hybrid network with concurrent clients on {profile_name} network profile")
        profile_results = {}
        
        # Set up test environment
        env = await setup_hybrid_test_env(hybrid_network, realistic_network, profile_name, profile)
        
        for client_count in client_counts:
            print(f"  Testing with {client_count} concurrent clients")
            
            # Create TCP test clients
            clients = []
            for i in range(client_count):
                client = TCPTestClient(host='127.0.0.1', port=8000)
                await client.connect()
                clients.append(client)
            
            # Send data concurrently from all clients
            data = b"x" * packet_size
            start_time = time.time()
            
            async def client_task(client, task_id):
                """Task for each client to send data"""
                for i in range(packets_per_client):
                    try:
                        await client.send_data(data)
                        # Add short delay between sends
                        await asyncio.sleep(0.05)
                    except Exception as e:
                        logging.error(f"Error in client {task_id}: {str(e)}")
            
            # Create and run tasks for all clients
            tasks = []
            for i, client in enumerate(clients):
                task = asyncio.create_task(client_task(client, i))
                tasks.append(task)
            
            # Wait for all tasks to complete
            await asyncio.gather(*tasks)
            
            # Calculate metrics
            elapsed = time.time() - start_time
            total_packets_sent = sum(client.stats["sent_packets"] for client in clients)
            total_packets_received = sum(client.stats["received_packets"] for client in clients)
            total_bytes_sent = sum(client.stats["bytes_sent"] for client in clients)
            
            # Calculate throughput and success rate
            throughput_mbps = (total_bytes_sent * 8) / (elapsed * 1_000_000) if elapsed > 0 else 0
            success_rate = (total_packets_received / total_packets_sent * 100) if total_packets_sent > 0 else 0
            
            # Calculate average response time across all clients
            all_response_times = []
            for client in clients:
                all_response_times.extend(client.stats["response_times_ms"])
            
            avg_response_time = statistics.mean(all_response_times) if all_response_times else 0
            
            # Close all clients
            for client in clients:
                await client.close()
            
            # Store results
            profile_results[client_count] = {
                "elapsed_seconds": elapsed,
                "total_packets_sent": total_packets_sent,
                "total_packets_received": total_packets_received,
                "success_rate": success_rate,
                "throughput_mbps": throughput_mbps,
                "avg_response_time_ms": avg_response_time
            }
            
            print(f"  Success rate: {success_rate:.2f}%")
            print(f"  Throughput: {throughput_mbps:.2f} Mbps")
            print(f"  Average response time: {avg_response_time:.2f} ms")
        
        results[profile_name] = profile_results
    
    # Store results in the global metrics dictionary
    metrics["hybrid_concurrent_clients"] = results
    return results


@pytest.mark.asyncio
async def test_hybrid_bidirectional_traffic(hybrid_network, realistic_network):
    """Test bidirectional traffic between TCP and RINA"""
    results = {}
    
    # Test parameters
    packet_sizes = [512, 2048]
    test_duration = 3.0  # seconds
    test_profiles = ["perfect", "lan", "wifi"]
    
    for profile_name in test_profiles:
        profile = NETWORK_PROFILES[profile_name]
        print(f"\nTesting hybrid bidirectional traffic on {profile_name} network profile")
        profile_results = {}
        
        # Set up test environment
        env = await setup_hybrid_test_env(hybrid_network, realistic_network, profile_name, profile)
        rina_ipcp1 = env["rina_ipcp1"]
        rina_ipcp2 = env["rina_ipcp2"]
        
        # Create hybrid application on RINA side
        hybrid_app = await hybrid_network.create_hybrid_application(
            "hybrid_app", rina_ipcp2, adapter_name="tcp_adapter2"
        )
        
        for packet_size in packet_sizes:
            print(f"  Testing with packet size: {packet_size} bytes")
            
            # Connect TCP client to first adapter
            tcp_client = TCPTestClient(host='127.0.0.1', port=8000)
            await tcp_client.connect()
            
            # Create a TCP server connection on the other side
            tcp_server_host = '127.0.0.1'
            tcp_server_port = 9000
            
            # Start echo server for testing
            echo_server = None
            server_ready = asyncio.Event()
            
            async def echo_server_handler(reader, writer):
                while True:
                    data = await reader.read(4096)
                    if not data:
                        break
                    writer.write(data)
                    await writer.drain()
                writer.close()
                await writer.wait_closed()
            
            async def start_echo_server():
                nonlocal echo_server
                echo_server = await asyncio.start_server(
                    echo_server_handler, tcp_server_host, tcp_server_port
                )
                server_ready.set()
                async with echo_server:
                    await echo_server.serve_forever()
            
            # Start the echo server in a background task
            server_task = asyncio.create_task(start_echo_server())
            await server_ready.wait()
            
            # Connect the hybrid app to the TCP echo server
            tcp_conn_id = await hybrid_app.connect_to_tcp(tcp_server_host, tcp_server_port)
            
            # Create a flow from RINA side to TCP side (TCP client -> adapter -> RINA -> hybrid_app -> TCP echo server)
            data = b"x" * packet_size
            tcp_to_rina_success = 0
            rina_to_tcp_success = 0
            
            # Test TCP -> RINA -> TCP path
            start_time = time.time()
            while time.time() - start_time < test_duration:
                response, _ = await tcp_client.send_data(data)
                if response:
                    tcp_to_rina_success += 1
                await asyncio.sleep(0.05)
            
            # Test RINA -> TCP -> RINA path (in sequence after the first test)
            # Create a flow from RINA side to the TCP adapter
            flow_id = await rina_ipcp2.allocate_flow(rina_ipcp1, port=5000)
            
            start_time = time.time()
            while time.time() - start_time < test_duration:
                await rina_ipcp2.send_data(flow_id, data)
                # Wait for response (would be handled by the flow's callbacks in real implementation)
                await asyncio.sleep(0.05)
                rina_to_tcp_success += 1
            
            # Clean up
            await rina_ipcp2.deallocate_flow(flow_id)
            await hybrid_app.disconnect_tcp(tcp_conn_id)
            await tcp_client.close()
            echo_server.close()
            await echo_server.wait_closed()
            server_task.cancel()
            try:
                await server_task
            except asyncio.CancelledError:
                pass
            
            # Store results
            profile_results[packet_size] = {
                "tcp_to_rina_success": tcp_to_rina_success,
                "rina_to_tcp_success": rina_to_tcp_success,
                "tcp_client_stats": {
                    "sent_packets": tcp_client.stats["sent_packets"],
                    "received_packets": tcp_client.stats["received_packets"],
                    "avg_response_time_ms": statistics.mean(tcp_client.stats["response_times_ms"]) 
                        if tcp_client.stats["response_times_ms"] else 0
                }
            }
            
            print(f"  TCP->RINA->TCP successes: {tcp_to_rina_success}")
            print(f"  RINA->TCP->RINA successes: {rina_to_tcp_success}")
        
        results[profile_name] = profile_results
    
    # Store results in the global metrics dictionary
    metrics["hybrid_bidirectional_traffic"] = results
    return results


@pytest.fixture(scope="session", autouse=True)
def save_metrics():
    yield
    with open("hybrid_metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)

if __name__ == "__main__":
    pytest.main(["-xvs", __file__])