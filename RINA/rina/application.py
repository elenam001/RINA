class Application:
    def __init__(self, name, ipcp):
        self.name = name
        self.ipcp = ipcp
        self.port = None
        self.supports_multiple = False

    async def bind(self, port):
        self.port = port
        self.ipcp.port_map[port] = self
    
    async def on_data(self, data):
        """Echo back data for latency tests"""
        if data == b"ping":
            await self.send(b"pong")
        if data == b"data":
            pass  # Just count reception
            
    async def send(self, data):
        """Send data using first available flow"""
        if not self.ipcp.flows:
            raise ValueError("No flows available")
        flow_id = next(iter(self.ipcp.flows))
        await self.ipcp.send_data(flow_id, data)
'''
    async def on_data(self, data):
        print(f"{self.name} received: {data.decode()}")
        # Count received packets
        self.ipcp.flows[list(self.ipcp.flows.keys())[0]].stats["received_packets"] += 1
        if data == b"ping":
            await self.ipcp.send_data(next(iter(self.ipcp.flows)), b"pong")
        if data == b"data":
            pass

    async def send(self, dest_app, data, qos=None, retries=3):
        """Send data with QoS and retry on failure."""
        for _ in range(retries):
            flow_id = await self.ipcp.allocate_flow(dest_app.ipcp, dest_app.port, qos)
            if flow_id is None:
                print(f"{self.name}: Flow rejected. Retrying...")
                await asyncio.sleep(1)  # Wait before retry
                continue
            
            await self.ipcp.send_data(flow_id, data)
            return
        
        print(f"{self.name}: Failed to send data after {retries} retries.")
'''