import pytest
import pytest_asyncio
import asyncio
import time
import statistics
import json
import random
from contextlib import AsyncExitStack
from rina.qos import QoS
from network_conditions import RealisticNetwork

@pytest_asyncio.fixture
async def network():
    """Create a clean network for each test"""
    network = RealisticNetwork()
    yield network
    await network.cleanup()

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
        "bandwidth_mbps": 1000,  # 1 Gbps
        "corruption_rate": 0.0001,
        "reordering_rate": 0.001
    },
    "wifi": {
        "latency_ms": 5,
        "jitter_ms": 3,
        "packet_loss_rate": 0.005,
        "bandwidth_mbps": 100,  # 100 Mbps
        "corruption_rate": 0.001,
        "reordering_rate": 0.002
    },
    "4g": {
        "latency_ms": 50,
        "jitter_ms": 15,
        "packet_loss_rate": 0.01,
        "bandwidth_mbps": 50,  # 50 Mbps
        "corruption_rate": 0.002,
        "reordering_rate": 0.005
    },
    "congested": {
        "latency_ms": 100,
        "jitter_ms": 40,
        "packet_loss_rate": 0.05,
        "bandwidth_mbps": 10,  # 10 Mbps
        "corruption_rate": 0.005,
        "reordering_rate": 0.01
    }
}


async def measure_flow_metrics(src_ipcp, dst_ipcp, packet_size, packet_count, 
                              inter_packet_delay=0.001, flow_qos=None):
    """Helper function to measure metrics for a flow"""
    start_time = time.time()
    
    # Create a flow
    flow_id = await src_ipcp.allocate_flow(dst_ipcp, port=5000, qos=flow_qos)
    flow_setup_time = time.time() - start_time
    
    metrics = {
        "flow_setup_time_ms": flow_setup_time * 1000,
        "packet_size": packet_size,
        "packet_count": packet_count,
        "latencies_ms": [],
        "rtts_ms": [],
        "jitter_ms": [],
        "sent": 0,
        "received": 0,
        "throughput_mbps": 0,
    }
    
    # Reset flow statistics
    src_flow = src_ipcp.flows[flow_id]
    dst_flow = dst_ipcp.flows[flow_id]
    dst_flow.stats["received_packets"] = 0
    
    # Send packets and measure
    data = b"x" * packet_size
    last_latency = 0
    
    send_start_time = time.time()
    for i in range(packet_count):
        packet_send_time = time.time()
        
        # Send the packet and capture sequence number
        await src_ipcp.send_data(flow_id, data)
        metrics["sent"] += 1
        
        # Small delay between packets
        if inter_packet_delay > 0:
            await asyncio.sleep(inter_packet_delay)
            
        # Calculate RTT
        rtt = (time.time() - packet_send_time) * 1000  # ms
        metrics["rtts_ms"].append(rtt)
        
        # Measure one-way latency (note: needs clock sync in real networks)
        latency = rtt / 2  # Approximation
        metrics["latencies_ms"].append(latency)
        
        # Calculate jitter only after first packet
        if i > 0:
            jitter = abs(latency - last_latency)
            metrics["jitter_ms"].append(jitter)
        last_latency = latency
    
    send_end_time = time.time()
    await asyncio.sleep(1.0)  # Wait for packets to arrive
    
    # Calculate metrics
    metrics["received"] = dst_flow.stats["received_packets"]
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
    await src_ipcp.deallocate_flow(flow_id)
    
    return metrics


@pytest.mark.asyncio
async def test_throughput_realistic_networks(network):
    """Test throughput across different realistic network profiles"""
    results = {}
    
    # Parameters
    packet_sizes = [64, 512, 1024, 4096, 8192]
    test_duration = 5.0  # seconds
    
    # Create network components
    await network.create_dif("test_dif")
    
    for profile_name, profile in NETWORK_PROFILES.items():
        print(f"\nTesting throughput on {profile_name} network profile")
        results[profile_name] = {}
        
        for packet_size in packet_sizes:
            # Create fresh IPCPs for each test
            src_ipcp_id = f"src_ipcp_{profile_name}_{packet_size}"
            dst_ipcp_id = f"dst_ipcp_{profile_name}_{packet_size}"
            
            src_ipcp = await network.create_ipcp(src_ipcp_id, "test_dif")
            dst_ipcp = await network.create_ipcp(dst_ipcp_id, "test_dif")
            
            await src_ipcp.enroll(dst_ipcp)
            
            await network.create_application(f"app_src_{profile_name}_{packet_size}", src_ipcp_id)
            await network.create_application(f"app_dst_{profile_name}_{packet_size}", dst_ipcp_id, port=5000)
            
            # Set network conditions
            await network.set_network_conditions(src_ipcp_id, dst_ipcp_id, profile)
            
            # Allocate a flow
            flow_id = await src_ipcp.allocate_flow(dst_ipcp, port=5000)
            
            # Send data continuously for the test duration
            data = b"x" * packet_size
            start_time = time.time()
            packets_sent = 0
            bytes_sent = 0
            
            print(f"  Sending {packet_size} byte packets for {test_duration}s...")
            while time.time() - start_time < test_duration:
                await src_ipcp.send_data(flow_id, data)
                packets_sent += 1
                bytes_sent += packet_size
                
                # Adjust sleep based on network profile to avoid overloading
                if profile["bandwidth_mbps"]:
                    # Calculate theoretical time to send based on bandwidth
                    packet_time = (packet_size * 8) / (profile["bandwidth_mbps"] * 1_000_000)
                    await asyncio.sleep(packet_time * 0.9)  # Sleep slightly less than theoretical time
                else:
                    await asyncio.sleep(0.0001)  # Minimal sleep
            
            # Wait for packets in flight
            await asyncio.sleep(max(profile["latency_ms"] / 1000 * 3, 0.5))
            
            # Deallocate flow
            await src_ipcp.deallocate_flow(flow_id)
            
            # Calculate throughput
            elapsed = time.time() - start_time
            throughput_mbps = (bytes_sent * 8) / (elapsed * 1_000_000)
            packets_per_second = packets_sent / elapsed
            
            # Store results
            results[profile_name][packet_size] = {
                "throughput_mbps": throughput_mbps,
                "packets_sent": packets_sent,
                "packets_per_second": packets_per_second,
                "bytes_sent": bytes_sent,
                "elapsed_seconds": elapsed
            }
            
            print(f"  Packet size: {packet_size} bytes - Throughput: {throughput_mbps:.2f} Mbps ({packets_per_second:.2f} packets/sec)")
    
    return results


@pytest.mark.asyncio
async def test_latency_jitter_realistic(network):
    """Test latency and jitter across different network profiles"""
    results = {}
    
    # Parameters
    packet_sizes = [64, 512, 1024, 4096]
    samples_per_size = 100
    
    # Create network components
    await network.create_dif("test_dif")
    
    for profile_name, profile in NETWORK_PROFILES.items():
        if profile_name in ["extreme", "satellite"] and samples_per_size > 50:
            # Reduce samples for high latency profiles
            current_samples = 50
        else:
            current_samples = samples_per_size
            
        print(f"\nTesting latency/jitter on {profile_name} network profile ({current_samples} samples)")
        profile_results = {}
        
        for packet_size in packet_sizes:
            # Create fresh IPCPs for each test
            src_ipcp_id = f"src_ipcp_{profile_name}_{packet_size}"
            dst_ipcp_id = f"dst_ipcp_{profile_name}_{packet_size}"
            
            src_ipcp = await network.create_ipcp(src_ipcp_id, "test_dif")
            dst_ipcp = await network.create_ipcp(dst_ipcp_id, "test_dif")
            
            await src_ipcp.enroll(dst_ipcp)
            
            await network.create_application(f"app_src_{profile_name}_{packet_size}", src_ipcp_id)
            await network.create_application(f"app_dst_{profile_name}_{packet_size}", dst_ipcp_id, port=5000)
            
            # Set network conditions
            await network.set_network_conditions(src_ipcp_id, dst_ipcp_id, profile)
            
            # Measure metrics
            metrics = await measure_flow_metrics(
                src_ipcp, dst_ipcp,
                packet_size=packet_size,
                packet_count=current_samples,
                inter_packet_delay=0.05  # Increased to reduce congestion in measurements
            )
            
            profile_results[packet_size] = {
                "avg_latency_ms": metrics["avg_latency_ms"],
                "min_latency_ms": metrics["min_latency_ms"],
                "max_latency_ms": metrics["max_latency_ms"],
                "avg_jitter_ms": metrics["avg_jitter_ms"],
                "max_jitter_ms": metrics["max_jitter_ms"],
                "avg_rtt_ms": metrics["avg_rtt_ms"]
            }
            
            print(f"  Packet size: {packet_size} bytes - "
                  f"Latency: {metrics['avg_latency_ms']:.2f}ms (min: {metrics['min_latency_ms']:.2f}, max: {metrics['max_latency_ms']:.2f}), "
                  f"Jitter: {metrics['avg_jitter_ms']:.2f}ms, "
                  f"RTT: {metrics['avg_rtt_ms']:.2f}ms")
        
        results[profile_name] = profile_results
    
    return results


@pytest.mark.asyncio
async def test_packet_delivery_ratio_realistic(network):
    """Test PDR under different network profiles and loads"""
    results = {}
    
    # Parameters
    packet_sizes = [64, 1024, 4096]
    packets_per_test = 500
    
    # Create network components
    await network.create_dif("test_dif")
    
    # Test different network profiles
    for profile_name, profile in NETWORK_PROFILES.items():
        print(f"\nTesting packet delivery ratio on {profile_name} network profile")
        profile_results = {}
        
        for packet_size in packet_sizes:
            # Create fresh IPCPs for each test
            src_ipcp_id = f"src_ipcp_{profile_name}_{packet_size}"
            dst_ipcp_id = f"dst_ipcp_{profile_name}_{packet_size}"
            
            src_ipcp = await network.create_ipcp(src_ipcp_id, "test_dif")
            dst_ipcp = await network.create_ipcp(dst_ipcp_id, "test_dif")
            
            await src_ipcp.enroll(dst_ipcp)
            
            await network.create_application(f"app_src_{profile_name}_{packet_size}", src_ipcp_id)
            await network.create_application(f"app_dst_{profile_name}_{packet_size}", dst_ipcp_id, port=5000)
            
            # Set network conditions
            await network.set_network_conditions(src_ipcp_id, dst_ipcp_id, profile)
            
            # Measure metrics
            metrics = await measure_flow_metrics(
                src_ipcp, dst_ipcp,
                packet_size=packet_size,
                packet_count=packets_per_test,
                inter_packet_delay=0.01  # Give packets time to arrive
            )
            
            profile_results[packet_size] = {
                "sent": metrics["sent"],
                "received": metrics["received"],
                "delivery_ratio": metrics["delivery_ratio"]
            }
            
            print(f"  Packet size: {packet_size} bytes - "
                  f"PDR: {metrics['delivery_ratio']:.2f}% ({metrics['received']}/{metrics['sent']} packets)")
        
        results[profile_name] = profile_results
    
    return results


@pytest.mark.asyncio
async def test_round_trip_time_realistic(network):
    """Test RTT under different network conditions"""
    results = {}
    
    # Parameters
    packet_sizes = [64, 512, 1024, 4096]
    samples_per_size = 50
    
    # Create network components
    await network.create_dif("test_dif")
    
    for profile_name, profile in NETWORK_PROFILES.items():
        if profile_name in ["extreme", "satellite"]:
            # Reduce samples for high latency profiles
            current_samples = 20
        else:
            current_samples = samples_per_size
            
        print(f"\nTesting RTT on {profile_name} network profile")
        profile_results = {}
        
        for packet_size in packet_sizes:
            # Create fresh IPCPs for each test
            src_ipcp_id = f"src_ipcp_{profile_name}_{packet_size}"
            dst_ipcp_id = f"dst_ipcp_{profile_name}_{packet_size}"
            
            src_ipcp = await network.create_ipcp(src_ipcp_id, "test_dif")
            dst_ipcp = await network.create_ipcp(dst_ipcp_id, "test_dif")
            
            await src_ipcp.enroll(dst_ipcp)
            
            await network.create_application(f"app_src_{profile_name}_{packet_size}", src_ipcp_id)
            await network.create_application(f"app_dst_{profile_name}_{packet_size}", dst_ipcp_id, port=5000)
            
            # Set network conditions
            await network.set_network_conditions(src_ipcp_id, dst_ipcp_id, profile)
            
            # Measure metrics with focus on RTT
            metrics = await measure_flow_metrics(
                src_ipcp, dst_ipcp,
                packet_size=packet_size,
                packet_count=current_samples,
                inter_packet_delay=0.05  # Give packets time to arrive
            )
            
            profile_results[packet_size] = {
                "avg_rtt_ms": metrics["avg_rtt_ms"],
                "min_rtt_ms": metrics["min_rtt_ms"],
                "max_rtt_ms": metrics["max_rtt_ms"]
            }
            
            print(f"  Packet size: {packet_size} bytes - "
                  f"RTT: avg={metrics['avg_rtt_ms']:.2f}ms, min={metrics['min_rtt_ms']:.2f}ms, max={metrics['max_rtt_ms']:.2f}ms")
        
        results[profile_name] = profile_results
    
    return results

@pytest.mark.asyncio
async def test_scalability_concurrent_flows(network):
    """Test scalability with concurrent flows"""
    results = {}
    
    # Parameters
    flow_counts = [1, 5, 10, 25, 50, 100, 250, 500]
    test_profiles = ["perfect", "lan", "wifi", "4g"]  # Limited set of profiles for practicality
    
    # Create network components
    await network.create_dif("test_dif")
    
    for profile_name in test_profiles:
        profile = NETWORK_PROFILES[profile_name]
        print(f"\nTesting scalability on {profile_name} network profile")
        profile_results = {}
        
        # Create base IPCPs
        src_ipcp_id = f"src_ipcp_scale_{profile_name}"
        dst_ipcp_id = f"dst_ipcp_scale_{profile_name}"
        
        src_ipcp = await network.create_ipcp(src_ipcp_id, "test_dif")
        dst_ipcp = await network.create_ipcp(dst_ipcp_id, "test_dif")
        
        await src_ipcp.enroll(dst_ipcp)
        
        await network.create_application(f"app_src_scale_{profile_name}", src_ipcp_id)
        await network.create_application(f"app_dst_scale_{profile_name}", dst_ipcp_id, port=5000)
        
        # Set network conditions
        await network.set_network_conditions(src_ipcp_id, dst_ipcp_id, profile)
        
        # Test different flow counts
        for flow_count in flow_counts:
            start_time = time.time()
            flows = []
            success_count = 0
            
            print(f"  Attempting to allocate {flow_count} concurrent flows...")
            
            # Try to allocate flows
            for i in range(flow_count):
                try:
                    flow_id = await asyncio.wait_for(
                        src_ipcp.allocate_flow(dst_ipcp, port=5000, qos=QoS(bandwidth=10)),
                        timeout=10.0
                    )
                    if flow_id:
                        flows.append(flow_id)
                        success_count += 1
                except asyncio.TimeoutError:
                    print(f"    Timeout allocating flow {i+1}")
                    break
                except Exception as e:
                    print(f"    Error allocating flow {i+1}: {str(e)}")
                    break
            
            allocation_time = time.time() - start_time
            actual_count = len(flows)
            
            # Test sending data through all flows
            test_data = b"test_data"
            send_success = 0
            
            for flow_id in flows:
                try:
                    await src_ipcp.send_data(flow_id, test_data)
                    send_success += 1
                except Exception as e:
                    print(f"    Error sending data on flow: {str(e)}")
            
            # Clean up flows
            for flow_id in flows:
                try:
                    await src_ipcp.deallocate_flow(flow_id)
                except Exception:
                    pass
            
            profile_results[flow_count] = {
                "target_flows": flow_count,
                "successful_flows": actual_count,
                "allocation_time_seconds": allocation_time,
                "allocation_time_per_flow_ms": (allocation_time * 1000) / max(actual_count, 1),
                "data_send_success_rate": (send_success / max(actual_count, 1)) * 100
            }
            
            print(f"    Results: {actual_count}/{flow_count} flows allocated in {allocation_time:.2f}s "
                  f"({profile_results[flow_count]['allocation_time_per_flow_ms']:.2f}ms per flow)")
            print(f"    Data send success rate: {profile_results[flow_count]['data_send_success_rate']:.2f}%")
            
            # Break if we're already failing to allocate all flows
            if actual_count < flow_count and flow_count > 10:  # Skip small differences but catch major failures
                print(f"    Failed to allocate all flows, skipping higher flow counts")
                break
        
        results[profile_name] = profile_results
    
    return results

metrics = {}

@pytest.fixture(scope="session", autouse=True)
def save_metrics():
    yield
    with open("metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)

if __name__ == "__main__":
    pytest.main(["-xvs", "test_rina.py"])