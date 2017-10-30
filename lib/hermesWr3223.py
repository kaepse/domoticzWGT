# -*- coding: utf-8 -*-
"""
Created on Tue Dec 08 22:34:48 2015

@author: Kai Käppeler

Modul to connect to the Schwörer WGT (Hermes wr3223)
"""

import serial
import struct
import time
import sys
import binascii

''' Control Characters '''
STX = "\x02" # Start of message
ETX = "\x03" # End of message
EOT = "\x04" # End of transmision 
ENQ = "\x05" # Enquiry (Request a response or an action)
ACK = "\x06" # Acknowledged
NAK = "\x15" # Not Acknowledged
CONTROLCHARS = dict()
CONTROLCHARS[STX] = '<STX>'
CONTROLCHARS[ETX] = '<ETX>'
CONTROLCHARS[EOT] = '<EOT>'
CONTROLCHARS[ENQ] = '<ENQ>'
CONTROLCHARS[ACK] = '<ACK>'
CONTROLCHARS[NAK] = '<NAK>'

class Command:
    def __init__(self, cmd, descr, unit=None, isWriteable=False):
        self.cmd = cmd
        self.descr = descr
        self.unit = unit
        self.isWriteable = isWriteable
        self.mapping = None

''' Commands '''
COMMANDS = dict()
COMMANDS['T1'] = Command('T1','Temperatur Verdampfer','[°C]')
COMMANDS['T2'] = Command('T2','Temperatur Kondensator','[°C]')
COMMANDS['T3'] = Command('T3','Aussentemperatur','[°C]')
COMMANDS['T4'] = Command('T4','Temperatur Abluft (Raumtemperatur)','[°C]')
COMMANDS['T5'] = Command('T5','Temperatur nach Wärmetauscher (Fortluft)','[°C]')
COMMANDS['T6'] = Command('T6','Zulufttemperatur','[°C]')
COMMANDS['T7'] = Command('T7','Temperatur nach Solevorerwärmung','[°C]')
COMMANDS['T8'] = Command('T8','Temperatur nach Wärmetauscher','[°C]')
COMMANDS['UZ'] = Command('UZ','Spannung Ventilator Zuluft','[0.1 V]')
COMMANDS['UA'] = Command('UA','Spannung Ventilator Abluft','[0.1 V]')
COMMANDS['NZ'] = Command('NZ','Drehzahl Zuluft','[U/min]')
COMMANDS['NA'] = Command('NA','Drehzahl Abluft','[U/min]')
COMMANDS['LS'] = Command('LS','Luftstufe','')
COMMANDS['LS'].mapping = {'0.':'Aus','1.':'Stufe 1','2.':'Stufe 2','3.':'Stufe 3'}
COMMANDS['L1'] = Command('L1','Luftstufe 1','[%]', isWriteable=True)
COMMANDS['L2'] = Command('L2','Luftstufe 2','[%]', isWriteable=True)
COMMANDS['L3'] = Command('L3','Luftstufe 3','[%]', isWriteable=True)
COMMANDS['LD'] = Command('LD','Luftdifferenz Zuluft','[%]', isWriteable=True)
COMMANDS['Ld'] = Command('Ld','Luftdifferenz Abluft','[%]', isWriteable=True)
COMMANDS['ES'] = Command('ES','EWT Sommer','[°C]', isWriteable=True)
COMMANDS['EW'] = Command('EW','EWT Winter','[°C]', isWriteable=True)
COMMANDS['KM'] = Command('KM','Maximale Kondensationstemperatur','[°C]', isWriteable=True)
COMMANDS['PA'] = Command('PA','Ausgleichszeit','[Sek.]')
COMMANDS['ZH'] = Command('ZH','Zusatzheizung frei','', isWriteable=True)
COMMANDS['ZE'] = Command('ZE','Zusatzheizung Ein','', isWriteable=True)
COMMANDS['WP'] = Command('WP','Wärmepumpe freigegeben','')
COMMANDS['MD'] = Command('MD','Mode','')
COMMANDS['MD'].mapping = {'0.':'Aus','1.':'Sommer','2.':'Abluft',
'3.':'Winter: WP aus','-125.':'Winter: WP an','4.':'Handbetrieb'}
COMMANDS['AE'] = Command('AE','Abtau ein','[°C]', isWriteable=True)
COMMANDS['AA'] = Command('AA','Abtau aus','[°C]', isWriteable=True)
COMMANDS['Az'] = Command('Az','Luftstufe Abtau','', isWriteable=True)
COMMANDS['AP'] = Command('AP','Abtaupause','min', isWriteable=True)
COMMANDS['AN'] = Command('AN','Abtaunachlauf','min', isWriteable=True)
COMMANDS['ER'] = Command('ER','Fehlermeldung','')
COMMANDS['ER'].mapping = {'0.':'Keine Meldung','4.':'Hochdruck',
'11.':'Kurzschluss an T1','12.':'Kurzschluss an T2','13.':'Kurzschluss an T3','15.':'Kurzschluss an T5',
'21.':'Offene Leitung an T1','22.':'Offene Leitung an T2','23.':'Offene Leitung an T3','25.':'Offenen Leitung an T5'}
COMMANDS['ST'] = Command('ST','Status','')
COMMANDS['ST'].mapping = {'217.':'Wärmepumpe aktiv?','249.':'Wärmepumpe inaktiv?'}
COMMANDS['Tf'] = Command('Tf','EVU Sperre','')
COMMANDS['Tf'].mapping = {'-47.':'Aktiv','-48.':'Inaktiv'}
COMMANDS['RL'] = Command('RL','Relais','')
COMMANDS['RL'].mapping = {'-47.':'Zustand?','64.':'EVU?',
'320.' :'Freigabe(WP/Kühl):Ja   | WP:Aus | Kühl:Aus | Freigabe(ZH):Nein | Bypass:Nein',
'321.' :'Freigabe(WP/Kühl):Nein | WP:Aus | Kühl:Aus | Freigabe(ZH):Nein | Bypass:Nein',
'322.' :'Freigabe(WP/Kühl):Ja   | WP:Aus | Kühl:Aus | Freigabe(ZH):Ja   | Bypass:Nein',
'328.' :'Freigabe(WP/Kühl):Nein | WP:Aus | Kühl:Aus | Freigabe(ZH):Nein | Bypass:Ja',
'833.' :'Freigabe(WP/Kühl):Ja   | WP:An  | Kühl:Aus | Freigabe(ZH):Nein | Bypass:Nein',
'835.' :'Freigabe(WP/Kühl):Ja   | WP:An  | Kühl:Aus | Freigabe(ZH):Ja   | Bypass:Nein',
'2377.':'Freigabe(WP/Kühl):Ja   | WP:Aus | Kühl:An  | Freigabe(ZH):Nein | Bypass:Ja'
}
COMMANDS['II'] = Command('II','Identifikation lesen','[Text]')

class HermesWr3223:
    def __init__(self, serialPort, adress=1):
        self._serial = serial.Serial()
        self._serial.port = serialPort
        self._serial.baudrate=9600
        self._serial.bytesize=serial.SEVENBITS
        self._serial.parity=serial.PARITY_EVEN
        self._serial.stopbits=serial.STOPBITS_ONE
        self._serial.timeout=5
        self._serial.xonxoff=0
        self._serial.rtscts=1
        self._adress = adress
        self._adressMessageString = HermesWr3223._createAdressString(adress)

    def isConnected(self):
        return self._serial.is_open

    def connect(self):
        self._serial.open()
        
    def disconnect(self):
        self._serial.close()        
        
    def readMultiple(self,commands):
        result = dict()
        for command in commands:
            result[command] = self.read(command)
        return result        
        
    def read(self,command):
        request = self._createReadRequest(command)
        #psprint("request: ", makeHumanReadable(request))
        # send the request
        self._serial.write(request.encode('ascii'))     
        # then receive the response
        response,checksum = self._receiveResponse()
        responseHumanReadable = self._makeHumanReadable(response)
        return self._getValueFromResponse(responseHumanReadable)

    def _createReadRequest(self,command):
        if len(command) != 2:
            raise ValueError("The given Command is invalid - must have 2 chars!")
        if not command in COMMANDS:
            raise ValueError("The given Command is unknown")
        readRequest = EOT + self._adressMessageString + command + ENQ
        return readRequest    
        
    
    def _makeHumanReadable(self,message):
        humanReadableMessage = ''
        for char in message:
            if char in CONTROLCHARS:
                humanReadableMessage += CONTROLCHARS[char]
            else:
                humanReadableMessage += char
        return humanReadableMessage
        
        
    @staticmethod        
    def _createAdressString(adress):
        '''
        Creates the adress string from a given int.
        "<ADR_H><ADR_H><ADR_L><ADR_L>"
        ADR_H Adresse der Steuerung 10er Stelle (ASCII, 2 mal)
        ADR_L Adresse der Steuerung 1er Stelle (ASCII, 2 mal)    
        Exampe: adress=2
        Returns: "0022"
        '''
        if adress < 0 or adress > 99:
            raise ValueError("The specified adress is out ouf range")
        adressString = str(adress)
        if len(adressString) == 1:
            adressString = '0' + adressString
        adressCharHigh = adressString[0]
        adressCharLow = adressString[1]
        adressMessageString = adressCharHigh + adressCharHigh + adressCharLow + adressCharLow
        return adressMessageString                
          
        
    def _receiveResponse(self):
        char = self._serial.read(1).decode('ascii')
        response = char    
        while char != ETX:
            char = self._serial.read(1).decode('ascii')
            response += char
        checksum = self._serial.read(1).decode('ascii')
        return response,checksum
         
    def _getValueFromResponse(self,response):
        value = response
        value = value.replace(CONTROLCHARS[STX],"")
        value = value.replace(CONTROLCHARS[ETX],"")
        value = value[2:]
        value = value.strip()
        return value
                
def getMappedResult(cmd,result):
    mappedResult = None
    mapping = COMMANDS[cmd].mapping
    if not mapping is None:
        if result in mapping:
            mappedResult = mapping[result]
    return mappedResult                
                
def getMessageByCommandResult(cmd,result):
    mappedResult = getMappedResult(cmd,result)
    msg = str()
    msg += cmd  + ": " + COMMANDS[cmd].descr + ": " + result
    if not mappedResult is None:
        msg += " (" + mappedResult + ")"
    msg += " " + COMMANDS[cmd].unit
    return msg    

def debugPrintCommandResult(cmd):
    wgt = HermesWr3223("/dev/ttyUSB0")
    wgt.connect()    
    result = wgt.read(cmd)
    print(getMessageByCommandResult(cmd,result))
    
def debugPrintMultiCommandResult(cmds):
    wgt = HermesWr3223("/dev/ttyUSB0")
    wgt.connect()    
    results = wgt.readMultiple(cmds)
    for cmd in cmds:
        if not cmd in results:
            print("Error! No result for cmd= " + cmd)
        print(getMessageByCommandResult(cmd,results[cmd]))
        
def debugPrintHex(s):
    out = ":".join("{:02x}".format(ord(c)) for c in s)
    print(out)        
     
def testAsciiHex():
    print(binascii.hexlify('kai'.encode('ascii')))
    print(binascii.unhexlify('6b6169'))
    debugPrintHex('kai') 
    
    wgt = HermesWr3223("InvalidSerialPort")
    requestT1 = wgt._createReadRequest("T1")
    print(wgt._makeHumanReadable(requestT1))

    asciiRequest="\x04\x30\x30\x31\x31\x54\x31\x05"       
    print(wgt._makeHumanReadable(asciiRequest))    

if __name__ == "__main__":
    #testAsciiHex()
    #debugPrintCommandResult("II") 
    #debugPrintMultiCommandResult(("T1","T2","T3","T4","T5","T6","T7","T8")) 
    allCommandsSorted = sorted(COMMANDS.keys())
    debugPrintMultiCommandResult(allCommandsSorted)


    
    
    