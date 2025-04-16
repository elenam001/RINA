import pytest_asyncio
import pytest
import asyncio
from rina.flow import FlowAllocationFSM
from rina.dif import DIF
from rina.ipcp import IPCP
from rina.application import Application
from rina.qos import QoS
import time
import json
from pathlib import Path

metrics = {
    "latency": [],
    "throughput": None,
    "packet_loss": None,
    "qos_compliance": {}
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

# Test functions
@pytest.mark.asyncio
async def test_connection_time(setup_dif):
    ipcp1, ipcp2, _, _ = setup_dif  # Unpack the tuple directly
    start_time = time.time()
    flow_id = await ipcp1.allocate_flow(ipcp2, port=5000)
    end_time = time.time()
    print(f"Connection Time: {end_time - start_time:.3f}s")

@pytest.mark.asyncio
async def test_latency_jitter(setup_dif):
    ipcp1, ipcp2, _, _ = setup_dif
    flow_id = await ipcp1.allocate_flow(ipcp2, port=5000)
    
    latencies = []
    for _ in range(100):
        start = time.time()
        await ipcp1.send_data(flow_id, b"ping")
        await asyncio.sleep(0.01)  # Allow time for echo
        latencies.append((time.time() - start) * 1000)
    
    avg_latency = sum(latencies) / len(latencies)
    jitter = max(latencies) - min(latencies)
    print(f"Latency: {avg_latency:.2f}ms | Jitter: {jitter:.2f}ms")
    metrics["latency"] = latencies
    metrics["jitter"] = jitter

@pytest.mark.asyncio
async def test_throughput(setup_dif):
    ipcp1, ipcp2, _, _ = setup_dif
    flow_id = await ipcp1.allocate_flow(ipcp2, port=5000)
    
    chunk_size = 1024  # 1KB
    data = b"x" * chunk_size
    total_chunks = 10240  # 10MB
    
    start_time = time.time()
    for _ in range(total_chunks):
        await ipcp1.send_data(flow_id, data)
    
    # Ensure minimum duration to prevent division by zero
    duration = max(time.time() - start_time, 0.001)
    throughput = (10 * 8) / duration
    print(f"Throughput: {throughput:.2f} Mbps")
    metrics["throughput"] = throughput

@pytest.mark.asyncio
async def test_qos_compliance(setup_dif):
    ipcp1, ipcp2, _, _ = setup_dif
    qos = QoS(latency=100, bandwidth=50)
    flow_id = await ipcp1.allocate_flow(ipcp2, port=5000, qos=qos)
    await asyncio.sleep(0.1)
    start_time = time.time()
    await ipcp1.send_data(flow_id, b"test")
    latency = (time.time() - start_time) * 1000
    assert latency <= qos.latency, f"Latency {latency:.2f}ms > {qos.latency}ms"
    assert ipcp1.dif.allocated_bandwidth >= qos.bandwidth, "Bandwidth not reserved"
    metrics["qos_compliance"] = {
        "target_latency": qos.latency,
        "actual_latency": latency,
        "target_bandwidth": qos.bandwidth,
        "allocated_bandwidth": ipcp1.dif.allocated_bandwidth
    }

@pytest.mark.asyncio
async def test_packet_loss(setup_dif):
    ipcp1, ipcp2, app1, app2 = setup_dif  # Need app2 to count receives
    flow_id = await ipcp1.allocate_flow(ipcp2, port=5000)
    
    sent = 0
    for _ in range(1000):
        await ipcp1.send_data(flow_id, b"data")
        sent += 1
    
    # Allow time for packets to deliver
    await asyncio.sleep(0.1)
    
    received = ipcp2.flows[flow_id].stats["received_packets"]
    loss_rate = (sent - received) / sent * 100
    print(f"Packet Loss Rate: {loss_rate:.2f}%")
    metrics["packet_loss"] = loss_rate
    
@pytest.mark.asyncio
async def test_flow_lifecycle(setup_dif):
    ipcp1, ipcp2, _, _ = setup_dif
    
    # Test allocation
    qos = QoS(bandwidth=50)
    flow_id = await ipcp1.allocate_flow(ipcp2, port=5000, qos=qos)
    flow = ipcp1.flows[flow_id]
    
    assert flow.state_machine.state == FlowAllocationFSM.State.ACTIVE
    assert ipcp1.dif.allocated_bandwidth == 50
    assert ipcp2.dif.allocated_bandwidth == 50
    
    # Test data transfer
    await ipcp1.send_data(flow_id, b"test")
    assert flow.stats["sent_packets"] == 1
    
    # Test deallocation
    await ipcp1.deallocate_flow(flow_id)
    assert flow_id not in ipcp1.flows
    assert ipcp1.dif.allocated_bandwidth == 0
    assert ipcp2.dif.allocated_bandwidth == 0
    
@pytest.mark.asyncio
async def test_qos_violation(setup_dif):
    ipcp1, ipcp2, _, _ = setup_dif

    qos = QoS(bandwidth=1500)
    flow_id = await ipcp1.allocate_flow(ipcp2, port=5000, qos=qos)
    
    if flow_id is not None:
        assert ipcp1.dif.allocated_bandwidth == 0
    else:
        assert True

@pytest.fixture(scope="session", autouse=True)
def save_metrics():
    yield
    with open("metrics.json", "w") as f:
        json.dump(metrics, f)
