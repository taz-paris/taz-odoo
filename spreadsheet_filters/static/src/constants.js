/** @odoo-module **/

import { _lt } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { RELATIVE_DATE_RANGE_TYPES } from "@spreadsheet/helpers/constants";

RELATIVE_DATE_RANGE_TYPES.push({ type: "year_to_date", description: _lt("Year to Date") });
