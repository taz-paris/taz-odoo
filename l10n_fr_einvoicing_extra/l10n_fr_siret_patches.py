import inspect
import logging
import textwrap

from odoo.addons.l10n_fr_siret.models.res_partner import Partner

logger = logging.getLogger(__name__)

OLD_LINE = "partner = self.parent_id or self"
NEW_LINE = (
    "partner = self if self.commercial_partner_id == self "
    "else (self.parent_id or self)"
)

# _get_siren() always prefers the parent's SIREN as soon as parent_id is
# set. This is wrong for a partner that has a parent_id (e.g. it is listed
# under a holding company in the contact hierarchy) but is its own
# commercial entity (is_company=True with its own SIREN): in that case
# commercial_partner_id == id and its own SIREN must be used, not the
# parent's.
METHOD_NAME = "_get_siren"


def _patch_get_siren():
    func = getattr(Partner, METHOD_NAME)
    src = textwrap.dedent(inspect.getsource(func))
    if OLD_LINE not in src:
        raise RuntimeError(
            f"l10n_fr_einvoicing_extra: expected to find {OLD_LINE!r} in "
            f"Partner.{METHOD_NAME}, upstream l10n_fr_siret code has "
            "changed. This patch needs to be reviewed."
        )
    patched_src = src.replace(OLD_LINE, NEW_LINE)
    namespace = dict(func.__globals__)
    exec(  # noqa: S102
        compile(patched_src, f"<l10n_fr_einvoicing_extra patch of {METHOD_NAME}>", "exec"),
        namespace,
    )
    setattr(Partner, METHOD_NAME, namespace[METHOD_NAME])
    logger.debug("l10n_fr_einvoicing_extra: patched Partner.%s", METHOD_NAME)


_patch_get_siren()
