from transitions import Machine
import json
import random
import paho.mqtt.client as mqtt

class Recruit(object):
    def __init__(self, name, strength, alignment):
        self.name = name
        self.strength = strength
        self.alignment = alignment

    def is_fit(self):
        return self.strength >= 10

    def train(self):
        self.strength += 1

    def is_evil(self):
        return self.alignment == 'evil'


def jsonify(machine, recruit):
    return json.dumps({"recruit.name": recruit.name if recruit else None,
                       "recruit.strength": recruit.strength if recruit else None,
                       "recruit.alignment": recruit.alignment if recruit else None,
                       "machine.state": machine.state})


# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe("$SYS/#")

def on_message(client, userdata, msg):
    print(msg.topic+" "+str(msg.payload))

class DominiationMachine(object):

    states = ['looking_for_recruits', 'process', 'good', 'accept', 'decline', 'train', 'motivated', 'assess', 'take_over_the_world']

    def __init__(self):

        self.client = mqtt.Client()
        self.client.on_connect = on_connect
        self.client.on_message = on_message
        self.mqtt_connect()
        self.recruits = []
        self.applicant = None
        self.applicants = []

        self.machine = Machine(model=self, states=DominiationMachine.states, initial='looking_for_recruits')

        # looking_for_recruits
        self.machine.add_transition(trigger='recruit', source='looking_for_recruits', dest='process', conditions='has_applicant')
        self.machine.add_transition(trigger='no_recruit', source='looking_for_recruits', dest='looking_for_recruits', unless='has_applicant')

        # process
        self.machine.add_transition(trigger='good', source='process', dest='decline', unless='check_is_evil')
        self.machine.add_transition(trigger='evil', source='process', dest='accept', conditions='check_is_evil')

        # accept
        self.machine.add_transition(trigger='unfit', source='accept', dest='train', unless='check_is_fit')
        self.machine.add_transition(trigger='fit', source='accept', dest='assess', conditions='check_is_fit')

        # decline
        self.machine.add_transition(trigger='new_recruitment', source='decline', dest='looking_for_recruits')

        # train
        self.machine.add_transition(trigger='unfit', source='train', dest='motivated', unless='check_is_fit')
        self.machine.add_transition(trigger='fit', source='train', dest='assess', conditions='check_is_fit')

        # motivated
        self.machine.add_transition(trigger='yes', source='motivated', dest='train', conditions='check_has_motivation')
        self.machine.add_transition(trigger='no', source='motivated', dest='decline')

        # assess
        self.machine.add_transition(trigger='not_enough_members', source='assess', dest='looking_for_recruits', unless='have_enough_members')
        self.machine.add_transition(trigger='enough_members', source='assess', dest='take_over_the_world', conditions='have_enough_members')

        # publish our current status
        self.client.publish("wd/status", jsonify(self, self.applicant))

    def mqtt_connect(self):
        self.client.connect("localhost")

    def has_applicant(self):
        return self.applicant != None

    def new_applicant(self, applicant):
        recruit = Recruit(applicant['name'], applicant['strength'], alignment=applicant['alignment'])
        if not self.applicant:
            self.applicant = recruit
        else:
            self.applicants.append(recruit)

    def load_applications(self, path):
        with open(path) as f:
            for applicant in json.load(f):
                self.new_applicant(applicant)
        

    def recruit_applicant(self):
        self.recruits.append(self.applicant)
        self.applicant = None
    def decline_applicant(self):
        self.applicant = None
    def check_for_applicants(self):
        if self.applicant == None:
            try:
                self.applicant = self.applicants.pop()
            except:
                self.applicant = None

    def have_enough_members(self):
        return len(self.recruits) >= 3

    def check_is_fit(self):
        return self.applicant.is_fit()
    def check_has_motivation(self):
        return random.random() > 0.3
    def check_is_evil(self):
        return self.applicant.is_evil()

    def on_enter_looking_for_recruits(self):
        self.check_for_applicants()
        self.client.publish("wd/status", jsonify(self, self.applicant))
    def on_enter_process(self):
        self.client.publish("wd/status", jsonify(self, self.applicant))
    def on_enter_no_recruit(self):
        self.client.publish("wd/status", jsonify(self, self.applicant))
    def on_enter_decline(self):
        self.client.publish("wd/status", jsonify(self, self.applicant))
        self.decline_applicant()
    def on_enter_accept(self):
        self.client.publish("wd/status", jsonify(self, self.applicant))
    def on_enter_train(self):
        self.applicant.train()
        self.client.publish("wd/status", jsonify(self, self.applicant))
    def on_enter_motivated(self):
        self.client.publish("wd/status", jsonify(self, self.applicant))
    def on_enter_assess(self):
        self.recruit_applicant()
        self.client.publish("wd/status", jsonify(self, self.applicant))
    def on_enter_take_over_the_world(self):
        self.client.publish("wd/status", jsonify(self, self.applicant))

    def tick(self):
        if self.state == 'looking_for_recruits':
            if not self.recruit():
                self.no_recruit()
            return
        if self.state == 'process':
            if not self.good():
                self.evil()
            return
        if self.state == 'accept':
            if not self.fit():
                return self.unfit()
            return
        if self.state == 'decline':
            self.new_recruitment()
            return
        if self.state == 'assess':
            if not self.not_enough_members():
                self.enough_members()
            return
        if self.state == 'train':
            if not self.fit():
                self.unfit()
            return
        if self.state == 'motivated':
            if not self.yes():
                self.no()
            return
