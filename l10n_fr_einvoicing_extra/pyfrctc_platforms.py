import logging

logger = logging.getLogger(__name__)

try:
    from pyfrctc.pyfrctc import PLATFORMS
except (OSError, ImportError) as err:
    logger.debug("Cannot import pyfrctc. Error details below.")
    logger.debug(err)
else:
    PLATFORMS["einvoicing_router"] = {
        "afnor_base_url": (
            "https://2a01-e34-ecb8-bb0-f869-a6ff-fe4a-edbf.sslip.io/api/afnor"
        ),
        "token_url": (
            "https://2a01-e34-ecb8-bb0-f869-a6ff-fe4a-edbf.sslip.io"
            "/api/afnor/oauth/token"
        ),
        "authorize_url": None,
        "label": "eInvoicing Router",
    }
