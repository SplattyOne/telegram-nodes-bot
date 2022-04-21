import paramiko
from time import sleep


def serverScreenCommand(command, server, username,password,screenid):

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(server, username=username, password=password)
    channel = client.get_transport().open_session()
    channel.resize_pty(width=10, height = 1, width_pixels =0, height_pixels =0)
    channel.get_pty()
    channel.settimeout(20)
    
    #channel.exec_command('screen -list')
    #print(channel.recv(2048).decode('utf-8'))
    
    screenTMP = 'screen -dr ' + screenid
    print(screenTMP)
    
    channel.exec_command(screenTMP)
    channel.send(command + '\n')
    
    print(channel.recv_ready())
    sleep(2)
    print(channel.recv_ready())
    
    result = channel.recv(1024).decode('utf8') 
     
    channel.close()
    client.close()
    #print(result)
    return(result)
    
def massaCleanOutput(outputraw):
    start = outputraw.index('do not share your private key')
    outputraw2 = outputraw[start:len(outputraw)]
    start = outputraw2.index('Public key:')
    end = outputraw2.index('=====') #len(result)
    #print(start, end)
    
    return(outputraw2[start:end])

# my = massaCleanOutput(serverScreenCommand('wallet_info', '144.91.71.157', 'root','q27KCcASSGtoeKl6O7a2O6w', '7022'))