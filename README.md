# kml-tools
A loose grab-bag of python scripts I've used to help deal with KML files and other GIS/mapping stuff.

Generally, this repo is a place where I can keep "official" copies of these scripts.

## fips

The fips module simply wraps a huge pile of static data from the US Census Bureau regarding states and counties.

It is named after the FIPS codes used by the USCB and some other federal entities to refer to specific geographic regions.

Everything worth doing in the module goes through its `states` table: `fips.states`.  By default, that table is indexed by states' postal abbreviations/codes (AL, AR, MS, etc.), which enables quick, human access to a state's info via `fips.states.[postal code here]`. The index is case-insensitive by default; so `fips.states.ak` works just as well as `fips.states.AK`, for example.  Each state is a dict that treats keys case-insensitively, treats unknown attributes as keys, and has a key `COUNTIES` that maps to a table of the county information for all the counties (or county-equivalents) in that state. Those county tables are indexed by the counties' FIPS codes (`'001'`, `'003'`, etc.). Those county tables use the same sort of case-insensitive, attribute-defering dict that the overall `states` table uses, but one other feature of these county tables is that calling the table with a single parameter will look that parameter up in the index, which gets around the inability to use digits at the start of attribute names.  Each county dict has a `STATE` key that points back to the state dict that the county (or county-equivalent) is part of.

    #For instance, 
    tangipahoa_parish = fips.states.la.counties('105')
    tangipahoa_water = tangipahoa_parish.awater
    tangipahoa_land = tangipahoa_parish.aland
    print(tangipahoa_parish.state is fips.states.la) # True

## kml

Basic tools for easily opening, saving, formatting, and otherwise handling KML files as bs4.BeautifulSoup XML documents, plus some tools for prepping a KML file for use as a KmlLayer in the Google Maps Javascript API.

