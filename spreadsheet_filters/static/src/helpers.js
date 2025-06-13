/** @odoo-module **/

//import * as helpers from "@spreadsheet/global_filters/helpers";
import { patch } from "@web/core/utils/patch";
import GlobalFiltersUIPlugin from "@spreadsheet/global_filters/plugins/global_filters_ui_plugin"
const { DateTime } = luxon;
import { Domain } from "@web/core/domain";
import { serializeDate, serializeDateTime } from "@web/core/l10n/dates";


export function getRelativeDateDomainNewFilters(now, offset, rangeType, fieldName, fieldType) {
        //console.log("========= Fonction getRelativeDateDomainNewFilter");
        //console.log(rangeType);
    let endDate = now.minus({ day: 1 }).endOf("day");
    let startDate = endDate;
    switch (rangeType) {
        case "year_to_date": { //year_to_date already exists in Odoo core 17.0 and should be remove from here when migrating this module **IF the serializeDateTime issue beelow is corrected**
            const offsetParam = { years: offset };
            startDate = now.startOf("year").plus(offsetParam);
            endDate = now.endOf("day").plus(offsetParam);
            break;
        }
        case "year_to_last_closed_month": {
            const offsetParam = { years: offset };
            startDate = now.startOf("year").plus(offsetParam);
            endDate = now.minus({months: 1}).endOf("day").plus(offsetParam);
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
	console.log(startDate);
	console.log(endDate);
            break;
        }
        default:{
            return undefined;
        }
    }
    startDate = startDate.startOf("day");

    let leftBound, rightBound;
    if (fieldType === "date") {
	    console.log("serializeDate");
        leftBound = serializeDate(startDate);
        rightBound = serializeDate(endDate);
    } else {
	    console.log("serializeDateTime");
	//leftBound = serializeDateTime(startDate);
        //rightBound = serializeDateTime(endDate);
	// BUG du core ? Le fonction serializeDateTime from "@web/core/l10n/dates" force le passage à UTC : setZone("utc").
	    // Ce qui conduit à remonter les clotures comptables du 31/12/N-1 puisque leftBound est le 31/12 à 23h en UTC.
	const SERVER_DATE_FORMAT = "yyyy-MM-dd";
	const SERVER_TIME_FORMAT = "HH:mm:ss";
	const SERVER_DATETIME_FORMAT = `${SERVER_DATE_FORMAT} ${SERVER_TIME_FORMAT}`;
	leftBound = startDate.toFormat(SERVER_DATETIME_FORMAT, { numberingSystem: "latn" })
	rightBound = endDate.toFormat(SERVER_DATETIME_FORMAT, { numberingSystem: "latn" })
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
	    		if (["year_to_date", "year_to_last_closed_month", "year_to_last_closed_week", "current_week_to_end_year", "current_year"].includes(value)){
				return getRelativeDateDomainNewFilters(now, offset, value, field, type);
			}
     		}
            	return this._super(filter, fieldMatching);
	}
});

