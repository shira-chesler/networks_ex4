import errno
import socket
import struct
import sys
import time
import threading

from watchdog import create_watchdog_tcp_socket
from ping import ICMP_ECHO_REPLY, ICMP_ECHO_REQUEST, ICMP_ECHO_CODE

# constants
WATCHDOG_PORT = 3000
WATCHDOG_IP = 'localhost'

# global
host = 0
seq = 0


def generate_checksum(packet) -> int:
    """
    this code is based on the generate checksum code from the Moodle in C converted to python
    :param packet: packet to calculate checksum to
    :return: packet checksum
    """
    checksum = 0
    count_to = (len(packet) // 2) * 2
    for i in range(0, count_to, 2):
        checksum += (packet[i] << 8) + packet[i + 1]
    if count_to < len(packet):
        checksum += packet[len(packet) - 1] << 8
    checksum = (checksum >> 16) + (checksum & 0xFFFF)
    checksum += checksum >> 16
    return (~checksum) & 0xFFFF


# Create an ICMP packet
def create_packet():
    """
    creates a packet to send
    :return: the data, and the packet created
    """
    global seq
    seq += 1
    # Generate a dummy header with a 0 checksum
    header = struct.pack('!BBHHH', ICMP_ECHO_REQUEST, ICMP_ECHO_CODE, 0, 0, seq)
    # Generate a timestamp for the data
    data = b'Hello world'
    # Calculate the checksum for the packet
    checksum = generate_checksum(header + data)
    # Create the packet with the correct checksum
    header = struct.pack('!BBHHH', ICMP_ECHO_REQUEST, ICMP_ECHO_CODE, checksum, 0, seq)
    packet = header + data
    return data, packet


# Send an ICMP packet to the specified host
def send_ping(raw_socket, packet):
    """
     sends packet to host
     :param raw_socket: raw socket that sends
     :param packet: the packet to sends
     """
    try:
        raw_socket.sendto(packet, (host, 1))
    except socket.error:
        print('Error: Failed to send packet')
        sys.exit()


def recv_ping(betterping_socket):
    """
    receives ICMP packet reply from the host and parses it
    :param betterping_socket: socket to receive from
    :return: string of statistics or 0 (if fails)
    """
    start_time = time.time()

    # not getting anything not blocking the main thread
    betterping_socket.setblocking(False)

    packet = None
    address = None

    try:
        packet, address = betterping_socket.recvfrom(1024)

    except socket.error as e:
        # if error occurs cause didn't receive anything
        if e.errno == errno.EWOULDBLOCK:
            betterping_socket.setblocking(True)
            return 0

    icmp_header = packet[20:28]

    # reads and convert the given back packet data
    respond_type, code, checksum, p_id, seq_number = struct.unpack(
        "bbHHh", icmp_header)
    if respond_type == ICMP_ECHO_REPLY:
        betterping_socket.setblocking(True)
        return f'{len(packet[28:])} bytes from {address[0]} icmp_seq={int(seq_number / 256)}' \
               f' ttl={packet[8]} time={(time.time() - start_time) * 1000:.3f} ms'


def ping_flow(betterping_socket, watchdog_thread) -> None:
    """
    the main flow of the betterping program
    :param betterping_socket: the TCP socket that's connected to the watchdog
    :param watchdog_thread: the watchdog thread
    """
    global host
    host = sys.argv[1]
    raw_socket = None
    try:
        raw_socket = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)

    except socket.error:
        print('Error: Failed to create socket')
        exit(1)

    status = True
    first_send = True
    try:
        while watchdog_thread.is_alive():
            data, packet = create_packet()
            send_ping(raw_socket, packet)
            if first_send is True:
                print(f'PING', host, f'({host})', f'{len(data)} data bytes')
                first_send = False
            # if got a reply - sends alive message to the watchdog
            if status is True:
                betterping_socket.send("ping".encode())
            statistics = recv_ping(raw_socket)
            if statistics != 0:
                print(statistics)
                status = True
            if statistics == 0:
                time.sleep(1)
                status = False
                continue
            time.sleep(1)
        print(f"server {host} cannot be reached.")
    except KeyboardInterrupt:
        print('\nPing stopped, closing program')
    finally:
        betterping_socket.close()
        raw_socket.close()
        exit(1)


def create_tcp_socket(watchdog_thread) -> None:
    """
    opens TCP socket, connect through it to te watchdog and starts the ping flow
    :param watchdog_thread: the watchdog thread
    """
    try:
        ping_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        ping_socket.connect((WATCHDOG_IP, WATCHDOG_PORT))
        ping_flow(ping_socket, watchdog_thread)
    except socket.error:
        print(f"Socket Error {socket.error}")
        exit(1)


def betterping_starter() -> None:
    """
    starting the betterping program
    """
    if len(sys.argv) != 2:
        print('Usage: python3 betterping.py <ip>')
        exit(1)

    # creates watchdog thread, makes it a daemon thread and activates it
    watchdog_thread = threading.Thread(target=create_watchdog_tcp_socket)
    watchdog_thread.daemon = True
    watchdog_thread.start()

    # waits for watchdog's TCP to initialize
    time.sleep(1)
    create_tcp_socket(watchdog_thread)


if __name__ == '__main__':
    betterping_starter()
