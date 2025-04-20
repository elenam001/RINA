import pytest
import pytest_asyncio
import asyncio
import time
import statistics
import json
from rina.dif import DIF
from rina.ipcp import IPCP
from rina.application import Application
from rina.qos import QoS
from rina.flow import FlowAllocationFSM

metrics = {
    "latency": {
        "values": [],
        "average": None,
        "min": None,
        "max": None,
        "median": None,
        "percentile_95": None,
        "percentile_99": None,
        "by_packet_size": {}
    },
    "jitter": {
        "values": [],
        "average": None,
        "max": None,
        "by_packet_size": {}
    },
    "throughput": {
        "values": [],
        "average": None,
        "by_size": {},
        "sustained": {
            "average": None,
            "samples": [],
            "min": None,
            "max": None
        }
    },
    "packet_delivery_ratio": {
        "total_sent": 0,
        "total_received": 0,
        "ratio": None,
        "by_packet_count": {},
        "by_network_load": {}
    },
    "round_trip_time": {
        "values": [],
        "average": None,
        "by_packet_size": {}
    },
    "scalability": {
        "concurrent_flows": [],
        "flow_setup_times": [],
        "max_concurrent_flows": None,
        "avg_flow_setup_time": None
    },
    "flow": {
        "total_packets": None,
        "sent_packets": None,
        "received_packets": None,
        "ack_packets": None,
        "retransmitted_packets": None,
        "window_efficiency": None,
        "packet_loss_rate": None
    },
    "error_recovery": {
        "recovery_time": [],
        "success_rate": None
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
    
    for flow_id in list(ipcp1.flows.keys()):
        await ipcp1.deallocate_flow(flow_id)
    for flow_id in list(ipcp2.flows.keys()):
        await ipcp2.deallocate_flow(flow_id)

@pytest.mark.asyncio
async def test_throughput_by_size(setup_dif):
    ipcp1, ipcp2, _, _ = setup_dif
    flow_id = await ipcp1.allocate_flow(ipcp2, port=5000)
    flow = ipcp1.flows[flow_id]
    flow.timeout = 0.5 #??
    packet_sizes = [64, 256, 512, 1024, 2048, 4096]
    chunks_per_size = 100
    results = {}
    for size in packet_sizes:
        data = b"x" * size
        start_time = time.time()
        success_count = 0
        for i in range(chunks_per_size):
            try:
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
        await asyncio.sleep(0.5)
    metrics["throughput"]["average"] = statistics.mean(metrics["throughput"]["values"]) if metrics["throughput"]["values"] else 0
    return results

@pytest.mark.asyncio
async def test_throughput_sustained(setup_dif):
    ipcp1, ipcp2, _, _ = setup_dif
    flow_id = await ipcp1.allocate_flow(ipcp2, port=5000)
    chunk_size = 4096
    data = b"x" * chunk_size
    test_duration = 5.0
    throughput_samples = []
    start_test = time.time()
    chunks_sent = 0
    while time.time() - start_test < test_duration:
        start_sample = time.time()
        sample_chunks = 0
        while time.time() - start_sample < 0.2:
            await ipcp1.send_data(flow_id, data)
            chunks_sent += 1
            sample_chunks += 1
        sample_duration = time.time() - start_sample
        sample_throughput = (sample_chunks * chunk_size * 8) / (sample_duration * 1000000)
        throughput_samples.append(sample_throughput)
    total_duration = time.time() - start_test
    overall_throughput = (chunks_sent * chunk_size * 8) / (total_duration * 1000000)
    metrics["throughput"]["sustained"]["average"] = overall_throughput
    metrics["throughput"]["sustained"]["samples"] = throughput_samples
    metrics["throughput"]["sustained"]["min"] = min(throughput_samples)
    metrics["throughput"]["sustained"]["max"] = max(throughput_samples)
    print(f"Sustained throughput over {test_duration:.1f}s: {overall_throughput:.2f} Mbps")
    print(f"Variation: min={min(throughput_samples):.2f}, max={max(throughput_samples):.2f} Mbps")
    return overall_throughput, throughput_samples

@pytest.mark.asyncio
async def test_throughput_with_congestion(setup_dif):
    ipcp1, ipcp2, _, _ = setup_dif
    flows = []
    for i in range(5):
        flow_id = await ipcp1.allocate_flow(ipcp2, port=5000)
        flows.append(flow_id)
    chunk_size = 1024
    data = b"x" * chunk_size
    test_duration = 3.0
    start_test = time.time()
    chunks_sent = [0] * len(flows)
    while time.time() - start_test < test_duration:
        for i, flow_id in enumerate(flows):
            try:
                await ipcp1.send_data(flow_id, data)
                chunks_sent[i] += 1
            except:
                pass
        await asyncio.sleep(0.001)
    total_duration = time.time() - start_test
    throughputs = [(sent * chunk_size * 8) / (total_duration * 1000000) for sent in chunks_sent]
    total_throughput = sum(throughputs)
    metrics["throughput"]["with_congestion"] = {
        "per_flow": throughputs,
        "total": total_throughput
    }
    print(f"Total throughput under congestion: {total_throughput:.2f} Mbps")
    for i, tp in enumerate(throughputs):
        print(f"  Flow {i}: {tp:.2f} Mbps")
    for flow_id in flows:
        await ipcp1.deallocate_flow(flow_id)
    return total_throughput, throughputs

@pytest.mark.asyncio
async def test_latency_comprehensive(setup_dif):
    ipcp1, ipcp2, _, _ = setup_dif
    packet_sizes = [64, 256, 1024, 4096]
    results_by_size = {}
    for size in packet_sizes:
        flow_id = await ipcp1.allocate_flow(ipcp2, port=5000)
        data = b"x" * size
        samples = 100
        latencies = []
        jitter_values = []
        last_latency = 0
        for i in range(samples):
            start = time.time()
            await ipcp1.send_data(flow_id, data)
            await asyncio.sleep(0.01)
            latency = (time.time() - start) * 1000  # ms
            latencies.append(latency)
            if i > 0:
                jitter_value = abs(latency - last_latency)
                jitter_values.append(jitter_value)
            last_latency = latency
        avg_latency = statistics.mean(latencies)
        min_latency = min(latencies)
        max_latency = max(latencies)
        median_latency = statistics.median(latencies)
        p95_latency = sorted(latencies)[int(0.95 * len(latencies))]
        p99_latency = sorted(latencies)[int(0.99 * len(latencies))]
        avg_jitter = statistics.mean(jitter_values) if jitter_values else 0
        max_jitter = max(jitter_values) if jitter_values else 0
        metrics["latency"]["values"].extend(latencies)
        metrics["latency"]["by_packet_size"][size] = {
            "average": avg_latency,
            "min": min_latency,
            "max": max_latency,
            "median": median_latency,
            "p95": p95_latency,
            "p99": p99_latency
        }
        metrics["jitter"]["values"].extend(jitter_values)
        metrics["jitter"]["by_packet_size"][size] = {
            "average": avg_jitter,
            "max": max_jitter
        }
        results_by_size[size] = {
            "latency": {
                "avg": avg_latency,
                "min": min_latency,
                "max": max_latency,
                "median": median_latency,
                "p95": p95_latency,
                "p99": p99_latency
            },
            "jitter": {
                "avg": avg_jitter,
                "max": max_jitter
            }
        }
        print(f"Size {size} bytes - Latency (ms): avg={avg_latency:.2f}, min={min_latency:.2f}, "
              f"max={max_latency:.2f}, median={median_latency:.2f}, p95={p95_latency:.2f}")
        print(f"Size {size} bytes - Jitter (ms): avg={avg_jitter:.2f}, max={max_jitter:.2f}")
        await ipcp1.deallocate_flow(flow_id)
    all_latencies = metrics["latency"]["values"]
    metrics["latency"]["average"] = statistics.mean(all_latencies)
    metrics["latency"]["min"] = min(all_latencies)
    metrics["latency"]["max"] = max(all_latencies)
    metrics["latency"]["median"] = statistics.median(all_latencies)
    metrics["latency"]["percentile_95"] = sorted(all_latencies)[int(0.95 * len(all_latencies))]
    metrics["latency"]["percentile_99"] = sorted(all_latencies)[int(0.99 * len(all_latencies))]
    all_jitter = metrics["jitter"]["values"]
    metrics["jitter"]["average"] = statistics.mean(all_jitter) if all_jitter else 0
    metrics["jitter"]["max"] = max(all_jitter) if all_jitter else 0
    return results_by_size

@pytest.mark.asyncio
async def test_packet_delivery_ratio(setup_dif):
    ipcp1, ipcp2, _, _ = setup_dif
    packet_counts = [100, 500, 1000, 2000]
    results = {}
    for count in packet_counts:
        flow_id = await ipcp1.allocate_flow(ipcp2, port=5000)
        ipcp2.flows[flow_id].stats["received_packets"] = 0
        sent = 0
        for _ in range(count):
            await ipcp1.send_data(flow_id, b"data")
            sent += 1
            if sent % 50 == 0:
                await asyncio.sleep(0.01)
        await asyncio.sleep(0.5)
        received = ipcp2.flows[flow_id].stats["received_packets"]
        delivery_ratio = (received / sent) * 100
        results[count] = delivery_ratio
        metrics["packet_delivery_ratio"]["total_sent"] += sent
        metrics["packet_delivery_ratio"]["total_received"] += received
        metrics["packet_delivery_ratio"]["by_packet_count"][count] = delivery_ratio
        print(f"Packet delivery ratio with {count} packets: {delivery_ratio:.2f}%")
        await ipcp1.deallocate_flow(flow_id)
    overall_ratio = (metrics["packet_delivery_ratio"]["total_received"] / 
                    metrics["packet_delivery_ratio"]["total_sent"]) * 100
    metrics["packet_delivery_ratio"]["ratio"] = overall_ratio
    return results

@pytest.mark.asyncio
async def test_packet_delivery_under_load(setup_dif):
    ipcp1, ipcp2, _, _ = setup_dif
    load_levels = [1, 3, 5, 7]
    results = {}
    for load in load_levels:
        flows = []
        for _ in range(load):
            flow_id = await ipcp1.allocate_flow(ipcp2, port=5000)
            flows.append(flow_id)
            ipcp2.flows[flow_id].stats["received_packets"] = 0
        packets_per_flow = 200
        total_sent = 0
        total_received = 0
        for flow_id in flows:
            for _ in range(packets_per_flow):
                await ipcp1.send_data(flow_id, b"data")
                total_sent += 1
        await asyncio.sleep(1.0)
        for flow_id in flows:
            received = ipcp2.flows[flow_id].stats["received_packets"]
            total_received += received
        delivery_ratio = (total_received / total_sent) * 100
        results[load] = delivery_ratio
        metrics["packet_delivery_ratio"]["by_network_load"][load] = delivery_ratio
        print(f"Packet delivery under load {load} flows: {delivery_ratio:.2f}%")
        for flow_id in flows:
            await ipcp1.deallocate_flow(flow_id)
    return results

@pytest.mark.asyncio
async def test_round_trip_time(setup_dif):
    ipcp1, ipcp2, _, _ = setup_dif
    packet_sizes = [64, 256, 1024, 4096]
    samples_per_size = 50
    results = {}
    for size in packet_sizes:
        data = b"x" * size
        rtts = []
        flow_id = await ipcp1.allocate_flow(ipcp2, port=5000)
        for _ in range(samples_per_size):
            start = time.time()
            await ipcp1.send_data(flow_id, data)
            await asyncio.sleep(0.01)
            rtt = (time.time() - start) * 1000
            rtts.append(rtt)
        avg_rtt = statistics.mean(rtts)
        min_rtt = min(rtts)
        max_rtt = max(rtts)
        median_rtt = statistics.median(rtts)
        results[size] = {
            "avg": avg_rtt,
            "min": min_rtt,
            "max": max_rtt,
            "median": median_rtt
        }
        metrics["round_trip_time"]["values"].extend(rtts)
        metrics["round_trip_time"]["by_packet_size"][size] = results[size]
        print(f"RTT for {size} bytes: avg={avg_rtt:.2f}, min={min_rtt:.2f}, max={max_rtt:.2f} ms")
        await ipcp1.deallocate_flow(flow_id)
    metrics["round_trip_time"]["average"] = statistics.mean(metrics["round_trip_time"]["values"])
    return results

@pytest.mark.asyncio
async def test_concurrent_flows(setup_dif):
    ipcp1, ipcp2, _, _ = setup_dif
    flow_counts = [1, 5, 10, 20, 50, 100]
    results = {}
    for count in flow_counts:
        start_time = time.time()
        flows = []
        for i in range(count):
            qos = QoS(bandwidth=10)
            try:
                flow_id = await asyncio.wait_for(
                    ipcp1.allocate_flow(ipcp2, port=5000, qos=qos),
                    timeout=5.0
                )
                if flow_id:
                    flows.append(flow_id)
            except asyncio.TimeoutError:
                print(f"Timeout allocating flow {i+1}")
                break
            except Exception as e:
                print(f"Error allocating flow {i+1}: {str(e)}")
                break
        setup_time = time.time() - start_time
        actual_count = len(flows)
        results[count] = {
            "allocated": actual_count,
            "setup_time": setup_time,
            "setup_time_per_flow": setup_time / max(actual_count, 1)
        }
        metrics["scalability"]["concurrent_flows"].append(actual_count)
        metrics["scalability"]["flow_setup_times"].append(setup_time)
        data = b"test"
        for flow_id in flows:
            await ipcp1.send_data(flow_id, data)
        for flow_id in flows:
            await ipcp1.deallocate_flow(flow_id)
        if actual_count < count:
            metrics["scalability"]["max_concurrent_flows"] = actual_count
            break
    if not metrics["scalability"]["max_concurrent_flows"]:
        metrics["scalability"]["max_concurrent_flows"] = max(metrics["scalability"]["concurrent_flows"])
    if metrics["scalability"]["flow_setup_times"]:
        metrics["scalability"]["avg_flow_setup_time"] = statistics.mean(metrics["scalability"]["flow_setup_times"])
    return results

@pytest.mark.asyncio
async def test_flow_control_reliability(setup_dif):
    ipcp1, ipcp2, _, _ = setup_dif
    flow_id = await ipcp1.allocate_flow(ipcp2, port=5000)
    flow = ipcp1.flows[flow_id]
    flow.window_size = 8
    flow.timeout = 0.5
    total_packets = 100
    packet_size = 512
    sent_seq_nums = []
    for i in range(total_packets):
        data = f"test-packet-{i}".encode() + b"x" * (packet_size - 15)
        seq_num = await flow.send_data(data)
        sent_seq_nums.append(seq_num)
        if i % flow.window_size == flow.window_size - 1:
            print(f"Window full at packet {i}, waiting for ACKs...")
            await asyncio.sleep(0.05)
    await asyncio.sleep(1.0)
    stats = {
        "sent_packets": flow.stats['sent_packets'],
        "received_packets": flow.stats['received_packets'],
        "ack_packets": flow.stats['ack_packets'],
        "retransmitted_packets": flow.stats['retransmitted_packets']
    }
    print(f"Statistics: Sent={stats['sent_packets']}, "
          f"Received={stats['received_packets']}, "
          f"ACKs={stats['ack_packets']}, "
          f"Retransmits={stats['retransmitted_packets']}")
    async with flow.window_lock:
        assert len(flow.unacked_packets) == 0, "Some packets were not acknowledged"
    window_efficiency = (stats['received_packets'] / stats['sent_packets']) * 100
    packet_loss_rate = (stats['retransmitted_packets'] / stats['sent_packets']) * 100 if stats['sent_packets'] > 0 else 0
    metrics["flow"].update({
        "total_packets": total_packets,
        "sent_packets": stats['sent_packets'],
        "received_packets": stats['received_packets'],
        "ack_packets": stats['ack_packets'],
        "retransmitted_packets": stats['retransmitted_packets'],
        "window_efficiency": window_efficiency,
        "packet_loss_rate": packet_loss_rate
    })
    return stats

@pytest.mark.asyncio
async def test_error_recovery(setup_dif):
    ipcp1, ipcp2, _, _ = setup_dif
    flow_id = await ipcp1.allocate_flow(ipcp2, port=5000)
    flow = ipcp1.flows[flow_id]
    flow.timeout = 0.2 
    flow.retries = 3
    test_packets = 20
    recovery_times = []
    success_count = 0
    for i in range(test_packets):
        data = f"recovery-test-{i}".encode() + b"x" * 100
        if i % 4 == 0 and i > 0:
            original_send_ack = flow.send_ack
            flow.send_ack = lambda seq_num: None
            start_time = time.time()
            try:
                await flow.send_data(data)
                success_count += 1
                recovery_time = time.time() - start_time
                recovery_times.append(recovery_time)
                print(f"Packet {i}: Recovered in {recovery_time:.4f}s")
            except Exception as e:
                print(f"Packet {i}: Failed to recover: {str(e)}")
            flow.send_ack = original_send_ack
        else:
            await flow.send_data(data)
            success_count += 1
    await asyncio.sleep(1.0)
    metrics["error_recovery"]["recovery_time"] = recovery_times
    metrics["error_recovery"]["success_rate"] = (success_count / test_packets) * 100
    print(f"Error recovery: {success_count}/{test_packets} packets delivered successfully")
    if recovery_times:
        avg_recovery = statistics.mean(recovery_times)
        print(f"Average recovery time: {avg_recovery:.4f}s")
        metrics["error_recovery"]["avg_recovery_time"] = avg_recovery
    return {
        "success_rate": metrics["error_recovery"]["success_rate"],
        "recovery_times": recovery_times
    }

@pytest.fixture(scope="session", autouse=True)
def save_metrics():
    yield
    with open("metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)

if __name__ == "__main__":
    pytest.main(["-xvs", "test_rina.py"])