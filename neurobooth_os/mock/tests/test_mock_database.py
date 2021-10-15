import psycopg2
from sshtunnel import SSHTunnelForwarder

from neurobooth_os.mock import insert_mock_rows, delete_mock_rows


def test_neurobooth_mock():
    """Call function to test neurobooth."""

    ssh_username = 'mj513'
    with SSHTunnelForwarder(
        'neurodoor.nmr.mgh.harvard.edu',
        ssh_username=ssh_username,
        ssh_config_file='~/.ssh/config',
        ssh_pkey='~/.ssh/id_rsa',
        remote_bind_address=('192.168.100.1', 5432),
        local_bind_address=('localhost', 6543)) as tunnel:

        with psycopg2.connect(database='mock_neurobooth',
                              user='neuroboother',
                              password='neuroboothrocks',
                              host=tunnel.local_bind_host,
                              port=tunnel.local_bind_port) as conn_mock:
            delete_mock_rows(conn_mock)
            insert_mock_rows(conn_mock)
            delete_mock_rows(conn_mock)