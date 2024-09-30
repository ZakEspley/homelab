import asyncio
from dbus_next.aio import MessageBus
from dbus_next import MessageType
from dbus_next.constants import BusType
import subprocess
import datetime

# Replace with your controller's MAC address in lowercase and underscores
CONTROLLER_MAC = '44_16_22_fa_cf_25'  # Convert AA:BB:CC:DD:EE:FF to aa_bb_cc_dd_ee_ff

# Replace with your program's command and arguments
PROGRAM_CMD = ['moonlight-qt']

# Time in seconds to wait before shutting down the program after disconnection
DISCONNECT_TIMEOUT = 300  # 5 minutes

class ControllerMonitor:
    def __init__(self):
        self.program_process = None
        self.program_running = False
        self.disconnection_time = None

    async def start(self):
        bus = await MessageBus(bus_type=BusType.SYSTEM).connect()
        introspection = await bus.introspect('org.bluez', '/org/bluez')
        obj = bus.get_proxy_object('org.bluez', '/org/bluez', introspection)
        mngr = obj.get_interface('org.freedesktop.DBus.ObjectManager')
        objects = await mngr.GetManagedObjects()

        # Subscribe to PropertiesChanged signals
        bus.add_message_handler(self.handle_signal)

        # Add match rules
        await bus.call(
            message=bus.introspect_remote_signal('org.bluez', '/org/bluez', 'org.freedesktop.DBus.Properties', 'PropertiesChanged').to_match_rule().message
        )

        # Initial check
        path = self.get_device_path(objects)
        if path:
            props_iface = 'org.freedesktop.DBus.Properties'
            introspection = await bus.introspect('org.bluez', path)
            device_obj = bus.get_proxy_object('org.bluez', path, introspection)
            properties = device_obj.get_interface(props_iface)
            props = await properties.GetAll('org.bluez.Device1')
            connected = props.get('Connected', False)
            if connected:
                self.start_program()

        # Keep the event loop running
        while True:
            await asyncio.sleep(1)
            if self.disconnection_time:
                elapsed = datetime.datetime.now() - self.disconnection_time
                if elapsed.total_seconds() >= DISCONNECT_TIMEOUT:
                    self.stop_program()
                    self.disconnection_time = None

    def get_device_path(self, objects):
        for path, interfaces in objects.items():
            if 'org.bluez.Device1' in interfaces:
                if interfaces['org.bluez.Device1'].get('Address', '').lower().replace(':', '_') == CONTROLLER_MAC:
                    return path
        return None

    def handle_signal(self, message):
        if message.message_type != MessageType.SIGNAL:
            return

        if message.interface != 'org.freedesktop.DBus.Properties' or message.member != 'PropertiesChanged':
            return

        args = message.body
        interface = args[0]
        changed_properties = args[1]
        if interface != 'org.bluez.Device1':
            return

        # Get the object path
        path = message.path

        if not path:
            return

        if CONTROLLER_MAC not in path.lower():
            return

        if 'Connected' in changed_properties:
            connected = changed_properties['Connected'].value
            if connected:
                print("Controller connected.")
                self.disconnection_time = None
                if not self.program_running:
                    self.start_program()
            else:
                print("Controller disconnected.")
                if self.program_running and self.disconnection_time is None:
                    self.disconnection_time = datetime.datetime.now()

    def start_program(self):
        print("Starting program...")
        self.program_process = subprocess.Popen(PROGRAM_CMD)
        self.program_running = True

    def stop_program(self):
        if self.program_running:
            print("Stopping program...")
            self.program_process.terminate()
            try:
                self.program_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                print("Force killing the program...")
                self.program_process.kill()
            self.program_running = False

if __name__ == '__main__':
    monitor = ControllerMonitor()
    asyncio.run(monitor.start())
