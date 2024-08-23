/** @odoo-module **/

import { _lt } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { RELATIVE_DATE_RANGE_TYPES } from "@spreadsheet/helpers/constants";

RELATIVE_DATE_RANGE_TYPES.push({ type: "year_to_date", description: _lt("Year to Date") }); //year_to_date already exists in Odoo core 17.0 and should be remove from here when migrating this module
RELATIVE_DATE_RANGE_TYPES.push({ type: "year_to_last_closed_month", description: _lt("Year to last closed month") });
RELATIVE_DATE_RANGE_TYPES.push({ type: "current_year", description: _lt("Complete current calendar year") });
