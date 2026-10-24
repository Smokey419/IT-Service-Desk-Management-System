
import os
from datetime import datetime, timezone

from flask import (
    Flask, render_template, request,
    redirect, url_for, flash, abort
)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin, login_user,
    login_required, logout_user, current_user
)
from werkzeug.security import check_password_hash

app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY",
    "development-only-change-before-deployment"
)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///servicedesk.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = "home"


# ==========================================
# DATABASE MODELS
# ==========================================

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="employee")


class Ticket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    priority = db.Column(db.String(20), nullable=False, default="Medium")
    status = db.Column(db.String(20), nullable=False, default="Open")

    created_by = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    assigned_to = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=True
    )

    resolution_notes = db.Column(db.Text, nullable=True)

    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    requester = db.relationship(
        "User",
        foreign_keys=[created_by],
        backref="submitted_tickets"
    )

    assignee = db.relationship(
        "User",
        foreign_keys=[assigned_to],
        backref="assigned_tickets"
    )


class Asset(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    asset_tag = db.Column(db.String(50), unique=True, nullable=False)
    asset_type = db.Column(db.String(50), nullable=False)
    manufacturer = db.Column(db.String(100))
    model = db.Column(db.String(100))
    serial_number = db.Column(db.String(100))
    assigned_to = db.Column(db.String(100))
    status = db.Column(db.String(30), nullable=False, default="Available")
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


# ==========================================
# AUTHENTICATION
# ==========================================

@login_manager.user_loader
def load_user(user_id):
    try:
        return db.session.get(User, int(user_id))
    except (TypeError, ValueError):
        return None


@app.route("/")
def home():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    return render_template("login.html")


@app.route("/login", methods=["POST"])
def login():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")

    user = User.query.filter_by(username=username).first()

    if user and check_password_hash(user.password_hash, password):
        login_user(user)
        return redirect(url_for("dashboard"))

    return "Invalid username or password", 401


@app.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return redirect(url_for("home"))


# ==========================================
# DASHBOARD
# ==========================================

@app.route("/dashboard")
@login_required
def dashboard():
    query = Ticket.query

    if current_user.role != "admin":
        query = query.filter_by(created_by=current_user.id)

    tickets = query.order_by(
        Ticket.created_at.desc(),
        Ticket.id.desc()
    ).all()

    stats = {
        "total": len(tickets),
        "open": sum(t.status == "Open" for t in tickets),
        "progress": sum(t.status == "In Progress" for t in tickets),
        "resolved": sum(t.status == "Resolved" for t in tickets)
    }

    return render_template(
        "dashboard.html",
        stats=stats,
        recent_tickets=tickets[:5]
    )


# ==========================================
# TICKET MANAGEMENT
# ==========================================

@app.route("/tickets/new", methods=["GET", "POST"])
@login_required
def new_ticket():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        category = request.form.get("category", "")
        priority = request.form.get("priority", "")

        valid_categories = [
            "Hardware", "Software", "Network / VPN",
            "Email", "Account Access", "Other"
        ]

        if (
            not title
            or not description
            or len(title) > 150
            or category not in valid_categories
            or priority not in ["Low", "Medium", "High"]
        ):
            flash("Please enter valid ticket details.", "error")
            return render_template("new_ticket.html"), 400

        ticket = Ticket(
            title=title,
            description=description,
            category=category,
            priority=priority,
            status="Open",
            created_by=current_user.id
        )

        db.session.add(ticket)
        db.session.commit()

        flash("Your support ticket was submitted!", "success")
        return redirect(url_for("my_tickets"))

    return render_template("new_ticket.html")


@app.route("/tickets")
@login_required
def my_tickets():
    query = Ticket.query

    if current_user.role != "admin":
        query = query.filter_by(created_by=current_user.id)

    tickets = query.order_by(
        Ticket.created_at.desc(),
        Ticket.id.desc()
    ).all()

    return render_template("tickets.html", tickets=tickets)


@app.route("/tickets/<int:ticket_id>")
@login_required
def ticket_details(ticket_id):
    ticket = db.get_or_404(Ticket, ticket_id)

    if current_user.role != "admin" and ticket.created_by != current_user.id:
        abort(403)

    admins = User.query.filter_by(role="admin").order_by(User.username).all()

    return render_template(
        "ticket_details.html",
        ticket=ticket,
        admins=admins
    )


@app.route("/tickets/<int:ticket_id>/update", methods=["POST"])
@login_required
def update_ticket(ticket_id):
    if current_user.role != "admin":
        abort(403)

    ticket = db.get_or_404(Ticket, ticket_id)

    status = request.form.get("status", "")
    priority = request.form.get("priority", "")
    assigned_to = request.form.get("assigned_to", "")
    resolution_notes = request.form.get("resolution_notes", "").strip()

    if status not in ["Open", "In Progress", "Resolved"]:
        abort(400)

    if priority not in ["Low", "Medium", "High"]:
        abort(400)

    if assigned_to:
        try:
            admin_id = int(assigned_to)
        except ValueError:
            abort(400)

        admin = db.session.get(User, admin_id)

        if not admin or admin.role != "admin":
            abort(400)

        ticket.assigned_to = admin.id
    else:
        ticket.assigned_to = None

    if len(resolution_notes) > 5000:
        abort(400)

    ticket.status = status
    ticket.priority = priority
    ticket.resolution_notes = resolution_notes

    db.session.commit()

    flash("Ticket updated successfully!", "success")

    return redirect(
        url_for("ticket_details", ticket_id=ticket.id)
    )


# ==========================================
# ASSET MANAGEMENT
# ==========================================

ASSET_TYPES = [
    "Laptop", "Desktop", "Monitor",
    "Printer", "Mobile Device", "Other"
]

ASSET_STATUSES = [
    "Available", "Assigned",
    "In Repair", "Retired"
]


@app.route("/assets")
@login_required
def assets():
    if current_user.role != "admin":
        abort(403)

    all_assets = Asset.query.order_by(Asset.id.desc()).all()

    return render_template(
        "assets.html",
        assets=all_assets
    )


@app.route("/assets/new", methods=["GET", "POST"])
@login_required
def new_asset():
    if current_user.role != "admin":
        abort(403)

    if request.method == "POST":
        asset_tag = request.form.get("asset_tag", "").strip()
        asset_type = request.form.get("asset_type", "")
        manufacturer = request.form.get("manufacturer", "").strip()
        model = request.form.get("model", "").strip()
        serial_number = request.form.get("serial_number", "").strip()
        assigned_to = request.form.get("assigned_to", "").strip()
        status = request.form.get("status", "")
        notes = request.form.get("notes", "").strip()

        if (
            not asset_tag
            or len(asset_tag) > 50
            or asset_type not in ASSET_TYPES
            or status not in ASSET_STATUSES
            or len(manufacturer) > 100
            or len(model) > 100
            or len(serial_number) > 100
            or len(assigned_to) > 100
            or len(notes) > 5000
        ):
            flash("Please enter valid asset information.", "error")
            return render_template(
                "asset_form.html",
                asset=None,
                asset_types=ASSET_TYPES,
                asset_statuses=ASSET_STATUSES
            ), 400

        if Asset.query.filter_by(asset_tag=asset_tag).first():
            flash("That asset tag already exists.", "error")
            return render_template(
                "asset_form.html",
                asset=None,
                asset_types=ASSET_TYPES,
                asset_statuses=ASSET_STATUSES
            ), 400

        asset = Asset(
            asset_tag=asset_tag,
            asset_type=asset_type,
            manufacturer=manufacturer,
            model=model,
            serial_number=serial_number,
            assigned_to=assigned_to,
            status=status,
            notes=notes
        )

        db.session.add(asset)
        db.session.commit()

        flash("Asset added successfully!", "success")
        return redirect(url_for("assets"))

    return render_template(
        "asset_form.html",
        asset=None,
        asset_types=ASSET_TYPES,
        asset_statuses=ASSET_STATUSES
    )


@app.route("/assets/<int:asset_id>/edit", methods=["GET", "POST"])
@login_required
def edit_asset(asset_id):
    if current_user.role != "admin":
        abort(403)

    asset = db.get_or_404(Asset, asset_id)

    if request.method == "POST":
        asset_tag = request.form.get("asset_tag", "").strip()
        asset_type = request.form.get("asset_type", "")
        manufacturer = request.form.get("manufacturer", "").strip()
        model = request.form.get("model", "").strip()
        serial_number = request.form.get("serial_number", "").strip()
        assigned_to = request.form.get("assigned_to", "").strip()
        status = request.form.get("status", "")
        notes = request.form.get("notes", "").strip()

        if (
            not asset_tag
            or len(asset_tag) > 50
            or asset_type not in ASSET_TYPES
            or status not in ASSET_STATUSES
            or len(manufacturer) > 100
            or len(model) > 100
            or len(serial_number) > 100
            or len(assigned_to) > 100
            or len(notes) > 5000
        ):
            flash("Please enter valid asset information.", "error")
            return render_template(
                "asset_form.html",
                asset=asset,
                asset_types=ASSET_TYPES,
                asset_statuses=ASSET_STATUSES
            ), 400

        duplicate = Asset.query.filter(
            Asset.asset_tag == asset_tag,
            Asset.id != asset.id
        ).first()

        if duplicate:
            flash("That asset tag already exists.", "error")
            return redirect(url_for("edit_asset", asset_id=asset.id))

        asset.asset_tag = asset_tag
        asset.asset_type = asset_type
        asset.manufacturer = manufacturer
        asset.model = model
        asset.serial_number = serial_number
        asset.assigned_to = assigned_to
        asset.status = status
        asset.notes = notes

        db.session.commit()

        flash("Asset updated successfully!", "success")
        return redirect(url_for("assets"))

    return render_template(
        "asset_form.html",
        asset=asset,
        asset_types=ASSET_TYPES,
        asset_statuses=ASSET_STATUSES
    )


# ==========================================
# TICKET SEARCH AND FILTERING
# ==========================================

@app.route("/tickets/search")
@login_required
def search_tickets():

    search = request.args.get("search", "").strip()
    status = request.args.get("status", "").strip()
    priority = request.args.get("priority", "").strip()
    category = request.args.get("category", "").strip()

    query = Ticket.query

    # Employees can only search their own tickets.
    # Administrators can search all tickets.
    if current_user.role != "admin":
        query = query.filter_by(created_by=current_user.id)

    # Search by ticket ID, title, or description.
    if search:
        from sqlalchemy import or_, cast, String

        query = query.filter(
            or_(
                cast(Ticket.id, String).ilike(f"%{search}%"),
                Ticket.title.ilike(f"%{search}%"),
                Ticket.description.ilike(f"%{search}%")
            )
        )

    # Apply filters.
    if status:
        query = query.filter(Ticket.status == status)

    if priority:
        query = query.filter(Ticket.priority == priority)

    if category:
        query = query.filter(Ticket.category == category)

    tickets = query.order_by(
        Ticket.created_at.desc(),
        Ticket.id.desc()
    ).all()

    return render_template(
        "tickets.html",
        tickets=tickets,
        search=search,
        selected_status=status,
        selected_priority=priority,
        selected_category=category
    )



# ==========================================
# START APPLICATION
# ==========================================

if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    app.run(debug=True)
