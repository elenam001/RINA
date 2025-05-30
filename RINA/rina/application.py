import asyncio


class Application:
    def __init__(self, name, ipcp):
        self.name = name
        self.ipcp = ipcp
        self.port = None
        self.supports_multiple = False
        self.receive_buffer = []

    async def bind(self, port):
        self.port = port
        self.ipcp.port_map[port] = self
    
    async def on_data(self, data):
        """Handle received data with acknowledgments"""
        self.receive_buffer.append(data)
        if data == b"ping":
            #print("qui2")
            await self.send(b"pong")
            #print("qui3")
        elif data == b"data":
            pass
            
    async def send(self, data):
        """Send data using flow control"""
        if not self.ipcp.flows:
            raise ValueError("No flows available")
        
        flow_id = next(iter(self.ipcp.flows))
        await self.ipcp.send_data(flow_id, data)
    
    async def send_reliable(self, dest_app, data, qos=None, retries=3):
        """Send data with reliability guarantees"""
        flow_id = None
        for existing_flow_id, flow in self.ipcp.flows.items():
            if flow.dest_ipcp == dest_app.ipcp and flow.port == dest_app.port:
                flow_id = existing_flow_id
                break
        if flow_id is None:
            for _ in range(retries):
                flow_id = await self.ipcp.allocate_flow(dest_app.ipcp, dest_app.port, qos)
                if flow_id is not None:
                    break
                await asyncio.sleep(1)
        
        if flow_id is None:
            raise ConnectionError(f"Failed to establish flow after {retries} attempts")
        await self.ipcp.send_data(flow_id, data)
        return True