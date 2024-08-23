/** @odoo-module **/

//import * as helpers from "@spreadsheet/global_filters/helpers";
import { patch } from "@web/core/utils/patch";
import GlobalFiltersUIPlugin from "@spreadsheet/global_filters/plugins/global_filters_ui_plugin"
import { serializeDate, serializeDateTime } from "@web/core/l10n/dates";
const { DateTime } = luxon;
import { Domain } from "@web/core/domain";

/*
import { _t } from "@web/core/l10n/translation";

import { sprintf } from "@web/core/utils/strings";
import { constructDateRange, getPeriodOptions, QUARTER_OPTIONS } from "@web/search/utils/dates";

import spreadsheet from "@spreadsheet/o_spreadsheet/o_spreadsheet_extended";
import CommandResult from "@spreadsheet/o_spreadsheet/cancelled_reason";

import { isEmpty } from "@spreadsheet/helpers/helpers";
import { FILTER_DATE_OPTION } from "@spreadsheet/assets_backend/constants";
import {
    checkFiltersTypeValueCombination,
    getRelativeDateDomain,
} from "@spreadsheet/global_filters/helpers";
import { RELATIVE_DATE_RANGE_TYPES } from "@spreadsheet/helpers/constants";


const MONTHS = {
    january: { value: 1, granularity: "month" },
    february: { value: 2, granularity: "month" },
    march: { value: 3, granularity: "month" },
    april: { value: 4, granularity: "month" },
    may: { value: 5, granularity: "month" },
    june: { value: 6, granularity: "month" },
    july: { value: 7, granularity: "month" },
    august: { value: 8, granularity: "month" },
    september: { value: 9, granularity: "month" },
    october: { value: 10, granularity: "month" },
    november: { value: 11, granularity: "month" },
    december: { value: 12, granularity: "month" },
};

const { UuidGenerator, createEmptyExcelSheet } = spreadsheet.helpers;
const uuidGenerator = new UuidGenerator();
*/

export function getRelativeDateDomainNewFilters(now, offset, rangeType, fieldName, fieldType) {
        //console.log("========= Fonction getRelativeDateDomain originale");
        //console.log(rangeType);
    let endDate = now.minus({ day: 1 }).endOf("day");
    let startDate = endDate;
    switch (rangeType) {
        case "year_to_date": {
            const offsetParam = { years: offset };
            startDate = now.startOf("year").plus(offsetParam);
            endDate = now.endOf("day").plus(offsetParam);
            break;
        }
        default:{
                console.log('indéfini');
            return undefined;
        }
    }
    startDate = startDate.startOf("day");

    let leftBound, rightBound;
    if (fieldType === "date") {
        leftBound = serializeDate(startDate);
        rightBound = serializeDate(endDate);
    } else {
        leftBound = serializeDateTime(startDate);
        rightBound = serializeDateTime(endDate);
    }

    return new Domain(["&", [fieldName, ">=", leftBound], [fieldName, "<=", rightBound]]);
}


patch(GlobalFiltersUIPlugin.prototype, 'spreadsheet_filters.GlobalFiltersUIPlugin', {
	_getDateDomain(filter, fieldMatching) {
		//console.log(">>>>> overided _getDateDomain");
		let granularity;
		const value = this.getGlobalFilterValue(filter.id);
		if (!value || !fieldMatching.chain) {
		    return new Domain();
		}
		const field = fieldMatching.chain;
		const type = fieldMatching.type;
		const offset = fieldMatching.offset || 0;
		const now = DateTime.local();
		if (filter.rangeType === "relative") {
	    		if (value == "year_to_date"){
				return getRelativeDateDomainNewFilters(now, offset, value, field, type);
			}
     		}
            	return this._super(filter, fieldMatching);
	}
});

