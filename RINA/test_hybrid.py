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
from rina.qos import QoS
import network_conditions
from hybrid_network import HybridNetwork, TCPIPAdapter, RINATCPApplication
import logging

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
    
    try:
        reader, writer = await asyncio.open_connection(*tcp_client)
        connection_setup_time = time.time() - start_time
        metrics["connection_setup_time_ms"] = connection_setup_time * 1000
    except Exception as e:
        logging.error(f"Failed to connect to TCP adapter: {str(e)}")
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
            response = await asyncio.wait_for(reader.read(packet_size), timeout=2.0)
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
async def test_hybrid_basic_connectivity(hybrid_net, realistic_network):
    """Test basic connectivity between TCP/IP and RINA networks"""
    dif = await hybrid_net.create_rina_dif("test_dif", layer=0)
    src_ipcp = await hybrid_net.create_rina_ipcp("src_ipcp", "test_dif")
    dst_ipcp = await hybrid_net.create_rina_ipcp("dst_ipcp", "test_dif")

    realistic_network.ipcps["src_ipcp"] = src_ipcp
    realistic_network.ipcps["dst_ipcp"] = dst_ipcp
    
    await src_ipcp.enroll(dst_ipcp)

    flow_id = await src_ipcp.allocate_flow(dst_ipcp, port=5000)
    
    adapter = await hybrid_net.create_tcp_adapter("test_adapter", host="127.0.0.1", port=8001)
    await hybrid_net.connect_adapter_to_rina("test_adapter", "src_ipcp", "test_dif")

    await adapter.start_server()
    
    hybrid_app = await hybrid_net.create_hybrid_application("test_app", dst_ipcp, adapter_name="test_adapter")
    await hybrid_app.bind(5000) 
    
    reader, writer = await asyncio.open_connection("127.0.0.1", 8001)
    
    test_message = b"Hello from TCP to RINA"
    writer.write(test_message)
    await writer.drain()
    
    try:
        response = await asyncio.wait_for(reader.read(1024), timeout=2.0)
        assert response == test_message, f"Response mismatch: {response} != {test_message}"
        logging.info("Successfully sent and received data through hybrid network")
    except (asyncio.TimeoutError, AssertionError) as e:
        pytest.fail(f"TCP to RINA communication failed: {str(e)}")
    finally:
        writer.close()
        await writer.wait_closed()
    
    metrics["hybrid_basic_connectivity"] = {"success": True}
    
    return True

@pytest.mark.asyncio
async def test_throughput_hybrid_network(hybrid_net, realistic_network):
    """Test throughput across different realistic network profiles in hybrid mode"""
    results = {}
    packet_sizes = [64, 512, 1024, 4096, 8192]
    test_duration = 5.0
    dif = await hybrid_net.create_rina_dif("test_dif", layer=0)
    
    for profile_name, profile in network_conditions.NETWORK_PROFILES.items():
        print(f"\nTesting throughput on {profile_name} hybrid network profile")
        results[profile_name] = {}
        
        for packet_size in packet_sizes:
            src_ipcp_id = f"src_ipcp_{profile_name}_{packet_size}"
            dst_ipcp_id = f"dst_ipcp_{profile_name}_{packet_size}"
            
            src_ipcp = await hybrid_net.create_rina_ipcp(src_ipcp_id, "test_dif")
            dst_ipcp = await hybrid_net.create_rina_ipcp(dst_ipcp_id, "test_dif")

            realistic_network.ipcps[src_ipcp_id] = src_ipcp
            realistic_network.ipcps[dst_ipcp_id] = dst_ipcp
            
            await src_ipcp.enroll(dst_ipcp)
            
            flow_id = await src_ipcp.allocate_flow(dst_ipcp, port=5000)
            adapter_name = f"adapter_{profile_name}_{packet_size}"
            tcp_port = 8000 + hash(adapter_name) % 1000  
            adapter = await hybrid_net.create_tcp_adapter(adapter_name, port=tcp_port)
            await hybrid_net.connect_adapter_to_rina(adapter_name, src_ipcp_id, "test_dif")
            
            await realistic_network.set_network_conditions(src_ipcp_id, dst_ipcp_id, profile)
            await hybrid_net.set_tcp_adapter_network_conditions(adapter_name, profile)
            
            app_src = await hybrid_net.create_hybrid_application(f"app_src_{profile_name}_{packet_size}", src_ipcp)
            app_dst = await hybrid_net.create_hybrid_application(f"app_dst_{profile_name}_{packet_size}", dst_ipcp)
            await app_dst.bind(5000)
            await adapter.start_server()
            
            try:
                reader, writer = await asyncio.open_connection("127.0.0.1", tcp_port)
            except Exception as e:
                logging.error(f"Failed to connect to TCP adapter: {str(e)}")
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
                        pass  
                    if profile["bandwidth_mbps"]:
                        packet_time = (packet_size * 8) / (profile["bandwidth_mbps"] * 1_000_000)
                        await asyncio.sleep(packet_time * 0.5)
                    else:
                        await asyncio.sleep(0.001) 
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
    
    metrics["throughput_hybrid_network"] = results
    return results

@pytest.mark.asyncio
async def test_latency_jitter_hybrid(hybrid_net, realistic_network):
    """Test latency and jitter across different network profiles in hybrid network"""
    results = {}
    packet_sizes = [64, 512, 1024, 4096]
    samples_per_size = 50
    dif = await hybrid_net.create_rina_dif("test_dif", layer=0)
    
    for profile_name, profile in network_conditions.NETWORK_PROFILES.items():
        if profile_name in ["congested"] and samples_per_size > 20:
            current_samples = 20
        else:
            current_samples = samples_per_size
            
        print(f"\nTesting latency/jitter on {profile_name} hybrid network profile ({current_samples} samples)")
        profile_results = {}
        
        for packet_size in packet_sizes:
            src_ipcp_id = f"src_ipcp_{profile_name}_{packet_size}"
            dst_ipcp_id = f"dst_ipcp_{profile_name}_{packet_size}"
            
            src_ipcp = await hybrid_net.create_rina_ipcp(src_ipcp_id, "test_dif")
            dst_ipcp = await hybrid_net.create_rina_ipcp(dst_ipcp_id, "test_dif")
            
            realistic_network.ipcps[src_ipcp_id] = src_ipcp
            realistic_network.ipcps[dst_ipcp_id] = dst_ipcp

            await src_ipcp.enroll(dst_ipcp)
            
            flow_id = await src_ipcp.allocate_flow(dst_ipcp, port=5000)

            adapter_name = f"adapter_{profile_name}_{packet_size}"
            tcp_port = 8000 + hash(adapter_name) % 1000 
            adapter = await hybrid_net.create_tcp_adapter(adapter_name, port=tcp_port)
            await hybrid_net.connect_adapter_to_rina(adapter_name, src_ipcp_id, "test_dif")
            await hybrid_net.set_tcp_adapter_network_conditions(adapter_name, profile)
            await realistic_network.set_network_conditions(src_ipcp_id, dst_ipcp_id, profile)

            app_dst = await hybrid_net.create_hybrid_application(f"app_dst_{profile_name}_{packet_size}", dst_ipcp)
            await app_dst.bind(5000)
            await adapter.start_server()
            test_metrics = await measure_hybrid_flow_metrics(
                adapter,
                ("127.0.0.1", tcp_port),
                packet_size=packet_size,
                packet_count=current_samples,
                inter_packet_delay=0.05 
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
    
    metrics["latency_jitter_hybrid"] = results
    return results

@pytest.mark.asyncio
async def test_packet_delivery_ratio_hybrid(hybrid_net, realistic_network):
    """Test PDR under different network profiles and loads in hybrid network"""
    results = {}
    
    packet_sizes = [64, 1024, 4096]
    packets_per_test = 500
    
    dif = await hybrid_net.create_rina_dif("test_dif", layer=0)
    
    for profile_name, profile in network_conditions.NETWORK_PROFILES.items():
        print(f"\nTesting packet delivery ratio on {profile_name} hybrid network profile")
        profile_results = {}
        
        for packet_size in packet_sizes:
            src_ipcp_id = f"src_ipcp_{profile_name}_{packet_size}"
            dst_ipcp_id = f"dst_ipcp_{profile_name}_{packet_size}"
            
            src_ipcp = await hybrid_net.create_rina_ipcp(src_ipcp_id, "test_dif")
            dst_ipcp = await hybrid_net.create_rina_ipcp(dst_ipcp_id, "test_dif")

            realistic_network.ipcps[src_ipcp_id] = src_ipcp
            realistic_network.ipcps[dst_ipcp_id] = dst_ipcp
            
            
            await src_ipcp.enroll(dst_ipcp)

            flow_id = await src_ipcp.allocate_flow(dst_ipcp, port=5000)
            
            adapter_name = f"adapter_{profile_name}_{packet_size}"
            tcp_port = 8000 + hash(adapter_name) % 1000  
            adapter = await hybrid_net.create_tcp_adapter(adapter_name, port=tcp_port)
            await hybrid_net.connect_adapter_to_rina(adapter_name, src_ipcp_id, "test_dif")
            await hybrid_net.set_tcp_adapter_network_conditions(adapter_name, profile)

            app_dst = await hybrid_net.create_hybrid_application(f"app_dst_{profile_name}_{packet_size}", dst_ipcp)
            await app_dst.bind(5000)
            
            await adapter.start_server()
            
            await realistic_network.set_network_conditions(src_ipcp_id, dst_ipcp_id, profile)
            
            test_metrics = await measure_hybrid_flow_metrics(
                adapter,
                ("127.0.0.1", tcp_port),
                packet_size=packet_size,
                packet_count=packets_per_test,
                inter_packet_delay=0.02 
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
    
    metrics["packet_delivery_ratio_hybrid"] = results
    return results

@pytest.mark.asyncio
async def test_concurrent_tcp_connections(hybrid_net, realistic_network):
    """Test scalability with concurrent TCP connections"""
    results = {}
    
    connection_counts = [1, 5, 10, 25]
    
    dif = await hybrid_net.create_rina_dif("test_dif", layer=0)
    src_ipcp = await hybrid_net.create_rina_ipcp("src_ipcp", "test_dif")
    dst_ipcp = await hybrid_net.create_rina_ipcp("dst_ipcp", "test_dif")

    realistic_network.ipcps["src_ipcp"] = src_ipcp
    realistic_network.ipcps["dst_ipcp"] = dst_ipcp
            
    
    await src_ipcp.enroll(dst_ipcp)

    flow_id = await src_ipcp.allocate_flow(dst_ipcp, port=5000)
    
    adapter = await hybrid_net.create_tcp_adapter("test_adapter", port=8100)
    await hybrid_net.connect_adapter_to_rina("test_adapter", "src_ipcp", "test_dif")
    app = await hybrid_net.create_hybrid_application("app_dst", dst_ipcp)
    await app.bind(5000)
    
    await adapter.start_server()
    
    for connection_count in connection_counts:
        print(f"\nTesting {connection_count} concurrent TCP connections")
        
        start_time = time.time()
        connections = []
        success_count = 0
        data_success = 0
        
        for i in range(connection_count):
            try:
                reader, writer = await asyncio.open_connection("127.0.0.1", 8100)
                connections.append((reader, writer))
                success_count += 1
            except Exception as e:
                logging.error(f"Failed to establish TCP connection {i+1}: {str(e)}")
        
        establishment_time = time.time() - start_time
        
        test_data = b"test_data"
        for i, (reader, writer) in enumerate(connections):
            try:
                writer.write(test_data)
                await writer.drain()
                
                response = await asyncio.wait_for(reader.read(len(test_data)), timeout=2.0)
                if response == test_data:
                    data_success += 1
            except Exception as e:
                logging.error(f"Error sending/receiving data through connection {i+1}: {str(e)}")
        
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
    
    metrics["concurrent_tcp_connections"] = results
    return results

@pytest.fixture(scope="session", autouse=True)
def save_metrics():
    yield
    with open("hybrid_metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)

if __name__ == "__main__":
    pytest.main(["-xvs", "test_hybrid_network.py"])