# domoticz-ecometers
Domoticz plugin for the Eco Meter S tank level sensor.

https://www.e-sensorix.com/product/ecometer-s

# Description
This plugin allows an Eco Meter S display connected to the computer running domoticz to read the live data from the display.

Based on the info from https://sarnau.info/communication-protocol-of-the-proteus-ecometer-tek603/

# Install
## Prerequisites
- Domoticz
- python3-serial

## Domoticz
1. Copy the plugin.py file to a sub directory in domoticz/plugins/. I.e.: /home/pi/domoticz/plugins/ecometers/plugin.py
2. In Domoticz under "Setup" -> "Hardware", add the "Ecometer S plugin"
3. Select the correct com port. I.e.: /dev/ttyUSB0
4. Set the correct tank height (like configured in the display)
5. Set the correct sensor offset from the level at full capacity (like configured in the display)

Step 4 and 5 are needed since these values are not (yet) received from the display. It should be possible, but at the time of writing the documentation is not clear about how to get it.
