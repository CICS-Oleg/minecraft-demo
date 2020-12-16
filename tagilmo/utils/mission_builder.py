#skipped:
#<ModSettings>
#    <MsPerTick>10</MsPerTick>
#</ModSettings>


class About:

    def __init__(self, summary_string=None):
        self.summary = summary_string

    def xml(self):
        _xml = '<About>\n'
        if self.summary:
            _xml += "<Summary>"+self.summary+"</Summary>"
        else:
            _xml += "<Summary/>";
        _xml += '\n</About>\n'
        return _xml



class ServerInitialConditions:
    
    def __init__(self, day_always=False, time_start_string=None, time_pass_string=None,
                 weather_string=None, spawning_string=None, allowedmobs_string=None):
        self.day_always = day_always
        self.time_start = time_start_string
        self.time_pass = time_pass_string
        self.weather = weather_string
        self.spawning = spawning_string
        self.allowedmobs = allowedmobs_string

    def xml(self):
        _xml = '<ServerInitialConditions>\n'
        if self.day_always:
            _xml += '''    <Time>
        <StartTime>6000</StartTime>
        <AllowPassageOfTime>false</AllowPassageOfTime>
    </Time>
    <Weather>clear</Weather>\n'''
        # ignore time_start_string, time_pass, and weather_string
        else:
            if self.time_start or self.time_pass:
                _xml += '<Time>\n'
                if self.time_start:
                    _xml += '<StartTime>'+self.time_start+'</StartTime>\n';
                if self.time_pass:
                    _xml += '<AllowPassageOfTime>'+self.time_pass+'</AllowPassageOfTime>\n';
                _xml += '</Time>\n'
            if self.weather:
                # "clear", "rain", "thunder"?
                _xml += '<Weather>'+self.weather+'</Weather>\n'
        if self.allowedmobs: self.spawning = "true"
        if self.spawning:
            # "false" or "true"
            _xml += '<AllowSpawning>'+self.spawning+'</AllowSpawning>\n'
            if allowedmobs_string:
                _xml += '<AllowedMobs>'+self.allowedmobs+'</AllowedMobs>\n' #e.g. "Pig Sheep"
        _xml += '</ServerInitialConditions>\n'
        return _xml


def flatworld(generatorString, forceReset="false"):
    return '<FlatWorldGenerator generatorString="' + generatorString + '" forceReset="' + forceReset + '"/>'

def defaultworld(seed=None, forceReset="false"):
    str = '<DefaultWorldGenerator '
    if seed:
        str += 'seed="' + seed + '" '
    if forceReset:
        str += 'forceReset="' + forceReset + '" '
    str += '/>'
    return str

def fileworld(uri2save, forceReset="false"):
    str = '<FileWorldGenerator '
    str += 'src="' + uri2save + '" '
    if forceReset:
        str += 'forceReset="' + forceReset + '" '
    str += '/>'
    return str


class ServerHandlers:
    
    def __init__(self, worldgenerator_xml=defaultworld(), drawingdecorator_xml=None,
                 bQuitAnyAgent=False, timeLimitsMs_string=None):
        self.worldgenerator = worldgenerator_xml
        self.drawingdecorator = drawingdecorator_xml
        self.bQuitAnyAgent = bQuitAnyAgent
        self.timeLimitsMs = timeLimitsMs_string

    def xml(self):
        _xml = '<ServerHandlers>\n' + self.worldgenerator + '\n'
        if self.drawingdecorator:
            _xml += '<DrawingDecorator>\n' + self.drawingdecorator + '\n</DrawingDecorator>\n'
        if self.bQuitAnyAgent:
            _xml += '<ServerQuitWhenAnyAgentFinishes />\n'
        if self.timeLimitsMs:
            _xml += '<ServerQuitFromTimeUp timeLimitMs="' + self.timeLimitsMs +\
                '" description="Time limit" />\n'
        _xml += '</ServerHandlers>\n'
        #<BuildBattleDecorator> --
        #<MazeDecorator> --
        return _xml


class ServerSection:

    def __init__(self, handlers=ServerHandlers(), initial_conditions=ServerInitialConditions()):
        self.handlers = handlers
        self.initial_conditions = initial_conditions
        
    def xml(self):
        return '<ServerSection>\n'+self.initial_conditions.xml()+self.handlers.xml()+'</ServerSection>\n'


class Commands:

    def __init__(self, bAll=True, bContinuous=None, bDiscrete=None, bInventory=None,
                 bSimpleCraft=None, bChat=None):
        self.bAll = bAll
        self.bContinuous = bContinuous
        self.bDiscrete = bDiscrete
        self.bInventory = bInventory
        self.bSimpleCraft = bSimpleCraft
        self.bChat = bChat

    def xml(self):
        _xml = ""
        if self.bAll or self.bContinuous:
            _xml += "<ContinuousMovementCommands turnSpeedDegs=\"420\"/>\n"
        if self.bAll or self.bDiscrete:
            _xml += "<DiscreteMovementCommands />\n"
        if self.bAll or self.bInventory:
            _xml += "<InventoryCommands />\n"
        if self.bAll or self.bSimpleCraft:
            _xml += "<SimpleCraftCommands />\n"
        if self.bAll or self.bChat:
            _xml += "<ChatCommands />\n"
        #<AbsoluteMovementCommands /> --
        #<MissionQuitCommands /> --
        #<HumanLevelCommands/> --
        return _xml


class Observations:

    def __init__(self, bAll=True, bRay=None, bFullStats=None, bHotBar=None, bNearby=None, bGrid=None):
        self.bAll = bAll
        self.bRay = bRay
        self.bFullStats = bFullStats
        self.bHotBar = bHotBar
        self.bNearby = bNearby
        self.bGrid = bGrid

    def xml(self):
        _xml = ""
        if (self.bAll or self.bRay) and not (self.bRay == False):
            _xml += "<ObservationFromRay />\n"
        if (self.bAll or self.bFullStats) and not (self.bFullStats == False):
            _xml += "<ObservationFromFullStats />\n"
        if (self.bAll or self.bHotBar) and not (self.bHotBar == False):
            _xml += "<ObservationFromHotBar />"
        if (self.bAll or self.bNearby) and not (self.bNearby == False):
            _xml += '''
<ObservationFromNearbyEntities>
    <Range name="r_close" xrange="2" yrange="2" zrange="2" update_frequency="1" />
    <Range name="r_far" xrange="20" yrange="10" zrange="20" update_frequency="100" />
</ObservationFromNearbyEntities>'''
        if (self.bAll or self.bGrid) and not (self.bGrid == False):
            _xml += '''
<ObservationFromGrid>
    <Grid name="g_nearby" absoluteCoords="false">
        <min x="-1" y="-1" z="-1"/>
        <max x="1" y="1" z="1"/>
    </Grid>
    <Grid name="g_far" absoluteCoords="false">
        <min x="-10" y="-10" z="-10"/>
        <max x="10" y="10" z="10"/>
    </Grid>
    <Grid name="very_far" absoluteCoords="false">
        <min x="-40" y="-40" z="-40"/>
        <max x="40" y="40" z="40"/>
    </Grid>
</ObservationFromGrid>
'''
        #<ObservationFromSubgoalPositionList> --
        #<ObservationFromDistance><Marker name="Start" x="0.5" y="227" z="0.5"/></ObservationFromDistance>
        return _xml


class AgentHandlers:

    def __init__(self, commands=Commands(), observations=Observations()):
        self.commands = commands
        self.observations = observations
        
    def xml(self):
        _xml = '<AgentHandlers>\n'
        _xml += self.commands.xml()
        _xml += self.observations.xml()
        _xml += '</AgentHandlers>\n'
        # <VideoProducer want_depth=... viewpoint=...> --
        # <DepthProducer> --
        # <ColourMapProducer> --
        # ...
        return _xml


class AgentStart:

    def __init__(self, place_xyzp=None, inventory_list=None):
        # place_xyzp format: [0.5, 1.0, 0.5, 0]
        self.place = place_xyzp
        self.inventory = inventory_list

    def xml(self):
        if self.place or self.inventory:
            _xml = '<AgentStart>\n';
            if self.place:
                _xml += '<Placement x="' + str(self.place[0]) + '" y="' + str(self.place[1]) +\
                    '" z="' + str(self.place[2]) + '" pitch="' + str(self.place[3]) + '\"/>\n'
            if self.inventory:
                _xml += '<Inventory>\n'
                for item in self.inventory:
                    _xml += '<InventoryItem type="'
                    if type(item) == list:
                        _xml += item[0] + '"'
                        if len(item) > 1: _xml += ' quantity="' + str(item[1]) + '"'
                        if len(item) > 2: _xml += ' slot="' + str(item[2]) + '"'
                    else: _xml += item + '"'
                    _xml += '/>\n'
                _xml += '</Inventory>\n'
            _xml += '</AgentStart>\n'
        else: _xml = '<AgentStart/>'
        return _xml


class AgentSection:

    def __init__(self, mode="Survival", name="Agent-0", agentstart=AgentStart(), agenthandlers=AgentHandlers()):
        self.mode = mode
        self.name = name
        self.agentstart = agentstart
        self.agenthandlers = agenthandlers

    def xml(self):
        _xml = '<AgentSection mode="' + self.mode + '">\n'
        _xml += '<Name>' + self.name + '</Name>\n'
        _xml += self.agentstart.xml()
        _xml += self.agenthandlers.xml()
        _xml += '</AgentSection>\n'
        return _xml


class MissionXML:

    def __init__(self, about=About(), serverSection=ServerSection(), agentSections=[AgentSection()]):
        self.about = about
        self.serverSection = serverSection
        self.agentSections = agentSections
    
    def setSummary(self, summary_string):
        self.about.summary = summary_string
    
    def setWorld(self, worldgenerator_xml):
        self.serverSection.handlers.worldgenerator = worldgenerator_xml
    
    def setTimeLimit(self, timeLimitMs):
        self.serverSection.handlers.timeLimitMs = str(timeLimitMs)
        
    def addAgent(self, nCount=1, agentSections=None):
        if agentSections:
            self.agentSections += agentSections
        else:
            for i in range(nCount):
                ag = AgentSection(name="Agent-"+str(len(self.agentSections)))
                self.agentSections += [ag]

    def setObservations(self, observations, nAgent=-1):
        if nAgent==-1:
            for ag in self.agentSections:
                ag.agenthandlers.observations = observations
        else:
            self.agentSections[nAgent].agenthandlers.observations = observations
    
    def getAgentNames(self):
        return [ag.name for ag in self.agentSections]

    def xml(self):
        _xml = '''<?xml version="1.0" encoding="UTF-8" ?>
<Mission xmlns="http://ProjectMalmo.microsoft.com" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
'''
        _xml += self.about.xml()
        _xml += self.serverSection.xml()
        for agentSection in self.agentSections:
            _xml += agentSection.xml()
        _xml += '</Mission>'
        return _xml
