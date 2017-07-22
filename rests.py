import logging

from flask_restful import Resource, reqparse


class RegisterAPI(Resource):
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('user_name', type=str, help='User name')
        parser.add_argument('team_name', type=str, help='Team name')
        parser.add_argument('sub_domain', type=str, help='Sub domain')
        args = parser.parse_args()
        logging.info(args)
        return {'hello': 'world'}
