# test_hybrid_network.py
import pytest
import pytest_asyncio
import asyncio
import time
import statistics
import json
import logging
from hybrid_network import HybridNetwork, TCPIPAdapter, RINATCPApplication
from rina.dif import DIF
from rina.ipcp import IPCP
from rina.application import Application
from rina.qos import QoS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Global metrics dictionary to store all test results
hybrid_metrics = {
    "rina": {
        "latency": {},
        "throughput": {},
        "packet_delivery_ratio": {},
        "round_trip_time": {},
        "flow_control": {},
        "error_recovery": {},
        "scalability": {}
    },
    "tcp": {
        "latency": {},
        "throughput": {},
        "packet_delivery_ratio": {},
        "round_trip_time": {},
        "flow_control": {},
        "error_recovery": {},
        "scalability": {}
    },
    "hybrid": {
        "latency": {},
        "throughput": {},
        "packet_delivery_ratio": {},
        "round_trip_time": {},
        "flow_control": {},
        "error_recovery": {},
        "scalability": {}
    }
}

@pytest_asyncio.fixture
async def setup_hybrid_network():
    print("Setting up hybrid network...")
    network = HybridNetwork()
    
    print("Creating RINA components...")
    rina_dif = await network.create_rina_dif("test_dif", layer=0, max_bandwidth=1000)
    ipcp1 = await network.create_rina_ipcp("ipcp1", "test_dif")
    ipcp2 = await network.create_rina_ipcp("ipcp2", "test_dif")
    await ipcp1.enroll(ipcp2)
    print("RINA components created.")
    
    print("Creating TCP adapters...")
    tcp_adapter1 = await network.create_tcp_adapter("adapter1", host='127.0.0.1', port=8001)
    tcp_adapter2 = await network.create_tcp_adapter("adapter2", host='127.0.0.1', port=8002)
    print("TCP adapters created.")
    
    print("Connecting TCP adapters to RINA...")
    await network.connect_adapter_to_rina("adapter1", "ipcp1", "test_dif")
    await network.connect_adapter_to_rina("adapter2", "ipcp2", "test_dif")
    print("TCP adapters connected to RINA.")
    
    print("Starting TCP adapters...")
    await network.start_tcp_adapters()
    print("TCP adapters started.")
    
    # Create applications
    rina_app1 = Application(name="rina_app1", ipcp=ipcp1)
    rina_app2 = Application(name="rina_app2", ipcp=ipcp2)
    await rina_app1.bind(5000)
    await rina_app2.bind(5000)
    
    hybrid_app1 = await network.create_hybrid_application("hybrid_app1", ipcp=ipcp1, adapter_name="adapter1")
    hybrid_app2 = await network.create_hybrid_application("hybrid_app2", ipcp=ipcp2, adapter_name="adapter2")
    await hybrid_app1.bind(5001)
    await hybrid_app2.bind(5001)
    
    yield network, ipcp1, ipcp2, rina_app1, rina_app2, hybrid_app1, hybrid_app2, tcp_adapter1, tcp_adapter2
    
    # Cleanup
    await network.shutdown()

async def tcp_client(host, port, data, iterations=1, delay=0.01):
    """Generic TCP client for testing"""
    total_rtt = 0
    rtts = []
    
    try:
        reader, writer = await asyncio.open_connection(host, port)
        for i in range(iterations):
            start_time = time.time()
            writer.write(data)
            await writer.drain()
            
            response = await reader.read(len(data))
            rtt = time.time() - start_time
            total_rtt += rtt
            rtts.append(rtt)
            
            if delay > 0 and i < iterations - 1:
                await asyncio.sleep(delay)
        
        writer.close()
        await writer.wait_closed()
        return {
            "success": True, 
            "avg_rtt": total_rtt / iterations, 
            "rtts": rtts
        }
    except Exception as e:
        logging.error(f"TCP client error: {str(e)}")
        return {"success": False, "error": str(e)}

@pytest.mark.asyncio
async def test_throughput_by_size_hybrid(setup_hybrid_network):
    """Test throughput with different packet sizes in hybrid network"""
    network, ipcp1, ipcp2, _, _, hybrid_app1, hybrid_app2, adapter1, adapter2 = setup_hybrid_network
    
    print("Setup completed, starting throughput test")

    # Test configurations
    packet_sizes = [64, 256, 512, 1024, 2048, 4096]
    chunks_per_size = 100
    
    logging.info("Starting RINA throughput test")

    # Test pure RINA throughput
    rina_results = {}
    for size in packet_sizes:
        flow_id = await ipcp1.allocate_flow(ipcp2, port=5000, qos=QoS(bandwidth=100))
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
                logging.warning(f"RINA: Timeout sending chunk {i+1}")
                break
            except Exception as e:
                logging.error(f"RINA: Error sending chunk {i+1}: {str(e)}")
                break
                
        duration = max(time.time() - start_time, 0.001)
        throughput = (size * success_count * 8) / (duration * 1000000)  # Mbps
        rina_results[size] = throughput
        hybrid_metrics["rina"]["throughput"][size] = throughput
        logging.info(f"RINA Throughput with {size} bytes packets: {throughput:.2f} Mbps")
        
        await ipcp1.deallocate_flow(flow_id)
        await asyncio.sleep(0.1)
    
    # Test TCP throughput
    tcp_results = {}
    for size in packet_sizes:
        data = b"x" * size
        start_time = time.time()
        success_count = 0
        
        clients = []
        for i in range(chunks_per_size):
            client = asyncio.create_task(tcp_client('127.0.0.1', 8002, data, iterations=1, delay=0))
            clients.append(client)
            
            if i % 10 == 0:
                await asyncio.sleep(0.01)
        
        results = await asyncio.gather(*clients, return_exceptions=True)
        success_count = sum(1 for r in results if isinstance(r, dict) and r.get("success", False))
        
        duration = max(time.time() - start_time, 0.001)
        throughput = (size * success_count * 8) / (duration * 1000000)  # Mbps
        tcp_results[size] = throughput
        hybrid_metrics["tcp"]["throughput"][size] = throughput
        logging.info(f"TCP Throughput with {size} bytes packets: {throughput:.2f} Mbps")
        
        await asyncio.sleep(0.1)
    
    # Test hybrid throughput (RINA to TCP)
    hybrid_results = {}
    for size in packet_sizes:
        # Establish TCP connection from hybrid app
        conn_id = await hybrid_app1.connect_to_tcp('127.0.0.1', 8002)
        if not conn_id:
            logging.error("Failed to establish TCP connection for hybrid test")
            continue
        
        data = b"x" * size
        start_time = time.time()
        success_count = 0
        
        for i in range(chunks_per_size):
            try:
                success = await hybrid_app1.send_to_tcp(conn_id, data)
                if success:
                    success_count += 1
                if i % 10 == 0:
                    await asyncio.sleep(0.01)
            except Exception as e:
                logging.error(f"Hybrid: Error sending chunk {i+1}: {str(e)}")
                break
                
        duration = max(time.time() - start_time, 0.001)
        throughput = (size * success_count * 8) / (duration * 1000000)  # Mbps
        hybrid_results[size] = throughput
        hybrid_metrics["hybrid"]["throughput"][size] = throughput
        logging.info(f"Hybrid Throughput with {size} bytes packets: {throughput:.2f} Mbps")
        
        await hybrid_app1.disconnect_tcp(conn_id)
        await asyncio.sleep(0.1)
    
    return {
        "rina": rina_results,
        "tcp": tcp_results,
        "hybrid": hybrid_results
    }

@pytest.fixture(scope="session", autouse=True)
def save_hybrid_metrics():
    """Save all metrics to a JSON file after tests complete"""
    yield
    with open("hybrid_metrics.json", "w") as f:
        json.dump(hybrid_metrics, f, indent=2)

if __name__ == "__main__":
    pytest.main(["-xvs", "test_hybrid_network.py"])