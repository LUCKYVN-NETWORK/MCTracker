import asyncio
import json
import time
import logging
import re
from aiohttp import web, WSMsgType
from mcstatus import JavaServer

# Configuration
HOST = '0.0.0.0'
PORT = 8080
PING_INTERVAL = 5  # Seconds between pings

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Tracker Service ---

class ServerTracker:
    def __init__(self, address, port, broadcast_callback):
        self.address = address
        self.port = int(port)
        self.broadcast = broadcast_callback
        self.is_running = True
        self.history = []
        self.current_status = "unknown"
        self.task = None
        
        # Uptime tracking statistics
        self.tracking_start_time = time.time()
        self.total_pings = 0
        self.successful_pings = 0

    async def start(self):
        self.task = asyncio.create_task(self.run_loop())
        logger.info(f"Started tracker for {self.address}:{self.port}")

    async def stop(self):
        self.is_running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info(f"Stopped tracker for {self.address}:{self.port}")

    async def run_loop(self):
        while self.is_running:
            loop_start = time.time()
            self.total_pings += 1
            
            # Default "Offline" state
            data = {
                "address": self.address,
                "port": self.port,
                "timestamp": loop_start,
                "online": False,
                "latency": 0,
                "players": {"online": 0, "max": 0},
                "motd": "",
                "favicon": None,
                "uptime": {
                    "duration_seconds": 0,
                    "percentage": 0.0
                }
            }

            try:
                # --- MCSTATUS MAGIC HAPPENS HERE ---
                # 1. Lookup (handles SRV records automatically)
                lookup_addr = f"{self.address}:{self.port}" if self.port != 25565 else self.address
                
                # Use async_lookup to avoid blocking the event loop during DNS resolution
                server = await JavaServer.async_lookup(lookup_addr)
                
                # 2. Status Only (Single Connection)
                # We do NOT use async_ping() separately to avoid triggering "soft blocks" 
                # or anti-DDoS shields that dislike rapid multiple connections.
                status = await server.async_status()
                
                self.successful_pings += 1
                
                # 3. Parse Data
                motd_plain = status.description
                if hasattr(motd_plain, 'to_plain'):
                    motd_plain = motd_plain.to_plain()
                
                # Clean MOTD: Strip whitespace and Minecraft color codes (§a, §1, etc.)
                clean_motd = str(motd_plain).strip()
                clean_motd = re.sub(r'§.', '', clean_motd)

                # 4. Latency Calculation
                # status.latency is the full Round Trip Time (RTT) for the handshake + JSON response.
                # We estimate one-way latency by dividing RTT by 2.
                rtt = status.latency
                one_way_est = rtt / 2

                # VERBOSE LOGGING: Success
                logger.info(f"[SUCCESS] {self.address}:{self.port} - RTT: {rtt:.2f}ms (Est 1-way: {one_way_est:.2f}ms) - Players: {status.players.online}/{status.players.max}")

                data.update({
                    "online": True,
                    "latency": round(one_way_est, 2),
                    "players": {
                        "online": status.players.online,
                        "max": status.players.max
                    },
                    "motd": clean_motd,
                    "favicon": getattr(status, 'favicon', None)
                })
                self.current_status = "online"

            except asyncio.TimeoutError:
                self.current_status = "timeout"
                logger.warning(f"[TIMEOUT] {self.address}:{self.port} timed out after {PING_INTERVAL}s")
            except Exception as e:
                self.current_status = "error"
                # Log detailed error for debugging the shield/socket issues
                logger.error(f"[ERROR] {self.address}:{self.port} failed: {e}")

            # Calculate uptime statistics
            tracking_duration = time.time() - self.tracking_start_time
            uptime_percentage = (self.successful_pings / self.total_pings) * 100 if self.total_pings > 0 else 0
            
            data["uptime"] = {
                "duration_seconds": int(tracking_duration),
                "percentage": round(uptime_percentage, 2)
            }

            # Keep history in memory
            # CHANGED: Increased limit to 24 hours (17280 points @ 5s interval)
            # This allows the frontend to show "Start -> Present" history
            self.history.append(data)
            if len(self.history) > 17280:
                self.history.pop(0)

            # Broadcast update to web clients
            await self.broadcast({
                "type": "update",
                "data": data
            })

            # Calculate sleep to maintain accurate interval
            elapsed = time.time() - loop_start
            sleep_time = max(0, PING_INTERVAL - elapsed)
            await asyncio.sleep(sleep_time)

# --- Web Server & Manager ---

class UptimeManager:
    def __init__(self):
        self.trackers = {} # Key: "ip:port", Value: ServerTracker instance
        self.websockets = set()

    async def register_tracker(self, address, port):
        key = f"{address}:{port}"
        if key in self.trackers:
            return False # Already exists
        
        tracker = ServerTracker(address, port, self.broadcast_to_clients)
        self.trackers[key] = tracker
        await tracker.start()
        return True

    async def remove_tracker(self, address, port):
        key = f"{address}:{port}"
        if key in self.trackers:
            await self.trackers[key].stop()
            del self.trackers[key]
            # Notify clients to remove from UI
            await self.broadcast_to_clients({
                "type": "remove",
                "key": key
            })
            return True
        return False

    async def broadcast_to_clients(self, message_dict):
        """Sends a JSON message to all connected WebSockets."""
        if not self.websockets:
            return
        
        message = json.dumps(message_dict)
        tasks = [ws.send_str(message) for ws in self.websockets if not ws.closed]
        if tasks:
            await asyncio.gather(*tasks)

    async def websocket_handler(self, request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        self.websockets.add(ws)
        logger.info("New WebSocket connection")

        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    
                    if data.get('action') == 'get_servers':
                        # Send all current trackers to the new client
                        for tracker in self.trackers.values():
                            # Send FULL history so client can build start->present graph
                            # We send it in one chunk if possible, or iterate
                            # For simplicity/performance, we send the whole history array in one packet
                            # or just the last state and let the client build up?
                            # The prompt implies persistent graph. 
                            # Let's send the *entire history* for the initial sync.
                            
                            # Note: Sending 17k items might be large, but for local usage it's fine.
                            # To keep it responsive, we just send the standard update loop 
                            # but iterate through history.
                            if tracker.history:
                                # Send batch of history? Or just let the client accumulate live?
                                # "Make the graph's window start -> present".
                                # If the backend has history, the client needs it.
                                # Let's send the whole history array in a special 'init' packet or just loop.
                                
                                # Optimization: Send the whole history in one go
                                await ws.send_json({
                                    "type": "history_dump",
                                    "data": tracker.history
                                })
                            else:
                                # Send "Initializing" state
                                await ws.send_json({
                                    "type": "update",
                                    "data": {
                                        "address": tracker.address,
                                        "port": tracker.port,
                                        "timestamp": time.time(),
                                        "online": False,
                                        "latency": 0,
                                        "players": {"online": 0, "max": 0},
                                        "motd": "Pinging...",
                                        "favicon": None,
                                        "uptime": {"duration_seconds": 0, "percentage": 0.0}
                                    }
                                })

                    elif data.get('action') == 'add':
                        address = data.get('address')
                        port = int(data.get('port', 25565))
                        await self.register_tracker(address, port)
                    
                    elif data.get('action') == 'delete':
                        address = data.get('address')
                        port = int(data.get('port', 25565))
                        await self.remove_tracker(address, port)

        finally:
            self.websockets.discard(ws)
            logger.info("WebSocket connection closed")
        return ws

    async def index_handler(self, request):
        return web.json_response({
            "status": "running",
            "service": "Minecraft Uptime Tracker Backend (mcstatus)",
            "endpoints": {
                "websocket": "/ws"
            }
        })

async def main():
    manager = UptimeManager()
    
    app = web.Application()
    app.router.add_get('/', manager.index_handler)
    app.router.add_get('/ws', manager.websocket_handler)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, HOST, PORT)
    
    print(f"Backend Server started at http://{HOST}:{PORT}")
    print("Press Ctrl+C to stop")
    
    await site.start()
    
    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        pass
    finally:
        await runner.cleanup()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass