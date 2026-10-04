import inspect
import logging
import textwrap

from odoo.addons.l10n_fr_einvoicing.models.res_partner import ResPartner

logger = logging.getLogger(__name__)

OLD_ASSERT = "assert not self.parent_id"
NEW_ASSERT = "assert self.commercial_partner_id == self"

# l10n_fr_einvoicing assumes everywhere that "top-level eInvoicing entity"
# means "no parent_id". But a partner can have a parent_id (e.g. it is
# listed under a holding company in the contact hierarchy) and still be
# its own commercial entity (is_company=True with its own SIREN), in which
# case commercial_partner_id == id. For such partners these asserts wrongly
# block directory sync. We patch the assert to use the real invariant we
# actually care about: is this partner its own commercial entity?
PATCHED_METHOD_NAMES = [
    "fr_directory_sync_button",
    "_fr_directory_sync_logs",
    "_fr_directory_sync",
    "_fr_directory_should_sync_upon_confirmation",
]


def _patch_assert(method_name):
    func = getattr(ResPartner, method_name)
    src = textwrap.dedent(inspect.getsource(func))
    if OLD_ASSERT not in src:
        raise RuntimeError(
            f"l10n_fr_einvoicing_extra: expected to find {OLD_ASSERT!r} in "
            f"ResPartner.{method_name}, upstream l10n_fr_einvoicing code has "
            "changed. This patch needs to be reviewed."
        )
    patched_src = src.replace(OLD_ASSERT, NEW_ASSERT)
    namespace = dict(func.__globals__)
    exec(  # noqa: S102
        compile(patched_src, f"<l10n_fr_einvoicing_extra patch of {method_name}>", "exec"),
        namespace,
    )
    setattr(ResPartner, method_name, namespace[method_name])
    logger.debug("l10n_fr_einvoicing_extra: patched ResPartner.%s", method_name)


for _method_name in PATCHED_METHOD_NAMES:
    _patch_assert(_method_name)
