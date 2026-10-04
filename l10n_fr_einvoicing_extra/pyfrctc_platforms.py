import logging

logger = logging.getLogger(__name__)

try:
    from pyfrctc.pyfrctc import PLATFORMS
except (OSError, ImportError) as err:
    logger.debug("Cannot import pyfrctc. Error details below.")
    logger.debug(err)
else:
    # afnor_base_url/token_url are filled in (and kept up to date) from the
    # ir.config_parameter 'einvoicing_router_root_url' by
    # ResCompany._update_einvoicing_router_platform_urls(), called from
    # ResCompany._fr_ctc_get_session(). They can't be read here: this module
    # is imported before any database/env exists, so ir.config_parameter
    # (a database table) isn't reachable yet.
    PLATFORMS["einvoicing_router"] = {
        "afnor_base_url": None,
        "token_url": None,
        "authorize_url": None,
        "label": "eInvoicing Router",
    }
