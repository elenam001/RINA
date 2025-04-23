import pytest
import pytest_asyncio
import asyncio
import time
import statistics
import json
import random
import socket
from contextlib import AsyncExitStack
from rina.qos import QoS
import network_conditions
from hybrid_network import HybridNetwork, TCPIPAdapter, RINATCPApplication
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

metrics = {}

@pytest_asyncio.fixture
async def hybrid_net():
    """Create a clean hybrid network for each test"""
    network = HybridNetwork()
    yield network
    await network.shutdown()

@pytest_asyncio.fixture
async def realistic_network():
    """Create a realistic network environment for testing"""
    network = network_conditions.RealisticNetwork()
    yield network
    await network.cleanup()

async def measure_hybrid_flow_metrics(tcp_adapter, tcp_client, packet_size, packet_count, 
                                    inter_packet_delay=0.001, flow_qos=None):
    """Helper function to measure metrics for a hybrid TCP-RINA flow"""
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
    
    # Connect to TCP adapter
    try:
        reader, writer = await asyncio.open_connection(*tcp_client)
        connection_setup_time = time.time() - start_time
        metrics["connection_setup_time_ms"] = connection_setup_time * 1000
    except Exception as e:
        logging.error(f"Failed to connect to TCP adapter: {str(e)}")
        return metrics
    
    # Send packets and measure
    data = b"x" * packet_size
    last_latency = 0
    
    send_start_time = time.time()
    for i in range(packet_count):
        packet_send_time = time.time()
        
        # Send the packet
        writer.write(data)
        await writer.drain()
        metrics["sent"] += 1
        
        # Wait for response
        try:
            response = await asyncio.wait_for(reader.read(packet_size), timeout=2.0)
            if response:
                metrics["received"] += 1
                
                # Calculate RTT
                rtt = (time.time() - packet_send_time) * 1000  # ms
                metrics["rtts_ms"].append(rtt)
                
                # Measure one-way latency (approximation)
                latency = rtt / 2
                metrics["latencies_ms"].append(latency)
                
                # Calculate jitter only after first packet
                if i > 0:
                    jitter = abs(latency - last_latency)
                    metrics["jitter_ms"].append(jitter)
                last_latency = latency
        except asyncio.TimeoutError:
            logging.warning(f"Timeout waiting for response to packet {i}")
        
        # Small delay between packets
        if inter_packet_delay > 0:
            await asyncio.sleep(inter_packet_delay)
    
    send_end_time = time.time()
    
    # Calculate metrics
    metrics["delivery_ratio"] = (metrics["received"] / metrics["sent"]) * 100 if metrics["sent"] > 0 else 0
    
    total_bits = metrics["sent"] * packet_size * 8
    duration = send_end_time - send_start_time
    metrics["throughput_mbps"] = total_bits / (duration * 1_000_000) if duration > 0 else 0
    
    # Calculate summary statistics
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
    
    # Clean up
    writer.close()
    await writer.wait_closed()
    
    return metrics

@pytest.mark.asyncio
async def test_hybrid_basic_connectivity(hybrid_net):
    """Test basic connectivity between TCP/IP and RINA networks"""
    # Create DIFs and IPCPs
    dif = await hybrid_net.create_rina_dif("test_dif", layer=0)
    src_ipcp = await hybrid_net.create_rina_ipcp("src_ipcp", "test_dif")
    dst_ipcp = await hybrid_net.create_rina_ipcp("dst_ipcp", "test_dif")
    
    # Enroll IPCPs
    await src_ipcp.enroll(dst_ipcp)
    
    # Create TCP adapter and connect to RINA
    adapter = await hybrid_net.create_tcp_adapter("test_adapter", host="127.0.0.1", port=8001)
    await hybrid_net.connect_adapter_to_rina("test_adapter", "src_ipcp", "test_dif")
    
    # Start TCP adapter
    await adapter.start_server()
    
    # Create a hybrid application
    hybrid_app = await hybrid_net.create_hybrid_application("test_app", dst_ipcp, adapter_name="test_adapter")
    await hybrid_app.bind(5000)  # Bind to port 5000 in RINA network
    
    # Test TCP connection to the adapter
    reader, writer = await asyncio.open_connection("127.0.0.1", 8001)
    
    # Send data through TCP
    test_message = b"Hello from TCP to RINA"
    writer.write(test_message)
    await writer.drain()
    
    # Wait for response (echoed back by the adapter in simple mode)
    try:
        response = await asyncio.wait_for(reader.read(1024), timeout=2.0)
        assert response == test_message, f"Response mismatch: {response} != {test_message}"
        logging.info("Successfully sent and received data through hybrid network")
    except (asyncio.TimeoutError, AssertionError) as e:
        pytest.fail(f"TCP to RINA communication failed: {str(e)}")
    finally:
        writer.close()
        await writer.wait_closed()
    
    # Record success in metrics
    metrics["hybrid_basic_connectivity"] = {"success": True}
    
    return True

@pytest.mark.asyncio
async def test_throughput_hybrid_network(hybrid_net, realistic_network):
    """Test throughput across different realistic network profiles in hybrid mode"""
    results = {}
    
    # Parameters
    packet_sizes = [64, 512, 1024, 4096]
    test_duration = 3.0  # seconds
    
    # Create network components
    dif = await hybrid_net.create_rina_dif("test_dif", layer=0)
    
    for profile_name, profile in network_conditions.NETWORK_PROFILES.items():
        print(f"\nTesting throughput on {profile_name} hybrid network profile")
        results[profile_name] = {}
        
        for packet_size in packet_sizes:
            # Create fresh IPCPs for each test
            src_ipcp_id = f"src_ipcp_{profile_name}_{packet_size}"
            dst_ipcp_id = f"dst_ipcp_{profile_name}_{packet_size}"
            
            src_ipcp = await hybrid_net.create_rina_ipcp(src_ipcp_id, "test_dif")
            dst_ipcp = await hybrid_net.create_rina_ipcp(dst_ipcp_id, "test_dif")
            
            await src_ipcp.enroll(dst_ipcp)
            
            # Create TCP adapter
            adapter_name = f"adapter_{profile_name}_{packet_size}"
            tcp_port = 8000 + hash(adapter_name) % 1000  # Generate a unique port
            adapter = await hybrid_net.create_tcp_adapter(adapter_name, port=tcp_port)
            await hybrid_net.connect_adapter_to_rina(adapter_name, src_ipcp_id, "test_dif")
            
            # Create applications
            app_src = await hybrid_net.create_hybrid_application(f"app_src_{profile_name}_{packet_size}", src_ipcp)
            app_dst = await hybrid_net.create_hybrid_application(f"app_dst_{profile_name}_{packet_size}", dst_ipcp)
            await app_dst.bind(5000)
            
            # Start TCP adapter
            await adapter.start_server()
            
            # Apply network conditions between IPCPs
            await realistic_network.set_network_conditions(src_ipcp_id, dst_ipcp_id, profile)
            
            # Connect to TCP adapter
            try:
                reader, writer = await asyncio.open_connection("127.0.0.1", tcp_port)
            except Exception as e:
                logging.error(f"Failed to connect to TCP adapter: {str(e)}")
                continue
                
            # Send data continuously for the test duration
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
                    
                    # Wait for response to measure received packets
                    try:
                        response = await asyncio.wait_for(reader.read(packet_size), timeout=0.1)
                        if response:
                            packets_received += 1
                    except asyncio.TimeoutError:
                        pass  # Continue without waiting for response
                    
                    # Adjust sleep based on network profile to avoid overloading
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
            
            # Calculate throughput
            elapsed = time.time() - start_time
            throughput_mbps = (bytes_sent * 8) / (elapsed * 1_000_000)
            packets_per_second = packets_sent / elapsed
            delivery_ratio = (packets_received / packets_sent * 100) if packets_sent > 0 else 0
            
            # Store results
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
    
    # Store results in the global metrics dictionary
    metrics["throughput_hybrid_network"] = results
    return results

@pytest.mark.asyncio
async def test_latency_jitter_hybrid(hybrid_net, realistic_network):
    """Test latency and jitter across different network profiles in hybrid network"""
    results = {}
    
    # Parameters
    packet_sizes = [64, 512, 1024]
    samples_per_size = 50
    
    # Create network components
    dif = await hybrid_net.create_rina_dif("test_dif", layer=0)
    
    for profile_name, profile in network_conditions.NETWORK_PROFILES.items():
        if profile_name in ["extreme", "satellite"] and samples_per_size > 20:
            # Reduce samples for high latency profiles
            current_samples = 20
        else:
            current_samples = samples_per_size
            
        print(f"\nTesting latency/jitter on {profile_name} hybrid network profile ({current_samples} samples)")
        profile_results = {}
        
        for packet_size in packet_sizes:
            # Create fresh IPCPs for each test
            src_ipcp_id = f"src_ipcp_{profile_name}_{packet_size}"
            dst_ipcp_id = f"dst_ipcp_{profile_name}_{packet_size}"
            
            src_ipcp = await hybrid_net.create_rina_ipcp(src_ipcp_id, "test_dif")
            dst_ipcp = await hybrid_net.create_rina_ipcp(dst_ipcp_id, "test_dif")
            
            await src_ipcp.enroll(dst_ipcp)
            
            # Create TCP adapter
            adapter_name = f"adapter_{profile_name}_{packet_size}"
            tcp_port = 8000 + hash(adapter_name) % 1000  # Generate a unique port
            adapter = await hybrid_net.create_tcp_adapter(adapter_name, port=tcp_port)
            await hybrid_net.connect_adapter_to_rina(adapter_name, src_ipcp_id, "test_dif")
            
            # Create applications
            app_dst = await hybrid_net.create_hybrid_application(f"app_dst_{profile_name}_{packet_size}", dst_ipcp)
            await app_dst.bind(5000)
            
            # Start TCP adapter
            await adapter.start_server()
            
            # Apply network conditions between IPCPs
            await realistic_network.set_network_conditions(src_ipcp_id, dst_ipcp_id, profile)
            
            # Measure metrics through TCP client
            test_metrics = await measure_hybrid_flow_metrics(
                adapter,
                ("127.0.0.1", tcp_port),
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
    metrics["latency_jitter_hybrid"] = results
    return results

@pytest.mark.asyncio
async def test_packet_delivery_ratio_hybrid(hybrid_net, realistic_network):
    """Test PDR under different network profiles and loads in hybrid network"""
    results = {}
    
    # Parameters
    packet_sizes = [64, 1024]
    packets_per_test = 200
    
    # Create network components
    dif = await hybrid_net.create_rina_dif("test_dif", layer=0)
    
    # Test different network profiles
    for profile_name, profile in network_conditions.NETWORK_PROFILES.items():
        print(f"\nTesting packet delivery ratio on {profile_name} hybrid network profile")
        profile_results = {}
        
        for packet_size in packet_sizes:
            # Create fresh IPCPs for each test
            src_ipcp_id = f"src_ipcp_{profile_name}_{packet_size}"
            dst_ipcp_id = f"dst_ipcp_{profile_name}_{packet_size}"
            
            src_ipcp = await hybrid_net.create_rina_ipcp(src_ipcp_id, "test_dif")
            dst_ipcp = await hybrid_net.create_rina_ipcp(dst_ipcp_id, "test_dif")
            
            await src_ipcp.enroll(dst_ipcp)
            
            # Create TCP adapter
            adapter_name = f"adapter_{profile_name}_{packet_size}"
            tcp_port = 8000 + hash(adapter_name) % 1000  # Generate a unique port
            adapter = await hybrid_net.create_tcp_adapter(adapter_name, port=tcp_port)
            await hybrid_net.connect_adapter_to_rina(adapter_name, src_ipcp_id, "test_dif")
            
            # Create applications
            app_dst = await hybrid_net.create_hybrid_application(f"app_dst_{profile_name}_{packet_size}", dst_ipcp)
            await app_dst.bind(5000)
            
            # Start TCP adapter
            await adapter.start_server()
            
            # Apply network conditions
            await realistic_network.set_network_conditions(src_ipcp_id, dst_ipcp_id, profile)
            
            # Measure metrics
            test_metrics = await measure_hybrid_flow_metrics(
                adapter,
                ("127.0.0.1", tcp_port),
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
    metrics["packet_delivery_ratio_hybrid"] = results
    return results

@pytest.mark.asyncio
async def test_concurrent_tcp_connections(hybrid_net):
    """Test scalability with concurrent TCP connections"""
    results = {}
    
    # Parameters
    connection_counts = [1, 5, 10, 25]
    
    # Create base network components
    dif = await hybrid_net.create_rina_dif("test_dif", layer=0)
    src_ipcp = await hybrid_net.create_rina_ipcp("src_ipcp", "test_dif")
    dst_ipcp = await hybrid_net.create_rina_ipcp("dst_ipcp", "test_dif")
    
    await src_ipcp.enroll(dst_ipcp)
    
    # Create TCP adapter
    adapter = await hybrid_net.create_tcp_adapter("test_adapter", port=8100)
    await hybrid_net.connect_adapter_to_rina("test_adapter", "src_ipcp", "test_dif")
    
    # Create application
    app = await hybrid_net.create_hybrid_application("app_dst", dst_ipcp)
    await app.bind(5000)
    
    # Start TCP adapter
    await adapter.start_server()
    
    for connection_count in connection_counts:
        print(f"\nTesting {connection_count} concurrent TCP connections")
        
        start_time = time.time()
        connections = []
        success_count = 0
        data_success = 0
        
        # Establish connections
        for i in range(connection_count):
            try:
                reader, writer = await asyncio.open_connection("127.0.0.1", 8100)
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

@pytest.mark.asyncio
async def test_bidirectional_communication(hybrid_net):
    """Test bidirectional communication between TCP client and RINA application"""
    # Create network components
    dif = await hybrid_net.create_rina_dif("test_dif", layer=0)
    src_ipcp = await hybrid_net.create_rina_ipcp("src_ipcp", "test_dif")
    dst_ipcp = await hybrid_net.create_rina_ipcp("dst_ipcp", "test_dif")
    
    await src_ipcp.enroll(dst_ipcp)
    
    # Create TCP adapter
    adapter = await hybrid_net.create_tcp_adapter("test_adapter", port=8200)
    await hybrid_net.connect_adapter_to_rina("test_adapter", "src_ipcp", "test_dif")
    
    # Create application with custom data handling
    app = await hybrid_net.create_hybrid_application("app_dst", dst_ipcp)
    
    # Override app's on_data to send back a modified response
    original_on_data = app.on_data
    
    async def custom_on_data(data):
        await original_on_data(data)
        # Echo back with a prefix to indicate it came from RINA app
        if isinstance(data, bytes):
            return b"RINA_RESPONSE:" + data
        else:
            return data
    
    app.on_data = custom_on_data
    await app.bind(5000)
    
    # Start TCP adapter
    await adapter.start_server()
    
    # Connect via TCP
    reader, writer = await asyncio.open_connection("127.0.0.1", 8200)
    
    results = {
        "tcp_to_rina": False,
        "rina_to_tcp": False,
        "round_trip": False
    }
    
    # Test bidirectional communication
    test_message = b"Hello from TCP to RINA"
    try:
        # Send message from TCP to RINA
        writer.write(test_message)
        await writer.drain()
        
        # Wait for response from RINA
        response = await asyncio.wait_for(reader.read(1024), timeout=2.0)
        
        # Verify the response
        expected_response = b"RINA_RESPONSE:" + test_message
        
        if response == test_message:  # Simple echo from adapter
            results["tcp_to_rina"] = True
            print("TCP to RINA communication successful")
        elif response == expected_response:  # Modified response from RINA app
            results["tcp_to_rina"] = True
            results["rina_to_tcp"] = True
            results["round_trip"] = True
            print("Bidirectional TCP-RINA communication successful")
        else:
            print(f"Unexpected response: {response}")
    except Exception as e:
        print(f"Error in bidirectional test: {str(e)}")
    finally:
        writer.close()
        await writer.wait_closed()
    
    # Restore original on_data method
    app.on_data = original_on_data
    
    # Store results in metrics
    metrics["bidirectional_communication"] = results
    
    return results

@pytest.mark.asyncio
async def test_tcp_reconnection_resilience(hybrid_net):
    """Test the ability of the TCP adapter to handle client disconnections and reconnections"""
    # Create network components
    dif = await hybrid_net.create_rina_dif("test_dif", layer=0)
    src_ipcp = await hybrid_net.create_rina_ipcp("src_ipcp", "test_dif")
    dst_ipcp = await hybrid_net.create_rina_ipcp("dst_ipcp", "test_dif")
    
    await src_ipcp.enroll(dst_ipcp)
    
    # Create TCP adapter
    adapter = await hybrid_net.create_tcp_adapter("test_adapter", port=8300)
    await hybrid_net.connect_adapter_to_rina("test_adapter", "src_ipcp", "test_dif")
    
    # Create application
    app = await hybrid_net.create_hybrid_application("app_dst", dst_ipcp)
    await app.bind(5000)
    
    # Start TCP adapter
    await adapter.start_server()
    
    reconnection_results = []
    total_attempts = 5
    
    for attempt in range(total_attempts):
        print(f"Reconnection test attempt {attempt+1}/{total_attempts}")
        
        try:
            # Connect to TCP adapter
            reader, writer = await asyncio.open_connection("127.0.0.1", 8300)
            
            # Send test data
            test_message = f"Test message {attempt+1}".encode()
            writer.write(test_message)
            await writer.drain()
            
            # Wait for response
            response = await asyncio.wait_for(reader.read(len(test_message)), timeout=2.0)
            success1 = response == test_message
            
            # Close connection
            writer.close()
            await writer.wait_closed()
            
            # Wait a bit before reconnecting
            await asyncio.sleep(0.5)
            
            # Reconnect
            reader, writer = await asyncio.open_connection("127.0.0.1", 8300)
            
            # Send another test message
            test_message2 = f"Reconnected message {attempt+1}".encode()
            writer.write(test_message2)
            await writer.drain()
            
            # Wait for response
            response = await asyncio.wait_for(reader.read(len(test_message2)), timeout=2.0)
            success2 = response == test_message2
            
            # Close connection
            writer.close()
            await writer.wait_closed()
            
            reconnection_results.append({
                "attempt": attempt + 1,
                "first_connection": success1,
                "reconnection": success2,
                "overall_success": success1 and success2
            })
            
            print(f"  Attempt {attempt+1}: {'Success' if success1 and success2 else 'Failed'}")
            
        except Exception as e:
            print(f"  Error in reconnection test attempt {attempt+1}: {str(e)}")
            reconnection_results.append({
                "attempt": attempt + 1,
                "first_connection": False,
                "reconnection": False,
                "overall_success": False,
                "error": str(e)
            })
    
    # Calculate success rate
    success_count = sum(1 for result in reconnection_results if result["overall_success"])
    success_rate = (success_count / total_attempts) * 100
    
    # Store results in metrics
    metrics["tcp_reconnection_resilience"] = {
        "attempts": total_attempts,
        "successful_reconnections": success_count,
        "success_rate": success_rate,
        "detailed_results": reconnection_results
    }
    
    print(f"Reconnection test completed: {success_count}/{total_attempts} successful ({success_rate:.2f}%)")
    
    return metrics["tcp_reconnection_resilience"]

@pytest.fixture(scope="session", autouse=True)
def save_metrics():
    yield
    with open("hybrid_metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)

if __name__ == "__main__":
    pytest.main(["-xvs", "test_hybrid_network.py"])