"""
@file   tmtcc_dummy_com_if.py
@date   09.03.2020
@brief  DUMMY Communication Interface

@author R. Mueller
"""
from typing import Tuple

from tmtccmd.com_if.com_interface_base import CommunicationInterface
from tmtccmd.ecss.tc import PusTelecommand
from tmtccmd.pus_tm.factory import PusTelemetryFactory
from tmtccmd.pus_tm.service_1_verification import Service1TmPacked
from tmtccmd.utility.tmtcc_logger import get_logger

LOGGER = get_logger()


class DummyComIF(CommunicationInterface):
    def __init__(self, tmtc_printer):
        super().__init__(tmtc_printer)
        self.service_sent = 0
        self.reply_pending = False
        self.ssc = 0
        self.tc_ssc = 0
        self.tc_packet_id = 0

    def initialize(self) -> any:
        pass

    def open(self):
        pass

    def close(self) -> None:
        pass

    def data_available(self, parameters):
        if self.reply_pending:
            return True
        return False

    def poll_interface(self, parameters: any = 0) -> Tuple[bool, list]:
        pass

    def send_data(self, data: bytearray):
        pass

    def receive_telemetry(self, parameters: any = 0):
        tm_list = []
        if (self.service_sent == 17 or self.service_sent == 5) and self.reply_pending:
            LOGGER.info("dummy_com_if: Receive function called")
            tm_packer = Service1TmPacked(subservice=1, ssc=self.ssc, tc_packet_id=self.tc_packet_id,
                                         tc_ssc=self.tc_ssc)

            tm_packet_raw = tm_packer.pack()
            tm_packet = PusTelemetryFactory.create(tm_packet_raw)
            tm_list.append(tm_packet)
            tm_packer = Service1TmPacked(subservice=7, ssc=self.ssc, tc_packet_id=self.tc_packet_id,
                                         tc_ssc=self.tc_ssc)
            tm_packet_raw = tm_packer.pack()
            tm_packet = PusTelemetryFactory.create(tm_packet_raw)
            tm_list.append(tm_packet)
            self.reply_pending = False
            self.ssc += 1
        return tm_list

    def send_telecommand(self, tc_packet: PusTelecommand, tc_packet_obj: PusTelecommand = None):
        if tc_packet_obj is not None:
            self.service_sent = tc_packet_obj.get_service()
            self.tc_packet_id = tc_packet_obj.get_packet_id()
            self.tc_ssc = tc_packet_obj.get_ssc()
            self.reply_pending = True
