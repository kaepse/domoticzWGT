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


''' Commands '''
COMMANDS = dict()
COMMANDS['T1'] = 'Temperatur Verdampfer'
COMMANDS['T2'] = 'Temperatur Kondensator'
COMMANDS['T3'] = 'Temperatur Luft aussen'
COMMANDS['T4'] = 'Temperatur Abluft (Raumtemperatur)'
COMMANDS['T5'] = 'Temperatur nach Wärmetauscher'

def printHex(s):
    out = "".join("{:02x}".format(ord(c)) for c in s)
    print(out)

def makeHumanReadable(message):
    humanReadableMessage = ''
    for char in message:
        if char in CONTROLCHARS:
            humanReadableMessage += CONTROLCHARS[char]
        else:
            humanReadableMessage += char
    return humanReadableMessage
    
def createReadRequest(adress,command):
    if len(command) != 2:
        raise ValueError("The given Command is invalid - must have 2 chars!")
    if not command in COMMANDS:
        raise ValueError("The given Command is unknown")
    adressMessageString = createAdressStringForRequest(adress)
    readRequest = EOT + adressMessageString + command + ENQ
    return readRequest    
    
        
def createAdressStringForRequest(adress):
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
        

def createConnection():
    conn = serial.Serial('/dev/ttyUSB0',
                         baudrate=9600,
                         bytesize=serial.SEVENBITS,
                         parity=serial.PARITY_EVEN,
                         stopbits=serial.STOPBITS_ONE,
                         timeout=5,
                         xonxoff=0,
                         rtscts=1)    
    '''
    conn = serial.Serial('/dev/ttyUSB0',
                         baudrate=9600,
                         timeout=5)
    '''
    return conn 
    
def readFromDevice(connection,command):
    adress = 1
    request = createReadRequest(adress,command)
    #psprint("request: ", makeHumanReadable(request))
    # send the request
    connection.write(request.encode('ascii'))     
    # then receive the response
    response,checksum = receiveResponse(connection)
    return makeHumanReadable(response)     
    
def receiveResponse(connection):
    char = connection.read(1).decode('ascii')
    response = char    
    while char != ETX:
        char = connection.read(1).decode('ascii')
        response += char
    checksum = connection.read(1).decode('ascii')
    return response,checksum
     
def getValueFromResponse(response):
    value = response
    value = value.replace(CONTROLCHARS[STX],"")
    value = value.replace(CONTROLCHARS[ETX],"")
    value = value[2:]
    value = value.strip()
    return value
     
def query(connection):
    result = dict()
    for command in COMMANDS.keys():
        response = readFromDevice(connection,command)
        result[command] = getValueFromResponse(response)
    return result
        
    
     
def testAsciiHex():
    hermesReadRequestTest = "\x04\x30\x30\x31\x31\x54\x31\x05"       
    print(makeHumanReadable(hermesReadRequestTest))
    print(binascii.hexlify('kai'.encode('ascii')))
    print(binascii.unhexlify('6b6169'))
    printHex('kai') 
    requestT1 = createReadRequest(1,"T1")
    print(makeHumanReadable(requestT1))
    
def main():
    print("")
    #testAsciiHex()
    conn = createConnection()

    result = query(conn)    
    print(result)
    
    #temperatureOutside = readFromDevice(conn,"T3")
    #print(temperatureOutside)
    
    #reponse = conn.read(12)
    #print "heatpump responds: "
    #print "len=",len(reponse)
    #print makeHumanReadable(reponse)
    

if __name__ == "__main__":
    main()
