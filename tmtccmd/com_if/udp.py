"""UDP Communication Interface"""
import select
import socket
from typing import Optional

from tmtccmd.logging import get_console_logger
from tmtccmd.com_if import ComInterface
from tmtccmd.tm import TelemetryListT
from tmtccmd.com_if.tcpip_utils import EthAddr

LOGGER = get_console_logger()


class UdpComIF(ComInterface):
    """Communication interface for UDP communication"""

    def __init__(
        self,
        com_if_id: str,
        send_address: EthAddr,
        max_recv_size: int,
        recv_addr: Optional[EthAddr] = None,
    ):
        """Initialize a communication interface to send and receive UDP datagrams.

        :param send_address:
        :param max_recv_size:
        :param recv_addr:
        """
        super().__init__(com_if_id=com_if_id)
        self.udp_socket = None
        self.send_address = send_address
        self.recv_addr = recv_addr
        self.max_recv_size = max_recv_size

    def __del__(self):
        try:
            self.close()
        except IOError:
            LOGGER.warning("Could not close UDP communication interface")

    def initialize(self, args: any = None) -> any:
        pass

    def open(self, args: any = None):
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Bind is possible but should not be necessary, and introduces risk of port already
        # being used.
        # See: https://docs.microsoft.com/en-us/windows/win32/api/winsock/nf-winsock-bind
        if self.recv_addr is not None:
            LOGGER.info(
                f"Binding UDP socket to {self.recv_addr.ip_addr} and port {self.recv_addr.port}"
            )
            self.udp_socket.bind(self.recv_addr.to_tuple)
        # Set non-blocking because we use select
        self.udp_socket.setblocking(False)

    def is_open(self) -> bool:
        return self.udp_socket is not None

    def close(self, args: any = None) -> None:
        if self.udp_socket is not None:
            self.udp_socket.close()

    def send(self, data: bytes):
        if self.udp_socket is None:
            return
        bytes_sent = self.udp_socket.sendto(data, self.send_address.to_tuple)
        if bytes_sent != len(data):
            LOGGER.warning("Not all bytes were sent!")

    def data_available(self, timeout: float = 0, parameters: any = 0) -> bool:
        if self.udp_socket is None:
            return False
        ready = select.select([self.udp_socket], [], [], timeout)
        if ready[0]:
            return True
        return False

    def receive(self, poll_timeout: float = 0) -> TelemetryListT:
        packet_list = []
        if self.udp_socket is None:
            return packet_list
        try:
            while self.data_available(poll_timeout):
                data, sender_addr = self.udp_socket.recvfrom(self.max_recv_size)
                packet_list.append(bytearray(data))
            return packet_list
        except ConnectionResetError:
            LOGGER.warning("Connection reset exception occured!")
            return []
