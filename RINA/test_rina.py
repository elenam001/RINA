import pytest
import pytest_asyncio
import asyncio
import time
import statistics
import json
import matplotlib.pyplot as plt
from pathlib import Path
from rina.dif import DIF
from rina.ipcp import IPCP
from rina.application import Application
from rina.qos import QoS
from rina.flow import FlowAllocationFSM

# Enhanced metrics dictionary to store all test results
metrics = {
    "latency": {
        "values": [],
        "average": None,
        "min": None,
        "max": None,
        "median": None,
        "percentile_95": None
    },
    "jitter": {
        "values": [],
        "average": None
    },
    "throughput": {
        "values": [],
        "average": None,
        "by_size": {}
    },
    "packet_delivery_ratio": {
        "total_sent": 0,
        "total_received": 0,
        "ratio": None
    },
    "round_trip_time": {
        "values": [],
        "average": None
    },
    "scalability": {
        "concurrent_flows": [],
        "flow_setup_times": []
    },
    "flow":{
        "total_packets": None,
        "sent_packets": None,
        "received_packets": None,
        "ack_packets": None,
        "retransmitted_packets": None,
    }
}

@pytest_asyncio.fixture
async def setup_dif():
    dif = DIF(name="test_dif", layer=0, max_bandwidth=1000)
    ipcp1 = IPCP(ipcp_id="ipcp1", dif=dif)
    ipcp2 = IPCP(ipcp_id="ipcp2", dif=dif)
    await ipcp1.enroll(ipcp2)
    
    app1 = Application(name="app1", ipcp=ipcp1)
    app2 = Application(name="app2", ipcp=ipcp2)
    await app1.bind(5000)
    await app2.bind(5000)
    
    yield ipcp1, ipcp2, app1, app2
    
    # Cleanup all flows
    for flow_id in list(ipcp1.flows.keys()):
        await ipcp1.deallocate_flow(flow_id)
    for flow_id in list(ipcp2.flows.keys()):
        await ipcp2.deallocate_flow(flow_id)

# 1. Throughput Tests
@pytest.mark.asyncio
async def test_throughput_by_size(setup_dif):
    """Test throughput with varying packet sizes"""
    ipcp1, ipcp2, _, _ = setup_dif
    flow_id = await ipcp1.allocate_flow(ipcp2, port=5000)
    
    flow = ipcp1.flows[flow_id]
    flow.timeout = 0.5
    
    packet_sizes = [64, 256, 1024]  # Smaller sizes first
    chunks_per_size = 50  # Start with fewer chunks
    
    results = {}
    
    for size in packet_sizes:
        data = b"x" * size
        start_time = time.time()
        
        success_count = 0
        for i in range(chunks_per_size):
            try:
                #print(f"Sending chunk {i+1}/{chunks_per_size} of size {size}")
                await asyncio.wait_for(ipcp1.send_data(flow_id, data), timeout=0.5)
                success_count += 1
                if i % 10 == 0:
                    await asyncio.sleep(0.01)
            except asyncio.TimeoutError:
                print(f"Timeout sending chunk {i+1}")
                break
            except Exception as e:
                print(f"Error sending chunk {i+1}: {str(e)}")
                break
        
        duration = max(time.time() - start_time, 0.001)
        throughput = (size * success_count * 8) / (duration * 1000000)  # Mbps
        results[size] = throughput
        metrics["throughput"]["by_size"][size] = throughput
        metrics["throughput"]["values"].append(throughput)
        
        print(f"Throughput with {size} bytes packets: {throughput:.2f} Mbps ({success_count}/{chunks_per_size} chunks sent)")
        
        # Wait a bit between sizes
        await asyncio.sleep(0.5)
    
    metrics["throughput"]["average"] = statistics.mean(metrics["throughput"]["values"]) if metrics["throughput"]["values"] else 0
    return results

@pytest.mark.asyncio
async def test_throughput_sustained(setup_dif):
    """Test sustained throughput over a longer period"""
    ipcp1, ipcp2, _, _ = setup_dif
    flow_id = await ipcp1.allocate_flow(ipcp2, port=5000)
    
    chunk_size = 4096  # 4KB
    data = b"x" * chunk_size
    test_duration = 2.0  # seconds
    
    throughput_samples = []
    start_test = time.time()
    chunks_sent = 0
    
    while time.time() - start_test < test_duration:
        start_sample = time.time()
        sample_chunks = 0
        
        # Send for 0.2 seconds
        while time.time() - start_sample < 0.2:
            await ipcp1.send_data(flow_id, data)
            chunks_sent += 1
            sample_chunks += 1
        
        sample_duration = time.time() - start_sample
        sample_throughput = (sample_chunks * chunk_size * 8) / (sample_duration * 1000000)  # Mbps
        throughput_samples.append(sample_throughput)
    
    total_duration = time.time() - start_test
    overall_throughput = (chunks_sent * chunk_size * 8) / (total_duration * 1000000)  # Mbps
    
    print(f"Sustained throughput over {test_duration:.1f}s: {overall_throughput:.2f} Mbps")
    print(f"Variation: min={min(throughput_samples):.2f}, max={max(throughput_samples):.2f} Mbps")
    
    return overall_throughput, throughput_samples

# 2. Enhanced Latency and Jitter Tests
@pytest.mark.asyncio
async def test_latency_comprehensive(setup_dif):
    """Comprehensive latency test with statistical analysis"""
    ipcp1, ipcp2, _, _ = setup_dif
    flow_id = await ipcp1.allocate_flow(ipcp2, port=5000)
    
    samples = 200
    latencies = []
    timestamps = []
    last_latency = 0
    jitter_values = []
    
    for i in range(samples):
        start = time.time()
        await ipcp1.send_data(flow_id, b"ping")
        await asyncio.sleep(0.01)
        latency = (time.time() - start) * 1000  # ms
        latencies.append(latency)
        timestamps.append(start)
        
        # Calculate jitter (variation in latency) as per RFC 3550
        if i > 0:
            jitter_value = abs(latency - last_latency)
            jitter_values.append(jitter_value)
            
        last_latency = latency
    
    # Calculate statistics
    avg_latency = statistics.mean(latencies)
    min_latency = min(latencies)
    max_latency = max(latencies)
    median_latency = statistics.median(latencies)
    p95_latency = sorted(latencies)[int(0.95 * len(latencies))]
    
    avg_jitter = statistics.mean(jitter_values) if jitter_values else 0
    max_jitter = max(jitter_values) if jitter_values else 0
    
    # Store in enhanced metrics
    metrics["latency"]["values"] = latencies
    metrics["latency"]["average"] = avg_latency
    metrics["latency"]["min"] = min_latency
    metrics["latency"]["max"] = max_latency
    metrics["latency"]["median"] = median_latency
    metrics["latency"]["percentile_95"] = p95_latency
    
    metrics["jitter"]["values"] = jitter_values
    metrics["jitter"]["average"] = avg_jitter
    
    print(f"Latency (ms): avg={avg_latency:.2f}, min={min_latency:.2f}, max={max_latency:.2f}, median={median_latency:.2f}, p95={p95_latency:.2f}")
    print(f"Jitter (ms): avg={avg_jitter:.2f}, max={max_jitter:.2f}")
    
    return latencies, jitter_values

# 3. Packet Delivery Ratio Tests
@pytest.mark.asyncio
async def test_packet_delivery_ratio(setup_dif):
    """Test packet delivery ratio under various conditions"""
    ipcp1, ipcp2, app1, app2 = setup_dif
    flow_id = await ipcp1.allocate_flow(ipcp2, port=5000)
    
    packet_counts = [100, 500, 1000]
    results = {}
    
    for count in packet_counts:
        # Reset received counter
        ipcp2.flows[flow_id].stats["received_packets"] = 0
        
        sent = 0
        for _ in range(count):
            await ipcp1.send_data(flow_id, b"data")
            sent += 1
        
        # Allow time for packets to deliver
        await asyncio.sleep(0.2)
        
        received = ipcp2.flows[flow_id].stats["received_packets"]
        delivery_ratio = (received / sent) * 100
        results[count] = delivery_ratio
        
        metrics["packet_delivery_ratio"]["total_sent"] += sent
        metrics["packet_delivery_ratio"]["total_received"] += received
        
        print(f"Packet delivery ratio with {count} packets: {delivery_ratio:.2f}%")
    
    # Calculate overall ratio
    overall_ratio = (metrics["packet_delivery_ratio"]["total_received"] / 
                    metrics["packet_delivery_ratio"]["total_sent"]) * 100
    metrics["packet_delivery_ratio"]["ratio"] = overall_ratio
    
    return results

# 4. Round Trip Time Test
@pytest.mark.asyncio
async def test_round_trip_time(setup_dif):
    """Test round trip time for different packet sizes"""
    ipcp1, ipcp2, _, _ = setup_dif
    flow_id = await ipcp1.allocate_flow(ipcp2, port=5000)
    
    packet_sizes = [64, 256, 1024, 4096]
    samples_per_size = 50
    results = {}
    
    for size in packet_sizes:
        data = b"x" * size
        rtts = []
        
        for _ in range(samples_per_size):
            start = time.time()
            await ipcp1.send_data(flow_id, data)
            # In a real implementation, you would wait for a response here
            await asyncio.sleep(0.01)  # Simulating response wait
            rtt = (time.time() - start) * 1000  # ms
            rtts.append(rtt)
        
        avg_rtt = statistics.mean(rtts)
        results[size] = avg_rtt
        metrics["round_trip_time"]["values"].extend(rtts)
        
        print(f"Average RTT for {size} bytes: {avg_rtt:.2f} ms")
    
    metrics["round_trip_time"]["average"] = statistics.mean(metrics["round_trip_time"]["values"])
    
    return results
# 6. Scalability Tests
@pytest.mark.asyncio
async def test_concurrent_flows(setup_dif):
    """Test the system's ability to handle multiple concurrent flows"""
    ipcp1, ipcp2, _, _ = setup_dif
    
    flow_counts = [1, 5, 10, 20]
    results = {}
    
    for count in flow_counts:
        start_time = time.time()
        flows = []
        
        # Allocate multiple flows
        for i in range(count):
            qos = QoS(bandwidth=10)  # Small bandwidth for each flow
            flow_id = await ipcp1.allocate_flow(ipcp2, port=5000, qos=qos)
            if flow_id:
                flows.append(flow_id)
        
        setup_time = time.time() - start_time
        actual_count = len(flows)
        
        results[count] = {
            "allocated": actual_count,
            "setup_time": setup_time
        }
        
        metrics["scalability"]["concurrent_flows"].append(actual_count)
        metrics["scalability"]["flow_setup_times"].append(setup_time)
        
        print(f"Allocated {actual_count}/{count} flows in {setup_time:.4f} seconds")
        
        # Send some data on each flow
        data = b"test"
        for flow_id in flows:
            await ipcp1.send_data(flow_id, data)
        
        # Clean up
        for flow_id in flows:
            await ipcp1.deallocate_flow(flow_id)
    
    return results

@pytest.mark.asyncio
async def test_flow_control_reliability(setup_dif):
    """Test the reliability of flow control with packet acknowledgments"""
    ipcp1, ipcp2, app1, app2 = setup_dif
    flow_id = await ipcp1.allocate_flow(ipcp2, port=5000)
    
    # Get the flow object
    flow = ipcp1.flows[flow_id]
    
    # Set a smaller window size and timeout for testing
    flow.window_size = 4
    flow.timeout = 0.5
    
    # Send multiple packets in sequence
    total_packets = 20
    packet_size = 512
    
    # Track sent sequence numbers
    sent_seq_nums = []
    
    print("\n--- Testing flow control reliability ---")
    for i in range(total_packets):
        data = f"test-packet-{i}".encode() + b"x" * (packet_size - 15)
        seq_num = await flow.send_data(data)
        sent_seq_nums.append(seq_num)
        #print(f"Sent packet {i} with seq_num {seq_num}")
        
        # Insert small delay between sends to avoid overloading
        if i % flow.window_size == flow.window_size - 1:
            print(f"Window full, waiting for ACKs...")
            await asyncio.sleep(0.1)
    
    # Wait for any remaining packets to be processed
    await asyncio.sleep(1.0)
    
    # Check statistics
    print(f"Statistics: Sent={flow.stats['sent_packets']}, "
          f"Received={flow.stats['received_packets']}, "
          f"ACKs={flow.stats['ack_packets']}, "
          f"Retransmits={flow.stats['retransmitted_packets']}")
    
    # Assert all packets were acknowledged (none left in unacked_packets)
    async with flow.window_lock:
        assert len(flow.unacked_packets) == 0, "Some packets were not acknowledged"
    
    # Check that all packets were received by the other side
    assert flow.stats['sent_packets'] >= total_packets
    assert flow.stats['received_packets'] >= total_packets
    assert flow.stats['ack_packets'] > 0
    
    metrics["flow"].update({
        "total_packets": total_packets,
        "sent_packets": flow.stats['sent_packets'],
        "received_packets": flow.stats['received_packets'],
        "ack_packets": flow.stats['ack_packets'],
        "retransmitted_packets": flow.stats['retransmitted_packets']
    })

    return {
        "total_packets": total_packets,
        "sent_packets": flow.stats['sent_packets'],
        "received_packets": flow.stats['received_packets'],
        "ack_packets": flow.stats['ack_packets'],
        "retransmitted_packets": flow.stats['retransmitted_packets'],
    }

@pytest.fixture(scope="session", autouse=True)
def save_metrics():
    yield
    with open("metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)