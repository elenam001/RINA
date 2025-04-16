import asyncio
import pytest
from rina.dif import DIF
from rina.ipcp import IPCP
from rina.application import Application
from rina.qos import QoS
from rina.flow import FlowAllocationFSM

# Simple test to verify flow allocation is working
async def debug_flow_allocation():
    # Set up test environment
    dif = DIF(name="debug_dif", layer=0, max_bandwidth=1000)
    ipcp1 = IPCP(ipcp_id="debug_ipcp1", dif=dif)
    ipcp2 = IPCP(ipcp_id="debug_ipcp2", dif=dif)
    await ipcp1.enroll(ipcp2)
    
    app1 = Application(name="debug_app1", ipcp=ipcp1)
    app2 = Application(name="debug_app2", ipcp=ipcp2)
    await app1.bind(6000)  # Use different port than tests
    await app2.bind(6000)
    
    # Test basic flow allocation
    print("\n=== Testing basic flow allocation ===")
    flow_id = await ipcp1.allocate_flow(ipcp2, port=6000)
    print(f"Basic flow allocation result: {flow_id}")
    
    if flow_id:
        flow = ipcp1.flows[flow_id]
        print(f"Flow state: {flow.state_machine.state}")
        
        # Test data transfer
        print("\n=== Testing data transfer ===")
        await ipcp1.send_data(flow_id, b"hello")
        print(f"Flow stats: {flow.stats}")
        
        # Clean up
        await ipcp1.deallocate_flow(flow_id)
    
    # Test QoS flow allocation
    print("\n=== Testing QoS flow allocation ===")
    qos = QoS(bandwidth=50)
    flow_id = await ipcp1.allocate_flow(ipcp2, port=6000, qos=qos)
    print(f"QoS flow allocation result: {flow_id}")
    
    if flow_id:
        flow = ipcp1.flows[flow_id]
        print(f"Flow state: {flow.state_machine.state}")
        print(f"DIF allocated bandwidth: {dif.allocated_bandwidth}")
        
        # Clean up
        await ipcp1.deallocate_flow(flow_id)

if __name__ == "__main__":
    asyncio.run(debug_flow_allocation())