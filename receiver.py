'''
-------------W4119 Programming Assignment 2-------------
Created Date:        Nov 1, 2014
File name:           receiver.py
Operating System:    Ubuntu 12.04 on VM (Parallels Desktop 9)
IDE:                 Eclipse 4.4.1
Language:            Python 2.7.3
------------------All rights reserved------------------
'''
#---------------------Source Import--------------------
import sys
import socket
import thread
from threading import Thread
import time
from time import strftime
import struct

#------------------------Variables---------------------
MAXSEGMENTSIZE = 576                   # File will be divided into this size of segments to be transferred
FIRST_CORRUPTION = False               # The flag of first receiving 
ACK_ACK = 0                            # ACK # used to send ACK back to sender
ACK_SEQUENCE = 0                       # Sequence # used to send ACK back to sender
TRANS_FINISH = False                   # The flag to mark if the transmission is finished


#-------------------------Classes----------------------
class Receiver:
    'The class used to describe the receiver'   
    
    def __init__(self, wrto_file, listening_port, sender_IP, sender_port, log_file):
        "To initialize the class with variables"
        self.wrto_filename = wrto_file
        self.listening_port = listening_port
        self.sender_IP = sender_IP
        self.sender_port = sender_port
        self.log_filename = log_file
    
    def displayReceiver(self):
        "To display the variables of the class (just for testing)"

        print 'Saved filename:'.ljust(30), self.wrto_filename
        print 'Receiver side log filename:'.ljust(30), self.log_filename
        print 'Sender IP:'.ljust(30), self.sender_IP
        print 'Sender port:'.ljust(30), self.sender_port
        print 'Receiver listening port:'.ljust(30), self.listening_port
    
    def filewriting(self, data):
        "To write received data to the file"
        
        # Open the file from the name specified in the command line
        try:
            Datafile = open(self.wrto_filename,"a") 
        except:
            print 'File not found'
        
        # Write data to the file
        Datafile.write(data)
        
        # Close the file
        Datafile.close()

def checksum_verify(sumstring):
    "To verify the received data"
    sum_calc = 0
    
    #Divide the string by 16 bits and calculate the sum
    for num in range(len(sumstring)):
        if num % 2 == 0:     # Even parts with higher order
            sum_calc = sum_calc + (ord(sumstring[num]) << 8)
        elif num % 2 == 1:   # Odd parts with lower order
            sum_calc = sum_calc + ord(sumstring[num])
    
    # Get the inverse as the checksum
    output_sum = (sum_calc % 65536)
    
    return output_sum

def logwriting(segment_num, direction, timestamp, source, destination, sequence_num, ACK_num, ackflag, finflag, trans_status):
    "To write log file after each sending"
    
    #Determine the writing direction     
    if direction == 'forward':
        logdirection = 'Sender -> Receiver'
    elif direction == 'backward':
        logdirection = 'Receiver -> Sender'
    else:
        logdirection = direction
    
    #Log line format     
    logline = str(segment_num).ljust(10) + logdirection.ljust(20) + timestamp.ljust(22) + source.ljust(15) + destination.ljust(15) + str(sequence_num).ljust(11) + \
              str(ACK_num).ljust(7) + str(ackflag).ljust(5) + str(finflag).ljust(5) + trans_status.ljust(8) + '\r\n'
    
    #Check the output method (stdout or write to a log file)   
    if rft_receiver.log_filename == 'stdout.txt':
        print logline
    else:
        try:
            logfile = open (rft_receiver.log_filename, "a")
        except:
            print 'File ERROR'
        logfile.write(logline)
        logfile.close()
    
    return
    
def datareceive(TCPsocket, UDPsocket, rft_receiver):
    "Receive packet from sender and send ACK back"
    
    global ACK_ACK, ACK_SEQUENCE
    global TRANS_FINISH
    
    while TRANS_FINISH == False:
        # Receive packets from sender
        receiveddata = UDPsocket.recvfrom(1024)
        
        unpacksuccess = False
        
        # Unpack the packet to read the data
        while unpacksuccess == False:
            for num in range(MAXSEGMENTSIZE+1):
                try:
                    received = struct.unpack('!HHIIHHHH%ds'%num, receiveddata[0])
                    unpacksuccess = True
                except:
                    pass
        
        if received[2] == ACK_ACK:
            # Update sequence # for ACK message
            ACK_SEQUENCE = ACK_SEQUENCE + 1
        
            # Interpret ACK and FIN flags in the packets
            if received[4] == 0:
                ackflag = 0
                finflag = 0
            elif received[4] == 1:
                ackflag = 0
                finflag = 1
            elif received[4] == 16:
                ackflag = 1
                finflag = 0
            elif received[4] == 17:
                ackflag = 1
                finflag = 1
        
            # Check if the data is corrupted
            sum_calc = checksum_verify(receiveddata[0])
            # If the data is not corrupted
            if sum_calc == 65535:
                logwriting((int(received[2]) / MAXSEGMENTSIZE + 1), 'forward', strftime("%d,%b,%Y %H:%M:%S", time.localtime()), rft_receiver.sender_IP, socket.gethostbyname(socket.gethostname()), received[2], received[3], ackflag, finflag, 'Received') 
                rft_receiver.filewriting(received[8])                         # Write the data to the file
                ACK_ACK = received[2] + MAXSEGMENTSIZE                        # Update the ACK # for the ACK message
                TCPsocket.send(str(ACK_SEQUENCE) + ',' + str(ACK_ACK))        # Send ACK message to the sender with sequence # and ACK #
                if finflag == 0:
                    logwriting('-', 'backward', strftime("%d,%b,%Y %H:%M:%S", time.localtime()), socket.gethostbyname(socket.gethostname()), rft_receiver.sender_IP, ACK_SEQUENCE, ACK_ACK, 1, 0, 'Succeed')
                else:
                    logwriting('-', 'backward', strftime("%d,%b,%Y %H:%M:%S", time.localtime()), socket.gethostbyname(socket.gethostname()), rft_receiver.sender_IP, ACK_SEQUENCE, ACK_ACK, 1, 1, 'Succeed')              
                if finflag == 1:
                    TRANS_FINISH = True
            else:
                logwriting((int(received[2]) / MAXSEGMENTSIZE + 1), 'forward', strftime("%d,%b,%Y %H:%M:%S", time.localtime()), rft_receiver.sender_IP, socket.gethostbyname(socket.gethostname()), received[2], received[3], ackflag, finflag, 'Discarded') 
                TCPsocket.send(str(ACK_SEQUENCE) + ',' + str(ACK_ACK))
                logwriting('-', 'backward', strftime("%d,%b,%Y %H:%M:%S", time.localtime()), socket.gethostbyname(socket.gethostname()), rft_receiver.sender_IP, ACK_SEQUENCE, ACK_ACK, 1, 0, 'Succeed')
    
    # Close the son thread
    thread.exit()
              
    return    

if __name__ == '__main__':
    #Invoke the program to import <filename>, <listening_port>, <sender_IP>, <sender_port> and <log_filename>
    if(len(sys.argv) != 6):
        print 'Please follow the format to invoke the program:'
        print 'python receiver.py <filename> <listening_port> <sender_IP> <sender_port> <log_filename>'
        sys.exit()
    filename = sys.argv[1]
    try:
        listening_port = int(sys.argv[2])
    except ValueError:
        print '<listening_port> should be an integrate.'
        sys.exit()
    sender_IP = sys.argv[3]    
    try:
        sender_port = int(sys.argv[4])
    except ValueError:
        print '<sender_port> should be an integrate.'
        sys.exit()
    log_filename = sys.argv[5]
    
    #Initialization of the object of Receiver class
    rft_receiver = Receiver(filename, listening_port, sender_IP, sender_port, log_filename)
    
    #To set up a UDP socket for receiving the data
    UDPsocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)        
    UDP_HOST = socket.gethostbyname(socket.gethostname())
    UDP_PORT = rft_receiver.listening_port
    
    #Bind UDPsocket to local host and port
    try:
        UDPsocket.bind((UDP_HOST, UDP_PORT))
    except socket.error , msg:
        print 'Bind failed. Error Code : ' + str(msg[0]) + ' Message ' + msg[1]
        sys.exit()
    
    print '>> Waiting for sender invoking...'   
    
    #Receive first data and check the packet
    receiveddata = UDPsocket.recvfrom(1024)  
    received = struct.unpack('!HHIIHHHH%ds'%MAXSEGMENTSIZE, receiveddata[0])
    if received[4] == 0:
        ackflag = 0
        finflag = 0
    elif received[4] == 1:
        ackflag = 0
        finflag = 1
    elif received[4] == 16:
        ackflag = 1
        finflag = 0
    elif received[4] == 17:
        ackflag = 1
        finflag = 1
    
    logwriting('Segment#', 'Trans_direction', 'Timestamp', 'Source', 'Destination', 'Sequence#', 'ACK#', 'ACK', 'FIN', 'Trans_status') 
    sum_calc = checksum_verify(receiveddata[0])
    if sum_calc == 65535:
        FIRST_CORRUPTION = False
        logwriting((int(received[2]) / MAXSEGMENTSIZE + 1), 'forward', strftime("%d,%b,%Y %H:%M:%S", time.localtime()), rft_receiver.sender_IP, socket.gethostbyname(socket.gethostname()), received[2], received[3], ackflag, finflag, 'Received') 
    else:
        FIRST_CORRUPTION = True
        logwriting((int(received[2]) / MAXSEGMENTSIZE + 1), 'forward', strftime("%d,%b,%Y %H:%M:%S", time.localtime()), rft_receiver.sender_IP, socket.gethostbyname(socket.gethostname()), received[2], received[3], ackflag, finflag, 'Discarded') 
        
   
    if FIRST_CORRUPTION == False:
        rft_receiver.filewriting(received[8])
    
        
    #To set up a TCP socket for sending the ACK
    TCPsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)    
    TCP_HOST = rft_receiver.sender_IP
    TCP_PORT = rft_receiver.sender_port
    
    
    try:
        TCPsocket.connect((TCP_HOST, TCP_PORT))
    except:
        print 'Can not connect to sender, please check your <sender_IP> and <sender_port>'
    if FIRST_CORRUPTION == False: 
        ACK_ACK = received[2] + MAXSEGMENTSIZE  
        TCPsocket.send(str(ACK_SEQUENCE) + ',' + str(ACK_ACK))
        logwriting('-', 'backward', strftime("%d,%b,%Y %H:%M:%S", time.localtime()), socket.gethostbyname(socket.gethostname()), rft_receiver.sender_IP, 0, (received[2] + MAXSEGMENTSIZE), 1, 0, 'Succeed')
    else:
        TCPsocket.send(str(ACK_SEQUENCE) + ',' + str(ACK_ACK))
        logwriting('-', 'backward', strftime("%d,%b,%Y %H:%M:%S", time.localtime()), socket.gethostbyname(socket.gethostname()), rft_receiver.sender_IP, 0, received[2], 1, 0, 'Succeed')
    
    #After the TCP connection set up, a thread can be used to receive data and send ACK    
    new_thread = Thread(target = datareceive, args = (TCPsocket, UDPsocket, rft_receiver,))
    new_thread.setDaemon(True)
    new_thread.start()
    
    # Display receiver side information
    print '-' * 78
    rft_receiver.displayReceiver()
    print 'Receiver side IP:'.ljust(30), socket.gethostbyname(socket.gethostname())
    print '-' * 78
    print '>> File receiving ...'
    
    while TRANS_FINISH == False:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            sys.exit()
    
    # When transmission finished
    print '>> Transmission completed successfully'        
    
    sys.exit()

