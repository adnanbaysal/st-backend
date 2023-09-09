import logging
import os

import psycopg2

logger = logging.getLogger(__name__)


def connect_to_db():
    con = psycopg2.connect(
        database="postgres_test",
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        host=os.environ["POSTGRES_HOST"],
        port=os.environ["POSTGRES_PORT_TEST"],
    )
    return con


def delete_users_after_test(func: callable) -> callable:
    def decorated(*args, **kwargs):
        ret_val = func(*args, **kwargs)

        logger.info("deleting users after test")
        con = connect_to_db()
        cursor = con.cursor()
        cursor.execute("DELETE FROM auth_user")
        con.commit()
        con.close()

        return ret_val

    return decorated
