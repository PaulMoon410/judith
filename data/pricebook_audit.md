# Price Book Material Price Audit

**Review date:** 2026-09-28  
**Scope:** all 120 material rows in `data/pricebook.json`; material unit prices only. Labor unit prices and global tax, markup, and consumables assumptions were not changed or audited.

## Method and limits

Compared listed allowances with current U.S. online retail listings, normalized cable and raceway to per-foot prices where a spool or stick size was shown, and selected common residential/commercial comparable products. Retail listings vary by location, brand, grade, package quantity, and stock. These are planning benchmarks, not a contractor supply quote. Prices exclude tax, shipping, waste, and bulk discounts. Listings are retailer pages and may update after this review.

“Adjusted” means there was a clear comparable listing supporting a material price change. “Retained” means the existing allowance was broadly plausible or grade-dependent; it does not mean a matching SKU was confirmed. “Needs specification” means the row’s description is too broad for a dependable quote.

## Changes made

| Item | Old | Audited | Basis |
|---|---:|---:|---|
| 4-Square Box w/ Mud Ring | $3.25/ea | $4.84/ea | Boxes benchmark below |
| 14/2 Romex NM-B Wire | $0.45/ft | $0.50/ft | Wire & Cable benchmark below |
| 12/2 Romex NM-B Wire | $0.65/ft | $0.72/ft | Wire & Cable benchmark below |
| 10/2 Romex NM-B Wire | $0.95/ft | $1.23/ft | Wire & Cable benchmark below |
| 14/3 Romex NM-B Wire | $0.65/ft | $0.66/ft | Wire & Cable benchmark below |
| 12/3 Romex NM-B Wire | $0.85/ft | $0.89/ft | Wire & Cable benchmark below |
| MC Cable 12/2 | $1.10/ft | $1.11/ft | Wire & Cable benchmark below |
| THHN Wire 12 AWG (in conduit) | $0.18/ft | $0.29/ft | Wire & Cable benchmark below |
| THHN Wire 10 AWG (in conduit) | $0.28/ft | $0.44/ft | Wire & Cable benchmark below |
| EMT Conduit 1/2 in | $1.10/ft | $0.70/ft | Conduit benchmark below |
| EMT Conduit 3/4 in | $1.50/ft | $1.18/ft | Conduit benchmark below |
| PVC Conduit 3/4 in Sch40 | $0.95/ft | $0.76/ft | Conduit benchmark below |
| 20A GFCI Breaker | $45.00/ea | $57.09/ea | Breakers benchmark below |
| 20A AFCI Breaker | $42.00/ea | $59.71/ea | Breakers benchmark below |
| 20A Dual-Function AFCI/GFCI Breaker | $55.00/ea | $66.80/ea | Breakers benchmark below |
| 30A Two-Pole Breaker (dryer/AC) | $16.00/ea | $18.24/ea | Breakers benchmark below |
| 40A Two-Pole Breaker (range) | $18.00/ea | $18.24/ea | Breakers benchmark below |
| 50A Two-Pole Breaker (range/EVSE) | $20.00/ea | $18.24/ea | Breakers benchmark below |
| 60A Two-Pole Breaker (subpanel feed) | $28.00/ea | $18.24/ea | Breakers benchmark below |
| 200A Load Center Panel | $210.00/ea | $270.00/ea | Panels benchmark below |
| Smoke/CO Combo Detector (hardwired) | $35.00/ea | $59.97/ea | Lighting & Fixtures benchmark below |
| Ground Rod 8ft Copper-Clad | $14.00/ea | $29.01/ea | Grounding benchmark below |
| Fan-Rated Retrofit Brace Box | $22.00/ea | $29.50/ea | Boxes benchmark below |
| Smoke/CO Combo Alarm (hardwired, interconnected) | $45.00/ea | $59.97/ea | Life Safety benchmark below |
| AC Disconnect 60A Fused, NEMA 3R | $40.00/ea | $34.97/ea | Disconnects benchmark below |

Current source comparisons by category:

- **Wire & Cable:** [NM-B cable listings (14/2, 12/2, 10/2, 14/3, 12/3)](https://www.homedepot.com/b/Electrical-Wire-Building-Wires-NM-Wires/Jacketed/250-ft/N-5yc1vZ2fkpc4xZ1z1b3wwZ1z1ugzt); [MC cable](https://www.homedepot.com/p/204842019); [12 AWG THHN](https://www.homedepot.com/p/203401704). 10 AWG THHN allowance derived from a current 500-ft spool listing in the same retailer catalog.
- **Conduit:** [EMT listings, 10-ft sticks](https://www.homedepot.com/b/Electrical-Electrical-Boxes-Conduit-Fittings-Conduit/EMT/10-ft/N-5yc1vZbohlZ1z116t7Z1z1uzju); [Schedule 40 PVC, 10-ft sticks](https://www.homedepot.com/b/Electrical-Electrical-Boxes-Conduit-Fittings-Conduit/Schedule-40/10-ft/N-5yc1vZbohlZ1z116t7Z1z23bex).
- **Breakers:** [Homeline 20-A breakers](https://www.homedepot.com/b/Electrical-Power-Distribution-Electrical-Panels-Protective-Devices-Circuit-Breakers/20-A/Single-Item/Homeline/N-5yc1vZbm16Z1z1uug6Z1z1xyriZ1z1zd2x); [AFCI breakers](https://www.homedepot.com/b/Electrical-Power-Distribution-Electrical-Panels-Protective-Devices-Circuit-Breakers/AFCI/20-A/Homeline/N-5yc1vZbm16Z1z0mha0Z1z1uug6Z1z1zd2x); [dual-function breakers](https://www.homedepot.com/b/Electrical-Power-Distribution-Electrical-Panels-Protective-Devices-Circuit-Breakers/AFCI-GFCI/20-amp/N-5yc1vZbm16Z1z1zdzdZ1z1zncy); [two-pole breaker range](https://www.homedepot.com/b/Electrical-Power-Distribution-Electrical-Panels-Protective-Devices-Circuit-Breakers/Square-D/30-amp/Homeline/N-5yc1vZbm16Zal2Z1z1zd2xZ1z1zne7).
- **Panels:** [100-A load centers](https://www.homedepot.com/b/Electrical-Power-Distribution-Electrical-Panels-Protective-Devices-Breaker-Boxes/Indoor/100-A/24-Circuit/N-5yc1vZbm2wZ1z17lgmZ1z1motgZ1z1v38d); [150-A subpanels](https://www.homedepot.com/b/Electrical-Power-Distribution-Electrical-Panels-Protective-Devices-Breaker-Boxes/Subpanel/Indoor/150-A/N-5yc1vZbm2wZ1z17lgmZ1z1uug1Z1z1zj6n); [200-A main-breaker panels](https://www.homedepot.com/b/Electrical-Power-Distribution-Electrical-Panels-Protective-Devices-Breaker-Boxes/Main-Breaker-Panel/200-amp/40-Spaces/N-5yc1vZ2fkpercZ1z17lgmZ1z1motbZ1z1znc6Z1z202b2).
- **Boxes:** [4-square box](https://www.homedepot.com/p/202590462); [single-gang mud ring](https://www.homedepot.com/p/202590484); [ceiling fan boxes and braces](https://www.homedepot.com/b/Electrical-Electrical-Boxes-Conduit-Fittings-Boxes-Brackets/Ceiling-Fan/Round/N-5yc1vZbohnZ1z0y7ncZ1z235k9); [retrofit fan brace](https://www.homedepot.com/b/Electrical-Electrical-Boxes-Conduit-Fittings-Boxes-Brackets/Ceiling-Fan/Octagon/N-5yc1vZbohnZ1z1xqlfZ1z235k9).
- **Plates:** [2-gang plates](https://www.homedepot.com/b/Electrical-Wall-Plates/White/2-Gang/Plastic/N-5yc1vZbm8mZ1z0v9zgZ1z13hucZ1z1c2ga); [3-gang plate](https://www.homedepot.com/p/301701222); [single Decora plate](https://www.homedepot.com/p/202059798); [stainless plates](https://www.homedepot.com/b/Electrical-Wall-Plates-Light-Switch-Plates/Stainless-Steel/N-5yc1vZc6qzZ1z13ht8).
- **Devices:** [Commercial-grade 20-A duplex](https://www.homedepot.com/p/301387049); [industrial 20-A duplex](https://www.homedepot.com/p/301361521); [20-A GFCI](https://www.supplyhouse.com/GFCI-Receptacles-21610000); [15-A GFCI](https://www.homedepot.com/p/301361542); [dimmers](https://www.homedepot.com/b/Electrical-Wiring-Devices-Light-Controls-Dimmers/Leviton/15-amp/N-5yc1vZc34iZwcZ1z17l6n); [switches](https://www.homedepot.com/b/Electrical-Wiring-Devices-Light-Controls-Light-Switches/Leviton/15-amp/Pick-Up-Today/N-5yc1vZc33wZwcZ1z175a5Z1z17l6n).
- **Lighting & Life Safety:** [4-in wafer](https://www.homedepot.com/p/308905674); [bath fan/light combo](https://www.homedepot.com/p/700381963); [hardwired smoke/CO combo](https://www.homedepot.com/p/301457754).
- **Grounding:** [5/8-in x 8-ft copper-clad grounding rod](https://www.homedepot.com/p/202195738).
- **Disconnects:** [Outdoor AC disconnect listings](https://www.homedepot.com/b/Electrical-Power-Distribution-Disconnects/Air-Conditioner/N-5yc1vZbm0hZ1z20yt5); [floor box kits](https://www.homedepot.com/p/324609632).

## Item-by-item disposition

The inventory below includes the current material value for each row. Values are per listed unit. “Needs specification” rows should be treated as allowances until the product grade/configuration is chosen.

### Devices

| Item | Current material price | Disposition |
|---|---:|---|
| Duplex Outlet 15A | $3.10/ea | Retained; comparable-price range depends on brand and grade. |
| Duplex Outlet 20A | $11.01/ea | Retained; comparable-price range depends on brand and grade. |
| Duplex Outlet 15A GFCI | $29.57/ea | Retained; comparable-price range depends on brand and grade. |
| Duplex Outlet 20A GFCI | $33.39/ea | Retained; comparable-price range depends on brand and grade. |
| AFCI/GFCI Combo Outlet | $34.98/ea | Retained; comparable-price range depends on brand and grade. |
| USB/USB-C Combo Outlet | $49.98/ea | Retained; comparable-price range depends on brand and grade. |
| Single-Pole Switch | $1.00/ea | Retained; comparable-price range depends on brand and grade. |
| 3-Way Switch | $2.58/ea | Retained; comparable-price range depends on brand and grade. |
| 4-Way Switch | $16.98/ea | Retained; comparable-price range depends on brand and grade. |
| Dimmer Switch | $25.99/ea | Retained; comparable-price range depends on brand and grade. |
| Smart Wi-Fi Switch/Dimmer | $48.67/ea | Retained; comparable-price range depends on brand and grade. |

### Boxes

| Item | Current material price | Disposition |
|---|---:|---|
| Electrical Box (single gang) | $1.75/ea | Retained as an allowance; exact spec/grade/package needs confirmation. |
| Electrical Box (double gang) | $2.75/ea | Retained as an allowance; exact spec/grade/package needs confirmation. |
| 4-Square Box w/ Mud Ring | $4.84/ea | Adjusted; see changes and source comparisons above. |
| Round Ceiling Box | $2.50/ea | Retained as an allowance; exact spec/grade/package needs confirmation. |
| Ceiling Fan Box (rated, w/ bar hanger) | $12.00/ea | Retained as an allowance; exact spec/grade/package needs confirmation. |
| Weatherproof In-Use Cover | $18.00/ea | Retained as an allowance; exact spec/grade/package needs confirmation. |
| 3-Gang New-Work Nail-On Box | $4.25/ea | Retained as an allowance; exact spec/grade/package needs confirmation. |
| Single-Gang Old-Work Box | $3.50/ea | Retained as an allowance; exact spec/grade/package needs confirmation. |
| 2-Gang Old-Work Box | $6.50/ea | Retained as an allowance; exact spec/grade/package needs confirmation. |
| 3-Gang Old-Work Box | $10.00/ea | Retained as an allowance; exact spec/grade/package needs confirmation. |
| 4-Square Box (deep, blank) | $4.50/ea | Retained as an allowance; exact spec/grade/package needs confirmation. |
| 4-Square Mud Ring (1-gang) | $1.75/ea | Retained as an allowance; exact spec/grade/package needs confirmation. |
| 4-Square Mud Ring (2-gang) | $2.75/ea | Retained as an allowance; exact spec/grade/package needs confirmation. |
| 4-11/16 Square Box (deep) | $8.00/ea | Retained as an allowance; exact spec/grade/package needs confirmation. |
| Octagon Ceiling Box | $3.50/ea | Retained as an allowance; exact spec/grade/package needs confirmation. |
| Pancake Ceiling Box | $3.00/ea | Retained as an allowance; exact spec/grade/package needs confirmation. |
| Fan-Rated Retrofit Brace Box | $29.50/ea | Adjusted; see changes and source comparisons above. |
| Junction Box (4 in square, blank cover) | $6.00/ea | Retained as an allowance; exact spec/grade/package needs confirmation. |
| Weatherproof 1-Gang Box | $7.00/ea | Retained as an allowance; exact spec/grade/package needs confirmation. |
| Weatherproof 2-Gang Box | $14.00/ea | Retained as an allowance; exact spec/grade/package needs confirmation. |
| Weatherproof Duplex Cover (while-in-use) | $18.00/ea | Retained as an allowance; exact spec/grade/package needs confirmation. |
| Weatherproof Toggle Cover | $10.00/ea | Retained as an allowance; exact spec/grade/package needs confirmation. |
| Floor Box Kit (single receptacle) | $45.00/ea | Retained as an allowance; exact spec/grade/package needs confirmation. |

### Plates

| Item | Current material price | Disposition |
|---|---:|---|
| Single-Gang Wall Plate (standard) | $0.75/ea | Retained as an allowance; exact spec/grade/package needs confirmation. |
| Single-Gang Decora Wall Plate | $1.25/ea | Retained as an allowance; exact spec/grade/package needs confirmation. |
| Double-Gang Wall Plate (standard) | $1.50/ea | Retained as an allowance; exact spec/grade/package needs confirmation. |
| Double-Gang Decora Wall Plate | $2.50/ea | Retained as an allowance; exact spec/grade/package needs confirmation. |
| Blank Wall Plate (single-gang) | $0.75/ea | Retained as an allowance; exact spec/grade/package needs confirmation. |
| Stainless Steel Wall Plate (single-gang) | $3.50/ea | Retained as an allowance; exact spec/grade/package needs confirmation. |
| Single-Gang Toggle Wall Plate | $0.75/ea | Retained as an allowance; exact spec/grade/package needs confirmation. |
| Single-Gang Duplex Receptacle Wall Plate | $0.75/ea | Retained as an allowance; exact spec/grade/package needs confirmation. |
| Single-Gang Blank Wall Plate (metal) | $1.25/ea | Retained as an allowance; exact spec/grade/package needs confirmation. |
| 2-Gang Toggle Wall Plate | $1.50/ea | Retained as an allowance; exact spec/grade/package needs confirmation. |
| 2-Gang Duplex Wall Plate | $1.50/ea | Retained as an allowance; exact spec/grade/package needs confirmation. |
| 2-Gang Toggle/Decora Combo Wall Plate | $2.50/ea | Retained as an allowance; exact spec/grade/package needs confirmation. |
| 2-Gang Blank Wall Plate | $1.50/ea | Retained as an allowance; exact spec/grade/package needs confirmation. |
| 3-Gang Toggle Wall Plate | $2.50/ea | Retained as an allowance; exact spec/grade/package needs confirmation. |
| 3-Gang Decora Wall Plate | $3.50/ea | Retained as an allowance; exact spec/grade/package needs confirmation. |
| 4-Gang Wall Plate (toggle) | $4.00/ea | Retained as an allowance; exact spec/grade/package needs confirmation. |
| Single-Gang Stainless Steel Decora Plate | $4.50/ea | Retained as an allowance; exact spec/grade/package needs confirmation. |
| Single-Gang Weatherproof Device Cover Plate | $2.00/ea | Retained as an allowance; exact spec/grade/package needs confirmation. |

### Wire & Cable

| Item | Current material price | Disposition |
|---|---:|---|
| 14/2 Romex NM-B Wire | $0.50/ft | Adjusted; see changes and source comparisons above. |
| 12/2 Romex NM-B Wire | $0.72/ft | Adjusted; see changes and source comparisons above. |
| 10/2 Romex NM-B Wire | $1.23/ft | Adjusted; see changes and source comparisons above. |
| 14/3 Romex NM-B Wire | $0.66/ft | Adjusted; see changes and source comparisons above. |
| 12/3 Romex NM-B Wire | $0.89/ft | Adjusted; see changes and source comparisons above. |
| MC Cable 12/2 | $1.11/ft | Adjusted; see changes and source comparisons above. |
| THHN Wire 12 AWG (in conduit) | $0.29/ft | Adjusted; see changes and source comparisons above. |
| THHN Wire 10 AWG (in conduit) | $0.44/ft | Adjusted; see changes and source comparisons above. |

### Conduit

| Item | Current material price | Disposition |
|---|---:|---|
| EMT Conduit 1/2 in | $0.70/ft | Adjusted; see changes and source comparisons above. |
| EMT Conduit 3/4 in | $1.18/ft | Adjusted; see changes and source comparisons above. |
| EMT Connector/Coupling | $0.85/ea | Retained; comparable-price range depends on brand and grade. |
| PVC Conduit 3/4 in Sch40 | $0.76/ft | Adjusted; see changes and source comparisons above. |

### Breakers

| Item | Current material price | Disposition |
|---|---:|---|
| 15A Single-Pole Breaker | $8.00/ea | Retained; comparable-price range depends on brand and grade. |
| 20A Single-Pole Breaker | $8.50/ea | Retained; comparable-price range depends on brand and grade. |
| 30A Single-Pole Breaker | $10.50/ea | Retained; comparable-price range depends on brand and grade. |
| 20A GFCI Breaker | $57.09/ea | Adjusted; see changes and source comparisons above. |
| 20A AFCI Breaker | $59.71/ea | Adjusted; see changes and source comparisons above. |
| 20A Dual-Function AFCI/GFCI Breaker | $66.80/ea | Adjusted; see changes and source comparisons above. |
| 30A Two-Pole Breaker (dryer/AC) | $18.24/ea | Adjusted; see changes and source comparisons above. |
| 40A Two-Pole Breaker (range) | $18.24/ea | Adjusted; see changes and source comparisons above. |
| 50A Two-Pole Breaker (range/EVSE) | $18.24/ea | Adjusted; see changes and source comparisons above. |
| 60A Two-Pole Breaker (subpanel feed) | $18.24/ea | Adjusted; see changes and source comparisons above. |

### Panels

| Item | Current material price | Disposition |
|---|---:|---|
| 100A Load Center Panel | $110.00/ea | Retained as an allowance; exact spec/grade/package needs confirmation. |
| 150A Load Center Panel | $150.00/ea | Retained as an allowance; exact spec/grade/package needs confirmation. |
| 200A Load Center Panel | $270.00/ea | Adjusted; see changes and source comparisons above. |
| 100A Indoor Subpanel | $95.00/ea | Retained as an allowance; exact spec/grade/package needs confirmation. |

### Lighting & Fixtures

| Item | Current material price | Disposition |
|---|---:|---|
| Recessed LED Can Light | $22.00/ea | Retained as an allowance; exact spec/grade/package needs confirmation. |
| Flush-Mount Ceiling Fixture | $35.00/ea | Retained as an allowance; exact spec/grade/package needs confirmation. |
| Exterior Wall Light Fixture | $45.00/ea | Retained as an allowance; exact spec/grade/package needs confirmation. |
| Bath Exhaust Fan | $65.00/ea | Retained as an allowance; exact spec/grade/package needs confirmation. |
| Smoke/CO Combo Detector (hardwired) | $59.97/ea | Adjusted; see changes and source comparisons above. |
| 4-in LED Recessed Wafer Light | $18.00/ea | Retained as an allowance; exact spec/grade/package needs confirmation. |
| 6-in LED Recessed Wafer Light | $22.00/ea | Retained as an allowance; exact spec/grade/package needs confirmation. |
| LED Recessed Retrofit Trim (4/6 in) | $15.00/ea | Retained as an allowance; exact spec/grade/package needs confirmation. |
| Vanity Light Fixture (allowance) | $75.00/ea | Retained as an allowance; exact spec/grade/package needs confirmation. |
| Pendant Light Fixture (allowance) | $90.00/ea | Retained as an allowance; exact spec/grade/package needs confirmation. |
| Chandelier Fixture (allowance) | $175.00/ea | Retained as an allowance; exact spec/grade/package needs confirmation. |
| LED Strip/Under-Cabinet Light (2 ft) | $35.00/ea | Retained as an allowance; exact spec/grade/package needs confirmation. |
| LED Strip/Under-Cabinet Light (4 ft) | $55.00/ea | Retained as an allowance; exact spec/grade/package needs confirmation. |
| LED Shop Light (4 ft) | $45.00/ea | Retained as an allowance; exact spec/grade/package needs confirmation. |
| Exterior LED Floodlight (motion sensor) | $65.00/ea | Retained as an allowance; exact spec/grade/package needs confirmation. |
| Exterior Soffit/Canopy LED Fixture | $45.00/ea | Retained as an allowance; exact spec/grade/package needs confirmation. |
| Landscape LED Path Light | $35.00/ea | Retained as an allowance; exact spec/grade/package needs confirmation. |
| Emergency Light (battery backup) | $65.00/ea | Retained as an allowance; exact spec/grade/package needs confirmation. |
| Exit Sign (LED, battery backup) | $80.00/ea | Retained as an allowance; exact spec/grade/package needs confirmation. |
| Bath Exhaust Fan/Light Combo | $125.00/ea | Retained as an allowance; exact spec/grade/package needs confirmation. |

### Grounding

| Item | Current material price | Disposition |
|---|---:|---|
| Ground Rod 8ft Copper-Clad | $29.01/ea | Adjusted; see changes and source comparisons above. |
| Ground Rod Clamp | $4.00/ea | Retained as an allowance; exact spec/grade/package needs confirmation. |
| Bonding Jumper #6 Bare Copper | $3.50/ea | Retained as an allowance; exact spec/grade/package needs confirmation. |

### Misc / Consumables

| Item | Current material price | Disposition |
|---|---:|---|
| Wire Nuts (box of 100) | $6.50/box | Retained as an allowance; exact spec/grade/package needs confirmation. |
| Cable Staples (box of 50) | $3.00/box | Retained as an allowance; exact spec/grade/package needs confirmation. |

### Life Safety

| Item | Current material price | Disposition |
|---|---:|---|
| Smoke Alarm (hardwired, battery backup) | $28.00/ea | Retained as an allowance; exact spec/grade/package needs confirmation. |
| Smoke Alarm (battery powered) | $22.00/ea | Retained as an allowance; exact spec/grade/package needs confirmation. |
| CO Alarm (hardwired, battery backup) | $32.00/ea | Retained as an allowance; exact spec/grade/package needs confirmation. |
| CO Alarm (battery powered) | $25.00/ea | Retained as an allowance; exact spec/grade/package needs confirmation. |
| Smoke/CO Combo Alarm (hardwired, interconnected) | $59.97/ea | Adjusted; see changes and source comparisons above. |
| Smoke Alarm Interconnect Harness/Adapter | $12.00/ea | Retained as an allowance; exact spec/grade/package needs confirmation. |

### Disconnects

| Item | Current material price | Disposition |
|---|---:|---|
| AC Disconnect 30A Non-Fused, NEMA 3R | $22.00/ea | Retained as an allowance; exact spec/grade/package needs confirmation. |
| AC Disconnect 60A Non-Fused, NEMA 3R | $22.00/ea | Retained as an allowance; exact spec/grade/package needs confirmation. |
| AC Disconnect 30A Fused, NEMA 3R | $30.00/ea | Retained as an allowance; exact spec/grade/package needs confirmation. |
| AC Disconnect 60A Fused, NEMA 3R | $34.97/ea | Adjusted; see changes and source comparisons above. |
| Fuse Set for Fused Disconnect (pair) | $18.00/set | Retained as an allowance; exact spec/grade/package needs confirmation. |
| Outdoor Disconnect Mounting Backplate | $12.00/ea | Retained as an allowance; exact spec/grade/package needs confirmation. |
| Liquidtight Whip (6 ft, fittings included) | $25.00/ea | Retained as an allowance; exact spec/grade/package needs confirmation. |
| Liquidtight Flexible Conduit (1/2 in) | $1.75/ft | Retained as an allowance; exact spec/grade/package needs confirmation. |
| Liquidtight Straight Connector (1/2 in) | $4.00/ea | Retained as an allowance; exact spec/grade/package needs confirmation. |
| Liquidtight 90-Degree Connector (1/2 in) | $5.00/ea | Retained as an allowance; exact spec/grade/package needs confirmation. |
| Disconnect Label / Circuit Identification | $2.00/ea | Retained as an allowance; exact spec/grade/package needs confirmation. |

## Important pricing notes

- **Receptacles and switches:** price depends strongly on grade and feature set. The listed 20-A receptacle at $11.01 aligns with an industrial-grade listing; a commercial-grade basic device can be much cheaper. Listed 15-A and 20-A GFCIs align with premium/heavy-duty examples; standard self-test devices may cost less. See device sources above.
- **Breakers and panels:** breaker prices are not interchangeable across panel brands or series. The adjusted breaker allowances use Square D Homeline examples. Select panel make/model, spaces, main rating, and included breakers before treating the total as a quote.
- **Lighting:** “vanity,” “pendant,” “chandelier,” exterior and landscape fixture rows have no lumens, finish, dimensions, listing, or brand. Their values are allowances only. Wafer lights have a clearer common specification and the existing allowances were retained after comparison.
- **Boxes and plates:** box depth, material, support rating, device openings, finish, and weatherproof configuration change price. A weatherproof cover may be an in-use cover, while-in-use assembly, or simple plate; confirm intended type.
- **Disconnects:** confirm voltage, poles, fuse class/ampacity, enclosure rating, and included fuse set. A “fused” unit price may not include fuses.
- **Wire quantities:** per-foot material price is not the installed run quantity. For a takeoff, allow for routing, vertical drops, panel slack, homeruns, and waste; conductor counts in conduit also matter.
- **Labor:** this review did not modify labor-unit allowances. Material price and installation labor remain separate pricebook fields.
