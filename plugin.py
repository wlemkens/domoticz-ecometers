# Ecometer S Plugin
#
# Author: Wim Lemkens
#
"""
<plugin key="EcometerSPlug" name="Ecometer S Plugin" author="Wim Lemkens" version="1.0.0" wikilink="http://www.domoticz.com/wiki/plugins/plugin.html" externallink="https://www.google.com/">
    <description>
        <h2>Ecometer S</h2><br/>
        Plugin for the Eceometer S water/oil/... tank volume sensor
        <h3>Devices</h3>
        <ul style="list-style-type:square">
            <li>Percentage - Fill level in percentage</li>
            <li>Level - Fill level in cm</li>
            <li>Volume - Fill level in liter</li>
            <li>Temperature - Water tank temperature in degrees Celcius</li>
            <li>Distance - Distance between water level and sensor in cm</li>
        </ul>
        <h3>Configuration</h3>
        <ul style="list-style-type:square">
            <li>Port - port to connect to the Eco Meter S display</li>
            <li>Height - Height of the tank</li>
            <li>Offset - Distance between the full tank water level and the sensor</li>
        </ul>
        Height and offset are added together to calculate the water level since these values are not 
        retreived from the display in the current plugin version.
    </description>
    <params>
	<param field="SerialPort" label="Port" required="true" default="/dev/ttyUSB0"/>
	<param field="Mode1" label="Tank height [cm]" width="30px" required="true" default="185"/>
        <param field="Mode2" label="Sensor offset [cm]" width="30px" required="true" default="5"/>
    </params>
</plugin>
"""
import Domoticz
import datetime as dt
import serial
import threading
import time

class Datagram:
    SETCLOCK = 1
    RESET = 2
    SEND = 4
    RECALCULATE = 8
    LIVE = 16

    def __init__(self, data):
        # 2 byte header (â'SI' = 0x53,0x49)

        self.header = data[0:2]
        # 2 byte length of the complete package (16 bit, big-endian)
        self.length = data[2:4]
        # 1 byte command (1: data send to the device, 2: data received from the device)
        self.direction = data[4]
        # 1 byte flags:
        #   bit 0: set the clock (hour/minutes/seconds) in the device on upload
        #   bit 1: force reset the device (set before an update of the device)
        #   bit 2: a non-empty payload is send to the device
        #   bit 3: force recalculate the device (set on upload after changing the Sensor Offset, Outlet Height or the lookup table)
        #   bit 4: live data received from the device
        #   bit 5: n/a
        #   bit 6: n/a
        #   bit 7: n/a
        self.command = data[5]
        # 1 byte hour - used to transmit the current time to the device
        self.hour = data[6]
        # 1 byte minutes
        self.minutes = data[7]
        # 1 byte seconds
        self.seconds = data[8]
        # 2 byte eeprom start (16 bit, big-endian) - unused in live data
        self.eeprom_start = int.from_bytes(data[9:11], "big")
        # 2 byte eeprom end (16 bit, big-endian)
        self.eeprom_end = int.from_bytes(data[11:13], "big")
        # n bytes payload
        self.payload = data[13:-2]
        # 2 byte CRC16 (16 bit, big-endian)
        self.crc = data[-2:]

class BasePlugin:
    enabled = False
    def __init__(self):
        self._running = False
        self._shutdown = False
        self.deviceThread = threading.Thread(name="EcometerThread", target=BasePlugin.monitorDevice, args=(self,))
        self.port = "/dev/ttyUSB0"
        self.offset = 5
        self.tank_height = 185
        self.height = self.offset + self.tank_height
        return

    def monitorDevice(self):
        try:
            Domoticz.Log("Entering device monitoring")
            while self._running:
                Domoticz.Debug("Reading")
                self.readData()
            Domoticz.Log("Stopping thread")
            self._shutdown = True
        except Excpetion as err:
            Domoticz.Error("monitorDevice: "+str(err))

    def readData(self):
        Domoticz.Log("Connecting to device on port {:}".format(self.port))
        with serial.Serial(self.port, 115200, bytesize=8, parity='N', stopbits=1, timeout=10) as ser:
                Domoticz.Debug("Connected to device")
                data = bytearray()
                header = ser.read(2)
                Domoticz.Debug("Received data or timeout")
                if header == b'SI':
                    Domoticz.Log("Received data with correct header")
                    length_bytes = ser.read(2)
                    length = int.from_bytes(length_bytes, "big")
                    Domoticz.Debug("Receiving "+str(length)+" bytes")
                    payload = ser.read(length - 4)
                    Domoticz.Debug("Received whole message")
                    data.extend(header)
                    data.extend(length_bytes)
                    data.extend(payload)
                    datagram = Datagram(data)
                    Domoticz.Debug("Parsed message")
                    if datagram.command == Datagram.LIVE:
                        Domoticz.Log("Received live data")
                        self.registerData(datagram)
        Domoticz.Debug("Connection closed")


    def registerData(self, datagram):
        tempF = datagram.payload[0] - 40
        self.temperature = round((tempF - 32) / 1.8, 1)
        self.distance = int.from_bytes(datagram.payload[1:3], "big")
        self.level = 190 - self.distance
        self.usable = int.from_bytes(datagram.payload[3:5], "big")
        self.total = int.from_bytes(datagram.payload[5:7], "big")
        self.updateTime = dt.datetime.now()
        self.volume = self.usable
        self.percentage = round(100.0 * self.volume / self.total, 1)
        UpdateDevice(1, 0, self.percentage)
        UpdateDevice(2, 0, self.level)
        UpdateDevice(3, 0, self.volume)
        UpdateDevice(4, 0, self.temperature)
        UpdateDevice(5, 0, self.distance)

    def onStart(self):
        Domoticz.Log("onStart called")
        self.port = Parameters["SerialPort"]
        self.tank_height = int(Parameters["Mode1"])
        self.offset = int(Parameters["Mode2"])
        self.height = self.tank_height + self.offset
        Domoticz.Log("Device on port {:}, with height {:}".format(self.port, self.height))
        if (len(Devices) == 0):
            Domoticz.Device(Name="Percentage",  Unit=1, TypeName="Percentage").Create()
            Domoticz.Device(Name="Level",  Unit=2, TypeName="Distance").Create()
            Domoticz.Device(Name="Volume",  Unit=3, TypeName="Custom").Create()
            Domoticz.Device(Name="Temperature",  Unit=4, TypeName="Temperature").Create()
            Domoticz.Device(Name="Distance",  Unit=5, TypeName="Distance").Create()
            Domoticz.Log("Devices created.")
        if (1 in Devices):
            self.percentage = Devices[1].nValue
        if (2 in Devices):
            self.distance = Devices[2].nValue
        if (3 in Devices):
            self.volume = Devices[3].nValue
        if (4 in Devices):
            self.temperature = Devices[4].nValue
        if (5 in Devices):
            self.temperature = Devices[5].nValue
        Domoticz.Debug("Starting device thread")
        self._running = True
        self.deviceThread.start()

    def onStop(self):
        Domoticz.Debug("onStop called")
        self._running = False
        while not self._shutdown:
            time.sleep(5)
        Domoticz.Debug("stopped")

#    def onConnect(self, Connection, Status, Description):
#        Domoticz.Log("onConnect called")

#    def onMessage(self, Connection, Data):
#        Domoticz.Log("onMessage called")

#    def onCommand(self, Unit, Command, Level, Hue):
#        Domoticz.Log("onCommand called for Unit " + str(Unit) + ": Parameter '" + str(Command) + "', Level: " + str(Level))

#    def onNotification(self, Name, Subject, Text, Status, Priority, Sound, ImageFile):
#        Domoticz.Log("Notification: " + Name + "," + Subject + "," + Text + "," + Status + "," + str(Priority) + "," + Sound + "," + ImageFile)

#    def onDisconnect(self, Connection):
#        Domoticz.Log("onDisconnect called")

global _plugin
_plugin = BasePlugin()

def onStart():
    global _plugin
    _plugin.onStart()

def onStop():
    global _plugin
    _plugin.onStop()

#def onConnect(Connection, Status, Description):
#    global _plugin
#    _plugin.onConnect(Connection, Status, Description)

#def onMessage(Connection, Data):
#    global _plugin
#    _plugin.onMessage(Connection, Data)

#def onCommand(Unit, Command, Level, Hue):
#    global _plugin
#    _plugin.onCommand(Unit, Command, Level, Hue)

#def onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile):
#    global _plugin
#    _plugin.onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile)

#def onDisconnect(Connection):
#    global _plugin
#    _plugin.onDisconnect(Connection)

#def onHeartbeat():
#    global _plugin
#    _plugin.onHeartbeat()

    # Generic helper functions
def DumpConfigToLog():
    for x in Parameters:
        if Parameters[x] != "":
            Domoticz.Debug( "'" + x + "':'" + str(Parameters[x]) + "'")
    Domoticz.Debug("Device count: " + str(len(Devices)))
    for x in Devices:
        Domoticz.Debug("Device:           " + str(x) + " - " + str(Devices[x]))
        Domoticz.Debug("Device ID:       '" + str(Devices[x].ID) + "'")
        Domoticz.Debug("Device Name:     '" + Devices[x].Name + "'")
        Domoticz.Debug("Device nValue:    " + str(Devices[x].nValue))
        Domoticz.Debug("Device sValue:   '" + Devices[x].sValue + "'")
        Domoticz.Debug("Device LastLevel: " + str(Devices[x].LastLevel))
    return

 
def UpdateDevice(Unit, nValue, sValue):
    # Make sure that the Domoticz device still exists (they can be deleted) before updating it 
    if (Unit in Devices):
        if (Devices[Unit].nValue != nValue) or (Devices[Unit].sValue != sValue):
            Devices[Unit].Update(nValue=nValue, sValue=str(sValue))
            Domoticz.Log("Update "+str(nValue)+":'"+str(sValue)+"' ("+Devices[Unit].Name+")")
