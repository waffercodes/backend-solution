# write me a route to get all stashpoints

from flask import Blueprint, jsonify
from app.models import Stashpoint


bp = Blueprint("stashpoints", __name__)


@bp.route("/", methods=["GET"])
def get_stashpoints():
    stashpoints = Stashpoint.query.all()
    return jsonify([stashpoint.to_dict() for stashpoint in stashpoints])
