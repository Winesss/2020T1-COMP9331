from socket import *
import sys
import datetime

#get arguments
serverName = sys.argv[1]
#serverName="127.0.0.1"
serverPort = int(sys.argv[-1])
#serverPort=12000

#create socket
clientSocket = socket(AF_INET, SOCK_DGRAM)
#time limit
clientSocket.settimeout(1)

i=0
rttTime=[]
num_succ=0
while i<10:
    seq_num=str(i)
    date_send=datetime.datetime.now()
    message = 'PING ' + seq_num + ' ' + str(date_send) + '\r' + '\n'
    try:
        clientSocket.sendto(message,(serverName, serverPort))
        modifiedMessage, serverAddress = clientSocket.recvfrom(2048)
        date_current=datetime.datetime.now()
        rtt=(date_current-date_send).microseconds/1000
        print('ping to '+serverName+', '+'sqe = '+seq_num+', '+'rtt = '+str(rtt)+' ms')
        rttTime.append(rtt)
        num_succ+=1
    except:
        print('ping to '+serverName+', '+'sqe = '+seq_num+', '+'timeout')
    i+=1

#related calculations
max_time=max(rttTime)
min_time=min(rttTime)
sum_time=0
for i in range(len(rttTime)):
    sum_time=sum_time+rttTime[i]
avg_time=sum_time/num_succ
print('round-trip min/avg/max = '+str(min_time)+'/'+str(avg_time)+'/'+str(max_time)+' ms')
clientSocket.close()

