"""Definitions for the TMTC commander core
"""
from pathlib import Path
from typing import Optional

from spacepackets.util import ByteFieldEmpty
from tmtccmd.core import TmMode, TcMode

from .args import (
    SetupParams,
    create_default_args_parser,
    add_default_tmtccmd_args,
    parse_default_tmtccmd_input_arguments,
    DefaultProcedureParams,
    PreArgsParsingWrapper,
    ProcedureParamsWrapper,
    CfdpParams,
)
from .defs import (
    CoreModeList,
    CoreModeConverter,
    CoreComInterfaces,
    CORE_COM_IF_DICT,
    default_json_path,
    CoreServiceList,
    ComIfDictT,
)
from .prompt import prompt_op_code, prompt_service
from .tmtc import TmtcDefinitionWrapper, OpCodeEntry, OpCodeOptionBase
from .hook import TmTcCfgHookBase
from tmtccmd.tc.procedure import (
    DefaultProcedureInfo,
    CfdpProcedureInfo,
    TcProcedureType,
    ProcedureWrapper,
)
from tmtccmd.cfdp.request import PutRequestCfg, PutRequest
from tmtccmd.core.base import ModeWrapper


def backend_mode_conversion(mode: CoreModeList, mode_wrapper: ModeWrapper):
    if mode == CoreModeConverter.get_str(CoreModeList.LISTENER_MODE):
        mode_wrapper.tm_mode = TmMode.LISTENER
        mode_wrapper.tc_mode = TcMode.IDLE
    elif mode == CoreModeConverter.get_str(CoreModeList.ONE_QUEUE_MODE):
        mode_wrapper.tm_mode = TmMode.LISTENER
        mode_wrapper.tc_mode = TcMode.ONE_QUEUE
    elif mode == CoreModeConverter.get_str(CoreModeList.MULTI_INTERACTIVE_QUEUE_MODE):
        mode_wrapper.tc_mode = TcMode.MULTI_QUEUE
        mode_wrapper.tm_mode = TmMode.LISTENER


def get_global_hook_obj() -> Optional[TmTcCfgHookBase]:
    """This function can be used to get the handle to the global hook object.
    :return:
    """
    from tmtccmd import get_console_logger

    logger = get_console_logger()
    try:
        from tmtccmd.core.globals_manager import get_global
        from tmtccmd.config.definitions import CoreGlobalIds

        from typing import cast

        hook_obj_raw = get_global(CoreGlobalIds.TMTC_HOOK)
        if hook_obj_raw is None:
            logger.error("Hook object is invalid!")
            return None
        return cast(TmTcCfgHookBase, hook_obj_raw)
    except ImportError:
        logger.exception("Issues importing modules to get global hook handle!")
        return None
    except AttributeError:
        logger.exception("Attribute error when trying to get global hook handle!")
        return None


class SetupWrapper:
    """This class encapsulates various important setup parameters required by tmtccmd components"""

    def __init__(
        self,
        hook_obj: TmTcCfgHookBase,
        setup_params: SetupParams,
        proc_param_wrapper: ProcedureParamsWrapper,
        json_cfg_path: Optional[str] = None,
    ):
        """
        :param hook_obj: User hook object. Needs to be implemented by the user
        :param setup_params: Optional helper wrapper which contains CLI arguments.
        """
        self.hook_obj = hook_obj
        self.json_cfg_path = json_cfg_path
        self._params = setup_params
        self.proc_param_wrapper = proc_param_wrapper
        self.json_cfg_path = json_cfg_path
        if json_cfg_path is None:
            self.json_cfg_path = default_json_path()

    @property
    def params(self):
        return self._params


def tmtc_params_to_procedure(params: DefaultProcedureParams) -> DefaultProcedureInfo:
    return DefaultProcedureInfo(service=params.service, op_code=params.op_code)


def cfdp_put_req_params_to_procedure(params: CfdpParams) -> CfdpProcedureInfo:
    proc_info = CfdpProcedureInfo()
    put_req_cfg = PutRequestCfg(
        destination_id=ByteFieldEmpty(),
        source_file=Path(params.source),
        dest_file=params.target,
        closure_requested=params.closure_requested,
        trans_mode=params.transmission_mode,
    )
    proc_info.request_wrapper.base = PutRequest(put_req_cfg)
    return proc_info


def params_to_procedure_conversion(
    param_wrapper: ProcedureParamsWrapper,
) -> ProcedureWrapper:
    proc_wrapper = ProcedureWrapper(None)
    if param_wrapper.ptype == TcProcedureType.DEFAULT:
        proc_wrapper.base = tmtc_params_to_procedure(param_wrapper.def_params())
    elif param_wrapper.ptype == TcProcedureType.CFDP:
        proc_wrapper.base = cfdp_put_req_params_to_procedure(
            param_wrapper.cfdp_params()
        )
    return proc_wrapper
