import sys
from typing import Optional, Tuple, cast

from tmtccmd.config.defs import CoreComInterfaces
from tmtccmd.config.globals import CoreGlobalIds
from tmtccmd.core.globals_manager import get_global, update_global
from tmtccmd.com_if import ComInterface
from tmtccmd.com_if.serial import (
    SerialConfigIds,
    SerialCommunicationType,
    SerialComIF,
)
from tmtccmd.com_if.ser_utils import determine_com_port, determine_baud_rate
from tmtccmd.com_if.tcpip_utils import TcpIpType, EthAddr
from tmtccmd.logging import get_console_logger
from tmtccmd.com_if.udp import UdpComIF
from tmtccmd.com_if.tcp import TcpComIF, TcpCommunicationType

LOGGER = get_console_logger()


class ComIfCfgBase:
    def __init__(
        self,
        com_if_key: str,
        json_cfg_path: str,
        space_packet_ids: Optional[Tuple[int]] = None,
    ):
        self.com_if_key = com_if_key
        self.json_cfg_path = json_cfg_path
        self.space_packet_ids = space_packet_ids


class TcpipCfg(ComIfCfgBase):
    def __init__(
        self,
        if_type: TcpIpType,
        com_if_key: str,
        json_cfg_path: str,
        send_addr: EthAddr,
        max_recv_buf_len: int,
        space_packet_ids: Optional[Tuple[int]] = None,
        recv_addr: Optional[EthAddr] = None,
    ):
        super().__init__(com_if_key, json_cfg_path, space_packet_ids)
        self.if_type = if_type
        self.send_addr = send_addr
        self.recv_addr = recv_addr
        self.max_recv_buf_len = max_recv_buf_len


def create_com_interface_cfg_default(
    com_if_key: str, json_cfg_path: str, space_packet_ids: Optional[Tuple[int]]
) -> ComIfCfgBase:
    if com_if_key == CoreComInterfaces.DUMMY.value:
        return ComIfCfgBase(com_if_key=com_if_key, json_cfg_path=json_cfg_path)
    if com_if_key == CoreComInterfaces.UDP.value:
        return default_tcpip_cfg_setup(
            com_if_key=com_if_key,
            json_cfg_path=json_cfg_path,
            tcpip_type=TcpIpType.UDP,
            space_packet_ids=space_packet_ids,
        )
    elif com_if_key == CoreComInterfaces.TCP.value:
        return default_tcpip_cfg_setup(
            com_if_key=com_if_key,
            json_cfg_path=json_cfg_path,
            tcpip_type=TcpIpType.TCP,
            space_packet_ids=space_packet_ids,
        )
    elif com_if_key in [
        CoreComInterfaces.SERIAL_DLE.value,
        CoreComInterfaces.SERIAL_FIXED_FRAME.value,
    ]:
        return None


def create_com_interface_default(cfg: ComIfCfgBase) -> Optional[ComInterface]:
    """Return the desired communication interface object

    :param cfg: Generic configuration
    :return:
    """
    from tmtccmd.com_if.dummy import DummyComIF
    from tmtccmd.com_if.qemu import QEMUComIF

    if cfg.com_if_key == "":
        LOGGER.warning("COM Interface key string is empty. Using dummy COM interface")
    try:
        if (
            cfg.com_if_key == CoreComInterfaces.UDP.value
            or cfg.com_if_key == CoreComInterfaces.TCP.value
        ):
            communication_interface = create_default_tcpip_interface(
                cast(TcpipCfg, cfg)
            )
        elif (
            cfg.com_if_key == CoreComInterfaces.SERIAL_DLE.value
            or cfg.com_if_key == CoreComInterfaces.SERIAL_FIXED_FRAME.value
        ):
            # TODO: Move to new model where config is passed externally
            communication_interface = create_default_serial_interface(
                com_if_key=cfg.com_if_key,
                json_cfg_path=cfg.json_cfg_path,
            )
        elif cfg.com_if_key == CoreComInterfaces.SERIAL_QEMU.value:
            # TODO: Move to new model where config is passed externally
            serial_cfg = get_global(CoreGlobalIds.SERIAL_CONFIG)
            serial_timeout = serial_cfg[SerialConfigIds.SERIAL_TIMEOUT]
            communication_interface = QEMUComIF(
                com_if_id=cfg.com_if_key,
                serial_timeout=serial_timeout,
                ser_com_type=SerialCommunicationType.DLE_ENCODING,
            )
            dle_max_queue_len = serial_cfg[SerialConfigIds.SERIAL_DLE_QUEUE_LEN]
            dle_max_frame_size = serial_cfg[SerialConfigIds.SERIAL_DLE_MAX_FRAME_SIZE]
            communication_interface.set_dle_settings(
                dle_max_queue_len, dle_max_frame_size, serial_timeout
            )
        else:
            communication_interface = DummyComIF()
        if communication_interface is None:
            return communication_interface
        if not communication_interface.valid:
            LOGGER.warning("Invalid communication interface!")
            return None
        communication_interface.initialize()
        return communication_interface
    except ConnectionRefusedError:
        LOGGER.exception("TCP/IP connection refused")
        if cfg.com_if_key == CoreComInterfaces.UDP.value:
            LOGGER.warning("Make sure that a UDP server is running")
        if cfg.com_if_key == CoreComInterfaces.TCP.value:
            LOGGER.warning("Make sure that a TCP server is running")
        sys.exit(1)
    except (IOError, OSError):
        LOGGER.exception("Error setting up communication interface")
        sys.exit(1)


def default_tcpip_cfg_setup(
    com_if_key: str,
    tcpip_type: TcpIpType,
    json_cfg_path: str,
    space_packet_ids: Tuple[int] = (0,),
) -> TcpipCfg:
    """Default setup for TCP/IP communication interfaces. This intantiates all required data in the
    globals manager so a TCP/IP communication interface can be built with
    :func:`create_default_tcpip_interface`

    :param com_if_key:
    :param tcpip_type:
    :param json_cfg_path:
    :param space_packet_ids:       Required if the TCP com interface needs to parse space packets
    :return:
    """
    from tmtccmd.com_if.tcpip_utils import (
        determine_udp_send_address,
        determine_tcp_send_address,
        determine_recv_buffer_len,
    )

    # TODO: Is this necessary? Where is it used?
    update_global(CoreGlobalIds.USE_ETHERNET, True)
    if tcpip_type == TcpIpType.UDP:
        send_addr = determine_udp_send_address(json_cfg_path=json_cfg_path)
    elif tcpip_type == TcpIpType.TCP:
        send_addr = determine_tcp_send_address(json_cfg_path=json_cfg_path)
    else:
        send_addr = ()
    max_recv_buf_size = determine_recv_buffer_len(
        json_cfg_path=json_cfg_path, tcpip_type=tcpip_type
    )
    cfg = TcpipCfg(
        com_if_key=com_if_key,
        if_type=tcpip_type,
        json_cfg_path=json_cfg_path,
        send_addr=send_addr,
        space_packet_ids=space_packet_ids,
        max_recv_buf_len=max_recv_buf_size,
    )
    return cfg


def default_serial_cfg_setup(com_if_key: str, json_cfg_path: str):
    """Default setup for serial interfaces

    :param com_if_key:
    :param json_cfg_path:
    :return:
    """
    baud_rate = determine_baud_rate(json_cfg_path=json_cfg_path)
    serial_port = determine_com_port(json_cfg_path=json_cfg_path)
    set_up_serial_cfg(
        json_cfg_path=json_cfg_path,
        com_if_key=com_if_key,
        baud_rate=baud_rate,
        com_port=serial_port,
    )


def create_default_tcpip_interface(tcpip_cfg: TcpipCfg) -> Optional[ComInterface]:
    """Create a default serial interface. Requires a certain set of global variables set up. See
    :py:func:`default_tcpip_cfg_setup` for more details.

    :param tcpip_cfg: Configuration parameters
    :return:
    """
    communication_interface = None
    if tcpip_cfg.com_if_key == CoreComInterfaces.UDP.value:
        communication_interface = UdpComIF(
            com_if_id=tcpip_cfg.com_if_key,
            send_address=tcpip_cfg.send_addr,
            recv_addr=tcpip_cfg.recv_addr,
            max_recv_size=tcpip_cfg.max_recv_buf_len,
        )
    elif tcpip_cfg.com_if_key == CoreComInterfaces.TCP.value:
        communication_interface = TcpComIF(
            com_if_id=tcpip_cfg.com_if_key,
            com_type=TcpCommunicationType.SPACE_PACKETS,
            space_packet_ids=tcpip_cfg.space_packet_ids,
            tm_polling_freqency=0.5,
            target_address=tcpip_cfg.send_addr,
            max_recv_size=tcpip_cfg.max_recv_buf_len,
        )
    return communication_interface


def create_default_serial_interface(
    com_if_key: str, json_cfg_path: str
) -> Optional[ComInterface]:
    """Create a default serial interface. Requires a certain set of global variables set up. See
    :func:`set_up_serial_cfg` for more details.

    :param com_if_key:
    :param json_cfg_path:
    :return:
    """
    try:
        # For a serial communication interface, there are some configuration values like
        # baud rate and serial port which need to be set once but are expected to stay
        # the same for a given machine. Therefore, we use a JSON file to store and extract
        # those values
        if (
            com_if_key == CoreComInterfaces.SERIAL_DLE.value
            or com_if_key == CoreComInterfaces.SERIAL_FIXED_FRAME.value
            or com_if_key == CoreComInterfaces.SERIAL_QEMU.value
        ):
            default_serial_cfg_setup(com_if_key=com_if_key, json_cfg_path=json_cfg_path)
        serial_cfg = get_global(CoreGlobalIds.SERIAL_CONFIG)
        serial_baudrate = serial_cfg[SerialConfigIds.SERIAL_BAUD_RATE]
        serial_timeout = serial_cfg[SerialConfigIds.SERIAL_TIMEOUT]
        com_port = serial_cfg[SerialConfigIds.SERIAL_PORT]
        if com_if_key == CoreComInterfaces.SERIAL_DLE.value:
            ser_com_type = SerialCommunicationType.DLE_ENCODING
        else:
            ser_com_type = SerialCommunicationType.FIXED_FRAME_BASED
        communication_interface = SerialComIF(
            com_if_id=com_if_key,
            com_port=com_port,
            baud_rate=serial_baudrate,
            serial_timeout=serial_timeout,
            ser_com_type=ser_com_type,
        )
        if com_if_key == CoreComInterfaces.SERIAL_DLE:
            dle_max_queue_len = serial_cfg[SerialConfigIds.SERIAL_DLE_QUEUE_LEN]
            dle_max_frame_size = serial_cfg[SerialConfigIds.SERIAL_DLE_MAX_FRAME_SIZE]
            communication_interface.set_dle_settings(
                dle_max_queue_len, dle_max_frame_size, serial_timeout
            )
    except KeyError:
        LOGGER.warning("Serial configuration global not configured properly")
        return None
    return communication_interface


def set_up_serial_cfg(
    json_cfg_path: str,
    com_if_key: str,
    baud_rate: int,
    com_port: str = "",
    tm_timeout: float = 0.01,
    ser_com_type: SerialCommunicationType = SerialCommunicationType.DLE_ENCODING,
    ser_frame_size: int = 256,
    dle_queue_len: int = 25,
    dle_frame_size: int = 1024,
):
    """Default configuration to set up serial communication. The serial port and the baud rate
    will be determined from a JSON configuration file and prompted from the user. Sets up all
    global variables so that a serial communication interface can be built with
    :func:`create_default_serial_interface`
    :param json_cfg_path:
    :param com_if_key:
    :param com_port:
    :param baud_rate:
    :param tm_timeout:
    :param ser_com_type:
    :param ser_frame_size:
    :param dle_queue_len:
    :param dle_frame_size:
    :return:
    """
    update_global(CoreGlobalIds.USE_SERIAL, True)
    if (
        com_if_key == CoreComInterfaces.SERIAL_DLE.value
        or com_if_key == CoreComInterfaces.SERIAL_FIXED_FRAME.value
    ) and com_port == "":
        LOGGER.warning("Invalid serial port specified!")
        com_port = determine_com_port(json_cfg_path=json_cfg_path)
    serial_cfg_dict = get_global(CoreGlobalIds.SERIAL_CONFIG)
    serial_cfg_dict.update({SerialConfigIds.SERIAL_PORT: com_port})
    serial_cfg_dict.update({SerialConfigIds.SERIAL_BAUD_RATE: baud_rate})
    serial_cfg_dict.update({SerialConfigIds.SERIAL_TIMEOUT: tm_timeout})
    serial_cfg_dict.update({SerialConfigIds.SERIAL_COMM_TYPE: ser_com_type})
    serial_cfg_dict.update({SerialConfigIds.SERIAL_FRAME_SIZE: ser_frame_size})
    serial_cfg_dict.update({SerialConfigIds.SERIAL_DLE_QUEUE_LEN: dle_queue_len})
    serial_cfg_dict.update({SerialConfigIds.SERIAL_DLE_MAX_FRAME_SIZE: dle_frame_size})
    update_global(CoreGlobalIds.SERIAL_CONFIG, serial_cfg_dict)
