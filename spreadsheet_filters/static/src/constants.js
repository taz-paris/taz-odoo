/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { RELATIVE_DATE_RANGE_TYPES } from "@spreadsheet/helpers/constants";

RELATIVE_DATE_RANGE_TYPES.push({ type: "year_to_last_closed_month", description: _t("Year to last closed month") });
RELATIVE_DATE_RANGE_TYPES.push({ type: "year_to_last_closed_week", description: _t("Year to last closed week") });
RELATIVE_DATE_RANGE_TYPES.push({ type: "current_week_to_end_year", description: _t("Current week to end year") });
RELATIVE_DATE_RANGE_TYPES.push({ type: "current_year", description: _t("Complete current calendar year") });
RELATIVE_DATE_RANGE_TYPES.push({ type: "past_until_today", description: _t("Past untill today (included)") });
RELATIVE_DATE_RANGE_TYPES.push({ type: "today_future", description: _t("Today(included) and future") });

