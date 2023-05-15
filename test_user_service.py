from flask_testing import TestCase
from user_service import app, db, User

class UserServiceTestCase(TestCase):
    def create_app(self):
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        return app

    def setUp(self):
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def test_add_user(self):
        response = self.client.post('/user', json={
            'username': 'test',
            'email': 'test@example.com',
            'password': 'password123',
            'interests': 'interests'
        })
        self.assert200(response)

    # Add more tests...

if __name__ == '__main__':
    import unittest
    unittest.main()
