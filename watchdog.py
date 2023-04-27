import socket
from time import sleep

# constant
PORT = 3000


def create_watchdog_tcp_socket() -> None:
    """
    creates watchdog TCP socket and opens watchdog timer
    """
    try:
        # creates watchdog TCP socket and makes the port reusable
        watchdog = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        watchdog.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        watchdog.bind(('', PORT))
        watchdog.listen(1)
        print("-----WATCHDOG IS UP-------")

        while True:
            ping_socket, address = watchdog.accept()
            print(f"-----PING Program connected------")
            status = watchdog_timer(ping_socket)
            if status == -1:
                watchdog.close()
                ping_socket.close()
                # indicates got out because of watchdog
                exit(2)
            break
    except socket.error:
        print(f"Socket Error {socket.error}")
        exit(1)


def watchdog_timer(betterping_socket):
    """
    opens a timer to 10 seconds and resets it if got life signal
    :param betterping_socket: the betterping_socket to get life signals from
    :return: -1 if didn't get life signal for 10 seconds
    """
    betterping_socket.setblocking(False)
    timer = 0
    while timer < 10:
        sleep(1)
        timer += 1
        if timer == 10:
            break
        try:
            # check if got life signal from betterping
            message_received = betterping_socket.recv(5)
            if len(message_received) > 0:
                timer = 0

        except BlockingIOError:
            pass
    return -1
