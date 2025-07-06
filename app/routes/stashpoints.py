from flask import Blueprint, jsonify, request
from pydantic import ValidationError
from datetime import datetime
from sqlalchemy import func, and_, or_, cast, Float
from app.models import Stashpoint, Booking
from app.schemas.stashpoints import StashpointSearchParams, StashpointResponse
from app import db


bp = Blueprint("stashpoints", __name__)


@bp.route("/", methods=["GET"])
def get_stashpoints():
    """
    Get stashpoints, optionally filtered by location/time/capacity.

    Query params:
    - lat/lng: search coordinates
    - dropoff/pickup: ISO datetime strings
    - bag_count: how many bags
    - radius_km: max distance (optional)

    Filters:
    - Within radius (if specified)
    - Has capacity for the bags during the time period
    - Open at both dropoff and pickup times

    Sorted by distance from search point.
    """
    # grab query params
    query_params = request.args.to_dict()

    # no params? return everything
    if not query_params:
        stashpoints = Stashpoint.query.all()
        return jsonify([stashpoint.to_dict() for stashpoint in stashpoints])

    # validate params
    try:
        # convert strings to proper types
        if 'lat' in query_params:
            query_params['lat'] = float(query_params['lat'])
        if 'lng' in query_params:
            query_params['lng'] = float(query_params['lng'])
        if 'bag_count' in query_params:
            query_params['bag_count'] = int(query_params['bag_count'])
        if 'radius_km' in query_params:
            query_params['radius_km'] = float(query_params['radius_km'])

        # parse datetime strings
        if 'dropoff' in query_params:
            query_params['dropoff'] = datetime.fromisoformat(query_params['dropoff'].replace('Z', '+00:00'))
        if 'pickup' in query_params:
            query_params['pickup'] = datetime.fromisoformat(query_params['pickup'].replace('Z', '+00:00'))

        # run pydantic validation
        search_params = StashpointSearchParams(**query_params)
    except (ValueError, ValidationError) as e:
        if isinstance(e, ValidationError):
            errors = []
            for error in e.errors():
                field = '.'.join(str(x) for x in error['loc'])
                errors.append({
                    'field': field,
                    'message': error['msg'],
                    'type': error['type']
                })
            return jsonify({'error': 'Validation failed', 'details': errors}), 400
        else:
            return jsonify({'error': str(e)}), 400

    # start building query
    query = Stashpoint.query

    # calculate distance using PostGIS
    # ST_Distance returns meters for geography types
    distance_meters = func.ST_Distance(
        Stashpoint.location,
        func.ST_GeogFromText(f'POINT({search_params.lng} {search_params.lat})')
    )

    # convert to km, handle nulls just in case
    distance_km = func.coalesce(cast(distance_meters / 1000.0, Float), 0.0)

    # add distance column
    query = query.add_columns(distance_km.label('distance_km'))

    # filter by radius if provided
    if search_params.radius_km:
        query = query.filter(distance_meters <= search_params.radius_km * 1000)

    # check capacity - count existing bookings in the time period
    booking_counts = db.session.query(
        Booking.stashpoint_id,
        func.sum(Booking.bag_count).label('booked_bags')
    ).filter(
        and_(
            # overlapping bookings
            Booking.dropoff_time < search_params.pickup,
            Booking.pickup_time > search_params.dropoff,
            # skip cancelled ones
            Booking.is_cancelled == False
        )
    ).group_by(Booking.stashpoint_id).subquery()

    # join and check available capacity
    query = query.outerjoin(
        booking_counts,
        Stashpoint.id == booking_counts.c.stashpoint_id
    ).filter(
        # enough space left?
        Stashpoint.capacity - func.coalesce(booking_counts.c.booked_bags, 0) >= search_params.bag_count
    )

    # check if open at both times
    dropoff_time = search_params.dropoff.time()
    pickup_time = search_params.pickup.time()

    # must be open for both dropoff and pickup
    query = query.filter(
        and_(
            Stashpoint.open_from <= dropoff_time,
            Stashpoint.open_until >= dropoff_time,
            Stashpoint.open_from <= pickup_time,
            Stashpoint.open_until >= pickup_time
        )
    )

    # sort by distance
    query = query.order_by(distance_km)
    results = query.all()

    # format results
    response_data = []
    for stashpoint, distance in results:
        stashpoint_dict = stashpoint.to_dict()
        stashpoint_dict['distance_km'] = round(distance, 2) if distance is not None else 0.0
        response_data.append(stashpoint_dict)

    return jsonify(response_data)
