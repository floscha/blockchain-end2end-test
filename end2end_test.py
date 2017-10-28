"""End-to-end test script for the blockchain using Docker containers.

Mainly built for the simplified implementation by Daniel van Flymen:
    https://github.com/dvf/blockchain
"""

import argparse
from termcolor import colored
import time

import docker
import requests


class Node(object):
    """Simple data object representing a node in the blockchain network."""

    def __init__(self, name, container_id, port):
        """Initialize a new node object."""
        self.name = name
        self.container_id = container_id
        self.port = port


client = docker.from_env()


def cleanup(image):
    """(Forcefully) stop and remove all running containers of a given image."""
    containers = client.containers.list(filters={'name': image}, all=True)

    print("Stopping and removing running nodes...")
    for cont in containers:
        cont.kill()
        cont.remove()


def list_nodes(image, base_port):
    """Retrieve a list of all currently running blockchain nodes."""
    containers = client.containers.list(filters={'name': image})
    nodes = []

    for container in containers:
        name = container.name
        short_id = container.id[:12]
        all_ports = container.attrs['NetworkSettings']['Ports']
        address = all_ports[str(base_port) + '/tcp']
        assert len(address) == 1
        port = address[0]['HostPort']
        new_node = Node(name, short_id, port)
        nodes.append(new_node)

    return nodes


def maybe_create_network(network):
    """Create a network if it does not already exist."""
    try:
        client.networks.get(network)
    except docker.errors.NotFound:
        client.networks.create(network)


def create_nodes(image, num_nodes, port, network):
    """Create a number of blockchain nodes as Docker containers."""
    assert type(port) is int

    maybe_create_network(network)

    print("Starting %d new nodes..." % num_nodes)
    for i in range(num_nodes):
        client.containers.run(image,
                              name='%s-%d' % (image, i),
                              detach=True,
                              network=network,
                              ports={port: port + i})

    print(colored("Nodes successfully started", 'green'))

    # Give Docker 2 seconds to spin up the containers.
    time.sleep(2)

    nodes = list_nodes(image, port)

    print("Validating initial state...")
    for v in nodes:
        try:
            r = requests.get('http://localhost:%s/chain' % v.port)
            initial_chain_length = r.json()['length']
            assert initial_chain_length == 1
            print("\t%s: good" % v.name)
        except Exception:
            print("\t%s: bad" % v.name)
    print(colored("All initial states are valid", 'green'))


def connect_nodes(image, port):
    """Register each nodes at all other nodes using the provided REST API."""
    nodes = list_nodes(image, port)

    for v in nodes:
        print("Connecting %s (%s) to" % (v.name, v.container_id))
        other_nodes = [cv for cv in nodes if cv.name != v.name]
        for cv in other_nodes:
            print("\t%s (%s)" % (cv.name, cv.container_id))
        # Use port samw port for all nodes!
        json_data = {'nodes': ['http://%s:%s' % (cv.container_id, port)
                               for cv in other_nodes]}
        r = requests.post('http://localhost:%s/nodes/register' %
                          v.port, json=json_data)
        json_response = r.json()
        assert len(json_response['total_nodes']) == len(other_nodes)

    print(colored("All notes were successfully connected", 'green'))


def sync_test(image, port):
    """Test if the synchronization mechanism between nodes works.

    First, add some blocks to the blockchain of one node.
    Then, update all other nodes using the provided REST API.
    """
    print("Running synchronization test...")
    blocks_to_add = 2
    nodes = list_nodes(image, port)

    if len(nodes) < 2:
        raise ValueError("At least 2 running nodes are needed to synchronize")

    first_node = nodes[0]
    print("\tCreating new blocks on %s (%s)" % (first_node.name,
                                                first_node.container_id))

    r = requests.get('http://localhost:%s/chain' % first_node.port)
    initial_chain_length = r.json()['length']

    # Add more blocks to first node's chain by mining.
    for _ in range(blocks_to_add):
        r = requests.get('http://localhost:%s/mine' % first_node.port)

    r = requests.get('http://localhost:%s/chain' % first_node.port)
    updated_chain_length = r.json()['length']
    assert updated_chain_length - initial_chain_length == blocks_to_add

    # Syncing other nodes.
    for i in range(1, len(nodes)):
        other_node = nodes[i]
        print("\tSyncing up %s (%s)" % (other_node.name,
                                        other_node.container_id))

        r = requests.get('http://localhost:%s/chain' % other_node.port)
        other_node_initial_chain_length = r.json()['length']

        try:
            r = requests.get('http://localhost:%s/nodes/resolve' %
                             other_node.port)
            message = r.json()['message']
            assert message == 'Our chain was replaced'
        except Exception as e:
            print(colored("Syncing '%s' failed:" % other_node.name, 'red'))
            raise e

        r = requests.get('http://localhost:%s/chain' % other_node.port)
        other_node_updated_chain_length = r.json()['length']

        assert other_node_updated_chain_length \
            - other_node_initial_chain_length == blocks_to_add

    print(colored("Synchronization successful", 'green'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Test a blockchain using \
                                     Docker containers.')
    parser.add_argument('--image', dest='image', type=str,
                        default='blockchain',
                        help='the Docker image to be run')
    parser.add_argument('--nodes', dest='nodes', type=int, default=2,
                        help='the number of nodes to launch')
    parser.add_argument('--port', dest='port', type=int, default=5000,
                        help='the port exposed through the Dockerfile')
    parser.add_argument('--net', dest='net', type=str, default='blockchain',
                        help='the Docker network in which the nodes \
                        communicate')
    parser.add_argument('--tasks', dest='tasks', type=str, nargs='+',
                        required=True,
                        help='an integer for the accumulator')

    args = parser.parse_args()
    image = args.image
    num_nodes = args.nodes
    port = args.port
    network = args.net
    tasks = args.tasks

    print(colored("Script launched with the following tasks: %s" % tasks,
                  'yellow'))

    if 'clean' in tasks:
        cleanup(image)

    assert port is not None

    if 'setup' in tasks:
        if not network:
            raise ValueError("'--net' parameter has to be set for \
                             'setup' task")
        create_nodes(image, num_nodes, port, network)

    if 'connect' in tasks:
        connect_nodes(image, port)

    if 'sync-test' in tasks:
        sync_test(image, port)
