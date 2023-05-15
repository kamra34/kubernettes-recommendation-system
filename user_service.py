from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from sqlalchemy.exc import IntegrityError
from flask_wtf import FlaskForm
from wtforms import Form, StringField
from wtforms.validators import InputRequired, Email
from werkzeug.security import generate_password_hash, check_password_hash
from wtforms import PasswordField
from werkzeug.datastructures import MultiDict
import os

app = Flask(__name__)


basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, 'db/test.db')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_path

db = SQLAlchemy(app)
ma = Marshmallow(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    interests = db.Column(db.String(300), nullable=True)
    password_hash = db.Column(db.String(128))

    def __repr__(self):
        return '<User %r>' % self.username
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def update_password(self, new_password):
        self.password_hash = generate_password_hash(new_password)

class UserPreferences(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    preferences = db.Column(db.String(300), nullable=True)

    user = db.relationship('User', backref='preferences')

    def __repr__(self):
        return '<UserPreferences %r>' % self.user_id

class UserSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = User

class UserPreferencesSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = UserPreferences

class JsonForm(Form):
    @classmethod
    def from_json(cls, data):
        return cls(MultiDict(data))

class UserForm(JsonForm):
    username = StringField('Username', validators=[InputRequired()])
    email = StringField('Email', validators=[InputRequired(), Email()])
    password = PasswordField('Password', validators=[InputRequired()])
    interests = StringField('Interests')

class LoginForm(JsonForm):
    username = StringField('Username', validators=[InputRequired()])
    password = PasswordField('Password', validators=[InputRequired()])

class UserPreferencesForm(JsonForm):
    preferences = StringField('Preferences')


user_schema = UserSchema()
users_schema = UserSchema(many=True)

@app.route('/user', methods=['POST'])
def add_user():
    form = UserForm.from_json(request.json)
    if not form.validate():
        return jsonify(form.errors), 400

    new_user = User(username=form.username.data, email=form.email.data, interests=form.interests.data)
    new_user.set_password(form.password.data)

    try:
        db.session.add(new_user)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify(message="Username or email already exists."), 400

    return user_schema.jsonify(new_user), 201

@app.route('/user/<id>', methods=['GET'])
def get_user(id):
    user = User.query.get(id)
    if user is None:
        return jsonify(message="User not found."), 404
    return user_schema.jsonify(user)

@app.route('/user/<id>', methods=['PUT'])
def update_user(id):
    user = User.query.get(id)
    if user is None:
        return jsonify(message="User not found."), 404

    username = request.json.get('username')
    email = request.json.get('email')
    interests = request.json.get('interests', '')

    if username is not None:
        user.username = username
    if email is not None:
        user.email = email
    if interests is not None:
        user.interests = interests

    db.session.commit()

    return user_schema.jsonify(user)

@app.route('/user/<id>/password', methods=['PUT'])
def update_password(id):
    user = User.query.get(id)
    if user is None:
        return jsonify(message="User not found."), 404

    form = JsonForm.from_json(request.json)
    if not form.validate():
        return jsonify(form.errors), 400

    new_password = form.data.get('new_password')

    if not new_password:
        return jsonify(message="New password is required."), 400

    user.update_password(new_password)
    db.session.commit()

    return jsonify(message="Password updated successfully.")


@app.route('/login', methods=['POST'])
def login():
    form = LoginForm.from_json(request.json)
    if not form.validate():
        return jsonify(form.errors), 400

    user = User.query.filter_by(username=form.username.data).first()
    if user is None or not user.check_password(form.password.data):
        return jsonify(message="Invalid username or password."), 400

    # for now, return a simple message. In a real application, you might want to return a token
    return jsonify(message="Logged in successfully.")

@app.route('/user/<id>/preferences', methods=['GET'])
def get_preferences(id):
    user = User.query.get(id)
    if user is None or user.preferences is None:
        return jsonify(message="Preferences not found."), 404

    return UserPreferencesSchema().jsonify(user.preferences)

@app.route('/user/<id>/preferences', methods=['PUT'])
def update_preferences(id):
    user = User.query.get(id)
    if user is None:
        return jsonify(message="User not found."), 404

    form = UserPreferencesForm.from_json(request.json)
    if not form.validate():
        return jsonify(form.errors), 400

    preferences = form.preferences.data

    if user.preferences is None:
        user.preferences = UserPreferences(user_id=user.id, preferences=preferences)
    else:
        user.preferences.preferences = preferences

    db.session.commit()

    return UserPreferencesSchema().jsonify(user.preferences)

@app.route('/', methods=['GET'])
def home():
    return "User Service is running!"

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0')
