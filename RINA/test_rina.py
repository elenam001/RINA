import pytest
import pytest_asyncio
import asyncio
import time
import statistics
import json
import random
from contextlib import AsyncExitStack
from rina.qos import QoS
import network_conditions

@pytest_asyncio.fixture
async def network():
    """Create a clean network for each test"""
    network = network_conditions.RealisticNetwork()
    yield network
    await network.cleanup()

metrics = {}

async def measure_flow_metrics(src_ipcp, dst_ipcp, packet_size, packet_count, 
                              inter_packet_delay=0.001, flow_qos=None):
    """Helper function to measure metrics for a flow"""
    start_time = time.time()
    
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
    
    # Create a tracking dictionary for packet send times and delivery times
    packet_tracking = {}
    ack_received_events = {}
    
    # Set up a callback to track packet reception at destination
    original_receive_data = dst_flow.receive_data
    
    async def receive_data_hook(packet):
        if not isinstance(packet, dict):
            await original_receive_data(packet)
            return
            
        if not packet.get("is_ack", False):
            # This is a data packet arriving at destination
            seq_num = packet.get("seq_num")
            if seq_num is not None and seq_num in packet_tracking:
                # Record arrival time for latency calculation
                packet_tracking[seq_num]["arrival_time"] = time.time()
        else:
            # This is an ACK packet arriving back at source
            ack_seq = packet.get("ack_seq_num")
            if ack_seq is not None and ack_seq in packet_tracking:
                # Record ACK receipt time for RTT calculation
                packet_tracking[ack_seq]["ack_time"] = time.time()
                # Signal that ACK is received
                if ack_seq in ack_received_events:
                    ack_received_events[ack_seq].set()
        
        await original_receive_data(packet)
    
    # Replace the receive_data method with our hook
    dst_flow.receive_data = receive_data_hook
    
    # Send packets and measure
    data = b"x" * packet_size
    last_latency = 0
    
    send_start_time = time.time()
    for i in range(packet_count):
        seq_num = src_flow.sequence_gen.next()
        
        # Create tracking entry and event for this packet
        packet_tracking[seq_num] = {"send_time": time.time()}
        ack_received_events[seq_num] = asyncio.Event()
        
        # Send the packet
        await src_ipcp.send_data(flow_id, data)
        metrics["sent"] += 1
        
        # Wait for ACK with timeout
        try:
            await asyncio.wait_for(ack_received_events[seq_num].wait(), timeout=2.0)
            
            # Calculate RTT from send time to ACK receipt
            if "ack_time" in packet_tracking[seq_num]:
                rtt = (packet_tracking[seq_num]["ack_time"] - packet_tracking[seq_num]["send_time"]) * 1000  # ms
                metrics["rtts_ms"].append(rtt)
            
            # Calculate one-way latency if we have arrival time
            if "arrival_time" in packet_tracking[seq_num]:
                latency = (packet_tracking[seq_num]["arrival_time"] - packet_tracking[seq_num]["send_time"]) * 1000  # ms
                metrics["latencies_ms"].append(latency)
                
                # Calculate jitter only after first packet
                if i > 0:
                    jitter = abs(latency - last_latency)
                    metrics["jitter_ms"].append(jitter)
                last_latency = latency
        except asyncio.TimeoutError:
            # Packet or ACK was lost
            pass
            
        # Small delay between packets
        if inter_packet_delay > 0:
            await asyncio.sleep(inter_packet_delay)
    
    send_end_time = time.time()
    await asyncio.sleep(1.0)  # Wait for packets to arrive
    
    # Restore original receive_data method
    dst_flow.receive_data = original_receive_data
    
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
    
    for profile_name, profile in network_conditions.NETWORK_PROFILES.items():
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
    
    # Store results in the global metrics dictionary
    metrics["throughput_realistic_networks"] = results
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
    
    for profile_name, profile in network_conditions.NETWORK_PROFILES.items():
        if profile_name in ["congested"] and samples_per_size > 50:
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
            test_metrics = await measure_flow_metrics(
                src_ipcp, dst_ipcp,
                packet_size=packet_size,
                packet_count=current_samples,
                inter_packet_delay=0.05  # Increased to reduce congestion in measurements
            )
            
            profile_results[packet_size] = {
                "avg_latency_ms": test_metrics["avg_latency_ms"],
                "min_latency_ms": test_metrics["min_latency_ms"],
                "max_latency_ms": test_metrics["max_latency_ms"],
                "avg_jitter_ms": test_metrics["avg_jitter_ms"],
                "max_jitter_ms": test_metrics["max_jitter_ms"],
                "avg_rtt_ms": test_metrics["avg_rtt_ms"]
            }
            
            print(f"  Packet size: {packet_size} bytes - "
                  f"Latency: {test_metrics['avg_latency_ms']:.2f}ms (min: {test_metrics['min_latency_ms']:.2f}, max: {test_metrics['max_latency_ms']:.2f}), "
                  f"Jitter: {test_metrics['avg_jitter_ms']:.2f}ms, "
                  f"RTT: {test_metrics['avg_rtt_ms']:.2f}ms")
        
        results[profile_name] = profile_results
    
    # Store results in the global metrics dictionary
    metrics["latency_jitter_realistic"] = results
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
    for profile_name, profile in network_conditions.NETWORK_PROFILES.items():
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
            test_metrics = await measure_flow_metrics(
                src_ipcp, dst_ipcp,
                packet_size=packet_size,
                packet_count=packets_per_test,
                inter_packet_delay=0.01  # Give packets time to arrive
            )
            
            profile_results[packet_size] = {
                "sent": test_metrics["sent"],
                "received": test_metrics["received"],
                "delivery_ratio": test_metrics["delivery_ratio"]
            }
            
            print(f"  Packet size: {packet_size} bytes - "
                  f"PDR: {test_metrics['delivery_ratio']:.2f}% ({test_metrics['received']}/{test_metrics['sent']} packets)")
        
        results[profile_name] = profile_results
    
    # Store results in the global metrics dictionary
    metrics["packet_delivery_ratio_realistic"] = results
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
    
    for profile_name, profile in network_conditions.NETWORK_PROFILES.items():
        if profile_name in ["congested"]:
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
            test_metrics = await measure_flow_metrics(
                src_ipcp, dst_ipcp,
                packet_size=packet_size,
                packet_count=current_samples,
                inter_packet_delay=0.05  # Give packets time to arrive
            )
            
            profile_results[packet_size] = {
                "avg_rtt_ms": test_metrics["avg_rtt_ms"],
                "min_rtt_ms": test_metrics["min_rtt_ms"],
                "max_rtt_ms": test_metrics["max_rtt_ms"]
            }
            
            print(f"  Packet size: {packet_size} bytes - "
                  f"RTT: avg={test_metrics['avg_rtt_ms']:.2f}ms, min={test_metrics['min_rtt_ms']:.2f}ms, max={test_metrics['max_rtt_ms']:.2f}ms")
        
        results[profile_name] = profile_results
    
    # Store results in the global metrics dictionary
    metrics["round_trip_time_realistic"] = results
    return results


@pytest.mark.asyncio
async def test_scalability_concurrent_flows(network):
    """Test scalability with concurrent flows"""
    results = {}
    
    # Parameters - reduce max flow count to something manageable
    flow_counts = [1, 5, 10, 25, 50]  # Reduced from [1, 5, 10, 25, 50, 100, 250, 500]
    test_profiles = ["perfect", "lan", "wifi"]  # Limited set of profiles
    
    # Create network components with higher bandwidth capacity
    await network.create_dif("test_dif", max_bandwidth=1000)  # 1000 Mbps (1 Gbps) total capacity
    
    for profile_name in test_profiles:
        profile = network_conditions.NETWORK_PROFILES[profile_name]
        print(f"\nTesting scalability on {profile_name} network profile")
        profile_results = {}
        
        # Create base IPCPs
        src_ipcp_id = f"src_ipcp_scale_{profile_name}"
        dst_ipcp_id = f"dst_ipcp_scale_{profile_name}"
        
        src_ipcp = await network.create_ipcp(src_ipcp_id, "test_dif")
        dst_ipcp = await network.create_ipcp(dst_ipcp_id, "test_dif")
        
        await src_ipcp.enroll(dst_ipcp)
        
        src_app = await network.create_application(f"app_src_scale_{profile_name}", src_ipcp_id)
        dst_app = await network.create_application(f"app_dst_scale_{profile_name}", dst_ipcp_id, port=5000)
        
        # Set network conditions
        await network.set_network_conditions(src_ipcp_id, dst_ipcp_id, profile)
        
        # Test different flow counts
        for flow_count in flow_counts:
            # Use less bandwidth per flow for higher counts
            bandwidth_per_flow = max(1, min(10, 100 // flow_count))  # Adaptive bandwidth
            
            start_time = time.time()
            flows = []
            success_count = 0
            
            print(f"  Attempting to allocate {flow_count} concurrent flows (with {bandwidth_per_flow} Mbps each)...")
            
            # Try to allocate flows
            for i in range(flow_count):
                try:
                    flow_id = await asyncio.wait_for(
                        src_ipcp.allocate_flow(dst_ipcp, port=5000, qos=QoS(bandwidth=bandwidth_per_flow)),
                        timeout=3.0  # Reduce timeout to speed up the test
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
            
            # Test sending data through all flows - with retries for robustness
            test_data = b"test_data"
            send_success = 0
            
            for flow_id in flows:
                retries = 3
                while retries > 0:
                    try:
                        await src_ipcp.send_data(flow_id, test_data)
                        send_success += 1
                        break
                    except Exception as e:
                        print(f"    Error sending data on flow (retry {4-retries}): {str(e)}")
                        retries -= 1
                        # Small delay before retry
                        await asyncio.sleep(0.1)
            
            # Allow time for packets in flight before deallocation
            await asyncio.sleep(max(0.5, profile.get("latency_ms", 0) / 500))
            
            # Clean up flows with careful error handling
            for flow_id in flows:
                try:
                    await asyncio.wait_for(src_ipcp.deallocate_flow(flow_id), timeout=2.0)
                except (asyncio.TimeoutError, Exception) as e:
                    print(f"    Error deallocating flow {flow_id}: {str(e)}")
            
            profile_results[flow_count] = {
                "target_flows": flow_count,
                "successful_flows": actual_count,
                "allocation_time_seconds": allocation_time,
                "allocation_time_per_flow_ms": (allocation_time * 1000) / max(actual_count, 1),
                "data_send_success_rate": (send_success / max(actual_count, 1)) * 100,
                "bandwidth_per_flow_mbps": bandwidth_per_flow
            }
            
            print(f"Results: {actual_count}/{flow_count} flows allocated in {allocation_time:.2f}s "
                  f"({profile_results[flow_count]['allocation_time_per_flow_ms']:.2f}ms per flow)")
            print(f"Data send success rate: {profile_results[flow_count]['data_send_success_rate']:.2f}%")
            
            # Wait a bit between tests to allow resources to fully clean up
            await asyncio.sleep(1.0)
            
            # Break if we're already failing to allocate all flows
            if actual_count < flow_count * 0.8:  # Allow for some failures (20%)
                print(f"Failed to allocate most flows, skipping higher flow counts")
                break
        
        results[profile_name] = profile_results
    
    # Store results in global metrics
    metrics["scalability_concurrent_flows"] = results
    
    return results


@pytest.fixture(scope="session", autouse=True)
def save_metrics():
    yield
    with open("rina_metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)

if __name__ == "__main__":
    pytest.main(["-xvs", "test_rina.py"])