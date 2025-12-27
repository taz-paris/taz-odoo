/** @odoo-module **/

import { registry } from "@web/core/registry";
import { GridController } from "./grid_controller";
import { GridArchParser } from "./grid_arch_parser";

export const gridView = {
    type: "grid",
    display_name: "Grid",
    icon: "fa fa-th",
    multiRecord: true,
    searchMenuTypes: ["filter", "groupBy", "favorite"],
    Controller: GridController,
    ArchParser: GridArchParser,
    props: (genericProps, view) => {
        const { arch } = genericProps;
        const archInfo = new GridArchParser().parse(arch);

        return {
            ...genericProps,
            Model: view.Model,
            Renderer: view.Renderer,
            archInfo,
        };
    },
};

registry.category("views").add("grid", gridView);
