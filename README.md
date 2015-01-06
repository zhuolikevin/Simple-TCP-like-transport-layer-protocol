Simple-TCP-like-transport-layer-protocol
========================================

It is a simplified TCP­-like transport layer protocol. The protocol should provide reliable, in order delivery of a stream of bytes. It can recover from in­-network packet loss, packet corruption, packet duplication and packet reordering and should be able cope with dynamic network delays. However, it doesn’t support congestion or flow control.


a. A brief description of the code

This is a simplified TCP-like transport layer protocol program for reliable transferring, based on socket programming and multi-thread processing. It contains two code files (sender.py & receiver.py) and a sample file (sender_file.txt) attached for testing. The sender and receiver program can be invoked in given format. (details at section e) And then the file in sender side (e.g. sender_file.txt if used) will be send to the receiver at given IP address and port. It can survive packet loss, pack corruption, pack duplication and delays. (Because I do not implement functions for window side more than 1, it is a STOP-AND-WAIT PROTOCOL. So there will be no reorder even if we use the proxy to emulate that. 

The brief structure of the two python files are as follows.
sender.py:
The codes contains a class Sender to read the file and record some of the variables. The main thread first gets the input arguments user given in the command line, then reads the file to be sent and sets up a UDP socket which is packed with 20 bytes header and file segments. It waits for the TCP connection request from the receive which indicates the first UDP datagram is received. Then the sender sets up a son thread to deal with the ack from receiver and sending new segments until the whole file is sent successfully.

receiver.py:
The codes also contains a class Receiver to undertake the some of the receiver works. The main thread waits for the UDP datagram from the sender after gets the input arguments from the command line. Then it check the datagram and set up a tcp connection with the sender to send the ACK. A son thread is set up to continuously receive the UDP datagrams and send the ACK.

b. Program features

1) TCP segment structure used

|Source port# (2 Bytes) | Destination port# (2 Bytes)|

|                  Sequence Number (4 Byte)                    |

|              Acknowledgment Number (4 Byte)             |

| ACK(1 bit)  |  FIN(1 bit)  |        Unused (30 bits)       |

|      Checksum(2 Bytes)     |     Unused (2 Bytes)      |

|                User Data Segment (576 Bytes)               |


Notes: The total length of header is 20 Byte. Unused bits in the header are set to be 0. For ACK bit, it is alway 1 because it seems to be useless in this implementation. The User data segment is constantly 576 Bytes. IF THE LAST SEGMENT OF THE FILE IS NOT SUFFICIENT, ‘’ WILL BE ADDED TO MAKE IT AS 576 BYTES.

2) States in sender and receiver

sender:
-SEND DATA: The sender will send next segment if the last segment is acknowledged to be received successfully
-FAILED RESED: The sender will resend last already sent segment if it is acknowledged to be not received successfully (with corruption) 
-TIMEOUT RESEND: The sender will resend last already sent segment if it does not receive the acknowledgment in expected time (may due to delay or loss) 

receiver:
-RECEIVE PACKET WITHOUT CORRUPTION: If a packet received is new and without corruption, the receiver will receive the packet and write the data to the file. Then send a ACK with expectation for next segment.
-DISCARD PACKET WITH CORRUPTION: If a packet receive a packet with corruption, it will be discarded and a ack with current expected segment will be sent to the sender.
-DISCARD PACKET ALREADY ACKNOWLEDGED: If a packet is received with a sequence number already acknowledged, it will be discarded and no ACK will be sent.

3) Loss recovery mechanism

If the sender do not receive a ACK from the receiver for more then the TimeoutInterval (dynamically calculated in the program), it will resend this packet. Because the receiver will discard already ACKed the packet, there is no problem for the possibility of duplicately sending if it is caused by delay instead of loss.


c. Details on development environment

Operating System:    Ubuntu 12.04 on VM (Parallels Desktop 9)
IDE:                 Eclipse 4.4.1
Language:            Python 2.7.3


d. Instructions on how to run the codes

Put sender.py and file to transfer (e.g. sender_file.txt) in the same dictionary.

FIRST, run the proxy in the setting you would like to test.

SECOND, run the receiver.py use the format in section e.

Finally, run the sender.py use the format in section e.


e. Sample command and usage scenario

For proxy:
root@parallels-Parallels-Virtual-Platform:/home/parallels/Desktop/newudpl-1.5# ./newudpl -vv -i 127.0.0.1:* -o 127.0.1.1:4119 -d1.7 -B 10000 -L 20


For receiver:
(Invoke format “python receiver.py <filename> <listening_port> <sender_IP> <sender_port> <log_filename>”)

parallels@parallels-Parallels-Virtual-Platform:~/Desktop/Parallels Shared Folders/Home/Documents/workspace/Reliablefiletrans/reliablefiletrans$ python receiver.py rcv_file.txt 4119 127.0.1.1 4118 rcv_logfile.txt


For sender:
(Invoke format “python sender.py <filename> <remote_IP> <remote_port> <ack_port_num> <log_filename> <window_size>”)
NOTE:<window_size> is not implemented in the codes. It is set to be 1 regardless what you entered. You can also ignore it as the following sample.

parallels@parallels-Parallels-Virtual-Platform:~/Desktop/Parallels Shared Folders/Home/Documents/workspace/Reliablefiletrans/reliablefiletrans$ python sender.py sender_file.txt 127.0.1.1 41192 4118 send_logfile.txt



f. Additional functions

1) Extra items in the log files

[DESRIPTION] Some addition items is added to the log files. Let’s take a look at it.

Segment#  Trans_direction     Timestamp             Source         Destination    Sequence # ACK #  ACK  FIN  EstimateRTT(s) Timeout(s)     Trans_status   resend_marks
1         Sender -> Receiver  06,Nov,2014 19:53:53  127.0.1.1      127.0.1.1      0          0      1    0    1.96477398276  2.21135610342  Failed                   
-         Receiver -> Sender  06,Nov,2014 19:53:53  127.0.1.1      127.0.1.1      0          0      1    0    -              -              Received       -         
1         Sender -> Receiver  06,Nov,2014 19:53:55  127.0.1.1      127.0.1.1      0          1      1    0    1.93254335597  2.34309433401  Failed         Corrup_resend
-         Receiver -> Sender  06,Nov,2014 19:53:55  127.0.1.1      127.0.1.1      1          0      1    0    -              -              Received       -         
1         Sender -> Receiver  06,Nov,2014 19:53:57  127.0.1.1      127.0.1.1      0          2      1    0    1.90478206566  2.40702433139  Succeed        Corrup_resend
-         Receiver -> Sender  06,Nov,2014 19:53:57  127.0.1.1      127.0.1.1      2          576    1    0    -              -              Received       -         
2         Sender -> Receiver  06,Nov,2014 19:53:58  127.0.1.1      127.0.1.1      576        3      1    0    1.88038168132  2.427866071    Succeed                  
-         Receiver -> Sender  06,Nov,2014 19:53:58  127.0.1.1      127.0.1.1      3          1152   1    0    -              -              Received       -         
3         Sender -> Receiver  06,Nov,2014 19:54:00  127.0.1.1      127.0.1.1      1152       4      1    0    1.85876234926  2.42071096593  Succeed                  
-         Receiver -> Sender  06,Nov,2014 19:54:00  127.0.1.1      127.0.1.1      4          1728   1    0    -              -              Received       -         
4         Sender -> Receiver  06,Nov,2014 19:54:02  127.0.1.1      127.0.1.1      1728       5      1    0    1.83988358068  2.39349642324  Succeed                  
-         Receiver -> Sender  06,Nov,2014 19:54:02  127.0.1.1      127.0.1.1      5          2304   1    0    -              -              Received       -         
5         Sender -> Receiver  06,Nov,2014 19:54:04  127.0.1.1      127.0.1.1      2304       6      1    0    1.82343639236  2.3537763425   Succeed                  
-         Receiver -> Sender  06,Nov,2014 19:54:04  127.0.1.1      127.0.1.1      6          2880   1    0    -              -              Received       -         
6         Sender -> Receiver  06,Nov,2014 19:54:06  127.0.1.1      127.0.1.1      2880       7      1    0    1.82343639236  2.3537763425   Timeout                  
6         Sender -> Receiver  06,Nov,2014 19:54:08  127.0.1.1      127.0.1.1      2880       7      1    0    1.82343639236  2.3537763425   Timeout        Timeout_resend
6         Sender -> Receiver  06,Nov,2014 19:54:10  127.0.1.1      127.0.1.1      2880       7      1    0    1.80908822654  2.30728034987  Failed         Timeout & Corrup_resend

This is part of rows for the sender_logfile. For each column, its representation is as follows:

-Segment#: This stands for the number of segment for the packet. The same number represents the same segment that is for some reason (specified in the resend_marks) sent for several times. It is only for the packet from sender to receiver. In receiver to sender rows, they will be set as ‘-‘.

-Trans_direction: This represents the direction of sending.(Sender -> Receiver or Receiver -> Sender)

-Timestamp: The sending time of the packet

-Source: Sender IP

-Destination: Receiver (proxy) IP

-Sequence#: For Sender -> Receiver, it is started from 0 and then added with the data segment size (as TCP defines). For Receiver -> Sender, it is started from 0 and then added with 1.

-ACK#: For Sender -> Receiver, it is the sequence# of ACK packet from receiver plus 1. For Receiver -> Sender, it is the sequence# of data packet from sender plus 1.

-ACK: ACK flag in the header, always be 1.

-FIN: FIN flag in the header. It is 0 for most sending packets and 1 for the last packet. (not presented above)  
   
-EstimatedRTT(s): Estimated RTT updates for each trip. It will finally converge to the delay time set in the proxy.

-Timeout(s): TimeoutInterval updates for each trip. It will finally converge to the delay time set in the proxy.

-Trans_status: 
For Sender -> Receiver, there are THREE status: Failed (received with corruption), Succeed (received without corruption), Timeout (do not response in the time interval)
For Receiver -> Sender, there is ONLY ONE status: Received (It is because the ACK packet from receiver to sender is sent by TCP, so it will always received correctly)

-resend_marks:This is only for Sender -> Receiver direction, used to mark the REASON OF RESENDING. There are FOUR status:
Corrup_resend: This packet is used for a resending because of corruption(indicates that last packet is ‘Failed’ in Trans_status)
Timeout_resend: This packet is used for a resending because of timeout(indicates that last packet is ‘Timeout’ in Trans_status)
Timeout & Corrup_resend: LAST packet is used to resend for a timeout packet but THIS packet is corrupted(indicates that last packet is ‘Timeout’ while this is ‘Failed’)
Corrp & Timeout_resend(not presented in the sample): LAST packet is used to resend for a corruption packet but we do not get response for THIS packet(indicates that last packet is ‘Failed’ while this is ‘Timeout’)

The columns in receive log file are only part of the sender log file, so we do not describe here.
 
This implementation can be used for the controller now the exact details about the transmission.

2) Transmission time, instant speed and finishing percentage display

[DESCRIPTION] As you may seen in the sample of section e, during the process of file transmission, the transmission time, instant speed and finishing percentage will be dynamically displayed. An the at the end of the transmission, statistics as follows will be displayed:

Total bytes sent:                                  8111
Total Segments sent:                               37
Segments retransmitted due to corruption:          13
Segments retransmitted due to sender timeout:      9
Total retransmitted segments:                      22
Transmission time (s):                             66.85
Average transmission speed (B/s):                  129.25

NOTE: instant speed equals to Bytes transmitted in a segment over the time it cost(from first segment sent to finally successfully received). Average speed equals to Total transmitted bytes over total transmission time.
