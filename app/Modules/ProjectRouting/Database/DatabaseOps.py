import sqlite3


def delete_table_nexus(mydb, cursor) -> None:
    """Deletes existing database table Routing_Nexus"""

    try:
        cursor.execute('''DROP TABLE Routing_Nexus''')
        mydb.commit()
    except sqlite3.OperationalError:
        pass


def db_table_cleanup(f):
    """Decorator for database table cleanup"""

    def db_check(self, mydb, cursor):

        funtion = None

        if f.__name__ == "create_database_table_nexus":
            delete_table_nexus(mydb, cursor)
            funtion = f(self, mydb, cursor)

        return funtion

    return db_check


def db_update_nexus(mydb, cursor, vdc=None, vrf=None, prefix=None, protocol=None, admin_distance=None, nexthops=None, interfaces=None,
                    metric=None, age=None, tag=None) -> None:
    cursor.execute("INSERT INTO Routing_Nexus VALUES ('%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s')" %
                   (vdc, vrf, prefix, protocol, admin_distance, nexthops, interfaces, metric, tag, age))
    mydb.commit()

class RoutingDatabase:
    """Class of methods performs database funtions:
                                Creates tables in database
                                Inserts rows into database tables"""

    def __init__(self, mydb, conn):
        self.create_database_table_nexus(mydb, conn)


    @db_table_cleanup
    def create_database_table_nexus(self, mydb, cursor) -> None:
        """Create routing TABLE in routing database"""

        cursor.execute('''CREATE TABLE Routing_Nexus (vdc, vrf, prefix, protocol, admin_distance, nexthops, 
        interfaces, metric, tag, age)''')
        mydb.commit()


