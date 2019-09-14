# What's all this, then?

These are just the `.dbf` files from the US Census Bureau's nationwide [county-equivalent](https://www.census.gov/cgi-bin/geo/shapefiles/index.php?year=2018&layergroup=Counties+%28and+equivalent%29) shapefile and the [state shapefile](https://www.census.gov/cgi-bin/geo/shapefiles/index.php?year=2018&layergroup=States+%28and+equivalent%29), but in plain text.

# But why?

For `fips.py`, which requires a source for the data it manages.

# But why?

Because I was sick of hardcoding stuff into scripts that only pertained to a single state, like the number of counties or some hacky way to generate the county fips codes.

With `fips.py`, getting magic-free access to all the county fips codes for, say, Kansas, is just a matter of 

    import fips
    fips.states.ks.counties.code #evaluates to a generator expression

Most states' counties' fips codes start at 1 and increase by 2s, but there are a few with some even-coded counties. That's some devilish detail. Memorized lists of fips codes are the only way around that sort of weird exception.
