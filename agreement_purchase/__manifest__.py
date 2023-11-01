{
    "name": "Agreement Purchase",
    "summary": "Agreement on purchases",
    "version": "14.0.1.0.0",
    "category": "Contract",
    "author": "Aurelien Dumaine",
    "license": "AGPL-3",
    "depends": ["purchase", "agreement"],
    "data": [
        "security/ir.model.access.csv",
        "views/agreement.xml",
        "views/purchase_order.xml",
    ],
    "development_status": "Beta",
    "installable": True,
}
