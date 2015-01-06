'''
-------------W4119 Programming Assignment 2-------------
Created Date:        Nov 1, 2014
File name:           sender.py
Operating System:    Ubuntu 12.04 on VM (Parallels Desktop 9)
IDE:                 Eclipse 4.4.1
Language:            Python 2.7.3
------------------All rights reserved------------------
'''
#---------------------Source Import--------------------
import sys
import socket
import thread
import threading
from threading import Thread
import time
from time import strftime
import struct
import os

#------------------------Variables---------------------
SENDINGPOINTER = 0                     # Number of current sending segment
MAXSEGMENTSIZE = 576                   # File will be divided into this size of segments to be transferred
SEQUENCE_NUM = 0                       # Sequence # used to send packets from sender to receiver
ACK_NUM = 0                            # ACK # used to send packets from sender to receiver
TRANS_FINISH = False                   # The flag to mark if the transmission is finished

OVERALL_SEGMENT_COUNT = 0              # Overall # of sent segments
OVERALL_CORRUP_RESEND = 0              # Overall # of resent segments by corruption
OVERALL_TIMEOUT_RESEND = 0
OVERALL_RESEND = 0
OVERALL_SENDBYTE_COUNT = 0

# Variables for calculating EstimatedRTT
alpha = 0.125
beta = 0.25
SampleRTT = 1
EstimatedRTT = 2
DevRTT = 0
TimeoutInterval = EstimatedRTT + 4 * DevRTT

corruption_flag = False                # The flag to mark the packet former just sent corrupted
timeout_flag = False                   # The flag to mark the packet former just sent with no response in timeout interval 
t_start = time.time()                  # Used to evaluate SampleRTT
t_stop = time.time()

START_TIME = 0                         # Used to calculate TRANS_TIME
STOP_TIME = 0
TRANS_TIME = 0                         # Transmission time
DURATION = 0                           # The time passed from transmission started
DURATION_MIN = 0
DURATION_S = 0               
INS_SPEED = 0                          # Instant transmission speed
AVR_SPEED = 0                          # Average transmission speed
SEGMENT_TIME = 1                       # The time for a segment from first sent by sender to finally received by receiver without corruption, to calculate instant speed
sp_t_start = time.time()               # Used to calculate SEGMENT_TIME
sp_t_stop = time.time()
#-------------------------Classes----------------------
class Sender:
    'The class used to describe the sender'
    total_sending_message = []         # List to save file contents
    file_size = 0                      # The size of the file readed
    
    def __init__(self, rdfrm_file, remote_IP, remote_port, ack_port_num, log_file, win_size):
        "To initialize the class with variables"
        self.rdfrm_filename = rdfrm_file
        self.remote_IP = remote_IP
        self.remote_port = remote_port
        self.ack_port_num = ack_port_num
        self.log_filename = log_file
        self.win_size = win_size
        
        return
    
    def displaySender(self):
        "To display the variables of the class"
        
        print 'Sending filename:'.ljust(25), self.rdfrm_filename
        print 'Sending file size:'.ljust(25), Sender.file_size
        print 'Receiver(or proxy) IP:'.ljust(25), self.remote_IP
        print 'Receiver(or proxy) port:'.ljust(25), self.remote_port        
        print 'Sender side log filename:'.ljust(25), self.log_filename
        print 'Sender window size:'.ljust(25), self.win_size
        print 'ACK receiving port:'.ljust(25), self.ack_port_num

        
        return
    
    def filereading(self):
        "To read the data that will be sent from the file"
        #Check the size of the reading file
        statinfo = os.stat(self.rdfrm_filename)
        
        #Open the file from the name specified in the command line
        try:
            Datafile = open(self.rdfrm_filename,"r") 
        except:
            print 'File not found'
        
        #Initialize the file size
        Sender.file_size = statinfo.st_size
        
        #Cut the file into different data chunks by the MAXSEGMENTSIZE given.
        for num in range(int(statinfo.st_size / MAXSEGMENTSIZE)):
            datachunk = Datafile.read(MAXSEGMENTSIZE)
            Sender.total_sending_message.append(datachunk)
        datachunk = Datafile.read(statinfo.st_size % MAXSEGMENTSIZE)
        Sender.total_sending_message.append(datachunk)
        
        #Close the file
        Datafile.close()
        
        return


#------------------------Functions---------------------
def checksum_calc(sumstring):
    "To calculate the checksum part"
    sum_calc = 0
    
    #Divide the string by 16 bits and calculate the sum
    for num in range(len(sumstring)):
        if num % 2 == 0:     # Even parts with higher order
            sum_calc = sum_calc + (ord(sumstring[num]) << 8)
        elif num % 2 == 1:   # Odd parts with lower order
            sum_calc = sum_calc + ord(sumstring[num])
    
    # Get the inverse as the checksum
    sendcheck = 65535 - (sum_calc % 65536)                       
    
    return sendcheck

def logwriting(segment_num, direction, timestamp, source, destination, sequence_num, ACK_num, ackflag, finflag, estimateRTT, timeout, trans_status, notes):
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
              str(ACK_num).ljust(7) + str(ackflag).ljust(5) + str(finflag).ljust(5) + str(estimateRTT).ljust(15) + str(timeout).ljust(15) + trans_status.ljust(15) + str(notes).ljust(10) + '\r\n'    
    
    #Check the output method (stdout or write to a log file)
    if rft_sender.log_filename == 'stdout.txt':
        print logline
    else:
        try:
            logfile = open (rft_sender.log_filename, "a")
        except:
            print 'File ERROR'
        logfile.write(logline)
        logfile.close()
    
    return

def rft_header(source_port, dest_port, seq_num, ack_num, ACK_flag, FIN_flag, checksum, datachunk):
    "To pack the reliable file transfer data with TCP-like header"
    
    #To determine the value of flag part in the header
    if ACK_flag == 0 and FIN_flag == 0:
        flagpart = 0         #0x0000
    elif ACK_flag == 0 and FIN_flag == 1:
        flagpart = 1         #0x0001
    elif ACK_flag == 1 and FIN_flag == 0:
        flagpart = 16        #0x0010
    elif ACK_flag == 1 and FIN_flag == 1:
        flagpart = 17        #0x0011
    
    #To pack the header in a size of 20 bytes header and MAXSEGMENTSIZE of segment    
    header = struct.pack('!HHIIHHHH%ds'%len(datachunk), source_port, dest_port, seq_num, ack_num, flagpart, 0, checksum, 0, datachunk)
    
    return header

def dealwithACK(conn, addr):
    "To deal with the received ACK back"
    global SENDINGPOINTER, SEQUENCE_NUM, ACK_NUM, TRANS_FINISH
    global OVERALL_SEGMENT_COUNT, OVERALL_CORRUP_RESEND, OVERALL_TIMEOUT_RESEND, OVERALL_RESEND, OVERALL_SENDBYTE_COUNT
    global SampleRTT, EstimatedRTT, DevRTT, TimeoutInterval, alpha, beta
    global corruption_flag, timeout_flag
    global t_start, t_stop, sp_t_start, sp_t_stop, SEGMENT_TIME
    
    fin = 0                            # Transmission finishing flag    
    notes = ''                         # Represent no corruption or timeout
    
    while TRANS_FINISH == False:
        # Set a timeout interval for no response resending
        conn.settimeout(TimeoutInterval)
        
        try:
            # To receive ACK message from receiver
            ACKstatus = conn.recv(1024) 
            
            # Calculate the SampleRTT
            t_stop = time.time()
            SampleRTT = t_stop - t_start
            EstimatedRTT = (1 - alpha) * EstimatedRTT + alpha * SampleRTT
            DevRTT = (1 - beta) * DevRTT + beta * abs(SampleRTT - EstimatedRTT)
            TimeoutInterval = EstimatedRTT + 4 * DevRTT
        
            # For the case that receiver received the packet successfully
            if ACKstatus[ACKstatus.find(',')+1:] == str(SEQUENCE_NUM + MAXSEGMENTSIZE):
                trans_status = 'Succeed'
                
                # Determine the notes part in logfile
                if corruption_flag == True:
                    notes = 'Corrup_resend'
                elif timeout_flag == True:
                    notes = 'Timeout_resend'
                else:
                    notes = ''
                
                logwriting((SEQUENCE_NUM / MAXSEGMENTSIZE +1), 'forward', strftime("%d,%b,%Y %H:%M:%S", time.localtime()), socket.gethostbyname(socket.gethostname()), rft_sender.remote_IP, SEQUENCE_NUM, ACK_NUM, str(1), fin, EstimatedRTT, TimeoutInterval, trans_status, notes)
                logwriting('-', 'backward', strftime("%d,%b,%Y %H:%M:%S", time.localtime()), rft_sender.remote_IP, socket.gethostbyname(socket.gethostname()), ACKstatus[0:ACKstatus.find(',')], ACKstatus[ACKstatus.find(',')+1:], 1, fin, '-', '-', 'Received', '-')                
                SEQUENCE_NUM = SEQUENCE_NUM + MAXSEGMENTSIZE              # Update sequence #
                OVERALL_SEGMENT_COUNT = OVERALL_SEGMENT_COUNT + 1         # Update overall segment sending counter
                OVERALL_SENDBYTE_COUNT = OVERALL_SENDBYTE_COUNT + len(rft_sender.total_sending_message[SENDINGPOINTER])
                SENDINGPOINTER = SENDINGPOINTER + 1                       # Update segment sending pointer
                # Update notes flags
                corruption_flag = False
                timeout_flag = False
                sp_t_stop = time.time()
                SEGMENT_TIME = sp_t_stop - sp_t_start
                sp_t_start = time.time()
            # For the case that last packet is not received successfully           
            else:
                trans_status = 'Failed'
                
                # Determine the notes part in logfile
                if corruption_flag == True:
                    notes = 'Corrup_resend'
                elif timeout_flag == True:
                    notes = 'Timeout & Corrup_resend'
                else:
                    notes = ''
                
                logwriting((SEQUENCE_NUM / MAXSEGMENTSIZE + 1), 'forward', strftime("%d,%b,%Y %H:%M:%S", time.localtime()), socket.gethostbyname(socket.gethostname()), rft_sender.remote_IP, SEQUENCE_NUM, ACK_NUM, str(1), fin, EstimatedRTT, TimeoutInterval, trans_status, notes)
                logwriting('-', 'backward', strftime("%d,%b,%Y %H:%M:%S", time.localtime()), rft_sender.remote_IP, socket.gethostbyname(socket.gethostname()), ACKstatus[0:ACKstatus.find(',')], ACKstatus[ACKstatus.find(',')+1:], 1, 0, '-', '-', 'Received', '-')
                OVERALL_CORRUP_RESEND = OVERALL_CORRUP_RESEND + 1         # Update overall corruption resending segment counter
                OVERALL_RESEND = OVERALL_RESEND + 1                       # Update overall resending segment counter
                OVERALL_SEGMENT_COUNT = OVERALL_SEGMENT_COUNT + 1         # Update overall segment sending counter 
                # Update notes flags
                corruption_flag = True                                    
                timeout_flag = False
        
            # Update ACK # according to the sequence # received in the ACK message
            ACK_NUM = int(ACKstatus[0:ACKstatus.find(',')]) + 1
        
            # If the segments not reach the end of the file, then send next segment
            if SENDINGPOINTER < len(rft_sender.total_sending_message):
                if SENDINGPOINTER == (len(rft_sender.total_sending_message) - 1):
                    fin = 1
                # Pack the header and segment without checksum part to calculate checksum
                sumstring = rft_header(rft_sender.remote_port, rft_sender.ack_port_num, SEQUENCE_NUM, ACK_NUM, 1, fin, 0, rft_sender.total_sending_message[SENDINGPOINTER])
                # Calculate checksum
                rft_checksum = checksum_calc(sumstring) 
                # Pack the final header and segment with the calculated checksum part                 
                sendchunk = rft_header(rft_sender.remote_port, rft_sender.ack_port_num, SEQUENCE_NUM, ACK_NUM, 1, fin, rft_checksum, rft_sender.total_sending_message[SENDINGPOINTER])
                # Use UDP to send the message
                try:
                    UDPsocket.sendto(sendchunk, (UDP_HOST, UDP_PORT)) 
                    t_start = time.time()                                 # Start calculate the SampleRTT here
                except socket.error, msg:
                    print 'Error Code : ' + str(msg[0]) + ' Message ' + msg[1]
                    sys.exit()
                    
            # If the segments reach the end of the file, stop sending
            else:
                TRANS_FINISH = True
                
        # If timeout exception occurs, resend the former packet
        except socket.timeout:
            trans_status = 'Timeout'
            
            # Determine the notes part in logfile
            if corruption_flag == True:
                notes = 'Corrup & Timeout_resend'
            elif timeout_flag == True:
                notes = 'Timeout_resend'
            else:
                notes = ''
            
            logwriting((SEQUENCE_NUM / MAXSEGMENTSIZE + 1), 'forward', strftime("%d,%b,%Y %H:%M:%S", time.localtime()), socket.gethostbyname(socket.gethostname()), rft_sender.remote_IP, SEQUENCE_NUM, ACK_NUM, str(1), str(0), EstimatedRTT, TimeoutInterval, trans_status, notes)
            UDPsocket.sendto(sendchunk, (UDP_HOST, UDP_PORT))             # Resend the last packet
            t_start = time.time()                                         # Restart to calculate the SampleRTT here
            OVERALL_TIMEOUT_RESEND = OVERALL_TIMEOUT_RESEND + 1           # Update overall timeout resending counter
            OVERALL_RESEND = OVERALL_RESEND + 1                           # Update overall resending segment counter
            OVERALL_SEGMENT_COUNT = OVERALL_SEGMENT_COUNT + 1             # Update overall segment sending counter
            # Update notes flags
            corruption_flag = False
            timeout_flag = True
         
    # Close the thread
    thread.exit()        
    
    return
    

#------------------Entry of the program----------------
if __name__ == '__main__':
    #Invoke the program to import <filename>, <remote_IP>, <remote_port>, <ack_port_num>, <log_filename> and <window_size>
    if(len(sys.argv) != 6 and len(sys.argv) != 7):
        print 'Please follow the format to invoke the program:'
        print 'python sender.py <filename> <remote_IP> <remote_port> <ack_port_num> <log_filename> <window_size>'
        print '<window_siz> is optional'
        sys.exit()
    filename = sys.argv[1]
    remote_IP = sys.argv[2]
    #Check the integrate values
    try:
        remote_port = int(sys.argv[3])
    except ValueError:
        print '<remote_port> should be an integrate.'
        sys.exit()
    try:
        ack_port_num = int(sys.argv[4])
    except ValueError:
        print '<ack_port_num> should be an integrate.'
        sys.exit()
    log_filename = sys.argv[5]
    #Choose a window_size from command, otherwise using a default value
    try:
        window_size = int(sys.argv[6])
    except ValueError:
        print '<window_size> should be an integrate'
        sys.exit()
    except:
        window_size = 1
        
    #Initialization of the object of Sender class
    rft_sender = Sender(filename, remote_IP, remote_port, ack_port_num, log_filename, window_size)
    rft_sender.filereading()                                         # Read the message to be sent from the file
      
    #To set up a UDP socket for sending the data
    UDPsocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)   
    UDP_HOST = rft_sender.remote_IP;
    UDP_PORT = rft_sender.remote_port;
    
    #To send the first segment to the receiver
    sumstring = rft_header(rft_sender.remote_port, rft_sender.ack_port_num, SEQUENCE_NUM, ACK_NUM, 1, 0, 0, rft_sender.total_sending_message[SENDINGPOINTER])
    rft_checksum = checksum_calc(sumstring)
    sendchunk = rft_header(rft_sender.remote_port, rft_sender.ack_port_num, SEQUENCE_NUM, ACK_NUM, 1, 0, rft_checksum, rft_sender.total_sending_message[SENDINGPOINTER])
    try:
        UDPsocket.sendto(sendchunk, (UDP_HOST, UDP_PORT)) 
        START_TIME = time.time()                                     # Transmission start time
        sp_t_start = time.time()
    except socket.error, msg:
        print 'Error Code : ' + str(msg[0]) + ' Message ' + msg[1]
        sys.exit()
        
    #To set up a TCP socket for receiving the ACK
    TCPsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    TCP_HOST = socket.gethostbyname(socket.gethostname())
    TCP_PORT = rft_sender.ack_port_num
    
    #TCP binding and listening
    TCPsocket.bind((TCP_HOST, TCP_PORT))
    TCPsocket.listen(10)
    
    #Display some information
    print '-' * 78
    rft_sender.displaySender()
    print 'Sender side IP:'.ljust(25), socket.gethostbyname(socket.gethostname())
    print '-' * 78
    print '>> File sending...'
    
    #Write log file title
    logwriting('Segment#','Trans_direction', 'Timestamp', 'Source', 'Destination', 'Sequence #', 'ACK #', 'ACK', 'FIN', 'EstimateRTT(s)', 'Timeout(s)', 'Trans_status', 'resend_marks')
    
    #Accept TCP connection from receiver and set up a thread to deal with the ACK from receiver
    tcp_connected = False                        # TCP connection setting up flag
    TCPsocket.settimeout(TimeoutInterval)        # Set a timeout in case that the first packet is lost (this will prevent the receiver from setting up a tcp connection)
    while tcp_connected == False:
        try:
            conn, addr = TCPsocket.accept()
                
            #Create a new son thread for each of the connected clients
            new_thread = Thread(target = dealwithACK, args = (conn,addr,))
            new_thread.setDaemon(True)
            new_thread.start()
            
            tcp_connected = True                 # Update the TCP setting up flag
            
        # If timeout occurs, resend the first packet
        except socket.timeout:
            trans_status = 'Timeout'
            
            # Determine the notes part in logfile
            if corruption_flag == True:
                notes = 'Corrup & Timeout_resend'
            elif timeout_flag == True:
                notes = 'Timeout_resend'
            else:
                notes = ''
            
            logwriting((SEQUENCE_NUM / MAXSEGMENTSIZE + 1), 'forward', strftime("%d,%b,%Y %H:%M:%S", time.localtime()), socket.gethostbyname(socket.gethostname()), rft_sender.remote_IP, SEQUENCE_NUM, ACK_NUM, str(1), str(0), EstimatedRTT, TimeoutInterval, trans_status, notes)
            UDPsocket.sendto(sendchunk, (UDP_HOST, UDP_PORT))             # Resend the last packet
            t_start = time.time()                                         # Restart to calculate the SampleRTT here
            OVERALL_TIMEOUT_RESEND = OVERALL_TIMEOUT_RESEND + 1           # Update overall timeout resending counter
            OVERALL_RESEND = OVERALL_RESEND + 1                           # Update overall resending segment counter
            OVERALL_SEGMENT_COUNT = OVERALL_SEGMENT_COUNT + 1             # Update overall segment sending counter
            # Update notes flags
            corruption_flag = False
            timeout_flag = True        
            
        except KeyboardInterrupt:                #To shut down the sender with 'Ctrl + C' gracefully
            sys.exit()
    
    while TRANS_FINISH == False:
        try:
            DURATION = int((time.time() - START_TIME))
            DURATION_MIN = DURATION / 60
            DURATION_S = DURATION % 60
            INS_SPEED = str(round ((MAXSEGMENTSIZE / SEGMENT_TIME), 2))
            print '\r>> Transmission time: %d min %d s, speed: %s B/s, finished %d%%     ' % (DURATION_MIN, DURATION_S, INS_SPEED, ((OVERALL_SENDBYTE_COUNT / float(rft_sender.file_size)) * 100)),
            
            sys.stdout.flush()
            time.sleep(1)
            #Here for display percentage, speed and used time
        except KeyboardInterrupt:
            sys.exit()
    
    # Calculate transmission time
    STOP_TIME = time.time()
    DURATION = int((STOP_TIME - START_TIME))
    DURATION_MIN = DURATION / 60
    DURATION_S = DURATION % 60
            
    # Display the transmission results   
    print '\r>> Transmission time: %d min %d s, speed: %s B/s, finished %d%%     ' % (DURATION_MIN, DURATION_S, INS_SPEED, ((OVERALL_SENDBYTE_COUNT / float(rft_sender.file_size)) * 100))
    sys.stdout.flush()
    print '-' * 78
    print 'Total bytes sent:'.ljust(50), OVERALL_SENDBYTE_COUNT
    print 'Total Segments sent:'.ljust(50), OVERALL_SEGMENT_COUNT
    print 'Segments retransmitted due to corruption:'.ljust(50), OVERALL_CORRUP_RESEND
    print 'Segments retransmitted due to sender timeout:'.ljust(50), OVERALL_TIMEOUT_RESEND
    print 'Total retransmitted segments:'.ljust(50), OVERALL_RESEND
    print 'Transmission time (s):'.ljust(50), round((STOP_TIME - START_TIME), 2)
    print 'Average transmission speed (B/s):'.ljust(50), round(((OVERALL_SEGMENT_COUNT - OVERALL_RESEND) * MAXSEGMENTSIZE) / (STOP_TIME - START_TIME), 2)
    print '-' * 78
    
    sys.exit()
    
