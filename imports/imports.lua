-- osm2pgsql --password --database=hiking_data --user=osmuser --host=127.0.0.1 --port=5432 --create --style=./imports/imports.lua --output=flex ./data/alps-latest.osm.pbf

local function isHut(tags)
    return tags.tourism == 'alpine_hut'
        or tags.tourism == 'wilderness_hut'
        or tags.tourism == 'basic_hut'
        or (tags.amenity == 'shelter' and tags.shelter_type == 'lean_to')
end

local function isAccomodation(tags)
    return tags.tourism == 'camp_site'
        or tags.tourism == 'chalet'
        or tags.tourism == 'quest_house'
        or tags.tourim == 'motel'
        or tags.tourism == 'hotel'
        or tags.tourism == 'hostel'
end

local function isWater(tags)
    return tags.amenity == 'drinking_water'
        or tags.natural == 'spring'
        or tags.drinking_water ~= nil
        or tags['drinking_water:legal'] ~= nil
        or tags['disused:amenity'] == 'drinking_water'
        or tags['abandoned:amenity'] == 'drinking_water'
        or tags.amenity == 'water_point'
        or tags.waterway == 'water_point'
end

local function isNatural(tags)
    return tags.natural == 'hot_spring'
        or tags.natural == 'cave_entrance'
        or tags.natural == 'hill'
        or tags.natural == 'peak'
        or tags.natural == 'saddle'
end

local function isPark(tags)
    return tags.boundary == 'national_park'
        or tags.boundary == 'protected_area'
        or tags.leisure == 'nature_reserve'
end

local function isGuidepost(tags)
    return tags.tourism == 'information'
        and tags.information == 'guidepost'
end

local function isInformation(tags)
    return tags.tourism == 'information'
        and (
            tags.information == 'board'
            or tags.information == 'office'
        )
end

local function isHistoric(tags)
    return tags.historic ~= nil
end

local function isCairn(tags)
    return tags.man_made == 'cairn'
end

local function isCross(tags)
    return tags['summit:cross'] == 'yes'
end

local function isViewPoint(tags)
    return tags.tourism == 'viewpoint'
end

local function isAtm(tags)
    return tags.amenity == 'atm'
    -- or tags.atm == 'yes'
end

local function isPost(tags)
    return tags.amenity == 'post_box'
        or tags.amenity == 'post_office'
end

local function isShop(tags)
    return tags.shop == 'cheese'
        or tags.shop == 'bakery'
        or tags.shop == 'supermarket'
        or tags.shop == 'sports'
        or tags.shop == 'outdoor'
end

local function isToilets(tags)
    return tags.amenity == 'toilets'
end

local function isHealth(tags)
    return tags.amenity == 'pharmacy'
end

-- order mater
-- a hut can be marker as drinking_water = yes for instance
local function getObjecType(tags)
    if isHut(tags) then
        return 'hut'
    elseif isWater(tags) then
        return 'water'
    elseif isNatural(tags) then
        return 'natural'
    elseif isAccomodation(tags) then
        return 'accomodation'
    elseif isPark(tags) then
        return 'park'
    elseif isGuidepost(tags) then
        return 'guidepost'
    elseif isInformation(tags) then
        return 'information'
    elseif isHistoric(tags) then
        return 'historic'
    elseif isCross(tags) then
        return 'cross'
        -- elseif isCairn(tags) then
        --     return 'cairn'
    elseif isViewPoint(tags) then
        return 'viewpoint'
    elseif isAtm(tags) then
        return 'atm'
    elseif isPost(tags) then
        return 'post'
    elseif isShop(tags) then
        return 'shop'
    elseif isToilets(tags) then
        return 'toilets'
    elseif isHealth(tags) then
        return 'health'
    else
        return nil
    end
end

local function clean_tags(tags)
    tags.odbl = nil
    tags.created_by = nil
    tags.source = nil
    tags['source:ref'] = nil

    return next(tags) == nil
end



local tables = {}

tables.nodes = osm2pgsql.define_table({
    name = 'nodes',
    ids = { type = 'any', id_column = 'id' },
    columns = {
        { column = 'name',        type = 'text' },
        { column = 'osm_type',    type = 'text' },
        { column = 'object_type', type = 'text' },
        { column = 'tags',        type = 'hstore' },
        { column = 'geom',        type = 'point', projection = 4326, not_null = true },
    }
})


tables.polygons = osm2pgsql.define_table({
    name = 'polygons',
    ids = { type = 'area', id_column = 'id' },
    columns = {
        { column = 'name',        type = 'text' },
        { column = 'osm_type',    type = 'text' },
        { column = 'object_type', type = 'text' },
        { column = 'tags',        type = 'hstore' },
        { column = 'centroid',    type = 'point',    projection = 4326, not_null = true },
        { column = 'geom',        type = 'geometry', projection = 4326, not_null = true },
    }
})


local function insert_node(tags, osm_type, object_type, geom)
    tables.nodes:insert({
        name = tags.name,
        osm_type = osm_type,
        object_type = object_type,
        tags = tags,
        geom = geom,
    })
end

function osm2pgsql.process_node(object)
    if clean_tags(object.tags) then
        return
    end

    local object_type = getObjecType(object.tags)

    if object_type == nil then
        return
    end

    local geom = object:as_point()

    insert_node(
        object.tags,
        'node',
        object_type,
        geom
    )
end

function osm2pgsql.process_way(object)
    if clean_tags(object.tags) then
        return
    end

    local object_type = getObjecType(object.tags)

    if object_type == nil then
        return
    end

    if object.is_closed then
        if isPark(object.tags) then
            local geom = object:as_polygon()

            tables.polygons:insert({
                name = object.tags.name,
                osm_type = 'way',
                object_type = 'park',
                tags = object.tags,
                centroid = geom:centroid(),
                geom = geom,
            })
        else
            local geom = object:as_polygon():centroid()

            insert_node(
                object.tags,
                'way',
                object_type,
                geom
            )
        end
    end
end

function osm2pgsql.process_relation(object)
    if clean_tags(object.tags) then
        return
    end

    if object.tags.type ~= 'multipolygon'
        and object.tags.type ~= 'boundary' then
        return
    end

    local object_type = getObjecType(object.tags)
    local osm_type = nil

    if object_type == nil then
        return
    end

    local geom = nil

    if object.tags.type == 'multipolygon' then
        osm_type = 'relation_multipolygon'
        geom = object:as_multipolygon()
    elseif object.tags.type == 'boundary' then
        osm_type = 'relation_boundary'
        -- geom = object:as_multilinestring():line_merge()
        geom = object:as_multipolygon()
    else
        return
    end

    if isPark(object.tags) then
        tables.polygons:insert({
            name = object.tags.name,
            osm_type = osm_type,
            object_type = object_type,
            tags = object.tags,
            centroid = geom:centroid(),
            geom = geom,
        })
    else
        insert_node(
            object.tags,
            osm_type,
            object_type,
            geom:centroid()
        )
    end
end
