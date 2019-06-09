# The Rise of the State Machine

Helpful guide for world domination

## Get it up and running

In console

``` shell
pip install -r requirements.txt
docker-compose up
ipython
```

In iPython REPL

``` python
from world_domination import domination

# starts our Domination Machine
d = domination.DominationMachine()

# we load the applicants we want
d.load_applications('applications.json')

# have the state machine run one tick
# the actions are sent out over MQTT and will be caught by the frontend that you
# will need to have running in order to see what's happening

# alternatively you can have MQTT.fx or some other client subscribe to the
# channel wd/status
d.tick()
```
