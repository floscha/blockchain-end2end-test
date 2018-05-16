# Blockchain End-to-End Test
End-to-end test script for simple blockchain implementations using Docker containers.


## Run
First make sure that Python 3 (including pip) and Docker are installed.
Then build the Docker image as described [here](https://github.com/dvf/blockchain/blob/master/README.md#docker).
Finally navigate into the project folder and run the following:

1. `pip3 install -r requirements.txt`
to make sure all requirements are installed.
2. `python3 end2end_test.py --nodes 10 --tasks clean setup connect sync-test`
to run the full test cycle with 10 blockchain nodes.


## Options
Run the *end2end_test.py* script with the following arguments:

- `--image`: The Docker image to be run. Defaults to *blockchain*.
- `--nodes`: The number of Docker containers to be run. Defaults to 2.
- `--port`: The port exposed by the Docker image. Defaults to 5000.
- `--net`: The Docker network in which nodes communicate. Defaults to *blockchain*.
- `--tasks`: Takes a number of tasks as strings, including:
  - `clean`: Stops and removes all existing blockchain containers to start from a clean slate.
  - `setup`: Runs the specified number of blockchain nodes as Docker containers.
  - `connect`: Connect all nodes for implementations where nodes cannot find each other automatically.
  - `sync-test`: Test if the synchronization mechanism between nodes works.
- `--keepalive`: Keeps the containers running after the script finishes.

While the first four arguments can be left at their defaults for [Learn Blockchains by Building One](https://github.com/dvf/blockchain), the `--tasks` argument always has to be set.
