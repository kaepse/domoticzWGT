# Domoticz Plugin fuer die Schwoerer WGT (Hermes wr3223)
#
# Author: Kai Kaeppeler
#
"""
<plugin key="SchwoererWGT" name="Schwoerer WGT (Hermes Wr3223)" author="Kai Kaeppeler" version="1.0.0">
    <params>
        <param field="SerialPort" label="Serial Port" required="true" default="/dev/ttyUSB0" width="150px"/>           
        <param field="Mode6" label="Debug" width="75px">
            <options>
                <option label="True" value="Debug"/>
                <option label="False" value="Normal"  default="true" />
            </options>
        </param>        
    </params>
</plugin>
"""

import sys
sys.path.append('/usr/lib/python3/dist-packages')
import serial

import lib.hermesWr3223 as wgtLib
try:
    import Domoticz
except ImportError:
    import lib.fakeDomoticz as Domoticz


class BasePlugin:
    usedSelectorSwitchCommands = ("MD","LS","Tf")
    usedTemperatureCommands = ("T1","T2","T3","T4","T5","T6","T7","T8")
    usedPercentageCommands = ("L1","L2","L3","LD","Ld") 
    usedCustomCommands = ("NZ","NA","UZ","UA")     
    usedSpecificCommands = usedSelectorSwitchCommands + usedTemperatureCommands + usedPercentageCommands + usedCustomCommands
    usedTextCommands = tuple(sorted(set(wgtLib.COMMANDS.keys()) - set(usedSpecificCommands)))
    usedCommands = usedSpecificCommands + usedTextCommands 
    
    def __init__(self):
        self.mapDeviceToUsedCmd = dict(enumerate(self.usedCommands,start=1))
        self.mapUsedCmdToDevice = {v: k for k,v in self.mapDeviceToUsedCmd.items()}

    def onStart(self):
        if Parameters["Mode6"] == "Debug":
            Domoticz.Debugging(1)
        if (len(Devices) == 0):
            self.createDevices()
            Domoticz.Log("Devices created.")

        DumpConfigToLog()
        Domoticz.Log("Plugin is started.")
        Domoticz.Heartbeat(20)        

    def onStop(self):
        Domoticz.Log("onStop called")

    def onConnect(self, Connection, Status, Description):
        Domoticz.Log("onConnect called")

    def onMessage(self, Connection, Data, Status, Extra):
        Domoticz.Log("onMessage called")

    def onCommand(self, Unit, Command, Level, Hue):
        Domoticz.Log("onCommand called for Unit " + str(Unit) + ": Parameter '" + str(Command) + "', Level: " + str(Level))

    def onNotification(self, Name, Subject, Text, Status, Priority, Sound, ImageFile):
        Domoticz.Log("Notification: " + Name + "," + Subject + "," + Text + "," + Status + "," + str(Priority) + "," + Sound + "," + ImageFile)

    def onDisconnect(self, Connection):
        Domoticz.Log("onDisconnect called")

    def onHeartbeat(self):
        self.updateDevices()

    def createDevice(self,cmd,deviceType,options=dict()):
        if not cmd in self.usedCommands:
            raise ValueError("cmd=%s is not a valid command! See BasePlugin.usedCommands!" % cmd)        
        if not cmd in wgtLib.COMMANDS:
            raise ValueError("cmd=%s is not a valid command! See hermesWr3223.COMMANDS!" % cmd)            
        deviceIdx = self.mapUsedCmdToDevice[cmd]
        deviceName = cmd + ": " + wgtLib.COMMANDS[cmd].descr
        Domoticz.Device(Name=deviceName, Unit=deviceIdx, TypeName=deviceType, Options=options).Create()        

    def createDevices(self):
        for cmd in self.usedTemperatureCommands:
            self.createDevice(cmd,"Temperature")
        for cmd in self.usedPercentageCommands:
            self.createDevice(cmd,"Percentage")                     
        for cmd in self.usedTextCommands:
            self.createDevice(cmd,"Text")  
        for cmd in self.usedCustomCommands:
            unit = wgtLib.COMMANDS[cmd].unit
            options = {"Custom":"1;"+unit}
            self.createDevice(cmd,"Custom",options)               
        for cmd in self.usedSelectorSwitchCommands:
            resultMapping = wgtLib.COMMANDS[cmd].mapping
            options = self.createSwitchOptionsFromResultMapping(resultMapping)            
            self.createDevice(cmd,"Selector Switch",options)
            
    def createSwitchOptionsFromResultMapping(self,resultMapping):
        if not type(resultMapping) is dict:
            return dict()        
        levelNames = str()
        levelActions = str()
        for result in sorted(resultMapping.keys()):
            mappedResult = resultMapping[result]
            levelNames += mappedResult + "|"
            levelActions += "|"
        levelNames = levelNames[:-1] #remove last '|'
        levelActions = levelActions[:-1] #remove last '|'
        options = dict()    
        options['LevelNames'] = levelNames
        options['LevelActions'] = levelActions
        options["LevelOffHidden"] = "false"
        options["SelectorStyle"] = "1"        
        return options
        
    def getDomoticzSwitchLevel(self,cmd,result):
        resultMapping = wgtLib.COMMANDS[cmd].mapping
        if not type(resultMapping) is dict:
            Domoticz.Error("Error! Unable to get SwitchLevel for result: %s of cmd: %s err: %s " % (result,cmd))
            return result
        try:
            index = sorted(resultMapping.keys()).index(result)
            switchLevel = str(10 * index)
            return switchLevel
        except ValueError as err:
            Domoticz.Error("Error! Unable to get SwitchLevel for result: %s of cmd: %s err: %s " % (result,cmd,err))
            return result
            
        
            
    def updateDevices(self):
        try:
            wgt = wgtLib.HermesWr3223(Parameters["SerialPort"])
            wgt.connect()
            results = wgt.readMultiple(self.usedCommands)
            for cmd in self.usedCommands:
                if not cmd in results:
                    Domoticz.Error("Error! No result for cmd= " + cmd)
                else:
                    result = results[cmd]
                    resultLogMessage = wgtLib.getMessageByCommandResult(cmd,result)
                    Domoticz.Debug(resultLogMessage)
                    
                    resultToSet = result                    
                    if cmd in self.usedSelectorSwitchCommands: 
                        resultToSet = self.getDomoticzSwitchLevel(cmd,result)
                    if cmd in self.usedTextCommands:
                        resultToSet = resultLogMessage 
                                        
                    deviceIdx = self.mapUsedCmdToDevice[cmd]                    
                    UpdateDevice(deviceIdx,0,resultToSet)
                    
        except serial.Serialexception as err:
            Domoticz.Error('Error when reading from serial port %s : %s' % (Parameters["SerialPort"], err))        
              

global _plugin
_plugin = BasePlugin()

def onStart():
    global _plugin
    _plugin.onStart()

def onStop():
    global _plugin
    _plugin.onStop()

def onConnect(Connection, Status, Description):
    global _plugin
    _plugin.onConnect(Connection, Status, Description)

def onMessage(Connection, Data, Status, Extra):
    global _plugin
    _plugin.onMessage(Connection, Data, Status, Extra)

def onCommand(Unit, Command, Level, Hue):
    global _plugin
    _plugin.onCommand(Unit, Command, Level, Hue)

def onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile):
    global _plugin
    _plugin.onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile)

def onDisconnect(Connection):
    global _plugin
    _plugin.onDisconnect(Connection)

def onHeartbeat():
    global _plugin
    _plugin.onHeartbeat()

    # Generic helper functions

def UpdateDevice(Unit, nValue, sValue):
	# Make sure that the Domoticz device still exists (they can be deleted) before updating it 
	if (Unit in Devices):
		if (Devices[Unit].nValue != nValue) or (Devices[Unit].sValue != sValue):
			Devices[Unit].Update(nValue, str(sValue))
			Domoticz.Log("Update "+str(nValue)+":'"+str(sValue)+"' ("+Devices[Unit].Name+")")
	return

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
    
if __name__ == "__main__":
    print ("Local testing:")