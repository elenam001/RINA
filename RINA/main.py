import time
from rina.ipcp import IPCP
from rina.dif import DIF
from rina.application import Application
import asyncio
import logging
from rina.qos import QoS


'''
Whitout recursion:

async def main():
    # Create a DIF and two IPCPs
    dif = DIF(name="example_dif", layer=0)
    ipcp1 = IPCP(ipcp_id="ipcp1", dif=dif)
    ipcp2 = IPCP(ipcp_id="ipcp2", dif=dif)
    dif.add_ipcp(ipcp1)
    dif.add_ipcp(ipcp2)

    # Enroll IPCPs
    await ipcp1.enroll(ipcp2)

    # Create applications
    app1 = Application(name="app1", ipcp=ipcp1)
    app2 = Application(name="app2", ipcp=ipcp2)
    await app1.bind(port=5000)
    await app2.bind(port=5000)

    # Send a message
    await app1.send(app2, b"Hello from app1!")

QoS
async def main():
    # Create DIF with limited bandwidth
    dif0 = DIF(name="dif0", layer=0, max_bandwidth=100)
    dif1 = DIF(name="dif1", layer=1, lower_dif=dif0)

    # Create IPCPs (same as before)
    ipcp0_a = IPCP(ipcp_id="ipcp0_a", dif=dif0)
    ipcp0_b = IPCP(ipcp_id="ipcp0_b", dif=dif0)
    ipcp1_a = IPCP(ipcp_id="ipcp1_a", dif=dif1, lower_ipcp=ipcp0_a)
    ipcp1_b = IPCP(ipcp_id="ipcp1_b", dif=dif1, lower_ipcp=ipcp0_b)

    # Enroll and bind applications (same as before)
    await ipcp0_a.enroll(ipcp0_b)
    await ipcp1_a.enroll(ipcp1_b)
    app1 = Application(name="app1", ipcp=ipcp1_a)
    app2 = Application(name="app2", ipcp=ipcp1_b)
    await app1.bind(5000)
    await app2.bind(5000)

    # Send data with QoS requirements
    qos = QoS(bandwidth=50, latency=50)
    await app1.send(app2, b"High-priority data", qos=qos)

asyncio.run(main())

'''
async def main():
    dif0 = DIF(name="dif0", layer=0)
    dif1 = DIF(name="dif1", layer=1, lower_dif=dif0)

    ipcp0_a = IPCP(ipcp_id="ipcp0_a", dif=dif0)
    ipcp0_b = IPCP(ipcp_id="ipcp0_b", dif=dif0)
    dif0.add_ipcp(ipcp0_a)
    dif0.add_ipcp(ipcp0_b)

    ipcp1_a = IPCP(ipcp_id="ipcp1_a", dif=dif1, lower_ipcp=ipcp0_a)
    ipcp1_b = IPCP(ipcp_id="ipcp1_b", dif=dif1, lower_ipcp=ipcp0_b)
    dif1.add_ipcp(ipcp1_a)
    dif1.add_ipcp(ipcp1_b)

    await ipcp0_a.enroll(ipcp0_b)
    await ipcp1_a.enroll(ipcp1_b)

    app1 = Application(name="app1", ipcp=ipcp1_a)
    app2 = Application(name="app2", ipcp=ipcp1_b)
    await app1.bind(5000)
    await app2.bind(5000)

    await app1.send(app2, b"Hello world!")

asyncio.run(main())
