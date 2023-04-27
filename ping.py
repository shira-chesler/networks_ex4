import sys
import struct
import socket
import time

# constants
ICMP_ECHO_REQUEST = 8
ICMP_ECHO_CODE = 0
ICMP_ECHO_REPLY = 0

# globals
host = 0
seq_number = 0


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


def create_packet() -> tuple:
    """
    creates a packet to send
    :return: the data, and the packet created
    """
    global seq_number
    seq_number += 1

    # creates a initial header for the packet
    header = struct.pack('!BBHHH', ICMP_ECHO_REQUEST, ICMP_ECHO_CODE, 0, 0, seq_number)

    # create data in bits
    data = b'Hello world'

    # calculates the checksum for the packet
    checksum = generate_checksum(header + data)

    # creates an header with checksum
    header = struct.pack('!BBHHH', ICMP_ECHO_REQUEST, ICMP_ECHO_CODE, checksum, 0, seq_number)
    packet = header + data
    return data, packet


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
        exit(1)


def recv_ping(raw_socket):
    """
    receives ICMP packet reply from the host and parses it
    :param raw_socket: socket to receive from
    :return: string of statistics or None (if fails)
    """
    start_time = time.time()
    packet, addr = raw_socket.recvfrom(1024)
    icmp_header = packet[20:28]

    # reads and convert the given back packet data
    respond_type, code, checksum, p_id, seq = struct.unpack(
        "bbHHh", icmp_header
    )

    if respond_type == ICMP_ECHO_REPLY:
        return f'{len(packet[28:])} bytes from {addr[0]} icmp_seq={int(seq / 256)} ttl={packet[8]}' \
               f' time={(time.time() - start_time) * 1000:.3f} ms'

    elif respond_type == 3:
        print(f"Host {host} unreachable")
        return


def ping_flow() -> None:
    """
    the main flow of the ping program
    """
    global host
    if len(sys.argv) != 2:
        print('Usage:sudo python3 ping.py <ip>')
        return

    # ip user entered
    host = sys.argv[1]

    raw_socket = None
    try:
        # opens raw socket - allows to communicate with icmp (pings)
        raw_socket = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
    except socket.error:
        print('Error: Failed to create socket')
        exit(1)

    # if it's the first sending
    first_send = True
    try:
        while True:
            data, packet = create_packet()
            if first_send:
                print(f'PING', host, f'({host})', f'{len(data)} data bytes')
                first_send = False
            send_ping(raw_socket, packet)
            statistics = recv_ping(raw_socket)
            if statistics is not None:
                print(statistics)
            else:
                print('Request timed out')
            time.sleep(1)
    except KeyboardInterrupt:
        print('\nPing stopped, closing program')
    finally:
        raw_socket.close()


if __name__ == '__main__':
    ping_flow()
