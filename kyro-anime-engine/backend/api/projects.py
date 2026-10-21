"""backend/api/projects.py
GET    /api/projects        list summaries
POST   /api/projects        create {name, settings?}
GET/POST /api/projects/demo   create the bouncing-ball demo
GET/POST /api/projects/templates/<template> create an editable starter scene
Legacy /demo endpoints remain supported for older clients
GET    /api/projects/<id>   load
PUT    /api/projects/<id>   validate + save (full document)
DELETE /api/projects/<id>   delete
"""
from flask import Blueprint, jsonify, request

from backend.app.exceptions import ApiError
from backend.services import project_service as svc

bp = Blueprint("projects", __name__)


def _body():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ApiError(400, "Request body must be a JSON object")
    return data


@bp.get("/storage-status")
def storage_status():
    from backend.storage import project_repository

    backend = project_repository.backend_name()
    return jsonify(
        backend=backend,
        durable=(backend == "postgresql"),
        configured=(backend == "postgresql"),
        note=(
            "Projects are stored in managed PostgreSQL."
            if backend == "postgresql"
            else "Projects are stored as local JSON files. On ephemeral hosting, files can be lost on restart or redeploy; configure DATABASE_URL for durable PostgreSQL storage."
        ),
    )


@bp.get("")
def list_projects():
    return jsonify(projects=svc.list_projects())


@bp.post("")
def create_project():
    data = _body()
    return jsonify(svc.create_project(data.get("name", "Untitled"), data.get("settings"))), 201


@bp.route("/demo", methods=["GET", "POST"])
def create_demo():
    return jsonify(svc.create_demo("bounce")), 201


@bp.route("/demo/<template>", methods=["GET", "POST"])
def create_demo_template(template):
    return jsonify(svc.create_demo(template)), 201

@bp.route("/templates", methods=["GET", "POST"])
def create_default_template():
    return jsonify(svc.create_demo("bounce")), 201


@bp.route("/templates/<template>", methods=["GET", "POST"])
def create_template(template):
    return jsonify(svc.create_demo(template)), 201


@bp.post("/import")
def import_project():
    data = _body()
    return jsonify(svc.import_project(data)), 201


@bp.get("/<pid>")
def get_project(pid):
    return jsonify(svc.get_project(pid))

@bp.put("/<pid>")
def save_project(pid):
    return jsonify(svc.save_project(pid, _body()))


@bp.delete("/<pid>")
def delete_project(pid):
    svc.delete_project(pid)
    return "", 204
