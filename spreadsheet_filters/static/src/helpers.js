/** @odoo-module **/


import { patch } from "@web/core/utils/patch";
import { GlobalFiltersUIPlugin } from "@spreadsheet/global_filters/plugins/global_filters_ui_plugin"
const { DateTime } = luxon;
import { Domain } from "@web/core/domain";
import { serializeDate, serializeDateTime } from "@web/core/l10n/dates";


export function getRelativeDateDomainNewFilters(now, offset, rangeType, fieldName, fieldType) {
    //console.log("========= Fonction getRelativeDateDomainNewFilter");
    //console.log(rangeType);
    let endDate = now.minus({ day: 1 }).endOf("day");
    let startDate = endDate;
    switch (rangeType) {
        case "year_to_last_closed_month": {
            const offsetParam = { years: offset };
            startDate = now.startOf("year").plus(offsetParam);
            endDate = now.minus({months: 1}).endOf("month").plus(offsetParam);
            break;
        }
        case "year_to_last_closed_week": {
            const offsetParam = { years: offset };
            startDate = now.startOf("year").plus(offsetParam);
            endDate = now.plus(offsetParam).minus({week: 1}).endOf("week");
            break;
        }
        case "current_year": {
            const offsetParam = { years: offset };
            startDate = now.startOf("year").plus(offsetParam);
            endDate = now.endOf("year").plus(offsetParam);
            break;
        }
        case "current_week_to_end_year": {
            const offsetParam = { years: offset };
            startDate = now.plus(offsetParam).startOf("week");
            endDate = now.endOf("year").plus(offsetParam);
            break;
        }
        case "past_until_today": {
            const offsetParam = { years: offset };
            startDate = now.minus({year:1000}).startOf("year");
            endDate = now.endOf("day").plus(offsetParam);
            break;
        }
        case "today_future": {
            const offsetParam = { years: offset };
            startDate = now.startOf("day").plus(offsetParam);
            endDate = now.plus({year:1000}).endOf("year");
            break;
        }
        default:{
            return undefined;
        }
    }

    let leftBound, rightBound;

    console.log(startDate);
    console.log(endDate);
    if (fieldType === "date") {
	    console.log("serializeDate");
        leftBound = serializeDate(startDate);
        rightBound = serializeDate(endDate);
    } else {
	//console.log("serializeDateTime");
        leftBound = serializeDateTime(startDate);
        rightBound = serializeDateTime(endDate);
    }
    console.log(leftBound);
    console.log(rightBound);

    return new Domain(["&", [fieldName, ">=", leftBound], [fieldName, "<=", rightBound]]);
}


patch(GlobalFiltersUIPlugin.prototype, {
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
	    	if (["year_to_last_closed_month", "year_to_last_closed_week", "current_week_to_end_year", "current_year", "past_until_today", "today_future"].includes(value)){
				return getRelativeDateDomainNewFilters(now, offset, value, field, type);
			}
     	}    	
        return super._getDateDomain(filter, fieldMatching);
	}
})

;
