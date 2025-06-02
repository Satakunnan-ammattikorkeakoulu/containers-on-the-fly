import pymysql
from urllib.parse import urlparse, unquote
import argparse

def check_database_connection(uri : str):
    '''
    Checks that connection to the given MySQL database URI can be established.

    Args:
        uri (str): URI to the database.

    Returns:
        OK (str): If connection was succesfull.
        NOT_OK (str): If connection was not succesfull.
    '''
    try:
        # Parse the URI
        parsed_uri = urlparse(uri)
        host = parsed_uri.hostname
        user = parsed_uri.username
        password = unquote(parsed_uri.password) if parsed_uri.password else None
        db = parsed_uri.path.lstrip('/')
        port = parsed_uri.port or 3306  # Default MySQL port
        
        # Attempt to establish a connection to the database
        connection = pymysql.connect(
            host=host,
            user=user,
            password=password,
            db=db,
            port=port
        )
        # If connection is successful
        print("CONNECTION_OK")
        connection.close()
    except pymysql.MySQLError as e:
        # If an error occurs, print the error
        print("CONNECTION_NOT_OK")
    except Exception as e:
        print("CONNECTION_NOT_OK")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Check MySQL database connection using URI.')
    parser.add_argument('database_uri', type=str, help='The database URI to connect to.')
    args = parser.parse_args()
    
    check_database_connection(args.database_uri)